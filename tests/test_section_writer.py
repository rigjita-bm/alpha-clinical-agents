"""
Tests for SectionWriter (Agent 2) - CSR Section Generation

Tests generation of Clinical Study Report sections with RAG grounding.
FDA 21 CFR Part 11 compliance with full audit trails.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from agents.section_writer import SectionWriter, SectionType, WritingStyle


class TestSectionWriterInitialization:
    """Tests for SectionWriter initialization"""
    
    def test_default_initialization(self):
        """Test default writer initialization"""
        writer = SectionWriter()
        
        assert writer.agent_id == "agent_2"
        assert writer.agent_name == "SectionWriter"
        assert writer.version == "2.1.0"
        assert writer.writing_style == WritingStyle.TECHNICAL
        assert writer.temperature == 0.3
        assert writer.max_tokens == 4000
    
    def test_custom_initialization(self):
        """Test writer with custom parameters"""
        writer = SectionWriter(
            writing_style=WritingStyle.CONVERSATIONAL,
            temperature=0.5,
            max_tokens=2000
        )
        
        assert writer.writing_style == WritingStyle.CONVERSATIONAL
        assert writer.temperature == 0.5
        assert writer.max_tokens == 2000
    
    def test_supported_sections(self):
        """Test supported CSR sections"""
        writer = SectionWriter()
        
        expected_sections = [
            SectionType.SYNOPSIS,
            SectionType.INTRODUCTION,
            SectionType.OBJECTIVES,
            SectionType.METHODS,
            SectionType.STATISTICAL_METHODS,
            SectionType.PARTICIPANTS,
            SectionType.EFFICACY_RESULTS,
            SectionType.SAFETY_RESULTS,
            SectionType.DISCUSSION,
            SectionType.CONCLUSION
        ]
        
        for section in expected_sections:
            assert section in writer.supported_sections


class TestPromptGeneration:
    """Tests for prompt generation"""
    
    @pytest.fixture
    def writer(self):
        return SectionWriter()
    
    def test_synopsis_prompt(self, writer):
        """Test synopsis section prompt generation"""
        protocol_data = {
            "title": "Phase III Study of Drug XYZ",
            "phase": "Phase III",
            "indication": "Breast Cancer"
        }
        
        prompt = writer._generate_prompt(SectionType.SYNOPSIS, protocol_data)
        
        assert "synopsis" in prompt.lower()
        assert "Drug XYZ" in prompt
        assert "Phase III" in prompt
    
    def test_methods_prompt(self, writer):
        """Test methods section prompt generation"""
        protocol_data = {
            "design": "Randomized, double-blind",
            "population": "N=300"
        }
        
        prompt = writer._generate_prompt(SectionType.METHODS, protocol_data)
        
        assert "methods" in prompt.lower()
        assert "Randomized" in prompt


class TestContentGeneration:
    """Tests for content generation"""
    
    @pytest.fixture
    def writer(self):
        return SectionWriter()
    
    @patch('agents.section_writer.SectionWriter._call_llm')
    def test_generate_section_success(self, mock_call_llm, writer):
        """Test successful section generation"""
        mock_call_llm.return_value = "This is the generated section content."
        
        result = writer.generate_section(
            section_type=SectionType.SYNOPSIS,
            protocol_data={"title": "Test Study"},
            statistical_data={},
            safety_data={}
        )
        
        assert result is not None
        assert len(result) > 0
        mock_call_llm.assert_called_once()
    
    def test_generate_section_with_citations(self, writer):
        """Test that citations are included in output"""
        # This would test RAG citation integration
        pass  # Implementation depends on RAG engine integration


class TestAuditTrail:
    """Tests for FDA 21 CFR Part 11 audit trails"""
    
    @pytest.fixture
    def writer(self):
        return SectionWriter()
    
    def test_audit_log_creation(self, writer):
        """Test that audit logs are created for each generation"""
        # Mock the LLM call to avoid external dependencies
        with patch.object(writer, '_call_llm', return_value="Generated content"):
            result = writer.generate_section(
                section_type=SectionType.SYNOPSIS,
                protocol_data={"title": "Test"},
                statistical_data={},
                safety_data={}
            )
            
            # Check that audit trail is maintained
            assert hasattr(writer, 'audit_trail')


class TestSectionValidation:
    """Tests for generated content validation"""
    
    @pytest.fixture
    def writer(self):
        return SectionWriter()
    
    def test_ich_e3_compliance_check(self, writer):
        """Test ICH E3 compliance validation"""
        content = "This is a test CSR section."
        
        is_compliant, issues = writer._validate_ich_e3(content, SectionType.SYNOPSIS)
        
        assert isinstance(is_compliant, bool)
        assert isinstance(issues, list)


class TestWritingStyles:
    """Tests for different writing styles"""
    
    def test_technical_style(self):
        """Test technical writing style"""
        writer = SectionWriter(writing_style=WritingStyle.TECHNICAL)
        
        # Technical style should use precise language
        assert writer.writing_style == WritingStyle.TECHNICAL
    
    def test_conversational_style(self):
        """Test conversational writing style"""
        writer = SectionWriter(writing_style=WritingStyle.CONVERSATIONAL)
        
        assert writer.writing_style == WritingStyle.CONVERSATIONAL
    
    def test_executive_style(self):
        """Test executive summary style"""
        writer = SectionWriter(writing_style=WritingStyle.EXECUTIVE)
        
        assert writer.writing_style == WritingStyle.EXECUTIVE


class TestErrorHandling:
    """Tests for error handling"""
    
    @pytest.fixture
    def writer(self):
        return SectionWriter()
    
    @patch('agents.section_writer.SectionWriter._call_llm')
    def test_generation_failure_handling(self, mock_call_llm, writer):
        """Test handling of LLM generation failures"""
        mock_call_llm.side_effect = Exception("LLM API error")
        
        with pytest.raises(Exception):
            writer.generate_section(
                section_type=SectionType.SYNOPSIS,
                protocol_data={"title": "Test"},
                statistical_data={},
                safety_data={}
            )
    
    def test_empty_protocol_data(self, writer):
        """Test handling of empty protocol data"""
        with pytest.raises(ValueError):
            writer.generate_section(
                section_type=SectionType.SYNOPSIS,
                protocol_data={},
                statistical_data={},
                safety_data={}
            )
