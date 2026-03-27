"""
Unit tests for ComplianceChecker Agent
Tests FDA 21 CFR Part 11 and ICH E3 compliance validation
"""
import pytest
from agents.compliance_checker import ComplianceChecker


class TestComplianceChecker:
    """Test suite for ComplianceChecker (Agent 4)"""
    
    def test_instantiation(self, compliance_checker):
        """Test agent can be instantiated"""
        assert compliance_checker.agent_id == "ComplianceChecker"
        assert compliance_checker.version == "1.0.0"
    
    def test_fda_structure_requirements(self, compliance_checker):
        """Test FDA structure requirements check"""
        compliant_doc = {
            "sections": ["TitlePage", "Synopsis", "Methodology", "Results", "Safety", "Conclusions", "References"]
        }
        result = compliance_checker._check_fda_structure(compliant_doc)
        assert result["compliant"] == True
        
        incomplete_doc = {
            "sections": ["TitlePage", "Results"]  # Missing critical sections
        }
        result = compliance_checker._check_fda_structure(incomplete_doc)
        assert result["compliant"] == False
        assert len(result["missing_sections"]) > 0
    
    def test_ich_e3_structure(self, compliance_checker):
        """Test ICH E3 structure compliance"""
        ich_compliant = {
            "sections": [
                "TitlePage", "Synopsis", "TableOfContents",
                "ListOfAbbreviations", "Ethics", "Investigators",
                "Methodology", "StudyPatients", "EfficacyResults",
                "SafetyResults", "Discussion", "Conclusions", "References"
            ]
        }
        result = compliance_checker._check_ich_e3_structure(ich_compliant)
        assert result["compliant"] == True
    
    def test_required_terminology_check(self, compliance_checker):
        """Test required terminology validation"""
        text_with_required = """
        The adverse events were coded using MedDRA version 25.0.
        The statistical analysis followed the Intent-to-treat principle.
        """
        result = compliance_checker._check_required_terminology(text_with_required)
        assert result["compliant"] == True
        
        text_missing = "This is a study report."  # Missing required terms
        result = compliance_checker._check_required_terminology(text_missing)
        assert result["compliant"] == False
    
    def test_prohibited_terminology_check(self, compliance_checker):
        """Test prohibited terminology detection"""
        text_with_prohibited = "The results prove that the drug works."
        result = compliance_checker._check_prohibited_terminology(text_with_prohibited)
        
        assert result["has_prohibited"] == True
        assert any("prove" in item["term"].lower() for item in result["violations"])
    
    def test_electronic_signature_check(self, compliance_checker):
        """Test electronic signature validation"""
        signed_doc = {
            "sections": {
                "TitlePage": {
                    "signed_by": "Dr. Smith",
                    "signature_date": "2026-03-27",
                    "signature_hash": "sha256:abc123"
                }
            }
        }
        result = compliance_checker._check_electronic_signatures(signed_doc)
        assert result["has_signatures"] == True
        assert result["valid"] == True
    
    def test_safety_reporting_compliance(self, compliance_checker):
        """Test safety reporting requirements"""
        complete_safety = {
            "deaths": {"count": 5, "reported": True},
            "serious_adverse_events": {"count": 25, "reported": True},
            "adverse_events": {"count": 150, "reported": True}
        }
        result = compliance_checker._check_safety_reporting(complete_safety)
        assert result["compliant"] == True
    
    def test_full_compliance_workflow(self, compliance_checker, sample_sections):
        """Test complete compliance validation"""
        input_data = {"drafts": sample_sections}
        result = compliance_checker.execute(input_data)
        
        assert "compliance_score" in result
        assert "findings" in result
        assert "critical_issues" in result
        assert isinstance(result["compliance_score"], (int, float))
    
    def test_compliance_score_range(self, compliance_checker):
        """Test that compliance score is within 0-100"""
        input_data = {"drafts": {"test": {"text": "Sample"}}}
        result = compliance_checker.execute(input_data)
        
        assert 0 <= result["compliance_score"] <= 100
    
    def test_critical_findings_detection(self, compliance_checker):
        """Test detection of critical compliance issues"""
        non_compliant = {
            "drafts": {
                "TitlePage": {"signed_by": None, "signature_date": None},  # Missing e-sig
                "Results": {"text": "The drug proves efficacy"}  # Prohibited term
            }
        }
        result = compliance_checker.execute(non_compliant)
        
        assert result["compliance_score"] < 50
        assert len(result["critical_issues"]) > 0
    
    def test_audit_trail(self, compliance_checker, sample_sections):
        """Test audit trail for compliance checks"""
        compliance_checker.execute({"drafts": sample_sections})
        audit = compliance_checker.get_audit_trail()
        
        assert len(audit) > 0
        assert any("compliance" in record["action"].lower() for record in audit)
