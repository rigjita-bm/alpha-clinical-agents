"""
Unit tests for CrossReferenceValidator Agent
Tests cross-section consistency validation
"""
import pytest
from agents.cross_reference_validator import CrossReferenceValidator


class TestCrossReferenceValidator:
    """Test suite for CrossReferenceValidator (Agent 5)"""
    
    def test_instantiation(self, cross_ref_validator):
        """Test agent can be instantiated"""
        assert cross_ref_validator.agent_id == "CrossReferenceValidator"
        assert cross_ref_validator.version == "1.0.0"
    
    def test_sample_size_consistency(self, cross_ref_validator):
        """Test sample size consistency across sections"""
        sections = {
            "Methods": {"text": "600 patients were randomized", "n": 600},
            "Results": {"text": "599 patients completed the study", "n": 599},
            "Safety": {"text": "All 600 patients were included in safety analysis", "n": 600}
        }
        
        result = cross_ref_validator._check_sample_size_consistency(sections)
        
        assert result["consistent"] == False
        assert len(result["discrepancies"]) > 0
    
    def test_percentage_consistency(self, cross_ref_validator):
        """Test percentage calculation consistency"""
        sections = {
            "Results": {
                "text": "Response rate was 45% (135/300)"
            }
        }
        
        result = cross_ref_validator._check_percentage_consistency(sections)
        # 135/300 = 45%, should be consistent
        assert result["consistent"] == True
        
        # Inconsistent percentage
        sections = {
            "Results": {
                "text": "Response rate was 50% (120/300)"  # Wrong calculation
            }
        }
        result = cross_ref_validator._check_percentage_consistency(sections)
        assert result["consistent"] == False
    
    def test_endpoint_reference_consistency(self, cross_ref_validator):
        """Test endpoint references are consistent"""
        protocol = {"endpoints": {"primary": ["Overall Survival", "Progression-Free Survival"]}}
        sections = {
            "Methods": {"text": "Primary endpoints: OS and PFS"},
            "Results": {"text": "OS analysis showed... PFS analysis showed..."}
        }
        
        result = cross_ref_validator._check_endpoint_references(protocol, sections)
        assert result["consistent"] == True
    
    def test_citation_tracking(self, cross_ref_validator):
        """Test that citations are tracked correctly"""
        sections = {
            "Results": {
                "text": "As shown in Table 1, the results were significant. See also Figure 2."
            }
        }
        
        result = cross_ref_validator._extract_citations(sections)
        
        assert "Table 1" in result["citations"]
        assert "Figure 2" in result["citations"]
    
    def test_protocol_alignment(self, cross_ref_validator):
        """Test alignment with protocol specifications"""
        protocol = {
            "phase": "Phase III",
            "planned_enrollment": 600,
            "treatment_duration": "12 months"
        }
        sections = {
            "Methods": {
                "phase": "Phase II",  # Mismatch!
                "enrollment": 600,
                "duration": "12 months"
            }
        }
        
        result = cross_ref_validator._check_protocol_alignment(protocol, sections)
        
        assert result["aligned"] == False
        assert any("phase" in issue["field"].lower() for issue in result["mismatches"])
    
    def test_full_validation_workflow(self, cross_ref_validator, sample_sections):
        """Test complete cross-reference validation"""
        input_data = {
            "drafts": sample_sections,
            "protocol": {"planned_enrollment": 600}
        }
        result = cross_ref_validator.execute(input_data)
        
        assert "consistency_score" in result
        assert "inconsistencies" in result
        assert isinstance(result["consistency_score"], (int, float))
    
    def test_table_figure_numbering(self, cross_ref_validator):
        """Test table and figure numbering consistency"""
        sections = {
            "Results": {
                "text": "Table 1 shows baseline. Table 3 shows results."  # Missing Table 2
            }
        }
        
        result = cross_ref_validator._check_table_figure_numbering(sections)
        
        assert result["consistent"] == False
        assert any("Table 2" in gap for gap in result["gaps"])
    
    def test_audit_trail(self, cross_ref_validator, sample_sections):
        """Test audit trail recording"""
        cross_ref_validator.execute({"drafts": sample_sections})
        audit = cross_ref_validator.get_audit_trail()
        
        assert len(audit) > 0
