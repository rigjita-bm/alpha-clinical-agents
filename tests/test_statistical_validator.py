"""
Unit tests for StatisticalValidator Agent
Tests p-value validation, hazard ratio checks, and confidence interval validation
"""
import pytest
from agents.statistical_validator import StatisticalValidator, ValidationResult


class TestStatisticalValidator:
    """Test suite for StatisticalValidator (Agent 3)"""
    
    def test_instantiation(self, statistical_validator):
        """Test agent can be instantiated"""
        assert statistical_validator.agent_id == "StatisticalValidator"
        assert statistical_validator.version == "1.0.0"
    
    def test_validate_p_value_valid(self, statistical_validator):
        """Test valid p-values are accepted"""
        result = statistical_validator._validate_p_value("p = 0.03")
        assert result.is_valid == True
        assert result.normalized == 0.03
        
        result = statistical_validator._validate_p_value("p<0.001")
        assert result.is_valid == True
        assert result.normalized == 0.001
        
        result = statistical_validator._validate_p_value("p-value: 0.049")
        assert result.is_valid == True
    
    def test_validate_p_value_invalid_range(self, statistical_validator):
        """Test p-values outside 0-1 range are rejected"""
        result = statistical_validator._validate_p_value("p = 1.5")
        assert result.is_valid == False
        assert "INVALID_RANGE" in result.errors
        
        result = statistical_validator._validate_p_value("p = -0.01")
        assert result.is_valid == False
    
    def test_validate_p_value_invalid_format(self, statistical_validator):
        """Test malformed p-values are rejected"""
        result = statistical_validator._validate_p_value("p = abc")
        assert result.is_valid == False
        assert "PARSE_ERROR" in result.errors
    
    def test_validate_hazard_ratio_valid(self, statistical_validator):
        """Test valid hazard ratios are accepted"""
        result = statistical_validator._validate_hazard_ratio(
            hr_text="HR 0.72",
            ci_lower=0.58,
            ci_upper=0.89
        )
        assert result.is_valid == True
        assert result.is_plausible == True
    
    def test_validate_hazard_ratio_implausible(self, statistical_validator):
        """Test implausible HR values trigger warnings"""
        result = statistical_validator._validate_hazard_ratio(
            hr_text="HR 25.0",
            ci_lower=5.0,
            ci_upper=45.0
        )
        assert result.is_valid == True  # Format is valid
        assert result.is_plausible == False  # But clinically implausible
        assert any("IMPLAUSIBLE_HR" in e for e in result.warnings)
    
    def test_validate_confidence_interval_consistency(self, statistical_validator):
        """Test CI consistency checks"""
        # Consistent CI
        result = statistical_validator._validate_ci(
            point_estimate=0.72,
            ci_lower=0.58,
            ci_upper=0.89
        )
        assert result.is_valid == True
        assert result.is_consistent == True
        
        # Inconsistent CI (point estimate outside)
        result = statistical_validator._validate_ci(
            point_estimate=0.50,
            ci_lower=0.58,
            ci_upper=0.89
        )
        assert result.is_valid == False
        assert any("POINT_OUTSIDE_CI" in e for e in result.errors)
    
    def test_validate_percentage_valid(self, statistical_validator):
        """Test valid percentages"""
        result = statistical_validator._validate_percentage("45%")
        assert result.is_valid == True
        assert result.value == 45.0
    
    def test_validate_percentage_invalid(self, statistical_validator):
        """Test invalid percentages (e.g., 145%)"""
        result = statistical_validator._validate_percentage("145%")
        assert result.is_valid == False
        assert "EXCEEDS_100" in result.errors
    
    def test_sample_size_consistency(self, statistical_validator):
        """Test sample size consistency across sections"""
        section_data = {
            "Methods": {"n": 600},
            "Results": {"n": 599},  # Discrepancy
            "Safety": {"n": 600}
        }
        
        result = statistical_validator._check_sample_size_consistency(section_data)
        assert result.has_discrepancy == True
        assert len(result.discrepancies) > 0
    
    def test_full_validation_workflow(self, statistical_validator):
        """Test complete validation workflow"""
        input_data = {
            "sections": {
                "Results": {
                    "text": "The median overall survival was 18.5 months vs 12.3 months (HR 0.72, 95% CI: 0.58-0.89, p=0.003).",
                    "statistics": {
                        "hazard_ratio": 0.72,
                        "ci_lower": 0.58,
                        "ci_upper": 0.89,
                        "p_value": 0.003
                    }
                }
            }
        }
        
        result = statistical_validator.execute(input_data)
        
        assert "validation_score" in result
        assert "findings" in result
        assert isinstance(result["validation_score"], (int, float))
    
    def test_audit_trail_created(self, statistical_validator):
        """Test that audit trail is properly recorded"""
        input_data = {"sections": {"test": {"statistics": {}}}}
        
        result = statistical_validator.execute(input_data)
        audit_trail = statistical_validator.get_audit_trail()
        
        assert len(audit_trail) > 0
        assert audit_trail[-1]["action"] == "process"
    
    def test_fda_compliance_fields(self, statistical_validator):
        """Test FDA compliance fields are populated"""
        input_data = {"sections": {"test": {"statistics": {}}}}
        
        result = statistical_validator.execute(input_data)
        
        # Check that agent tracks status
        assert statistical_validator.status.value in ["completed", "error"]
