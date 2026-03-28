"""
Tests for RiskPredictor (Agent 9) - Pre-Execution Complexity Analysis

Tests risk prediction and complexity analysis for CSR generation.
Predicts problems before they happen.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from agents.risk_predictor import RiskPredictor, RiskAssessment, RiskLevel, ComplexityFactor


class TestRiskAssessmentDataclass:
    """Tests for RiskAssessment dataclass"""
    
    def test_assessment_creation(self):
        """Test creating risk assessment"""
        assessment = RiskAssessment(
            study_id="STUDY_001",
            risk_level=RiskLevel.MEDIUM,
            complexity_score=65.5,
            estimated_hours=120,
            recommended_agents=["ProtocolAnalyzer", "SectionWriter"]
        )
        
        assert assessment.study_id == "STUDY_001"
        assert assessment.risk_level == RiskLevel.MEDIUM
        assert assessment.complexity_score == 65.5
        assert assessment.estimated_hours == 120
        assert len(assessment.recommended_agents) == 2
        assert isinstance(assessment.assessed_at, datetime)
    
    def test_risk_factors(self):
        """Test risk factors tracking"""
        assessment = RiskAssessment(
            study_id="STUDY_002",
            risk_level=RiskLevel.HIGH,
            complexity_score=80.0,
            estimated_hours=200,
            risk_factors=["Multiple arms", "Adaptive design"]
        )
        
        assert len(assessment.risk_factors) == 2
        assert "Multiple arms" in assessment.risk_factors


class TestRiskPredictorInitialization:
    """Tests for RiskPredictor initialization"""
    
    def test_default_initialization(self):
        """Test default predictor initialization"""
        predictor = RiskPredictor()
        
        assert predictor.agent_id == "agent_9"
        assert predictor.agent_name == "RiskPredictor"
        assert predictor.version == "2.1.0"
        assert predictor.high_risk_threshold == 70.0
        assert predictor.critical_risk_threshold == 90.0


class TestComplexityAnalysis:
    """Tests for complexity analysis"""
    
    @pytest.fixture
    def predictor(self):
        return RiskPredictor()
    
    def test_analyze_protocol_length(self, predictor):
        """Test complexity based on protocol length"""
        short_protocol = "Short protocol text."
        long_protocol = "Long protocol text. " * 1000
        
        short_score = predictor._analyze_protocol_length(short_protocol)
        long_score = predictor._analyze_protocol_length(long_protocol)
        
        assert long_score > short_score
    
    def test_analyze_study_design(self, predictor):
        """Test complexity based on study design"""
        simple_design = "Single arm study."
        complex_design = "Randomized, double-blind, adaptive, multi-arm study with Bayesian analysis."
        
        simple_score = predictor._analyze_study_design(simple_design)
        complex_score = predictor._analyze_study_design(complex_design)
        
        assert complex_score > simple_score
    
    def test_detect_adaptive_design(self, predictor):
        """Test detection of adaptive designs"""
        protocol = "This is an adaptive design study."
        
        has_adaptive = predictor._detect_adaptive_design(protocol)
        
        assert has_adaptive is True
    
    def test_detect_multiple_arms(self, predictor):
        """Test detection of multiple arms"""
        protocol = "Three-arm randomized study comparing drug A, B, and placebo."
        
        arm_count = predictor._count_arms(protocol)
        
        assert arm_count >= 3


class TestRiskLevelAssignment:
    """Tests for risk level assignment"""
    
    @pytest.fixture
    def predictor(self):
        return RiskPredictor()
    
    def test_low_risk(self, predictor):
        """Test LOW risk assignment"""
        level = predictor._assign_risk_level(30.0)
        
        assert level == RiskLevel.LOW
    
    def test_medium_risk(self, predictor):
        """Test MEDIUM risk assignment"""
        level = predictor._assign_risk_level(50.0)
        
        assert level == RiskLevel.MEDIUM
    
    def test_high_risk(self, predictor):
        """Test HIGH risk assignment"""
        level = predictor._assign_risk_level(75.0)
        
        assert level == RiskLevel.HIGH
    
    def test_critical_risk(self, predictor):
        """Test CRITICAL risk assignment"""
        level = predictor._assign_risk_level(95.0)
        
        assert level == RiskLevel.CRITICAL


class TestTimeEstimation:
    """Tests for time estimation"""
    
    @pytest.fixture
    def predictor(self):
        return RiskPredictor()
    
    def test_estimate_time_low_complexity(self, predictor):
        """Test time estimate for low complexity"""
        hours = predictor._estimate_hours(30.0, "single_arm")
        
        assert hours < 50
    
    def test_estimate_time_high_complexity(self, predictor):
        """Test time estimate for high complexity"""
        hours = predictor._estimate_hours(80.0, "adaptive_multi_arm")
        
        assert hours > 100


class TestAgentRecommendation:
    """Tests for agent recommendations"""
    
    @pytest.fixture
    def predictor(self):
        return RiskPredictor()
    
    def test_recommend_agents_simple(self, predictor):
        """Test agent recommendation for simple study"""
        recommendations = predictor._recommend_agents(
            complexity_score=30.0,
            has_adaptive=False,
            arm_count=1
        )
        
        # Simple studies need fewer agents
        assert len(recommendations) >= 3
    
    def test_recommend_agents_complex(self, predictor):
        """Test agent recommendation for complex study"""
        recommendations = predictor._recommend_agents(
            complexity_score=80.0,
            has_adaptive=True,
            arm_count=4
        )
        
        # Complex studies need all agents
        assert len(recommendations) >= 10
        assert "MetaValidator" in recommendations
        assert "HallucinationDetector" in recommendations


class TestFullAssessment:
    """Tests for complete risk assessment"""
    
    @pytest.fixture
    def predictor(self):
        return RiskPredictor()
    
    def test_assess_simple_protocol(self, predictor):
        """Test assessment of simple protocol"""
        protocol = """
        Phase II single-arm study of Drug X in 50 patients.
        Primary endpoint: Response rate.
        """
        
        assessment = predictor.assess_risk(
            study_id="STUDY_SIMPLE",
            protocol_text=protocol
        )
        
        assert isinstance(assessment, RiskAssessment)
        assert assessment.study_id == "STUDY_SIMPLE"
        assert assessment.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
        assert assessment.complexity_score < 70.0
    
    def test_assess_complex_protocol(self, predictor):
        """Test assessment of complex protocol"""
        protocol = """
        Phase III randomized, double-blind, adaptive, multi-arm study
        comparing experimental drug, active control, and placebo.
        Bayesian adaptive design with interim analyses.
        Multiple endpoints including OS, PFS, ORR.
        500 patients across 50 sites globally.
        """
        
        assessment = predictor.assess_risk(
            study_id="STUDY_COMPLEX",
            protocol_text=protocol
        )
        
        assert assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert assessment.complexity_score > 70.0
        assert assessment.estimated_hours > 150


class TestWarningGeneration:
    """Tests for warning generation"""
    
    @pytest.fixture
    def predictor(self):
        return RiskPredictor()
    
    def test_generate_warnings(self, predictor):
        """Test warning generation"""
        warnings = predictor._generate_warnings(
            complexity_score=85.0,
            has_adaptive=True,
            arm_count=4,
            has_interim=True
        )
        
        assert len(warnings) > 0
        assert any("adaptive" in w.lower() for w in warnings)
        assert any("complex" in w.lower() for w in warnings)


class TestRiskLevelEnum:
    """Tests for RiskLevel enum"""
    
    def test_risk_level_values(self):
        """Test risk level enum values"""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"
    
    def test_risk_level_ordering(self):
        """Test risk level ordering"""
        assert RiskLevel.LOW < RiskLevel.MEDIUM
        assert RiskLevel.MEDIUM < RiskLevel.HIGH
        assert RiskLevel.HIGH < RiskLevel.CRITICAL


class TestComplexityFactorEnum:
    """Tests for ComplexityFactor enum"""
    
    def test_factor_values(self):
        """Test complexity factor values"""
        assert ComplexityFactor.PROTOCOL_LENGTH.value == "protocol_length"
        assert ComplexityFactor.STUDY_DESIGN.value == "study_design"
        assert ComplexityFactor.PATIENT_COUNT.value == "patient_count"
        assert ComplexityFactor.ENDPOINT_COUNT.value == "endpoint_count"
