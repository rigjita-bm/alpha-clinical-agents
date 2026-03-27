"""
Protocol Analyzer - Agent 1
Extracts structured study design from clinical protocol documents
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from core.base_agent import BaseAgent
from core.logging_config import AgentLogger


class ProtocolAnalyzer(BaseAgent):
    """
    Agent 1: Protocol Intelligence with NLP
    
    Extracts structured information from clinical protocol documents using:
    - Regex patterns for structured data
    - spaCy NER for medical entities (optional)
    - Section classification
    - Complexity scoring for downstream RiskPredictor
    
    Output: Structured JSON for downstream agents
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(
            agent_id="ProtocolAnalyzer",
            version="3.0.0",
            config=config
        )
        
        self.logger = AgentLogger("ProtocolAnalyzer")
        
        # Try to load spaCy for enhanced NLP
        self.nlp = None
        try:
            import spacy
            # Use small model for speed, can upgrade to en_core_sci_sm for medical
            self.nlp = spacy.load("en_core_web_sm")
            self.logger.info("spacy_loaded", model="en_core_web_sm")
        except (ImportError, OSError):
            self.logger.warning("spacy_not_available", fallback="regex_only")
        
        # Compile regex patterns for efficiency
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for protocol extraction"""
        return {
            "phase": re.compile(r'Phase\s*(I{1,3}V?|IV|One|Two|Three|Four)', re.IGNORECASE),
            "n_value": re.compile(r'(N\s*=\s*|enroll|planned|target)\s*[:\s]*([0-9,]+)', re.IGNORECASE),
            "primary_endpoint": re.compile(
                r'primary\s+endpoint[s]?[:\s]*([^\n]+?)(?=secondary|\.\s|$)',
                re.IGNORECASE | re.DOTALL
            ),
            "alpha": re.compile(r'alpha\s*=\s*(0\.\d+)', re.IGNORECASE),
            "power": re.compile(r'power\s*(?:of\s*)?(\d+)%', re.IGNORECASE),
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing logic for protocol analysis
        
        Args:
            input_data: {
                "protocol_text": str,
                "protocol_format": str,  # "pdf", "docx", "text"
                "use_nlp": bool  # Whether to use spaCy enhancement
            }
            
        Returns:
            Structured study design JSON
        """
        protocol_text = input_data.get("protocol_text", "")
        use_nlp = input_data.get("use_nlp", True)
        
        if not protocol_text or len(protocol_text) < 100:
            return {
                "error": "Insufficient protocol text",
                "extraction_confidence": 0.0,
                "study_design": {},
                "endpoints": {},
                "population": {},
                "complexity_score": 0.0
            }
        
        self.logger.info("protocol_analysis_started", text_length=len(protocol_text))
        
        # Extract structured information
        study_design = self._extract_study_design(protocol_text, use_nlp)
        endpoints = self._extract_endpoints(protocol_text, use_nlp)
        population = self._extract_population(protocol_text)
        schedule = self._extract_schedule(protocol_text)
        statistics = self._extract_statistical_methods(protocol_text)
        
        # Compute complexity score
        complexity_score = self._compute_complexity(
            study_design, endpoints, population, statistics
        )
        
        # Calculate extraction confidence
        confidence = self._calculate_confidence(
            study_design, endpoints, population, statistics
        )
        
        result = {
            "study_design": study_design,
            "endpoints": endpoints,
            "population": population,
            "schedule": schedule,
            "statistical_methods": statistics,
            "complexity_score": complexity_score,
            "extraction_confidence": confidence,
            "rationale": f"Extracted using {'NLP+regex' if (use_nlp and self.nlp) else 'regex-only'} from {len(protocol_text)} characters",
            "extraction_metadata": {
                "text_length": len(protocol_text),
                "nlp_used": use_nlp and self.nlp is not None,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        self.logger.info(
            "protocol_analysis_complete",
            confidence=confidence,
            complexity=complexity_score,
            phase=study_design.get("phase", "unknown")
        )
        
        return result
    
    def _extract_study_design(self, text: str, use_nlp: bool) -> Dict[str, Any]:
        """Extract study design elements with NLP enhancement"""
        design = {
            "phase": self._extract_phase(text),
            "study_type": self._extract_study_type(text),
            "randomization": self._extract_randomization(text),
            "blinding": self._extract_blinding(text),
            "control_type": self._extract_control_type(text)
        }
        
        # NLP enhancement for study type classification
        if use_nlp and self.nlp:
            doc = self.nlp(text[:50000])  # Limit for performance
            
            # Extract named entities that might be relevant
            organizations = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
            if organizations:
                design["sponsor_hints"] = organizations[:3]
        
        return design
    
    def _extract_phase(self, text: str) -> str:
        """Extract study phase with multiple pattern matching"""
        # Try primary pattern
        match = self.patterns["phase"].search(text[:5000])  # Usually in first pages
        if match:
            phase = match.group(1).upper()
            # Normalize
            phase_map = {"ONE": "I", "TWO": "II", "THREE": "III", "FOUR": "IV"}
            return phase_map.get(phase, phase)
        
        # Fallback: look for phase mention
        for phase, pattern in [
            ("I", r'\bphase\s+1\b|\bphase\s+i\b'),
            ("II", r'\bphase\s+2\b|\bphase\s+ii\b'),
            ("III", r'\bphase\s+3\b|\bphase\s+iii\b'),
            ("IV", r'\bphase\s+4\b|\bphase\s+iv\b')
        ]:
            if re.search(pattern, text[:10000], re.IGNORECASE):
                return phase
        
        return "Unknown"
    
    def _extract_study_type(self, text: str) -> str:
        """Extract study type (interventional, observational, etc.)"""
        patterns = [
            ("Randomized Interventional", r'randomized.*interventional|interventional.*randomized'),
            ("Randomized", r'\brandomized\b'),
            ("Interventional", r'\binterventional\b'),
            ("Observational", r'\bobservational\b'),
            ("Single-arm", r'single[-\s]?arm'),
        ]
        
        for study_type, pattern in patterns:
            if re.search(pattern, text[:10000], re.IGNORECASE):
                return study_type
        
        return "Interventional"
    
    def _extract_randomization(self, text: str) -> Dict[str, Any]:
        """Extract randomization details"""
        result = {"is_randomized": False}
        
        if re.search(r'\brandomi[sz]ed\b', text[:10000], re.IGNORECASE):
            result["is_randomized"] = True
            
            # Look for ratio
            ratio_match = re.search(r'(\d+):(\d+)(?::(\d+))?\s*(?:ratio|allocation)', text[:10000], re.IGNORECASE)
            if ratio_match:
                result["ratio"] = ratio_match.group(0).split()[0]
            else:
                result["ratio"] = "1:1"
            
            # Stratification factors
            strat_match = re.search(
                r'stratif[^.]*by[:\s]*([^\.]+)',
                text[:15000],
                re.IGNORECASE | re.DOTALL
            )
            if strat_match:
                factors = re.split(r'[,;]\s*|\s+and\s+', strat_match.group(1))
                result["stratification_factors"] = [f.strip() for f in factors if len(f.strip()) > 3][:5]
        
        return result
    
    def _extract_blinding(self, text: str) -> Dict[str, Any]:
        """Extract blinding information"""
        blinding_types = [
            ("Double-blind", r'double[-\s]?blind'),
            ("Single-blind", r'single[-\s]?blind'),
            ("Open-label", r'open[-\s]?label'),
            ("Triple-blind", r'triple[-\s]?blind'),
        ]
        
        for blinding_type, pattern in blinding_types:
            if re.search(pattern, text[:10000], re.IGNORECASE):
                return {
                    "type": blinding_type,
                    "is_blinded": blinding_type != "Open-label"
                }
        
        return {"type": "Open-label", "is_blinded": False}
    
    def _extract_control_type(self, text: str) -> str:
        """Extract control type"""
        patterns = [
            ("Placebo-controlled", r'placebo[-\s]?controlled|placebo control'),
            ("Active-controlled", r'active[-\s]?controlled|active comparator'),
            ("Standard of Care", r'standard of care|treatment as usual'),
        ]
        
        for control_type, pattern in patterns:
            if re.search(pattern, text[:10000], re.IGNORECASE):
                return control_type
        
        return "Not specified"
    
    def _extract_endpoints(self, text: str, use_nlp: bool) -> Dict[str, List[str]]:
        """Extract endpoints with NLP enhancement"""
        endpoints = {"primary": [], "secondary": [], "exploratory": []}
        
        # Primary endpoint
        primary_match = self.patterns["primary_endpoint"].search(text[:20000])
        if primary_match:
            primary_text = primary_match.group(1).strip()
            # Clean up and split multiple primaries
            primaries = re.split(r'[,;]\s*and\s*|\s+and\s+', primary_text)
            endpoints["primary"] = [p.strip() for p in primaries if len(p.strip()) > 10][:3]
        
        # Secondary endpoints
        secondary_section = re.search(
            r'secondary\s+endpoint[s]?[:\s]*([^\n]+(?:\n[^\n]+){0,20})',
            text[:30000],
            re.IGNORECASE
        )
        if secondary_section:
            secondary_text = secondary_section.group(1)
            # Split by bullets or numbers
            secondaries = re.split(r'[•\-\*]\s*|\d+\.\s*', secondary_text)
            endpoints["secondary"] = [s.strip() for s in secondaries if len(s.strip()) > 10][:10]
        
        # NLP enhancement: extract medical entities
        if use_nlp and self.nlp and not endpoints["primary"]:
            doc = self.nlp(text[:30000])
            # Look for disease/condition mentions that might be endpoints
            conditions = [ent.text for ent in doc.ents if ent.label_ in ["DISEASE", "CONDITION"]]
            if conditions:
                endpoints["nlp_detected_conditions"] = list(set(conditions))[:5]
        
        return endpoints
    
    def _extract_population(self, text: str) -> Dict[str, Any]:
        """Extract study population information"""
        population = {
            "target_disease": self._extract_disease(text),
            "planned_enrollment": self._extract_enrollment(text),
            "age_range": self._extract_age_range(text),
            "inclusion_criteria": self._extract_inclusion_criteria(text),
            "exclusion_criteria": self._extract_exclusion_criteria(text)
        }
        
        return population
    
    def _extract_disease(self, text: str) -> str:
        """Extract target disease/indication"""
        patterns = [
            r'patients\s+with\s+([^.]+(?:cancer|carcinoma|disease|syndrome|disorder))',
            r'in\s+([^.]{3,50}(?:cancer|carcinoma|disease|syndrome))',
            r'indication[:\s]*([^.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text[:15000], re.IGNORECASE)
            if match:
                disease = match.group(1).strip()
                # Clean up
                disease = re.sub(r'\s+', ' ', disease)
                return disease[:100]  # Limit length
        
        return "Not specified"
    
    def _extract_enrollment(self, text: str) -> Optional[int]:
        """Extract planned enrollment number"""
        # Try compiled pattern first
        match = self.patterns["n_value"].search(text[:15000])
        if match:
            try:
                return int(match.group(2).replace(',', ''))
            except (ValueError, IndexError):
                pass
        
        # Fallback patterns
        patterns = [
            r'(\d{2,4})\s+patients\s+(?:will\s+)?(?:be\s+)?(?:enrolled|randomized|included)',
            r'enroll(?:ment)?[:\s]*(?:approximately\s+)?([\d,]+)',
            r'sample\s+size[:\s]*(?:of\s+)?([\d,]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text[:15000], re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1).replace(',', ''))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_age_range(self, text: str) -> Dict[str, Optional[int]]:
        """Extract age inclusion criteria"""
        age_range = {"min": None, "max": None}
        
        # Look for age patterns
        patterns = [
            ("min", r'(?:age|aged)\s*(?:≥|>=|at least)\s*(\d+)'),
            ("min", r'(\d+)\s*(?:years?|y)\s*(?:of age|old)?\s*(?:or older|and older)'),
            ("max", r'(?:age|aged)\s*(?:≤|<=|up to)\s*(\d+)'),
            ("max", r'(\d+)\s*(?:years?|y)\s*(?:of age|old)?\s*(?:or younger|and younger)'),
        ]
        
        for key, pattern in patterns:
            match = re.search(pattern, text[:15000], re.IGNORECASE)
            if match:
                try:
                    age_range[key] = int(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return age_range
    
    def _extract_inclusion_criteria(self, text: str) -> List[str]:
        """Extract key inclusion criteria"""
        criteria = []
        
        # Look for inclusion criteria section
        section = re.search(
            r'(?:inclusion\s+criteria|key\s+inclusion)[:\s]*([^#]+?)(?=exclusion|\.\s*KEY|CONTRA)',
            text[:20000],
            re.IGNORECASE | re.DOTALL
        )
        
        if section:
            # Extract numbered/bulleted items
            items = re.findall(r'(?:^|\n)[\s•\-\d\.]*([^\n]+)', section.group(1))
            criteria = [item.strip() for item in items if len(item.strip()) > 20][:10]
        
        return criteria
    
    def _extract_exclusion_criteria(self, text: str) -> List[str]:
        """Extract key exclusion criteria"""
        criteria = []
        
        section = re.search(
            r'(?:exclusion\s+criteria|key\s+exclusion)[:\s]*([^#]+?)(?=\n\s*\n|\Z)',
            text[10000:30000],  # Usually after inclusion
            re.IGNORECASE | re.DOTALL
        )
        
        if section:
            items = re.findall(r'(?:^|\n)[\s•\-\d\.]*([^\n]+)', section.group(1))
            criteria = [item.strip() for item in items if len(item.strip()) > 20][:10]
        
        return criteria
    
    def _extract_schedule(self, text: str) -> Dict[str, Any]:
        """Extract study schedule information"""
        schedule = {
            "treatment_duration": None,
            "follow_up_duration": None,
            "visit_frequency": None
        }
        
        # Treatment duration
        duration_match = re.search(
            r'treatment(?:\s+period)?[:\s]*(?:for\s+)?(?:up to|maximum|≤)?\s*(\d+)\s*(weeks?|months?|years?)',
            text[:20000],
            re.IGNORECASE
        )
        if duration_match:
            schedule["treatment_duration"] = f"{duration_match.group(1)} {duration_match.group(2)}"
        
        # Follow-up
        followup_match = re.search(
            r'follow[-\s]?up[:\s]*(?:for\s+)?(?:up to|≤)?\s*(\d+)\s*(weeks?|months?|years?)',
            text[:20000],
            re.IGNORECASE
        )
        if followup_match:
            schedule["follow_up_duration"] = f"{followup_match.group(1)} {followup_match.group(2)}"
        
        return schedule
    
    def _extract_statistical_methods(self, text: str) -> Dict[str, Any]:
        """Extract statistical methodology"""
        stats = {
            "primary_analysis": None,
            "significance_level": 0.05,
            "power": 0.80,
            "analysis_population": "Intent-to-treat"
        }
        
        # Primary analysis method
        analysis_match = re.search(
            r'primary\s+analysis[:\s]*([^\.]+?)(?=will|was|is|\.)',
            text[:25000],
            re.IGNORECASE
        )
        if analysis_match:
            stats["primary_analysis"] = analysis_match.group(1).strip()[:200]
        
        # Alpha
        alpha_match = self.patterns["alpha"].search(text[:25000])
        if alpha_match:
            try:
                stats["significance_level"] = float(alpha_match.group(1))
            except ValueError:
                pass
        
        # Power
        power_match = self.patterns["power"].search(text[:25000])
        if power_match:
            try:
                stats["power"] = int(power_match.group(1)) / 100
            except ValueError:
                pass
        
        return stats
    
    def _compute_complexity(
        self,
        study_design: Dict,
        endpoints: Dict,
        population: Dict,
        statistics: Dict
    ) -> float:
        """Compute study complexity score (0-10)"""
        score = 5.0  # Base complexity
        
        # Phase complexity
        phase = study_design.get("phase", "")
        if phase in ["III", "IV"]:
            score += 1.0
        
        # Randomization complexity
        if study_design.get("randomization", {}).get("stratification_factors"):
            score += len(study_design["randomization"]["stratification_factors"]) * 0.3
        
        # Endpoint complexity
        if len(endpoints.get("primary", [])) > 1:
            score += 0.5  # Multiple primary endpoints
        if len(endpoints.get("secondary", [])) > 5:
            score += 0.5
        
        # Population size
        enrollment = population.get("planned_enrollment")
        if enrollment:
            if enrollment > 1000:
                score += 1.0
            elif enrollment > 500:
                score += 0.5
        
        # Statistical complexity
        if statistics.get("power", 0.8) < 0.85:
            score += 0.3  # Lower power = more complex design
        
        return min(round(score, 1), 10.0)
    
    def _calculate_confidence(
        self,
        study_design: Dict,
        endpoints: Dict,
        population: Dict,
        statistics: Dict
    ) -> float:
        """Calculate extraction confidence"""
        checks = []
        
        # Required fields
        checks.append(study_design.get("phase") != "Unknown")
        checks.append(study_design.get("study_type") is not None)
        checks.append(len(endpoints.get("primary", [])) > 0)
        checks.append(population.get("planned_enrollment") is not None)
        checks.append(population.get("target_disease") != "Not specified")
        
        return sum(checks) / len(checks) if checks else 0.0
