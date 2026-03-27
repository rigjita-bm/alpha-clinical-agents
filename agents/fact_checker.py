"""
Fact Checker - Agent 3.5 (Hallucination Detection Layer)
Dedicated verification of factual claims against source documents
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from core.base_agent import BaseAgent
from core.logging_config import AgentLogger


@dataclass
class FactClaim:
    """Represents a factual claim extracted from text"""
    claim_text: str
    claim_type: str  # "number", "percentage", "p_value", "endpoint", "date"
    location: str    # Where in document
    confidence: float = 0.0
    verified: bool = False
    source: Optional[str] = None
    verification_method: str = ""


class FactChecker(BaseAgent):
    """
    Agent 3.5: Hallucination Detection Layer with NLI
    
    Detects and prevents hallucinations by:
    1. Extracting all factual claims from generated text
    2. Verifying each claim against source documents
    3. Using NLI (Natural Language Inference) for semantic verification
    4. Flagging unverified claims for human review
    5. Adding required citations
    
    Verification Methods:
    - Exact match: Claim found verbatim in source
    - Semantic match: NLI-based claim entailment
    - Calculation: Claim derived from source data
    - No source: Claim not found → HALLUCINATION FLAG
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(
            agent_id="FactChecker",
            version="2.0.0",  # Major version for NLI
            config=config
        )
        
        self.logger = AgentLogger("FactChecker")
        
        # Thresholds for verification
        self.exact_match_threshold = 0.95
        self.semantic_match_threshold = 0.85
        self.hallucination_threshold = 0.70
        
        # Initialize NLI model for semantic verification
        self.nli_model = None
        try:
            from sentence_transformers import CrossEncoder
            self.nli_model = CrossEncoder('cross-encoder/nli-deberta-v3-base')
            self.logger.info("nli_model_loaded", model="cross-encoder/nli-deberta-v3-base")
        except (ImportError, Exception) as e:
            self.logger.warning("nli_model_unavailable", error=str(e), fallback="embedding_similarity")
            # Fallback to sentence similarity
            try:
                from sentence_transformers import SentenceTransformer
                self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                self.similarity_model = None
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main fact-checking logic with NLI
        
        Args:
            input_data: {
                "draft_text": str,
                "section_name": str,
                "protocol_data": Dict,
                "statistical_data": Dict,
                "required_citations": bool
            }
            
        Returns:
            Verification report with hallucination flags
        """
        draft_text = input_data.get("draft_text", "")
        section_name = input_data.get("section_name", "")
        protocol_data = input_data.get("protocol_data", {})
        statistical_data = input_data.get("statistical_data", {})
        add_citations = input_data.get("required_citations", True)
        
        # Step 1: Extract all factual claims
        claims = self._extract_claims(draft_text, section_name)
        
        # Step 2: Verify each claim against sources
        verified_claims = []
        hallucinations = []
        
        for claim in claims:
            verification = self._verify_claim_with_nli(claim, protocol_data, statistical_data)
            
            if verification["is_verified"]:
                claim.verified = True
                claim.source = verification["source"]
                claim.verification_method = verification["method"]
                claim.confidence = verification["confidence"]
                verified_claims.append(claim)
            else:
                claim.verified = False
                hallucinations.append({
                    "claim": claim,
                    "confidence": verification.get("confidence", 0.0),
                    "reason": verification.get("reason", "No source found")
                })
        
        # Step 3: Add citations if requested
        cited_text = draft_text
        if add_citations and verified_claims:
            cited_text = self._add_citations(draft_text, verified_claims)
        
        # Calculate metrics
        total_claims = len(claims)
        verified_count = len(verified_claims)
        hallucination_count = len(hallucinations)
        hallucination_rate = hallucination_count / max(total_claims, 1)
        
        requires_human_review = (
            hallucination_rate > 0.10 or
            any(h["claim"].claim_type in ["p_value", "endpoint"] 
                for h in hallucinations)
        )
        
        return {
            "section_name": section_name,
            "original_text": draft_text,
            "cited_text": cited_text,
            "total_claims": total_claims,
            "verified_claims": verified_count,
            "hallucination_count": hallucination_count,
            "hallucination_rate": hallucination_rate,
            "claims": [self._claim_to_dict(c) for c in verified_claims],
            "hallucinations": hallucinations,
            "requires_human_review": requires_human_review,
            "verification_score": (verified_count / max(total_claims, 1)) * 100,
            "rationale": f"Fact-checked {total_claims} claims: {verified_count} verified, {hallucination_count} flagged",
            "nli_enabled": self.nli_model is not None
        }
    
    def _verify_claim_with_nli(
        self,
        claim: FactClaim,
        protocol_data: Dict,
        statistical_data: Dict
    ) -> Dict[str, Any]:
        """Verify claim using NLI or embedding similarity"""
        
        # First try exact match
        exact_result = self._verify_exact_match(claim, protocol_data, statistical_data)
        if exact_result["is_verified"]:
            return {**exact_result, "method": "exact_match", "confidence": 0.98}
        
        # Try semantic verification with NLI
        if self.nli_model:
            nli_result = self._verify_with_nli(claim, protocol_data, statistical_data)
            if nli_result["is_verified"]:
                return {**nli_result, "method": "nli_entailment"}
        
        # Fallback to embedding similarity
        if hasattr(self, 'similarity_model') and self.similarity_model:
            sim_result = self._verify_with_similarity(claim, protocol_data, statistical_data)
            if sim_result["is_verified"]:
                return {**sim_result, "method": "embedding_similarity"}
        
        # Not verified
        return {
            "is_verified": False,
            "confidence": 0.0,
            "reason": "No matching source found"
        }
    
    def _verify_with_nli(
        self,
        claim: FactClaim,
        protocol_data: Dict,
        statistical_data: Dict
    ) -> Dict[str, Any]:
        """Verify claim using NLI model (premise, hypothesis)"""
        # Build source text from protocol
        source_texts = self._build_source_texts(protocol_data, statistical_data)
        
        best_score = 0.0
        best_source = None
        
        for source_name, source_text in source_texts:
            # Truncate for efficiency
            source_chunks = self._chunk_text(source_text, max_length=512)
            
            for chunk in source_chunks:
                # NLI prediction: (premise=source, hypothesis=claim)
                prediction = self.nli_model.predict([(chunk, claim.claim_text)])
                
                # prediction is [[entailment, contradiction, neutral]]
                entailment_score = prediction[0][0]
                
                if entailment_score > best_score:
                    best_score = entailment_score
                    best_source = source_name
        
        # Threshold for verification
        if best_score >= self.semantic_match_threshold:
            return {
                "is_verified": True,
                "source": best_source,
                "confidence": best_score,
                "nli_score": float(best_score)
            }
        
        return {"is_verified": False, "confidence": best_score}
    
    def _verify_with_similarity(
        self,
        claim: FactClaim,
        protocol_data: Dict,
        statistical_data: Dict
    ) -> Dict[str, Any]:
        """Fallback: Use cosine similarity of embeddings"""
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        source_texts = self._build_source_texts(protocol_data, statistical_data)
        
        claim_embedding = self.similarity_model.encode([claim.claim_text])
        
        best_score = 0.0
        best_source = None
        
        for source_name, source_text in source_texts:
            source_embedding = self.similarity_model.encode([source_text[:500]])
            similarity = cosine_similarity(claim_embedding, source_embedding)[0][0]
            
            if similarity > best_score:
                best_score = similarity
                best_source = source_name
        
        if best_score >= self.semantic_match_threshold:
            return {
                "is_verified": True,
                "source": best_source,
                "confidence": best_score
            }
        
        return {"is_verified": False, "confidence": best_score}
    
    def _build_source_texts(self, protocol_data: Dict, statistical_data: Dict) -> List[Tuple[str, str]]:
        """Build list of (source_name, source_text) tuples"""
        sources = []
        
        # Protocol sections
        if protocol_data.get("study_design"):
            sources.append(("Protocol:StudyDesign", str(protocol_data["study_design"])))
        if protocol_data.get("endpoints"):
            sources.append(("Protocol:Endpoints", str(protocol_data["endpoints"])))
        if protocol_data.get("population"):
            sources.append(("Protocol:Population", str(protocol_data["population"])))
        
        # Statistical data
        if statistical_data:
            sources.append(("StatisticalOutput", str(statistical_data)))
        
        return sources
    
    def _chunk_text(self, text: str, max_length: int = 512) -> List[str]:
        """Split text into chunks for NLI"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1
            
            if current_length >= max_length:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks if chunks else [text]

    # Keep existing methods:
    # _extract_claims, _verify_exact_match, _verify_calculation, 
    # _add_citations, _claim_to_dict
        """
        Main fact-checking logic
        
        Args:
            input_data: {
                "draft_text": str,           # Text to verify
                "section_name": str,         # Which section
                "protocol_data": Dict,       # Source protocol
                "statistical_data": Dict,    # Optional SAS outputs
                "required_citations": bool   # Whether to add citations
            }
            
        Returns:
            Verification report with hallucination flags
        """
        draft_text = input_data.get("draft_text", "")
        section_name = input_data.get("section_name", "")
        protocol_data = input_data.get("protocol_data", {})
        statistical_data = input_data.get("statistical_data", {})
        add_citations = input_data.get("required_citations", True)
        
        # Step 1: Extract all factual claims
        claims = self._extract_claims(draft_text, section_name)
        
        # Step 2: Verify each claim against sources
        verified_claims = []
        hallucinations = []
        
        for claim in claims:
            verification = self._verify_claim(claim, protocol_data, statistical_data)
            
            if verification["is_verified"]:
                claim.verified = True
                claim.source = verification["source"]
                claim.verification_method = verification["method"]
                verified_claims.append(claim)
            else:
                claim.verified = False
                hallucinations.append({
                    "claim": claim,
                    "confidence": verification.get("confidence", 0.0),
                    "reason": verification.get("reason", "No source found")
                })
        
        # Step 3: Add citations if requested
        cited_text = draft_text
        if add_citations and verified_claims:
            cited_text = self._add_citations(draft_text, verified_claims)
        
        # Step 4: Calculate hallucination metrics
        total_claims = len(claims)
        verified_count = len(verified_claims)
        hallucination_count = len(hallucinations)
        
        hallucination_rate = hallucination_count / max(total_claims, 1)
        
        # Step 5: Determine if human review required
        requires_human_review = (
            hallucination_rate > 0.10 or  # >10% unverified claims
            any(h["claim"].claim_type in ["p_value", "endpoint"] 
                for h in hallucinations)  # Critical unverified facts
        )
        
        return {
            "section_name": section_name,
            "original_text": draft_text,
            "cited_text": cited_text,
            "total_claims": total_claims,
            "verified_claims": verified_count,
            "hallucination_count": hallucination_count,
            "hallucination_rate": hallucination_rate,
            "claims": [self._claim_to_dict(c) for c in verified_claims],
            "hallucinations": hallucinations,
            "requires_human_review": requires_human_review,
            "verification_score": (verified_count / max(total_claims, 1)) * 100,
            "rationale": f"Fact-checked {total_claims} claims: {verified_count} verified, {hallucination_count} flagged"
        }
    
    def _extract_claims(self, text: str, section_name: str) -> List[FactClaim]:
        """Extract all factual claims from text"""
        claims = []
        
        # Pattern 1: Sample sizes (n=XXX)
        n_pattern = r'(?:approximately|n\s*=|total of)\s*(\d+)\s*(?:patients|subjects)'
        for match in re.finditer(n_pattern, text, re.IGNORECASE):
            claims.append(FactClaim(
                claim_text=f"n={match.group(1)}",
                claim_type="sample_size",
                location=f"{section_name}:{match.start()}",
                confidence=0.95
            ))
        
        # Pattern 2: Percentages (XX%)
        pct_pattern = r'(\d+(?:\.\d+)?)%'
        for match in re.finditer(pct_pattern, text):
            # Context check - is it a factual claim?
            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 50)
            context = text[context_start:context_end].lower()
            
            if any(word in context for word in ['patients', 'response', 'adverse', 'survival']):
                claims.append(FactClaim(
                    claim_text=f"{match.group(1)}%",
                    claim_type="percentage",
                    location=f"{section_name}:{match.start()}",
                    confidence=0.90
                ))
        
        # Pattern 3: P-values (p=0.XXX or p<0.XXX)
        pvalue_pattern = r'p\s*(?:=|<|>)\s*(0?\.\d+|\d+e-\d+)'
        for match in re.finditer(pvalue_pattern, text, re.IGNORECASE):
            claims.append(FactClaim(
                claim_text=match.group(0),
                claim_type="p_value",
                location=f"{section_name}:{match.start()}",
                confidence=0.98  # High confidence because critical
            ))
        
        # Pattern 4: Hazard Ratios (HR=X.XX)
        hr_pattern = r'HR\s*=\s*(\d+\.\d+)'
        for match in re.finditer(hr_pattern, text, re.IGNORECASE):
            claims.append(FactClaim(
                claim_text=f"HR={match.group(1)}",
                claim_type="hazard_ratio",
                location=f"{section_name}:{match.start()}",
                confidence=0.95
            ))
        
        # Pattern 5: Phase (Phase I/II/III/IV)
        phase_pattern = r'Phase\s+([IV]{1,3})'
        for match in re.finditer(phase_pattern, text, re.IGNORECASE):
            claims.append(FactClaim(
                claim_text=f"Phase {match.group(1)}",
                claim_type="phase",
                location=f"{section_name}:{match.start()}",
                confidence=0.95
            ))
        
        # Pattern 6: Endpoint mentions
        endpoint_keywords = [
            "overall survival", "progression-free survival", "objective response rate",
            "duration of response", "disease-free survival"
        ]
        text_lower = text.lower()
        for endpoint in endpoint_keywords:
            if endpoint in text_lower:
                # Find position
                pos = text_lower.find(endpoint)
                claims.append(FactClaim(
                    claim_text=endpoint.title(),
                    claim_type="endpoint",
                    location=f"{section_name}:{pos}",
                    confidence=0.90
                ))
        
        # Pattern 7: Confidence Intervals (95% CI: X.XX-X.XX)
        ci_pattern = r'95%\s*CI[:\s]+(\d+\.\d+)[\s\-–]+(\d+\.\d+)'
        for match in re.finditer(ci_pattern, text, re.IGNORECASE):
            claims.append(FactClaim(
                claim_text=f"95% CI: {match.group(1)}-{match.group(2)}",
                claim_type="confidence_interval",
                location=f"{section_name}:{match.start()}",
                confidence=0.95
            ))
        
        return claims
    
    def _verify_claim(self, claim: FactClaim, 
                     protocol_data: Dict, 
                     statistical_data: Dict) -> Dict:
        """Verify a single claim against sources"""
        
        # Check 1: Protocol exact match
        protocol_text = str(protocol_data)
        if claim.claim_text.lower() in protocol_text.lower():
            return {
                "is_verified": True,
                "source": "Protocol",
                "method": "exact_match",
                "confidence": 0.95
            }
        
        # Check 2: Protocol semantic match (simplified)
        if self._semantic_match(claim, protocol_data):
            return {
                "is_verified": True,
                "source": "Protocol",
                "method": "semantic_match",
                "confidence": 0.85
            }
        
        # Check 3: Statistical data match
        if statistical_data:
            stat_verification = self._verify_against_statistical_data(claim, statistical_data)
            if stat_verification["is_verified"]:
                return stat_verification
        
        # Check 4: Type-specific verification
        type_verification = self._verify_by_type(claim, protocol_data)
        if type_verification["is_verified"]:
            return type_verification
        
        # Not verified → potential hallucination
        return {
            "is_verified": False,
            "source": None,
            "method": "none",
            "confidence": 0.3,
            "reason": f"Claim '{claim.claim_text}' not found in source documents"
        }
    
    def _semantic_match(self, claim: FactClaim, protocol_data: Dict) -> bool:
        """Check if claim is semantically supported by protocol"""
        # Simplified: check for related terms
        claim_lower = claim.claim_text.lower()
        protocol_str = str(protocol_data).lower()
        
        # Sample size checks
        if claim.claim_type == "sample_size":
            n_value = re.search(r'(\d+)', claim.claim_text)
            if n_value:
                return n_value.group(1) in protocol_str
        
        # Phase checks
        if claim.claim_type == "phase":
            phase = re.search(r'phase\s+([iv]+)', claim_lower)
            if phase:
                return phase.group(1) in protocol_str
        
        return False
    
    def _verify_against_statistical_data(self, claim: FactClaim, 
                                        statistical_data: Dict) -> Dict:
        """Verify statistical claims against SAS outputs"""
        
        # P-value verification
        if claim.claim_type == "p_value":
            p_value = re.search(r'0?\.(\d+)', claim.claim_text)
            if p_value:
                # Check if this p-value exists in statistical outputs
                stat_str = str(statistical_data)
                if claim.claim_text in stat_str:
                    return {
                        "is_verified": True,
                        "source": "Statistical Output",
                        "method": "exact_match",
                        "confidence": 0.98
                    }
        
        # Hazard ratio verification
        if claim.claim_type == "hazard_ratio":
            hr_value = re.search(r'(\d+\.\d+)', claim.claim_text)
            if hr_value:
                stat_str = str(statistical_data)
                if hr_value.group(1) in stat_str:
                    return {
                        "is_verified": True,
                        "source": "Statistical Output",
                        "method": "exact_match",
                        "confidence": 0.95
                    }
        
        return {"is_verified": False}
    
    def _verify_by_type(self, claim: FactClaim, protocol_data: Dict) -> Dict:
        """Type-specific verification logic"""
        
        # Endpoint verification
        if claim.claim_type == "endpoint":
            endpoints = protocol_data.get("endpoints", {})
            primary = [e.lower() for e in endpoints.get("primary", [])]
            secondary = [e.lower() for e in endpoints.get("secondary", [])]
            
            claim_endpoint = claim.claim_text.lower()
            
            if any(claim_endpoint in pe for pe in primary):
                return {
                    "is_verified": True,
                    "source": "Protocol: Primary Endpoint",
                    "method": "endpoint_match",
                    "confidence": 0.95
                }
            
            if any(claim_endpoint in se for se in secondary):
                return {
                    "is_verified": True,
                    "source": "Protocol: Secondary Endpoint",
                    "method": "endpoint_match",
                    "confidence": 0.90
                }
        
        return {"is_verified": False}
    
    def _add_citations(self, text: str, verified_claims: List[FactClaim]) -> str:
        """Add inline citations to verified claims"""
        cited_text = text
        
        for claim in verified_claims:
            if claim.source:
                # Simple citation format: [Source: Protocol]
                # In production, would be more sophisticated
                pass
        
        # Add references section at end
        if verified_claims:
            cited_text += "\n\n---\nReferences:\n"
            sources = set(c.source for c in verified_claims if c.source)
            for source in sorted(sources):
                cited_text += f"• {source}\n"
        
        return cited_text
    
    def _claim_to_dict(self, claim: FactClaim) -> Dict:
        """Convert claim to dictionary"""
        return {
            "claim_text": claim.claim_text,
            "claim_type": claim.claim_type,
            "location": claim.location,
            "verified": claim.verified,
            "source": claim.source,
            "verification_method": claim.verification_method
        }
    
    def detect_hallucination_risk(self, draft_text: str) -> Dict[str, Any]:
        """
        Quick risk assessment for hallucination potential
        Returns risk score and flagged phrases
        """
        risk_indicators = []
        
        # High-risk patterns
        risky_patterns = [
            (r"\b(significant|significantly)\b", "Significance claim without p-value"),
            (r"\b(improved|benefit|effective)\b", "Efficacy claim without data"),
            (r"\b(safe|well.tolerated)\b", "Safety claim without AE data"),
        ]
        
        for pattern, description in risky_patterns:
            matches = list(re.finditer(pattern, draft_text, re.IGNORECASE))
            for match in matches:
                # Check if supported by statistical data nearby
                context = draft_text[max(0, match.start()-100):min(len(draft_text), match.end()+100)]
                if not re.search(r'p[=\u003c\u003e]|HR[=\u003c\u003e]|\d+%|\d+ patients', context):
                    risk_indicators.append({
                        "phrase": match.group(0),
                        "location": match.start(),
                        "description": description,
                        "risk_level": "HIGH"
                    })
        
        risk_score = len(risk_indicators) * 10  # 0-100 scale
        
        return {
            "risk_score": min(risk_score, 100),
            "risk_level": "HIGH" if risk_score > 50 else "MEDIUM" if risk_score > 20 else "LOW",
            "indicators": risk_indicators,
            "recommendation": "Add statistical support" if risk_indicators else "No immediate risk"
        }


# Demo/test
if __name__ == "__main__":
    # Sample draft with intentional hallucination
    sample_draft = """11. STUDY RESULTS

A total of 599 patients were randomized. The primary endpoint of Overall Survival 
showed a significant benefit with a hazard ratio of 0.72 (95% CI: 0.58-0.89, p=0.003).

The response rate was 45% in the treatment group compared to 25% in the control group.
Treatment was well-tolerated with no new safety signals."""
    
    # Sample protocol data (for verification)
    protocol_data = {
        "study_design": {"phase": "III"},
        "population": {"planned_enrollment": 600},
        "endpoints": {
            "primary": ["Overall Survival (OS)"],
            "secondary": ["Progression-Free Survival (PFS)"]
        }
    }
    
    # Sample statistical data (what we actually have)
    statistical_data = {
        "primary_analysis": {
            "hazard_ratio": 0.72,
            "ci_lower": 0.58,
            "ci_upper": 0.89,
            "p_value": 0.003
        },
        "response_rates": {
            "treatment": 0.42,  # Note: 42%, not 45% (hallucination!)
            "control": 0.25
        }
    }
    
    # Run fact checker
    checker = FactChecker()
    result = checker.execute({
        "draft_text": sample_draft,
        "section_name": "Results",
        "protocol_data": protocol_data,
        "statistical_data": statistical_data,
        "required_citations": True
    })
    
    # Display results
    import json
    print("=" * 70)
    print("FACT CHECKER - HALLUCINATION DETECTION REPORT")
    print("=" * 70)
    
    print(f"\n📊 Summary:")
    print(f"   Total claims found: {result['total_claims']}")
    print(f"   ✅ Verified: {result['verified_claims']}")
    print(f"   ⚠️  Hallucinations flagged: {result['hallucination_count']}")
    print(f"   📉 Hallucination rate: {result['hallucination_rate']:.1%}")
    print(f"   🎯 Verification score: {result['verification_score']:.0f}/100")
    
    print(f"\n{'─' * 70}")
    print("VERIFIED CLAIMS:")
    print('─' * 70)
    
    for claim in result['claims']:
        icon = "✅" if claim['verified'] else "❌"
        print(f"{icon} {claim['claim_type']}: '{claim['claim_text']}'")
        print(f"   Source: {claim['source']} ({claim['verification_method']})")
    
    if result['hallucinations']:
        print(f"\n{'─' * 70}")
        print("🚨 HALLUCINATIONS DETECTED:")
        print('─' * 70)
        
        for hal in result['hallucinations']:
            claim = hal['claim']
            print(f"❌ {claim.claim_type}: '{claim.claim_text}'")
            print(f"   Reason: {hal['reason']}")
            print(f"   Location: {claim.location}")
            print()
    
    print(f"\n{'─' * 70}")
    print(f"HUMAN REVIEW REQUIRED: {'YES ⚠️' if result['requires_human_review'] else 'NO ✅'}")
    print("=" * 70)
    
    # Risk assessment
    print("\n" + "=" * 70)
    print("RISK ASSESSMENT")
    print("=" * 70)
    risk = checker.detect_hallucination_risk(sample_draft)
    print(f"Risk Score: {risk['risk_score']}/100 ({risk['risk_level']})")
    print(f"Recommendation: {risk['recommendation']}")
    
    if risk['indicators']:
        print("\nRisk Indicators:")
        for indicator in risk['indicators']:
            print(f"  ⚠️  '{indicator['phrase']}': {indicator['description']}")
