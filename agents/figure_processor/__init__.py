"""
Figure Processor Module for Alpha Clinical Agents.

Multi-Modal Figures-to-Text conversion for clinical studies.
FDA 21 CFR Part 11 compliant.
"""

from .models import FigureMetadata, ExtractedData
from .extractors import KMExtractor, ForestPlotExtractor, ConsortExtractor
from .processor import FigureProcessor
from .integration import MultiModalCSRIntegration

__all__ = [
    "FigureMetadata",
    "ExtractedData", 
    "KMExtractor",
    "ForestPlotExtractor",
    "ConsortExtractor",
    "FigureProcessor",
    "MultiModalCSRIntegration"
]
