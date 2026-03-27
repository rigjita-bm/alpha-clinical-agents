"""
Statistical Validator - Agent 3
Validates numerical claims, p-values, confidence intervals, and statistical methods
"""

import re
import math
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP

import sys
sys.path.append('/root/.openclaw/workspace/alpha-clinical-agents')

from core import BaseAgent


class StatisticalErrorType(Enum):
    INVALID_P_VALUE = "invalid_p_value"
    IMPOSSIBLE_PERCENTAGE = "impossible_percentage"
    HR_OUT_OF_RANGE = "hr_out_of_range"
    CI_MISMATCH = "ci_mismatch"
    SAMPLE_SIZE_MISMATCH = "sample_size_mismatch"
    SIGNIFICANCE_MISMATCH = "significance_mismatch"
    DECIMAL_PRECISION_ERROR = "decimal_precision_error"


class SeverityLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class StatisticalFinding:
    """A statistical validation finding"""
    error_type: StatisticalErrorType
    severity: SeverityLevel
    claim_text: str
    expected: Optional[str]
    actual: str
    explanation: str
    confidence: float
    suggested_fix: str
    
    def to_dict(self) -> Dict:
        return {
            "type": self.error_type.value,
            "severity": self.severity.value,
            "claim": self.claim_text,
            "expected": self.expected,
            "actual": self.actual,
            "explanation": self.explanation,
            "confidence": self.confidence,
            "fix": self.suggested_fix
        }


@dataclass
class StatisticalClaim:
    """Extracted statistical claim"""
    claim_type: str  # "p_value", "hazard_ratio", "ci", "percentage", "n"
    value: Any
    context: str
    location: str


class StatisticalValidator(BaseAgent):
    """
    Agent 3: Statistical Validator
    
    Validates all numerical and statistical claims in clinical documents:
    - P-values (range, significance thresholds)
    - Hazard ratios (plausibility, CIs)
    - Confidence intervals (consistency)
    - Percentages (0-100% range)
    - Sample sizes (consistency across sections)
    - Statistical significance claims
    
    Output: Statistical validation report with errors and corrections
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(
            agent_id="StatisticalValidator",
            version="1.0.0",
            config=config
        )
        
        # Validation thresholds
        self.p_value_alpha = 0.05
        self.hr_plausible_range = (0.1, 10.0)
        self.ci_confidence_level = 0.95
        
        # Patterns for extraction
        self.patterns = self._compile_patterns()
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main validation logic
        
        Args:
            input_data: {
                "draft_text": str,
                "section_name": str,
                "statistical_data": Dict,
                "protocol_data": Dict
            }
        """
        draft_text = input_data.get("draft_text", "")
        section_name = input_data.get("section_name", "")
        statistical_data = input_data.get("statistical_data", {})
        protocol_data = input_data.get("protocol_data", {})
        
        findings = []
        
        # Extract all statistical claims
        claims = self._extract_statistical_claims(draft_text)
        
        # Validate each claim type
        for claim in claims:
            if claim.claim_type == "p_value":
                findings.extend(self._validate_p_value(claim, statistical_data))
            elif claim.claim_type == "hazard_ratio":
                findings.extend(self._validate_hazard_ratio(claim, statistical_data))
            elif claim.claim_type == "ci":
                findings.extend(self._validate_confidence_interval(claim, statistical_data))
            elif claim.claim_type == "percentage":
                findings.extend(self._validate_percentage(claim))
            elif claim.claim_type == "n":
                findings.extend(self._validate_sample_size(claim, protocol_data))
        
        # Cross-validate significance claims
        findings.extend(self._validate_significance_claims(draft_text, claims))
        
        # Calculate overall validation score
        validation_score = self._calculate_validation_score(findings)
        risk_level = self._determine_risk_level(findings)
        
        # Generate corrections
        corrections = self._generate_corrections(findings, draft_text)
        
        return {
            "section_name": section_name,
            "validation_score": validation_score,  # 0-100
            "risk_level": risk_level,
            "total_claims": len(claims),
            "findings_count": len(findings),
            "critical": len([f for f in findings if f.severity == SeverityLevel.CRITICAL]),
            "high": len([f for f in findings if f.severity == SeverityLevel.HIGH]),
            "medium": len([f for f in findings if f.severity == SeverityLevel.MEDIUM]),
            "low": len([f for f in findings if f.severity == SeverityLevel.LOW]),
            "findings": [f.to_dict() for f in findings],
            "corrections": corrections,
            "requires_rejection": risk_level in ["CRITICAL", "HIGH"],
            "requires_statistician_review": len([f for f in findings if f.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]]) > 0
        }
    
    def _compile_patterns(self) -> Dict:
        """Compile regex patterns for claim extraction"""
        return {
            "p_value": re.compile(r'p\s*([=<≥>])\s*(0?\.\d+)', re.IGNORECASE),
            "hazard_ratio": re.compile(r'(?:hazard ratio|HR)\s*([=<≥>])\s*(\d+\.?\d*)', re.IGNORECASE),
            "ci": re.compile(r'\(?(\d+\.?\d*)\s*%,?\s*CI:?\s*(\d+\.\d+)\s*[-–]\s*(\d+\.\d+)\)?', re.IGNORECASE),
            "percentage": re.compile(r'(\d+\.?\d*)\s*%', re.IGNORECASE),
            "n_equals": re.compile(r'[Nn]\s*=\s*(\d+)', re.IGNORECASE),
            "n_patients": re.compile(r'(\d+)\s+(?:patients?|subjects?)', re.IGNORECASE)
        }
    
    def _extract_statistical_claims(self, text: str) -> List[StatisticalClaim]:
        """Extract all statistical claims from text"""
        claims = []
        
        # P-values
        for match in self.patterns["p_value"].finditer(text):
            operator = match.group(1)
            value = float(match.group(2))
            claims.append(StatisticalClaim(
                claim_type="p_value",
                value={"operator": operator, "value": value},
                context=text[max(0, match.start()-30):min(len(text), match.end()+30)],
                location=f"position {match.start()}"
            ))
        
        # Hazard ratios
        for match in self.patterns["hazard_ratio"].finditer(text):
            operator = match.group(1)
            value = float(match.group(2))
            claims.append(StatisticalClaim(
                claim_type="hazard_ratio",
                value={"operator": operator, "value": value},
                context=text[max(0, match.start()-30):min(len(text), match.end()+30)],
                location=f"position {match.start()}"
            ))
        
        # Confidence intervals
        for match in self.patterns["ci"].finditer(text):
            confidence = float(match.group(1))
            lower = float(match.group(2))
            upper = float(match.group(3))
            claims.append(StatisticalClaim(
                claim_type="ci",
                value={"confidence": confidence, "lower": lower, "upper": upper},
                context=text[max(0, match.start()-30):min(len(text), match.end()+30)],
                location=f"position {match.start()}"
            ))
        
        # Percentages
        for match in self.patterns["percentage"].finditer(text):
            value = float(match.group(1))
            claims.append(StatisticalClaim(
                claim_type="percentage",
                value=value,
                context=text[max(0, match.start()-30):min(len(text), match.end()+30)],
                location=f"position {match.start()}"
            ))
        
        # Sample sizes
        for match in self.patterns["n_equals"].finditer(text):
            value = int(match.group(1))
            claims.append(StatisticalClaim(
                claim_type="n",
                value=value,
                context=text[max(0, match.start()-30):min(len(text), match.end()+30)],
                location=f"position {match.start()}"
            ))
        
        for match in self.patterns["n_patients"].finditer(text):
            value = int(match.group(1))
            claims.append(StatisticalClaim(
                claim_type="n",
                value=value,
                context=text[max(0, match.start()-30):min(len(text), match.end()+30)],
                location=f"position {match.start()}"
            ))
        
        return claims
    
    def _validate_p_value(self, claim: StatisticalClaim, 
                         statistical_data: Dict) -> List[StatisticalFinding]:
        """Validate p-value claim"""
        findings = []
        value = claim.value["value"]
        operator = claim.value["operator"]
        
        # Check range
        if value < 0 or value > 1:
            findings.append(StatisticalFinding(
                error_type=StatisticalErrorType.INVALID_P_VALUE,
                severity=SeverityLevel.CRITICAL,
                claim_text=claim.context,
                expected="0 ≤ p ≤ 1",
                actual=f"p{operator}{value}",
                explanation=f"P-value {value} is outside valid range [0, 1]",
                confidence=0.99,
                suggested_fix="Correct p-value to be within 0-1 range"
            ))
        
        # Check against statistical data if available
        if statistical_data and "primary_analysis" in statistical_data:
            expected_p = statistical_data["primary_analysis"].get("p_value")
            if expected_p is not None:
                if abs(value - expected_p) > 0.001:  # Allow small rounding differences
                    findings.append(StatisticalFinding(
                        error_type=StatisticalErrorType.SIGNIFICANCE_MISMATCH,
                        severity=SeverityLevel.CRITICAL,
                        claim_text=claim.context,
                        expected=f"p={expected_p}",
                        actual=f"p{operator}{value}",
                        explanation=f"P-value mismatch: statistical output shows p={expected_p}",
                        confidence=0.95,
                        suggested_fix=f"Update to p={expected_p} per statistical analysis"
                    ))
        
        # Check significance threshold consistency
        if operator == ">" and value < self.p_value_alpha:
            findings.append(StatisticalFinding(
                error_type=StatisticalErrorType.SIGNIFICANCE_MISMATCH,
                severity=SeverityLevel.HIGH,
                claim_text=claim.context,
                expected="p < 0.05 for significance",
                actual=f"p > {value}",
                explanation="Claimed p > threshold but value suggests significance",
                confidence=0.90,
                suggested_fix="Use p < 0.05 for significant results"
            ))
        
        return findings
    
    def _validate_hazard_ratio(self, claim: StatisticalClaim,
                              statistical_data: Dict) -> List[StatisticalFinding]:
        """Validate hazard ratio claim"""
        findings = []
        value = claim.value["value"]
        
        # Check range
        if value < 0:
            findings.append(StatisticalFinding(
                error_type=StatisticalErrorType.HR_OUT_OF_RANGE,
                severity=StatisticalErrorType.HR_OUT_OF_RANGE,
                claim_text=claim.context,
                expected="HR > 0",
                actual=f"HR={value}",
                explanation=f"Hazard ratio cannot be negative: {value}",
                confidence=0.99,
                suggested_fix="Hazard ratio must be positive"
            ))
        
        # Check plausibility
        if value < self.hr_plausible_range[0] or value > self.hr_plausible_range[1]:
            findings.append(StatisticalFinding(
                error_type=StatisticalErrorType.HR_OUT_OF_RANGE,
                severity=SeverityLevel.MEDIUM,
                claim_text=claim.context,
                expected=f"HR in range {self.hr_plausible_range}",
                actual=f"HR={value}",
                explanation=f"HR {value} is outside typical range {self.hr_plausible_range}",
                confidence=0.80,
                suggested_fix="Verify HR value with statistical team"
            ))
        
        # Check against statistical data
        if statistical_data and "primary_analysis" in statistical_data:
            expected_hr = statistical_data["primary_analysis"].get("hazard_ratio")
            if expected_hr is not None and abs(value - expected_hr) > 0.01:
                findings.append(StatisticalFinding(
                    error_type=StatisticalErrorType.SIGNIFICANCE_MISMATCH,
                    severity=SeverityLevel.CRITICAL,
                    claim_text=claim.context,
                    expected=f"HR={expected_hr}",
                    actual=f"HR={value}",
                    explanation=f"HR mismatch: statistical output shows HR={expected_hr}",
                    confidence=0.95,
                    suggested_fix=f"Update to HR={expected_hr} per statistical analysis"
                ))
        
        return findings
    
    def _validate_confidence_interval(self, claim: StatisticalClaim,
                                     statistical_data: Dict) -> List[StatisticalFinding]:
        """Validate confidence interval claim"""
        findings = []
        lower = claim.value["lower"]
        upper = claim.value["upper"]
        confidence = claim.value["confidence"]
        
        # Check ordering
        if lower >= upper:
            findings.append(StatisticalFinding(
                error_type=StatisticalErrorType.CI_MISMATCH,
                severity=SeverityLevel.CRITICAL,
                claim_text=claim.context,
                expected="lower < upper",
                actual=f"[{lower}, {upper}]",
                explanation=f"CI lower bound ({lower}) >= upper bound ({upper})",
                confidence=0.99,
                suggested_fix="Correct CI bounds: lower must be less than upper"
            ))
        
        # Check confidence level
        if confidence not in [90, 95, 99]:
            findings.append(StatisticalFinding(
                error_type=StatisticalErrorType.CI_MISMATCH,
                severity=SeverityLevel.LOW,
                claim_text=claim.context,
                expected="90%, 95%, or 99% CI",
                actual=f"{confidence}% CI",
                explanation=f"Unusual confidence level: {confidence}%",
                confidence=0.70,
                suggested_fix="Verify confidence level with statistical team"
            ))
        
        return findings
    
    def _validate_percentage(self, claim: StatisticalClaim) -> List[StatisticalFinding]:
        """Validate percentage claim"""
        findings = []
        value = claim.value
        
        # Check range
        if value < 0 or value > 100:
            findings.append(StatisticalFinding(
                error_type=StatisticalErrorType.IMPOSSIBLE_PERCENTAGE,
                severity=SeverityLevel.CRITICAL,
                claim_text=claim.context,
                expected="0-100%",
                actual=f"{value}%",
                explanation=f"Percentage {value}% is outside valid range [0, 100]",
                confidence=0.99,
                suggested_fix="Percentage must be between 0% and 100%"
            ))
        
        return findings
    
    def _validate_sample_size(self, claim: StatisticalClaim,
                             protocol_data: Dict) -> List[StatisticalFinding]:
        """Validate sample size claim"""
        findings = []
        value = claim.value
        
        # Check against protocol
        protocol_n = protocol_data.get("population", {}).get("planned_enrollment")
        if protocol_n is not None:
            # Allow small variance for screening failures
            if abs(value - protocol_n) > max(protocol_n * 0.05, 10):
                findings.append(StatisticalFinding(
                    error_type=StatisticalErrorType.SAMPLE_SIZE_MISMATCH,
                    severity=SeverityLevel.HIGH,
                    claim_text=claim.context,
                    expected=str(protocol_n),
                    actual=str(value),
                    explanation=f"Sample size {value} differs significantly from protocol ({protocol_n})",
                    confidence=0.90,
                    suggested_fix=f"Update to {protocol_n} or add explanation for difference"
                ))
        
        return findings
    
    def _validate_significance_claims(self, text: str, 
                                     claims: List[StatisticalClaim]) -> List[StatisticalFinding]:
        """Validate consistency of significance claims"""
        findings = []
        
        # Look for significance claims
        significance_patterns = [
            (r'statistically\s+significant', 'significant'),
            (r'not\s+statistically\s+significant', 'not_significant'),
            (r'failed\s+to\s+reach\s+significance', 'not_significant')
        ]
        
        # Find p-values in claims
        p_values = [c for c in claims if c.claim_type == "p_value"]
        
        if p_values:
            # Get the smallest p-value (most significant)
            min_p = min(c.value["value"] for c in p_values)
            
            for pattern, claim_type in significance_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    if claim_type == "significant" and min_p >= self.p_value_alpha:
                        findings.append(StatisticalFinding(
                            error_type=StatisticalErrorType.SIGNIFICANCE_MISMATCH,
                            severity=SeverityLevel.CRITICAL,
                            claim_text=f"Claimed 'statistically significant' but p={min_p}",
                            expected=f"p < {self.p_value_alpha}",
                            actual=f"p={min_p}",
                            explanation=f"Claims significance but p-value {min_p} >= {self.p_value_alpha}",
                            confidence=0.95,
                            suggested_fix="Either correct p-value or change significance claim"
                        ))
                    elif claim_type == "not_significant" and min_p < self.p_value_alpha:
                        findings.append(StatisticalFinding(
                            error_type=StatisticalErrorType.SIGNIFICANCE_MISMATCH,
                            severity=StatisticalErrorType.SIGNIFICANCE_MISMATCH,
                            claim_text=f"Claimed 'not significant' but p={min_p}",
                            expected=f"p >= {self.p_value_alpha}",
                            actual=f"p={min_p}",
                            explanation=f"Claims no significance but p-value {min_p} < {self.p_value_alpha}",
                            confidence=0.95,
                            suggested_fix="Either correct p-value or change significance claim"
                        ))
        
        return findings
    
    def _calculate_validation_score(self, findings: List[StatisticalFinding]) -> float:
        """Calculate overall validation score (0-100)"""
        if not findings:
            return 100.0
        
        severity_weights = {
            SeverityLevel.CRITICAL: 25,
            SeverityLevel.HIGH: 15,
            SeverityLevel.MEDIUM: 5,
            SeverityLevel.LOW: 1
        }
        
        penalty = sum(severity_weights.get(f.severity, 5) for f in findings)
        return max(0, 100 - penalty)
    
    def _determine_risk_level(self, findings: List[StatisticalFinding]) -> str:
        """Determine overall risk level"""
        critical_count = len([f for f in findings if f.severity == SeverityLevel.CRITICAL])
        high_count = len([f for f in findings if f.severity == SeverityLevel.HIGH])
        
        if critical_count > 0:
            return "CRITICAL"
        elif high_count > 0:
            return "HIGH"
        elif len([f for f in findings if f.severity == SeverityLevel.MEDIUM]) > 0:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_corrections(self, findings: List[StatisticalFinding],
                             text: str) -> List[Dict]:
        """Generate suggested corrections"""
        corrections = []
        
        for finding in findings:
            if finding.expected:
                corrections.append({
                    "original": finding.actual,
                    "corrected": finding.expected,
                    "explanation": finding.explanation,
                    "location": finding.claim_text[:50] + "..." if len(finding.claim_text) > 50 else finding.claim_text
                })
        
        return corrections


# Demo
if __name__ == "__main__":
    # Sample text with statistical errors
    sample_text = """The primary analysis showed a statistically significant improvement 
    in Overall Survival with a hazard ratio of -0.72 (95% CI: 0.58-0.89, p=0.003). 
    The overall response rate was 145%. A total of 599 patients were enrolled (n=599)."""
    
    protocol_data = {
        "population": {"planned_enrollment": 600}
    }
    
    statistical_data = {
        "primary_analysis": {
            "hazard_ratio": 0.72,
            "p_value": 0.003,
            "ci_lower": 0.58,
            "ci_upper": 0.89
        }
    }
    
    # Run validation
    validator = StatisticalValidator()
    result = validator.execute({
        "draft_text": sample_text,
        "section_name": "Results",
        "statistical_data": statistical_data,
        "protocol_data": protocol_data
    })
    
    # Display results
    print("=" * 70)
    print("STATISTICAL VALIDATOR - AGENT 3")
    print("=" * 70)
    
    print(f"\n📊 Validation Score: {result['validation_score']}/100")
    print(f"⚠️  Risk Level: {result['risk_level']}")
    print(f"\n📈 Claims Found: {result['total_claims']}")
    print(f"🚨 Findings: {result['findings_count']}")
    print(f"   Critical: {result['critical']}")
    print(f"   High: {result['high']}")
    print(f"   Medium: {result['medium']}")
    print(f"   Low: {result['low']}")
    
    print(f"\n🚫 Requires Rejection: {'YES' if result['requires_rejection'] else 'NO'}")
    print(f"👤 Requires Statistician Review: {'YES' if result['requires_statistician_review'] else 'NO'}")
    
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
        print(f"   Claim: '{finding['claim'][:60]}...'")
        print(f"   Expected: {finding['expected']}")
        print(f"   Actual: {finding['actual']}")
        print(f"   Explanation: {finding['explanation']}")
        print(f"   Fix: {finding['fix']}")
    
    if result['corrections']:
        print("\n" + "=" * 70)
        print("SUGGESTED CORRECTIONS:")
        print("=" * 70)
        for correction in result['corrections']:
            print(f"\n• Replace: '{correction['original']}'")
            print(f"  With:    '{correction['corrected']}'")
    
    print("\n" + "=" * 70)
