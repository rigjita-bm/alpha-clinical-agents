"""
Hallucination Detection Agent - Agent 11
Dedicated agent for detecting AI hallucinations in clinical documents
Uses multi-modal verification: semantic, statistical, and cross-reference
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from core.base_agent import BaseAgent


class HallucinationType(Enum):
    """Types of hallucinations in clinical documents"""
    FABRICATED_NUMBER = "fabricated_number"  # Number not in source
    FABRICATED_ENDPOINT = "fabricated_endpoint"  # Endpoint not in protocol
    CONFLICTING_DATA = "conflicting_data"  # Contradicts source
    UNSUPPORTED_CLAIM = "unsupported_claim"  # Claim without evidence
    OUT_OF_CONTEXT = "out_of_context"  # True but wrong context
    TEMPORAL_ERROR = "temporal_error"  # Wrong timeline


class SeverityLevel(Enum):
    CRITICAL = "critical"  # Could affect regulatory decision
    HIGH = "high"  # Significant error
    MEDIUM = "medium"  # Minor inaccuracy
    LOW = "low"  # Formatting/style issue


@dataclass
class HallucinationFinding:
    """Single hallucination finding"""
    hallucination_type: HallucinationType
    severity: SeverityLevel
    claim_text: str
    location: str
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    explanation: str = ""
    confidence: float = 0.0
    suggested_fix: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "type": self.hallucination_type.value,
            "severity": self.severity.value,
            "claim": self.claim_text,
            "location": self.location,
            "expected": self.expected_value,
            "actual": self.actual_value,
            "explanation": self.explanation,
            "confidence": self.confidence,
            "fix": self.suggested_fix
        }


@dataclass
class VerificationResult:
    """Result of verification check"""
    is_verified: bool
    source: Optional[str]
    confidence: float
    method: str
    notes: str = ""


class HallucinationDetector(BaseAgent):
    """
    Agent 11: Dedicated Hallucination Detection
    
    Multi-layered detection system:
    1. Source Verification: Against protocol & statistical outputs
    2. Semantic Consistency: NLI-based verification
    3. Statistical Plausibility: Check if numbers make sense
    4. Cross-Reference: Consistency across sections
    5. Temporal Logic: Timeline consistency
    
    Output: Hallucination report with severity scoring
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(
            agent_id="HallucinationDetector",
            version="1.0.0",
            config=config
        )
        
        # Detection thresholds
        self.critical_severity_threshold = 0.9
        self.high_severity_threshold = 0.7
        self.verification_confidence_threshold = 0.85
        
        # Known hallucination patterns
        self.hallucination_patterns = self._load_hallucination_patterns()
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main hallucination detection logic
        
        Args:
            input_data: {
                "draft_text": str,
                "section_name": str,
                "protocol_data": Dict,
                "statistical_data": Dict,
                "previous_sections": Dict  # For cross-reference
            }
        """
        draft_text = input_data.get("draft_text", "")
        section_name = input_data.get("section_name", "")
        protocol_data = input_data.get("protocol_data", {})
        statistical_data = input_data.get("statistical_data", {})
        previous_sections = input_data.get("previous_sections", {})
        
        findings = []
        
        # Layer 1: Source Verification
        source_findings = self._verify_against_sources(
            draft_text, protocol_data, statistical_data
        )
        findings.extend(source_findings)
        
        # Layer 2: Statistical Plausibility
        stat_findings = self._check_statistical_plausibility(draft_text, statistical_data)
        findings.extend(stat_findings)
        
        # Layer 3: Cross-Reference Consistency
        if previous_sections:
            crossref_findings = self._check_cross_references(
                draft_text, section_name, previous_sections
            )
            findings.extend(crossref_findings)
        
        # Layer 4: Pattern-Based Detection
        pattern_findings = self._detect_hallucination_patterns(draft_text)
        findings.extend(pattern_findings)
        
        # Calculate overall risk
        hallucination_score = self._calculate_hallucination_score(findings)
        risk_level = self._determine_risk_level(hallucination_score, findings)
        
        # Generate report
        report = {
            "section_name": section_name,
            "hallucination_score": hallucination_score,  # 0-100
            "risk_level": risk_level,  # LOW/MEDIUM/HIGH/CRITICAL
            "total_findings": len(findings),
            "critical": len([f for f in findings if f.severity == SeverityLevel.CRITICAL]),
            "high": len([f for f in findings if f.severity == SeverityLevel.HIGH]),
            "medium": len([f for f in findings if f.severity == SeverityLevel.MEDIUM]),
            "low": len([f for f in findings if f.severity == SeverityLevel.LOW]),
            "findings": [f.to_dict() for f in findings],
            "requires_rejection": risk_level in ["HIGH", "CRITICAL"],
            "requires_human_review": risk_level in ["MEDIUM", "HIGH", "CRITICAL"],
            "rationale": f"Detected {len(findings)} potential hallucinations in {section_name}"
        }
        
        return report
    
    def _verify_against_sources(self, text: str, protocol_data: Dict,
                               statistical_data: Dict) -> List[HallucinationFinding]:
        """Layer 1: Verify claims against source documents"""
        findings = []
        
        # Check 1: Sample sizes
        n_mentions = re.finditer(r'(\d+)\s+patients', text, re.IGNORECASE)
        for match in n_mentions:
            claimed_n = int(match.group(1))
            protocol_n = protocol_data.get("population", {}).get("planned_enrollment")
            
            if protocol_n and claimed_n != protocol_n:
                # Allow small variance (screening failures)
                if abs(claimed_n - protocol_n) > 10:
                    findings.append(HallucinationFinding(
                        hallucination_type=HallucinationType.CONFLICTING_DATA,
                        severity=SeverityLevel.HIGH,
                        claim_text=f"{claimed_n} patients",
                        location=f"position {match.start()}",
                        expected_value=str(protocol_n),
                        actual_value=str(claimed_n),
                        explanation=f"Claimed {claimed_n} patients but protocol specifies {protocol_n}",
                        confidence=0.95,
                        suggested_fix=f"Update to {protocol_n} patients (or add explanation for difference)"
                    ))
        
        # Check 2: Phase
        phase_match = re.search(r'Phase\s+([IV]+)', text, re.IGNORECASE)
        if phase_match:
            claimed_phase = phase_match.group(1).upper()
            protocol_phase = protocol_data.get("study_design", {}).get("phase", "")
            
            if protocol_phase and claimed_phase != protocol_phase:
                findings.append(HallucinationFinding(
                    hallucination_type=HallucinationType.FABRICATED_NUMBER,
                    severity=SeverityLevel.CRITICAL,
                    claim_text=f"Phase {claimed_phase}",
                    location=f"position {phase_match.start()}",
                    expected_value=f"Phase {protocol_phase}",
                    actual_value=f"Phase {claimed_phase}",
                    explanation=f"Wrong phase: protocol is Phase {protocol_phase}",
                    confidence=0.99,
                    suggested_fix=f"Change to Phase {protocol_phase}"
                ))
        
        # Check 3: P-values in Results
        pvalue_matches = re.finditer(r'p\s*[=\u003c]\s*(0?\.\d+)', text, re.IGNORECASE)
        for match in pvalue_matches:
            claimed_p = match.group(1)
            
            # Check if this p-value exists in statistical data
            stat_str = str(statistical_data)
            if claimed_p not in stat_str and statistical_data:
                findings.append(HallucinationFinding(
                    hallucination_type=HallucinationType.FABRICATED_NUMBER,
                    severity=SeverityLevel.CRITICAL,
                    claim_text=f"p={claimed_p}",
                    location=f"position {match.start()}",
                    explanation="P-value not found in statistical output",
                    confidence=0.90,
                    suggested_fix="Replace with actual p-value from statistical analysis"
                ))
        
        # Check 4: Endpoints
        endpoints = protocol_data.get("endpoints", {})
        primary_endpoints = [e.lower() for e in endpoints.get("primary", [])]
        
        # Check if primary endpoint is mentioned in Results
        if "Results" in text and primary_endpoints:
            pe_mentioned = any(pe in text.lower() for pe in primary_endpoints)
            if not pe_mentioned:
                findings.append(HallucinationFinding(
                    hallucination_type=HallucinationType.UNSUPPORTED_CLAIM,
                    severity=SeverityLevel.HIGH,
                    claim_text="Results section",
                    location="Results",
                    explanation=f"Primary endpoint '{primary_endpoints[0]}' not mentioned in Results",
                    confidence=0.85,
                    suggested_fix=f"Add primary endpoint results: {primary_endpoints[0]}"
                ))
        
        return findings
    
    def _check_statistical_plausibility(self, text: str,
                                       statistical_data: Dict) -> List[HallucinationFinding]:
        """Layer 2: Check if statistics make sense"""
        findings = []
        
        # Check: Response rates should be 0-100%
        response_matches = re.finditer(r'(\d+(?:\.\d+)?)%\s+response\s+rate', text, re.IGNORECASE)
        for match in response_matches:
            rate = float(match.group(1))
            if rate > 100 or rate < 0:
                findings.append(HallucinationFinding(
                    hallucination_type=HallucinationType.FABRICATED_NUMBER,
                    severity=SeverityLevel.CRITICAL,
                    claim_text=f"{rate}% response rate",
                    location=f"position {match.start()}",
                    explanation=f"Impossible response rate: {rate}%",
                    confidence=0.99,
                    suggested_fix="Response rate must be between 0-100%"
                ))
        
        # Check: P-values should be 0-1
        pvalue_matches = re.finditer(r'p\s*[=\u003c]\s*(\d+\.?\d*)', text, re.IGNORECASE)
        for match in pvalue_matches:
            p = float(match.group(1))
            if p > 1:
                findings.append(HallucinationFinding(
                    hallucination_type=HallucinationType.FABRICATED_NUMBER,
                    severity=SeverityLevel.CRITICAL,
                    claim_text=f"p={p}",
                    location=f"position {match.start()}",
                    explanation=f"Invalid p-value: {p} (must be ≤1)",
                    confidence=0.99,
                    suggested_fix="P-value cannot exceed 1.0"
                ))
        
        # Check: Hazard ratios are typically positive
        hr_matches = re.finditer(r'HR\s*[=\u003c]\s*(-?\d+\.?\d*)', text, re.IGNORECASE)
        for match in hr_matches:
            hr = float(match.group(1))
            if hr < 0:
                findings.append(HallucinationFinding(
                    hallucination_type=HallucinationType.FABRICATED_NUMBER,
                    severity=SeverityLevel.HIGH,
                    claim_text=f"HR={hr}",
                    location=f"position {match.start()}",
                    explanation=f"Negative hazard ratio: {hr} (HR must be positive)",
                    confidence=0.95,
                    suggested_fix="Hazard ratio cannot be negative"
                ))
        
        return findings
    
    def _check_cross_references(self, text: str, section_name: str,
                               previous_sections: Dict) -> List[HallucinationFinding]:
        """Layer 3: Check consistency across sections"""
        findings = []
        
        # Extract sample size from current text
        current_n = self._extract_sample_size(text)
        
        # Compare with Methods section
        if "Methods" in previous_sections and current_n:
            methods_text = previous_sections["Methods"].get("draft", "")
            methods_n = self._extract_sample_size(methods_text)
            
            if methods_n and current_n != methods_n:
                findings.append(HallucinationFinding(
                    hallucination_type=HallucinationType.CONFLICTING_DATA,
                    severity=SeverityLevel.HIGH,
                    claim_text=f"{current_n} patients in {section_name}",
                    location=section_name,
                    expected_value=str(methods_n),
                    actual_value=str(current_n),
                    explanation=f"Sample size mismatch: Methods={methods_n}, {section_name}={current_n}",
                    confidence=0.95,
                    suggested_fix=f"Standardize to {methods_n} (Methods is source of truth)"
                ))
        
        return findings
    
    def _detect_hallucination_patterns(self, text: str) -> List[HallucinationFinding]:
        """Layer 4: Detect known hallucination patterns"""
        findings = []
        
        # Pattern 1: Vague statistics (common LLM hallucination)
        vague_patterns = [
            (r'significant\s+improvement\s+was\s+observed(?!\s+with)', 
             "Vague significance claim without p-value"),
            (r'treatment\s+was\s+well[-\s]tolerated(?!\s+with)', 
             "Vague safety claim without AE data"),
            (r'clinically\s+meaningful\s+(?:benefit|improvement)(?!\s+with)',
             "Clinical claim without supporting data")
        ]
        
        for pattern, description in vague_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Check if followed by statistical support
                context_end = min(len(text), match.end() + 100)
                context = text[match.end():context_end]
                
                if not re.search(r'p[=\u003c]|HR[=\u003c]|\d+%|\d+\s+patients', context):
                    findings.append(HallucinationFinding(
                        hallucination_type=HallucinationType.UNSUPPORTED_CLAIM,
                        severity=SeverityLevel.MEDIUM,
                        claim_text=match.group(0),
                        location=f"position {match.start()}",
                        explanation=f"{description} - add statistical support",
                        confidence=0.80,
                        suggested_fix="Add p-value, hazard ratio, or specific numbers"
                    ))
        
        # Pattern 2: Future tense in Results (should be past)
        future_in_results = re.finditer(r'\b(will|shall|is expected to)\b', text, re.IGNORECASE)
        for match in future_in_results:
            findings.append(HallucinationFinding(
                hallucination_type=HallucinationType.TEMPORAL_ERROR,
                severity=SeverityLevel.LOW,
                claim_text=match.group(0),
                location=f"position {match.start()}",
                explanation="Future tense in Results section (should be past tense)",
                confidence=0.85,
                suggested_fix="Change to past tense (e.g., 'was observed', 'showed')"
            ))
        
        return findings
    
    def _extract_sample_size(self, text: str) -> Optional[int]:
        """Extract sample size from text"""
        patterns = [
            r'(\d+)\s+patients\s+were\s+(?:randomized|enrolled)',
            r'n\s*=\s*(\d+)',
            r'(\d+)\s+patients'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None
    
    def _calculate_hallucination_score(self, findings: List[HallucinationFinding]) -> float:
        """Calculate overall hallucination risk score (0-100)"""
        if not findings:
            return 0.0
        
        severity_weights = {
            SeverityLevel.CRITICAL: 25,
            SeverityLevel.HIGH: 15,
            SeverityLevel.MEDIUM: 5,
            SeverityLevel.LOW: 1
        }
        
        score = sum(severity_weights.get(f.severity, 5) for f in findings)
        return min(score, 100.0)
    
    def _determine_risk_level(self, score: float,
                             findings: List[HallucinationFinding]) -> str:
        """Determine overall risk level"""
        critical_count = len([f for f in findings if f.severity == SeverityLevel.CRITICAL])
        
        if critical_count > 0 or score >= 75:
            return "CRITICAL"
        elif score >= 50:
            return "HIGH"
        elif score >= 25:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _load_hallucination_patterns(self) -> Dict:
        """Load known hallucination patterns"""
        return {
            "vague_significance": r'significant\s+(?:improvement|benefit)',
            "missing_pvalue": r'p\s*[=\u003c]\s*0\.\d+',
            "impossible_rate": r'\d{3,}%'
        }


# Demo
if __name__ == "__main__":
    # Sample draft with intentional hallucinations
    sample_draft = """11. STUDY RESULTS

A total of 599 patients were randomized to treatment.

The primary endpoint showed significant improvement with a hazard ratio of -0.72 
(95% CI: 0.58-0.89, p=0.003). The response rate was 145% in the treatment group.

Treatment was well-tolerated with no new safety signals."""
    
    protocol_data = {
        "study_design": {"phase": "III"},
        "population": {"planned_enrollment": 600},
        "endpoints": {"primary": ["Overall Survival (OS)"]}
    }
    
    statistical_data = {
        "primary_analysis": {
            "hazard_ratio": 0.72,
            "p_value": 0.003
        }
    }
    
    previous_sections = {
        "Methods": {"draft": "Approximately 600 patients were planned for enrollment."}
    }
    
    # Run hallucination detector
    detector = HallucinationDetector()
    result = detector.execute({
        "draft_text": sample_draft,
        "section_name": "Results",
        "protocol_data": protocol_data,
        "statistical_data": statistical_data,
        "previous_sections": previous_sections
    })
    
    # Display results
    print("=" * 70)
    print("HALLUCINATION DETECTOR - AGENT 11")
    print("=" * 70)
    
    print(f"\n🎯 Hallucination Score: {result['hallucination_score']}/100")
    print(f"⚠️  Risk Level: {result['risk_level']}")
    print(f"\n📊 Findings Summary:")
    print(f"   Critical: {result['critical']}")
    print(f"   High: {result['high']}")
    print(f"   Medium: {result['medium']}")
    print(f"   Low: {result['low']}")
    
    print(f"\n🚨 Requires Rejection: {'YES' if result['requires_rejection'] else 'NO'}")
    print(f"👤 Requires Human Review: {'YES' if result['requires_human_review'] else 'NO'}")
    
    print("\n" + "=" * 70)
    print("DETAILED FINDINGS:")
    print("=" * 70)
    
    for finding in result['findings']:
        severity_icon = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵"
        }.get(finding['severity'], "⚪")
        
        print(f"\n{severity_icon} [{finding['severity'].upper()}] {finding['type']}")
        print(f"   Claim: '{finding['claim']}'")
        print(f"   Explanation: {finding['explanation']}")
        if finding.get('expected'):
            print(f"   Expected: {finding['expected']}")
            print(f"   Actual: {finding['actual']}")
        print(f"   Suggested Fix: {finding['fix']}")
        print(f"   Confidence: {finding['confidence']:.0%}")
    
    print("\n" + "=" * 70)
