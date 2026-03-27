"""
Unit tests for ProtocolAnalyzer Agent
Tests protocol parsing, study design extraction, and complexity scoring
"""
import pytest
from agents.protocol_analyzer import ProtocolAnalyzer


class TestProtocolAnalyzer:
    """Test suite for ProtocolAnalyzer (Agent 1)"""
    
    def test_instantiation(self, protocol_analyzer):
        """Test agent can be instantiated"""
        assert protocol_analyzer.agent_id == "ProtocolAnalyzer"
        assert protocol_analyzer.version == "1.0.0"
    
    def test_extract_phase(self, protocol_analyzer):
        """Test phase extraction from protocol"""
        protocol = "Phase III randomized trial of Drug X in cancer patients"
        result = protocol_analyzer._extract_phase(protocol)
        assert result == "Phase III"
    
    def test_extract_study_design(self, protocol_analyzer):
        """Test study design extraction"""
        protocol = "Randomized, double-blind, placebo-controlled, parallel-group study"
        result = protocol_analyzer._extract_study_design(protocol)
        
        assert result["randomized"] == True
        assert result["blinding"] == "double-blind"
        assert result["control_type"] == "placebo"
    
    def test_extract_enrollment(self, protocol_analyzer):
        """Test enrollment number extraction"""
        protocol = "Planned enrollment: 600 patients"
        result = protocol_analyzer._extract_enrollment(protocol)
        assert result == 600
        
        protocol = "N = 450 subjects will be enrolled"
        result = protocol_analyzer._extract_enrollment(protocol)
        assert result == 450
    
    def test_extract_endpoints(self, protocol_analyzer):
        """Test endpoint extraction"""
        protocol = """
        Primary endpoint: Overall survival
        Secondary endpoints: Progression-free survival, objective response rate, quality of life
        """
        result = protocol_analyzer._extract_endpoints(protocol)
        
        assert result["primary"] == ["Overall survival"]
        assert "Progression-free survival" in result["secondary"]
        assert len(result["secondary"]) == 3
    
    def test_calculate_complexity_score(self, protocol_analyzer):
        """Test complexity scoring"""
        # Simple study
        simple = {"phase": "Phase II", "endpoints": {"primary": ["OS"], "secondary": []}}
        score = protocol_analyzer._calculate_complexity(simple)
        assert score < 5.0  # Should be low complexity
        
        # Complex study
        complex_study = {
            "phase": "Phase III",
            "study_design": {"adaptive": True, "multi_arm": True},
            "endpoints": {"primary": ["OS", "PFS"], "secondary": ["ORR", "QoL", "Biomarker"]},
            "population": {"stratification": ["age", "gender", "biomarker"]}
        }
        score = protocol_analyzer._calculate_complexity(complex_study)
        assert score > 6.0  # Should be high complexity
    
    def test_full_analysis_workflow(self, protocol_analyzer, sample_protocol):
        """Test complete protocol analysis"""
        result = protocol_analyzer.execute({"protocol_text": sample_protocol})
        
        assert result["phase"] == "Phase III"
        assert result["planned_enrollment"] == 600
        assert "study_design" in result
        assert "endpoints" in result
        assert "complexity_score" in result
        assert result["extraction_confidence"] > 0.8
    
    def test_confidence_scoring(self, protocol_analyzer):
        """Test confidence scoring for extraction"""
        # Clear protocol
        clear = "Phase III, randomized, double-blind study. N=600. Primary: OS."
        result = protocol_analyzer.execute({"protocol_text": clear})
        assert result["extraction_confidence"] > 0.9
        
        # Ambiguous protocol
        ambiguous = "Clinical study of a new drug"
        result = protocol_analyzer.execute({"protocol_text": ambiguous})
        assert result["extraction_confidence"] < 0.7
    
    def test_audit_trail(self, protocol_analyzer, sample_protocol):
        """Test audit trail recording"""
        protocol_analyzer.execute({"protocol_text": sample_protocol})
        audit = protocol_analyzer.get_audit_trail()
        
        assert len(audit) > 0
        assert audit[0]["agent_id"] == "ProtocolAnalyzer"
        assert "input_hash" in audit[0]
        assert "output_hash" in audit[0]
    
    def test_error_handling(self, protocol_analyzer):
        """Test error handling for invalid input"""
        result = protocol_analyzer.execute({"protocol_text": ""})
        
        assert "error" in result or "status" in result
        assert protocol_analyzer.status.value in ["completed", "error"]
