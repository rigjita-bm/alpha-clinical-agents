"""
Agents Module - 12 Clinical Document Automation Agents

Complete agent ecosystem for FDA-compliant clinical document generation:

Content Generation Agents:
- ProtocolAnalyzer (Agent 1): Extracts study design from protocols
- SectionWriter (Agent 2): Generates CSR sections

Validation Agents:
- StatisticalValidator (Agent 3): Validates numbers, p-values, HRs, CIs
- FactChecker (Agent 3.5): Verifies claims against sources
- ComplianceChecker (Agent 4): FDA 21 CFR 11, ICH E3 validation
- CrossReferenceValidator (Agent 5): Cross-section consistency

Coordination Agents:
- HumanCoordinator (Agent 6): Review workflow management
- FinalCompiler (Agent 7): FDA-ready package assembly
- ConflictResolver (Agent 8): Mediates agent disagreements
- RiskPredictor (Agent 9): Pre-execution complexity analysis

Quality Assurance Agents:
- MetaValidator (Agent 10): QA layer - validates ALL agents
- HallucinationDetector (Agent 11): Multi-layer hallucination detection
"""

from .protocol_analyzer import ProtocolAnalyzer
from .section_writer import SectionWriter
from .statistical_validator import StatisticalValidator
from .fact_checker import FactChecker
from .compliance_checker import ComplianceChecker
from .cross_reference_validator import CrossReferenceValidator
from .human_coordinator import HumanCoordinator
from .final_compiler import FinalCompiler
from .conflict_resolver import ConflictResolver
from .risk_predictor import RiskPredictor
from .meta_validator import MetaValidator
from .hallucination_detector import HallucinationDetector

__all__ = [
    # Content Generation
    'ProtocolAnalyzer',
    'SectionWriter',
    
    # Validation
    'StatisticalValidator',
    'FactChecker',
    'ComplianceChecker',
    'CrossReferenceValidator',
    
    # Coordination
    'HumanCoordinator',
    'FinalCompiler',
    'ConflictResolver',
    'RiskPredictor',
    
    # Quality Assurance
    'MetaValidator',
    'HallucinationDetector',
]

__version__ = "2.0.0"
__agents_count__ = 12
