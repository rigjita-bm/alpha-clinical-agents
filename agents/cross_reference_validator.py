"""
Cross-Reference Validator - Agent 5
Ensures consistency across all sections and documents
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict

from core.base_agent import BaseAgent


class InconsistencyType(Enum):
    SAMPLE_SIZE_MISMATCH = "sample_size_mismatch"
    PERCENTAGE_MISMATCH = "percentage_mismatch"
    ENDPOINT_MISMATCH = "endpoint_mismatch"
    TIMELINE_MISMATCH = "timeline_mismatch"
    DEFINITION_MISMATCH = "definition_mismatch"
    CITATION_MISMATCH = "citation_mismatch"
    NUMBERING_MISMATCH = "numbering_mismatch"


class ConsistencySeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CrossReferenceFinding:
    """A cross-reference inconsistency finding"""
    inconsistency_type: InconsistencyType
    severity: ConsistencySeverity
    claim_a: str
    claim_b: str
    section_a: str
    section_b: str
    expected_value: str
    actual_value: str
    explanation: str
    confidence: float
    suggested_fix: str
    
    def to_dict(self) -> Dict:
        return {
            "type": self.inconsistency_type.value,
            "severity": self.severity.value,
            "claim_a": self.claim_a,
            "claim_b": self.claim_b,
            "section_a": self.section_a,
            "section_b": self.section_b,
            "expected": self.expected_value,
            "actual": self.actual_value,
            "explanation": self.explanation,
            "confidence": self.confidence,
            "fix": self.suggested_fix
        }


class CrossReferenceValidator(BaseAgent):
    """
    Agent 5: Cross-Reference Validator
    
    Ensures consistency across:
    - All sections of the CSR
    - Protocol vs CSR alignment
    - Tables vs text alignment
    - Figures vs text alignment
    - Internal citations
    
    Output: Cross-reference consistency report
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(
            agent_id="CrossReferenceValidator",
            version="1.0.0",
            config=config
        )
        
        self.tolerance_percentages = 0.5  # 0.5% tolerance for percentage comparisons
        self.tolerance_n = 5  # 5 patient tolerance for sample sizes
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main cross-reference validation logic
        
        Args:
            input_data: {
                "sections": Dict[str, str],  # section_name: content
                "protocol_data": Dict,
                "tables": Dict[str, Any],
                "figures": Dict[str, Any]
            }
        """
        sections = input_data.get("sections", {})
        protocol_data = input_data.get("protocol_data", {})
        tables = input_data.get("tables", {})
        figures = input_data.get("figures", {})
        
        findings = []
        
        # Extract all claims from sections
        section_claims = self._extract_all_claims(sections)
        
        # Run cross-section consistency checks
        findings.extend(self._check_sample_size_consistency(section_claims))
        findings.extend(self._check_percentage_consistency(section_claims))
        findings.extend(self._check_endpoint_consistency(section_claims, protocol_data))
        findings.extend(self._check_protocol_alignment(section_claims, protocol_data))
        findings.extend(self._check_table_text_alignment(section_claims, tables))
        findings.extend(self._check_citation_consistency(sections))
        
        # Calculate consistency score
        consistency_score = self._calculate_consistency_score(findings)
        risk_level = self._determine_risk_level(findings)
        
        return {
            "consistency_score": consistency_score,  # 0-100
            "risk_level": risk_level,
            "total_findings": len(findings),
            "critical": len([f for f in findings if f.severity == ConsistencySeverity.CRITICAL]),
            "high": len([f for f in findings if f.severity == ConsistencySeverity.HIGH]),
            "medium": len([f for f in findings if f.severity == ConsistencySeverity.MEDIUM]),
            "low": len([f for f in findings if f.severity == ConsistencySeverity.LOW]),
            "findings": [f.to_dict() for f in findings],
            "sections_checked": len(sections),
            "requires_reconciliation": risk_level in ["CRITICAL", "HIGH"],
            "auto_fixable": len([f for f in findings if f.severity in [ConsistencySeverity.LOW, ConsistencySeverity.MEDIUM]])
        }
    
    def _extract_all_claims(self, sections: Dict[str, str]) -> Dict[str, List[Dict]]:
        """Extract all numerical claims from all sections"""
        section_claims = {}
        
        for section_name, content in sections.items():
            claims = []
            
            # Sample sizes
            for match in re.finditer(r'(\d+)\s+patients?', content, re.IGNORECASE):
                claims.append({
                    "type": "n",
                    "value": int(match.group(1)),
                    "context": content[max(0, match.start()-20):min(len(content), match.end()+20)],
                    "location": match.start()
                })
            
            # Percentages
            for match in re.finditer(r'(\d+\.?\d*)\s*%', content):
                claims.append({
                    "type": "percentage",
                    "value": float(match.group(1)),
                    "context": content[max(0, match.start()-20):min(len(content), match.end()+20)],
                    "location": match.start()
                })
            
            # P-values
            for match in re.finditer(r'p\s*[=\u003c]\s*(0?\.\d+)', content, re.IGNORECASE):
                claims.append({
                    "type": "p_value",
                    "value": float(match.group(1)),
                    "context": content[max(0, match.start()-20):min(len(content), match.end()+20)],
                    "location": match.start()
                })
            
            # Hazard ratios
            for match in re.finditer(r'HR\s*[=\u003c]\s*(\d+\.?\d*)', content, re.IGNORECASE):
                claims.append({
                    "type": "hazard_ratio",
                    "value": float(match.group(1)),
                    "context": content[max(0, match.start()-20):min(len(content), match.end()+20)],
                    "location": match.start()
                })
            
            section_claims[section_name] = claims
        
        return section_claims
    
    def _check_sample_size_consistency(self, 
                                      section_claims: Dict[str, List[Dict]]) -> List[CrossReferenceFinding]:
        """Check sample size consistency across sections"""
        findings = []
        
        # Collect all sample sizes by section
        section_ns = {}
        for section, claims in section_claims.items():
            n_claims = [c for c in claims if c["type"] == "n"]
            if n_claims:
                # Use the most common N in this section
                values = [c["value"] for c in n_claims]
                section_ns[section] = max(set(values), key=values.count)
        
        # Check consistency
        if len(section_ns) >= 2:
            sections_list = list(section_ns.items())
            reference_section, reference_n = sections_list[0]
            
            for section, n in sections_list[1:]:
                if abs(n - reference_n) > self.tolerance_n:
                    findings.append(CrossReferenceFinding(
                        inconsistency_type=InconsistencyType.SAMPLE_SIZE_MISMATCH,
                        severity=ConsistencySeverity.HIGH,
                        claim_a=f"{reference_n} patients in {reference_section}",
                        claim_b=f"{n} patients in {section}",
                        section_a=reference_section,
                        section_b=section,
                        expected_value=str(reference_n),
                        actual_value=str(n),
                        explanation=f"Sample size differs between {reference_section} ({reference_n}) and {section} ({n})",
                        confidence=0.95,
                        suggested_fix=f"Standardize to {reference_n} or add explanation for difference"
                    ))
        
        return findings
    
    def _check_percentage_consistency(self,
                                     section_claims: Dict[str, List[Dict]]) -> List[CrossReferenceFinding]:
        """Check percentage consistency across sections"""
        findings = []
        
        # Group percentages by context (simplified)
        all_percentages = []
        for section, claims in section_claims.items():
            for claim in claims:
                if claim["type"] == "percentage":
                    all_percentages.append({
                        "section": section,
                        "value": claim["value"],
                        "context": claim["context"]
                    })
        
        # Check for very similar contexts with different percentages
        for i, pct_a in enumerate(all_percentages):
            for pct_b in all_percentages[i+1:]:
                # Check if same metric mentioned in different sections
                if self._same_metric(pct_a["context"], pct_b["context"]):
                    diff = abs(pct_a["value"] - pct_b["value"])
                    if diff > self.tolerance_percentages:
                        findings.append(CrossReferenceFinding(
                            inconsistency_type=InconsistencyType.PERCENTAGE_MISMATCH,
                            severity=ConsistencySeverity.HIGH,
                            claim_a=f"{pct_a['value']}% in {pct_a['section']}",
                            claim_b=f"{pct_b['value']}% in {pct_b['section']}",
                            section_a=pct_a["section"],
                            section_b=pct_b["section"],
                            expected_value=f"{pct_a['value']}%",
                            actual_value=f"{pct_b['value']}%",
                            explanation=f"Same metric shows different percentages: {pct_a['value']}% vs {pct_b['value']}%",
                            confidence=0.85,
                            suggested_fix="Verify which percentage is correct and standardize"
                        ))
        
        return findings
    
    def _check_endpoint_consistency(self,
                                   section_claims: Dict[str, List[Dict]],
                                   protocol_data: Dict) -> List[CrossReferenceFinding]:
        """Check primary endpoint consistency"""
        findings = []
        
        # Get protocol endpoints
        primary_endpoints = protocol_data.get("endpoints", {}).get("primary", [])
        
        if not primary_endpoints:
            return findings
        
        protocol_pe = primary_endpoints[0].lower()
        
        # Check if all sections mentioning results reference the same endpoint
        for section, claims in section_claims.items():
            if "result" in section.lower() or "efficacy" in section.lower():
                # Check if endpoint is mentioned
                has_endpoint = any(protocol_pe in str(c.get("context", "")).lower() 
                                 for c in claims)
                
                if not has_endpoint and claims:  # Has claims but no endpoint
                    findings.append(CrossReferenceFinding(
                        inconsistency_type=InconsistencyType.ENDPOINT_MISMATCH,
                        severity=ConsistencySeverity.MEDIUM,
                        claim_a=f"Primary endpoint: {primary_endpoints[0]} (Protocol)",
                        claim_b=f"No endpoint mention in {section}",
                        section_a="Protocol",
                        section_b=section,
                        expected_value=primary_endpoints[0],
                        actual_value="Not mentioned",
                        explanation=f"{section} should reference primary endpoint: {primary_endpoints[0]}",
                        confidence=0.80,
                        suggested_fix=f"Add primary endpoint reference: {primary_endpoints[0]}"
                    ))
        
        return findings
    
    def _check_protocol_alignment(self,
                                 section_claims: Dict[str, List[Dict]],
                                 protocol_data: Dict) -> List[CrossReferenceFinding]:
        """Check alignment with protocol"""
        findings = []
        
        # Check enrollment numbers
        protocol_n = protocol_data.get("population", {}).get("planned_enrollment")
        if protocol_n:
            for section, claims in section_claims.items():
                n_claims = [c for c in claims if c["type"] == "n"]
                for claim in n_claims:
                    if abs(claim["value"] - protocol_n) > self.tolerance_n:
                        findings.append(CrossReferenceFinding(
                            inconsistency_type=InconsistencyType.SAMPLE_SIZE_MISMATCH,
                            severity=ConsistencySeverity.MEDIUM,
                            claim_a=f"{protocol_n} patients (Protocol)",
                            claim_b=f"{claim['value']} patients ({section})",
                            section_a="Protocol",
                            section_b=section,
                            expected_value=str(protocol_n),
                            actual_value=str(claim["value"]),
                            explanation=f"Sample size in {section} differs from protocol",
                            confidence=0.90,
                            suggested_fix=f"Update to {protocol_n} or explain discrepancy"
                        ))
        
        # Check phase
        protocol_phase = protocol_data.get("study_design", {}).get("phase", "")
        if protocol_phase:
            for section, content in section_claims.items():
                content_str = str(content)
                phase_match = re.search(r'Phase\s+([IV]+)', content_str, re.IGNORECASE)
                if phase_match:
                    claimed_phase = phase_match.group(1).upper()
                    if claimed_phase != protocol_phase:
                        findings.append(CrossReferenceFinding(
                            inconsistency_type=InconsistencyType.DEFINITION_MISMATCH,
                            severity=ConsistencySeverity.CRITICAL,
                            claim_a=f"Phase {protocol_phase} (Protocol)",
                            claim_b=f"Phase {claimed_phase} ({section})",
                            section_a="Protocol",
                            section_b=section,
                            expected_value=f"Phase {protocol_phase}",
                            actual_value=f"Phase {claimed_phase}",
                            explanation=f"Study phase mismatch with protocol",
                            confidence=0.99,
                            suggested_fix=f"Change to Phase {protocol_phase}"
                        ))
        
        return findings
    
    def _check_table_text_alignment(self,
                                   section_claims: Dict[str, List[Dict]],
                                   tables: Dict[str, Any]) -> List[CrossReferenceFinding]:
        """Check consistency between tables and text"""
        findings = []
        
        # Simplified check: ensure tables are referenced in text
        for table_id in tables.keys():
            referenced = False
            for section, claims in section_claims.items():
                content_str = str(claims)
                if re.search(rf'(?:Table|table)\s+{table_id}', content_str):
                    referenced = True
                    break
            
            if not referenced:
                findings.append(CrossReferenceFinding(
                    inconsistency_type=InconsistencyType.CITATION_MISMATCH,
                    severity=ConsistencySeverity.LOW,
                    claim_a=f"Table {table_id} exists",
                    claim_b=f"No reference to Table {table_id} in text",
                    section_a="Tables",
                    section_b="Text",
                    expected_value=f"Reference to Table {table_id}",
                    actual_value="No reference found",
                    explanation=f"Table {table_id} should be referenced in text",
                    confidence=0.80,
                    suggested_fix=f"Add '(Table {table_id})' reference in appropriate section"
                ))
        
        return findings
    
    def _check_citation_consistency(self, sections: Dict[str, str]) -> List[CrossReferenceFinding]:
        """Check internal citation consistency"""
        findings = []
        
        # Find all section references
        all_refs = defaultdict(list)
        
        for section_name, content in sections.items():
            # Find references like "Section 9.2" or "see Section 11"
            refs = re.findall(r'(?:Section|section)\s+(\d+(?:\.\d+)?)', content)
            for ref in refs:
                all_refs[ref].append(section_name)
        
        # Check if referenced sections exist
        section_numbers = set()
        for section_name in sections.keys():
            # Extract number from section name (e.g., "9. Study Design" -> "9")
            match = re.match(r'(\d+)', section_name)
            if match:
                section_numbers.add(match.group(1))
        
        for ref, citing_sections in all_refs.items():
            ref_base = ref.split('.')[0]
            if ref_base not in section_numbers:
                findings.append(CrossReferenceFinding(
                    inconsistency_type=InconsistencyType.NUMBERING_MISMATCH,
                    severity=ConsistencySeverity.MEDIUM,
                    claim_a=f"Reference to Section {ref}",
                    claim_b=f"Section {ref} not found",
                    section_a=citing_sections[0],
                    section_b="Missing",
                    expected_value=f"Section {ref}",
                    actual_value="Not found",
                    explanation=f"Reference to non-existent Section {ref}",
                    confidence=0.90,
                    suggested_fix=f"Create Section {ref} or correct reference"
                ))
        
        return findings
    
    def _same_metric(self, context_a: str, context_b: str) -> bool:
        """Check if two contexts refer to the same metric"""
        # Simplified: check for common keywords
        keywords_a = set(re.findall(r'\b\w+\b', context_a.lower()))
        keywords_b = set(re.findall(r'\b\w+\b', context_b.lower()))
        
        # Check for disease/endpoint keywords
        medical_terms = {"response", "survival", "progression", "adverse", "efficacy", 
                        "safety", "endpoint", "death", "hazard"}
        
        overlap = keywords_a & keywords_b & medical_terms
        return len(overlap) >= 1
    
    def _calculate_consistency_score(self, findings: List[CrossReferenceFinding]) -> float:
        """Calculate overall consistency score"""
        if not findings:
            return 100.0
        
        weights = {
            ConsistencySeverity.CRITICAL: 25,
            ConsistencySeverity.HIGH: 15,
            ConsistencySeverity.MEDIUM: 5,
            ConsistencySeverity.LOW: 1
        }
        
        penalty = sum(weights.get(f.severity, 5) for f in findings)
        return max(0, 100 - penalty)
    
    def _determine_risk_level(self, findings: List[CrossReferenceFinding]) -> str:
        """Determine consistency risk level"""
        critical = len([f for f in findings if f.severity == ConsistencySeverity.CRITICAL])
        high = len([f for f in findings if f.severity == ConsistencySeverity.HIGH])
        
        if critical > 0:
            return "CRITICAL"
        elif high > 0:
            return "HIGH"
        elif len([f for f in findings if f.severity == ConsistencySeverity.MEDIUM]) > 2:
            return "MEDIUM"
        else:
            return "LOW"


# Demo
if __name__ == "__main__":
    # Sample sections with inconsistencies
    sections = {
        "Methods": """
        9. STUDY DESIGN AND METHODS
        
        Approximately 600 patients were planned for enrollment.
        This was a Phase III study.
        """,
        
        "Results": """
        11. STUDY RESULTS
        
        A total of 599 patients were randomized.
        This Phase II study showed significant results.
        The response rate was 45% in the treatment group.
        See Table 1 for details.
        """,
        
        "Safety": """
        12. SAFETY EVALUATION
        
        Safety was evaluated in all 601 patients.
        The response rate was 48% in treated patients.
        """
    }
    
    protocol_data = {
        "study_design": {"phase": "III"},
        "population": {"planned_enrollment": 600},
        "endpoints": {"primary": ["Overall Survival"]}
    }
    
    tables = {"1": {"title": "Patient Disposition"}}
    
    # Run validation
    validator = CrossReferenceValidator()
    result = validator.execute({
        "sections": sections,
        "protocol_data": protocol_data,
        "tables": tables,
        "figures": {}
    })
    
    # Display results
    print("=" * 70)
    print("CROSS-REFERENCE VALIDATOR - AGENT 5")
    print("=" * 70)
    
    print(f"\n📊 Consistency Score: {result['consistency_score']}/100")
    print(f"⚠️  Risk Level: {result['risk_level']}")
    print(f"\n📈 Sections Checked: {result['sections_checked']}")
    print(f"🚨 Total Findings: {result['total_findings']}")
    print(f"   Critical: {result['critical']}")
    print(f"   High: {result['high']}")
    print(f"   Medium: {result['medium']}")
    print(f"   Low: {result['low']}")
    
    print(f"\n🔄 Requires Reconciliation: {'YES' if result['requires_reconciliation'] else 'NO'}")
    print(f"🤖 Auto-Fixable Issues: {result['auto_fixable']}")
    
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
        print(f"   {finding['section_a']}: {finding['claim_a']}")
        print(f"   {finding['section_b']}: {finding['claim_b']}")
        print(f"   Explanation: {finding['explanation']}")
        print(f"   Fix: {finding['fix']}")
    
    print("\n" + "=" * 70)
