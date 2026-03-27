"""
Compliance Checker - Agent 4
Validates FDA 21 CFR Part 11, ICH E3, and regulatory compliance
"""

import re
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from core.base_agent import BaseAgent


class ComplianceRule(Enum):
    FDA_21CFR11 = "fda_21cfr11"
    ICH_E3 = "ich_e3"
    ICH_E6 = "ich_e6"
    ICH_E9 = "ich_e9"
    GCP = "gcp"


class ComplianceSeverity(Enum):
    CRITICAL = "critical"  # Regulatory submission blocker
    MAJOR = "major"  # Must fix before submission
    MINOR = "minor"  # Should fix for quality
    OBSERVATION = "observation"  # Best practice


class ComplianceCategory(Enum):
    ELECTRONIC_SIGNATURES = "electronic_signatures"
    AUDIT_TRAIL = "audit_trail"
    DATA_INTEGRITY = "data_integrity"
    DOCUMENT_STRUCTURE = "document_structure"
    REQUIRED_CONTENT = "required_content"
    TERMINOLOGY = "terminology"
    SAFETY_REPORTING = "safety_reporting"


@dataclass
class ComplianceFinding:
    """A compliance finding"""
    rule: ComplianceRule
    category: ComplianceCategory
    severity: ComplianceSeverity
    requirement: str
    finding: str
    location: str
    explanation: str
    regulation_ref: str
    suggested_fix: str
    
    def to_dict(self) -> Dict:
        return {
            "rule": self.rule.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "requirement": self.requirement,
            "finding": self.finding,
            "location": self.location,
            "explanation": self.explanation,
            "regulation": self.regulation_ref,
            "fix": self.suggested_fix
        }


class ComplianceChecker(BaseAgent):
    """
    Agent 4: Compliance Checker
    
    Validates clinical documents against regulatory requirements:
    - FDA 21 CFR Part 11 (electronic records/signatures)
    - ICH E3 (Structure and Content of Clinical Study Reports)
    - ICH E6 (Good Clinical Practice)
    - ICH E9 (Statistical Principles)
    
    Output: Compliance report with findings and remediation guidance
    """
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(
            agent_id="ComplianceChecker",
            version="1.0.0",
            config=config
        )
        
        # Load regulatory requirements
        self.requirements = self._load_requirements()
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main compliance validation logic
        
        Args:
            input_data: {
                "document": str,
                "document_type": str,  # "CSR", "Protocol", etc.
                "section_name": str,
                "metadata": Dict
            }
        """
        document = input_data.get("document", "")
        document_type = input_data.get("document_type", "CSR")
        section_name = input_data.get("section_name", "")
        metadata = input_data.get("metadata", {})
        
        findings = []
        
        # Run all compliance checks
        findings.extend(self._check_ich_e3_structure(document, document_type))
        findings.extend(self._check_required_terminology(document, document_type))
        findings.extend(self._check_safety_reporting(document, document_type))
        findings.extend(self._check_fda_21cfr11(metadata))
        findings.extend(self._check_statistical_compliance(document, document_type))
        findings.extend(self._check_cross_reference_completeness(document))
        
        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(findings)
        risk_level = self._determine_risk_level(findings)
        
        # Generate remediation plan
        remediation = self._generate_remediation_plan(findings)
        
        return {
            "document_type": document_type,
            "section_name": section_name,
            "compliance_score": compliance_score,  # 0-100
            "risk_level": risk_level,
            "total_findings": len(findings),
            "critical": len([f for f in findings if f.severity == ComplianceSeverity.CRITICAL]),
            "major": len([f for f in findings if f.severity == ComplianceSeverity.MAJOR]),
            "minor": len([f for f in findings if f.severity == ComplianceSeverity.MINOR]),
            "observation": len([f for f in findings if f.severity == ComplianceSeverity.OBSERVATION]),
            "findings": [f.to_dict() for f in findings],
            "remediation_plan": remediation,
            "submission_ready": risk_level == "LOW" and compliance_score >= 90,
            "requires_regulatory_review": risk_level in ["CRITICAL", "MAJOR"]
        }
    
    def _load_requirements(self) -> Dict:
        """Load regulatory requirements database"""
        return {
            ComplianceRule.ICH_E3: {
                "required_sections": {
                    "CSR": [
                        "Title Page", "Synopsis", "Table of Contents",
                        "List of Abbreviations", "Ethics", "Investigators",
                        "Study Participants", "Treatments", "Efficacy",
                        "Safety", "Discussion", "Conclusions", "References",
                        "Tables", "Figures", "Appendices"
                    ]
                },
                "section_numbering": {
                    "Study Design": "9",
                    "Study Objectives": "8",
                    "Efficacy Results": "11",
                    "Safety Results": "12"
                },
                "required_tables": [
                    "Demographic Characteristics",
                    "Efficacy Results",
                    "Adverse Events"
                ]
            },
            ComplianceRule.FDA_21CFR11: {
                "requires_electronic_signature": True,
                "requires_audit_trail": True,
                "requires_data_integrity": True
            },
            ComplianceRule.ICH_E6: {
                "requires_informed_consent": True,
                "requires_ethics_approval": True,
                "requires_safety_reporting": True
            }
        }
    
    def _check_ich_e3_structure(self, document: str, 
                                document_type: str) -> List[ComplianceFinding]:
        """Check ICH E3 structural requirements"""
        findings = []
        
        # Check required sections
        required_sections = self.requirements[ComplianceRule.ICH_E3]["required_sections"].get(document_type, [])
        
        section_patterns = {
            "Title Page": r'(?i)title\s+page|clinical\s+study\s+report',
            "Synopsis": r'(?i)synopsis|executive\s+summary',
            "Efficacy": r'(?i)efficacy\s+results|10\.\s*efficacy',
            "Safety": r'(?i)safety\s+results|12\.\s*safety',
            "Discussion": r'(?i)discussion|13\.\s*discussion',
            "Conclusions": r'(?i)conclusions|14\.\s*conclusions'
        }
        
        for section in required_sections[:6]:  # Check key sections
            pattern = section_patterns.get(section, rf'(?i){section}')
            if not re.search(pattern, document):
                findings.append(ComplianceFinding(
                    rule=ComplianceRule.ICH_E3,
                    category=ComplianceCategory.DOCUMENT_STRUCTURE,
                    severity=ComplianceSeverity.MAJOR,
                    requirement=f"Section '{section}' required per ICH E3",
                    finding=f"Missing required section: {section}",
                    location="Document structure",
                    explanation=f"ICH E3 requires '{section}' in {document_type}",
                    regulation_ref="ICH E3 Section 2",
                    suggested_fix=f"Add {section} section per ICH E3 guidelines"
                ))
        
        # Check ICH E3 section numbering
        if "9." in document and "Study Design" in document:
            if not re.search(r'9\.\d+\s+Study\s+Design', document):
                findings.append(ComplianceFinding(
                    rule=ComplianceRule.ICH_E3,
                    category=ComplianceCategory.DOCUMENT_STRUCTURE,
                    severity=ComplianceSeverity.MINOR,
                    requirement="ICH E3 section numbering",
                    finding="Section numbering may not follow ICH E3",
                    location="Section headers",
                    explanation="ICH E3 recommends specific numbering (9.x for Study Design)",
                    regulation_ref="ICH E3 Section 9",
                    suggested_fix="Use ICH E3 standard numbering (9.1, 9.2, etc.)"
                ))
        
        return findings
    
    def _check_required_terminology(self, document: str, 
                                   document_type: str) -> List[ComplianceFinding]:
        """Check required regulatory terminology"""
        findings = []
        
        # Terms that should be used
        required_terms = {
            "adverse event": "treatment-emergent adverse event",
            "serious adverse event": "serious adverse event (SAE)",
            "intent-to-treat": "intent-to-treat (ITT)"
        }
        
        # Check for discouraged terms
        discouraged_patterns = [
            (r'\bside\s+effect\b', "side effect", "adverse event"),
            (r'\bplacebo\s+arm\b', "placebo arm", "placebo group"),
            (r'\bdrug\s+arm\b', "drug arm", "treatment group")
        ]
        
        for pattern, found_term, suggested in discouraged_patterns:
            if re.search(pattern, document, re.IGNORECASE):
                findings.append(ComplianceFinding(
                    rule=ComplianceRule.ICH_E3,
                    category=ComplianceCategory.TERMINOLOGY,
                    severity=ComplianceSeverity.MINOR,
                    requirement="ICH E3 preferred terminology",
                    finding=f"Discouraged term: '{found_term}'",
                    location=f"Found in document",
                    explanation=f"ICH E3 recommends using '{suggested}' instead of '{found_term}'",
                    regulation_ref="ICH E3 Section 11-12",
                    suggested_fix=f"Replace '{found_term}' with '{suggested}'"
                ))
        
        # Check for E2A safety terms if Safety section present
        if re.search(r'(?i)safety|adverse\s+event', document):
            e2a_terms = ["treatment-emergent", "serious adverse event", "SADE"]
            for term in e2a_terms:
                if not re.search(rf'(?i)\b{re.escape(term)}\b', document):
                    findings.append(ComplianceFinding(
                        rule=ComplianceRule.ICH_E6,
                        category=ComplianceCategory.TERMINOLOGY,
                        severity=ComplianceSeverity.MINOR,
                        requirement="ICH E2A safety terminology",
                        finding=f"Missing safety term: '{term}'",
                        location="Safety section",
                        explanation=f"ICH E2A recommends using '{term}' in safety reporting",
                        regulation_ref="ICH E2A",
                        suggested_fix=f"Add '{term}' where appropriate in safety reporting"
                    ))
        
        return findings
    
    def _check_safety_reporting(self, document: str, 
                               document_type: str) -> List[ComplianceFinding]:
        """Check safety reporting requirements"""
        findings = []
        
        # Check if safety section exists
        has_safety = re.search(r'(?i)12\.\s*safety|safety\s+(?:evaluation|results)', document)
        
        if has_safety:
            # Required safety elements per ICH E3
            safety_requirements = [
                (r'(?i)extent\s+of\s+exposure', "Extent of exposure"),
                (r'(?i)adverse\s+event.*?table', "Adverse events table"),
                (r'(?i)serious\s+adverse\s+event', "Serious adverse events"),
                (r'(?i)death', "Deaths"),
                (r'(?i)laboratory', "Laboratory findings")
            ]
            
            for pattern, requirement in safety_requirements:
                if not re.search(pattern, document):
                    severity = ComplianceSeverity.MAJOR if requirement in ["Deaths", "Serious adverse events"] else ComplianceSeverity.MINOR
                    findings.append(ComplianceFinding(
                        rule=ComplianceRule.ICH_E3,
                        category=ComplianceCategory.SAFETY_REPORTING,
                        severity=severity,
                        requirement=f"Safety section must include {requirement}",
                        finding=f"Missing safety element: {requirement}",
                        location="Safety section",
                        explanation=f"ICH E3 Section 12 requires {requirement}",
                        regulation_ref="ICH E3 Section 12",
                        suggested_fix=f"Add {requirement} subsection to safety"
                    ))
        
        return findings
    
    def _check_fda_21cfr11(self, metadata: Dict) -> List[ComplianceFinding]:
        """Check FDA 21 CFR Part 11 compliance"""
        findings = []
        
        # Check for electronic signature
        if not metadata.get("electronic_signature"):
            findings.append(ComplianceFinding(
                rule=ComplianceRule.FDA_21CFR11,
                category=ComplianceCategory.ELECTRONIC_SIGNATURES,
                severity=ComplianceSeverity.CRITICAL,
                requirement="21 CFR Part 11.50 - Electronic signatures",
                finding="Missing electronic signature",
                location="Document metadata",
                explanation="FDA requires electronic signatures on official records",
                regulation_ref="21 CFR 11.50",
                suggested_fix="Add electronic signature with meaning and date"
            ))
        
        # Check for audit trail
        if not metadata.get("audit_trail"):
            findings.append(ComplianceFinding(
                rule=ComplianceRule.FDA_21CFR11,
                category=ComplianceCategory.AUDIT_TRAIL,
                severity=ComplianceSeverity.MAJOR,
                requirement="21 CFR Part 11.10 - Audit trail",
                finding="Missing audit trail",
                location="Document metadata",
                explanation="FDA requires audit trails for electronic records",
                regulation_ref="21 CFR 11.10",
                suggested_fix="Enable audit trail tracking"
            ))
        
        return findings
    
    def _check_statistical_compliance(self, document: str, 
                                     document_type: str) -> List[ComplianceFinding]:
        """Check ICH E9 statistical compliance"""
        findings = []
        
        # Check for primary analysis specification
        if re.search(r'(?i)primary\s+endpoint', document):
            if not re.search(r'(?i)primary\s+analysis|statistical\s+analysis\s+plan', document):
                findings.append(ComplianceFinding(
                    rule=ComplianceRule.ICH_E9,
                    category=ComplianceCategory.REQUIRED_CONTENT,
                    severity=ComplianceSeverity.MAJOR,
                    requirement="ICH E9 - Statistical analysis description",
                    finding="Missing primary analysis method description",
                    location="Statistical Methods or Results",
                    explanation="ICH E9 requires description of primary analysis method",
                    regulation_ref="ICH E9 Section 3",
                    suggested_fix="Add statistical analysis methodology including primary analysis"
                ))
        
        # Check for alpha level
        if re.search(r'(?i)statistically\s+significant', document):
            if not re.search(r'(?i)alpha\s*=|significance\s+level|p\s*<\s*0\.05', document):
                findings.append(ComplianceFinding(
                    rule=ComplianceRule.ICH_E9,
                    category=ComplianceCategory.REQUIRED_CONTENT,
                    severity=ComplianceSeverity.MINOR,
                    requirement="ICH E9 - Significance level",
                    finding="Missing significance level (alpha)",
                    location="Statistical Methods",
                    explanation="ICH E9 recommends stating significance level",
                    regulation_ref="ICH E9 Section 3.2",
                    suggested_fix="Add significance level (e.g., α = 0.05)"
                ))
        
        return findings
    
    def _check_cross_reference_completeness(self, document: str) -> List[ComplianceFinding]:
        """Check cross-reference completeness"""
        findings = []
        
        # Find all table references
        table_refs = re.findall(r'(?:Table|table)\s+(\d+)', document)
        figure_refs = re.findall(r'(?:Figure|figure)\s+(\d+)', document)
        section_refs = re.findall(r'(?:Section|section)\s+(\d+\.\d*)', document)
        
        # Check if referenced items exist (simplified check)
        for table_num in set(table_refs):
            if not re.search(rf'(?:Table|TABLE)\s+{table_num}\s*[:\n]', document):
                findings.append(ComplianceFinding(
                    rule=ComplianceRule.ICH_E3,
                    category=ComplianceCategory.DOCUMENT_STRUCTURE,
                    severity=ComplianceSeverity.MINOR,
                    requirement="ICH E3 - Cross-references",
                    finding=f"Table {table_num} referenced but not found",
                    location=f"Reference to Table {table_num}",
                    explanation="All referenced tables should be included in document",
                    regulation_ref="ICH E3 Section 16",
                    suggested_fix=f"Add Table {table_num} or remove reference"
                ))
        
        return findings
    
    def _calculate_compliance_score(self, findings: List[ComplianceFinding]) -> float:
        """Calculate overall compliance score"""
        if not findings:
            return 100.0
        
        weights = {
            ComplianceSeverity.CRITICAL: 30,
            ComplianceSeverity.MAJOR: 15,
            ComplianceSeverity.MINOR: 5,
            ComplianceSeverity.OBSERVATION: 1
        }
        
        penalty = sum(weights.get(f.severity, 5) for f in findings)
        return max(0, 100 - penalty)
    
    def _determine_risk_level(self, findings: List[ComplianceFinding]) -> str:
        """Determine compliance risk level"""
        critical = len([f for f in findings if f.severity == ComplianceSeverity.CRITICAL])
        major = len([f for f in findings if f.severity == ComplianceSeverity.MAJOR])
        
        if critical > 0:
            return "CRITICAL"
        elif major > 0:
            return "MAJOR"
        elif len([f for f in findings if f.severity == ComplianceSeverity.MINOR]) > 5:
            return "MINOR"
        else:
            return "LOW"
    
    def _generate_remediation_plan(self, findings: List[ComplianceFinding]) -> Dict:
        """Generate remediation plan"""
        critical_fixes = [f for f in findings if f.severity == ComplianceSeverity.CRITICAL]
        major_fixes = [f for f in findings if f.severity == ComplianceSeverity.MAJOR]
        minor_fixes = [f for f in findings if f.severity == ComplianceSeverity.MINOR]
        
        return {
            "critical_fixes": len(critical_fixes),
            "major_fixes": len(major_fixes),
            "minor_fixes": len(minor_fixes),
            "estimated_remediation_time": f"{len(critical_fixes) * 2 + len(major_fixes) * 1 + len(minor_fixes) * 0.5} hours",
            "priority_actions": [f.suggested_fix for f in critical_fixes[:3]]
        }


# Demo
if __name__ == "__main__":
    # Sample document with compliance issues
    sample_document = """
CLINICAL STUDY REPORT

Title Page

SYNOPSIS

This study evaluated the safety and side effects of Drug X in patients.

9. STUDY DESIGN

This was a randomized trial.

11. EFFICACY

Statistically significant improvement was observed (p=0.003).

12. SAFETY EVALUATION

Side effects were reported in 15% of patients. No serious events noted.

See Table 5 for details.
"""
    
    metadata = {
        "electronic_signature": False,
        "audit_trail": False
    }
    
    # Run compliance check
    checker = ComplianceChecker()
    result = checker.execute({
        "document": sample_document,
        "document_type": "CSR",
        "section_name": "Full Document",
        "metadata": metadata
    })
    
    # Display results
    print("=" * 70)
    print("COMPLIANCE CHECKER - AGENT 4")
    print("=" * 70)
    
    print(f"\n📋 Document Type: {result['document_type']}")
    print(f"📊 Compliance Score: {result['compliance_score']}/100")
    print(f"⚠️  Risk Level: {result['risk_level']}")
    print(f"\n📈 Total Findings: {result['total_findings']}")
    print(f"   Critical: {result['critical']}")
    print(f"   Major: {result['major']}")
    print(f"   Minor: {result['minor']}")
    print(f"   Observation: {result['observation']}")
    
    print(f"\n✅ Submission Ready: {'YES' if result['submission_ready'] else 'NO'}")
    print(f"👤 Requires Regulatory Review: {'YES' if result['requires_regulatory_review'] else 'NO'}")
    
    print("\n" + "=" * 70)
    print("REMEDIATION PLAN:")
    print("=" * 70)
    print(f"Critical fixes: {result['remediation_plan']['critical_fixes']}")
    print(f"Major fixes: {result['remediation_plan']['major_fixes']}")
    print(f"Minor fixes: {result['remediation_plan']['minor_fixes']}")
    print(f"Estimated time: {result['remediation_plan']['estimated_remediation_time']}")
    
    if result['remediation_plan']['priority_actions']:
        print("\nPriority Actions:")
        for action in result['remediation_plan']['priority_actions']:
            print(f"  • {action}")
    
    print("\n" + "=" * 70)
    print("DETAILED FINDINGS:")
    print("=" * 70)
    
    for finding in result['findings']:
        severity_icon = {
            "critical": "🔴",
            "major": "🟠",
            "minor": "🟡",
            "observation": "🔵"
        }.get(finding['severity'], "⚪")
        
        print(f"\n{severity_icon} [{finding['severity'].upper()}] {finding['rule']}")
        print(f"   Category: {finding['category']}")
        print(f"   Finding: {finding['finding']}")
        print(f"   Regulation: {finding['regulation']}")
        print(f"   Fix: {finding['fix']}")
    
    print("\n" + "=" * 70)
