import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from agents import (
    ProtocolAnalyzer, SectionWriter, StatisticalValidator, FactChecker,
    ComplianceChecker, CrossReferenceValidator, HumanCoordinator, 
    FinalCompiler, ConflictResolver, RiskPredictor, MetaValidator, 
    HallucinationDetector
)

@pytest.fixture
def protocol_analyzer():
    return ProtocolAnalyzer()

@pytest.fixture
def section_writer():
    return SectionWriter()

@pytest.fixture
def statistical_validator():
    return StatisticalValidator()

@pytest.fixture
def compliance_checker():
    return ComplianceChecker()

@pytest.fixture
def cross_ref_validator():
    return CrossReferenceValidator()

@pytest.fixture
def human_coordinator():
    return HumanCoordinator()

@pytest.fixture
def final_compiler():
    return FinalCompiler()

@pytest.fixture
def conflict_resolver():
    return ConflictResolver()

@pytest.fixture
def risk_predictor():
    return RiskPredictor()

@pytest.fixture
def meta_validator():
    return MetaValidator()

@pytest.fixture
def hallucination_detector():
    return HallucinationDetector()

@pytest.fixture
def fact_checker():
    return FactChecker()

@pytest.fixture
def sample_protocol():
    return """
    Phase III, randomized, double-blind, placebo-controlled study
    to evaluate the efficacy and safety of Drug XYZ in patients
    with advanced non-small cell lung cancer.
    
    Planned enrollment: 600 patients
    Primary endpoint: Overall survival
    Secondary endpoints: Progression-free survival, objective response rate
    Treatment duration: Until disease progression or unacceptable toxicity
    """

@pytest.fixture
def sample_sections():
    return {
        "Methods": """
        A total of 600 patients were randomized in a 1:1 ratio to receive
        either Drug XYZ (n=300) or placebo (n=300).
        The median age was 65 years (range: 18-85).
        """,
        "Results": """
        The median overall survival was 18.5 months in the Drug XYZ group
        compared to 12.3 months in the placebo group (HR 0.72, 95% CI: 0.58-0.89, p=0.003).
        The objective response rate was 45% (95% CI: 39%-51%) vs 28% (95% CI: 23%-33%).
        """,
        "Safety": """
        Treatment-related adverse events occurred in 85% of patients receiving Drug XYZ
        vs 62% receiving placebo. Grade 3-4 adverse events occurred in 35% vs 22%.
        No treatment-related deaths occurred.
        """
    }
