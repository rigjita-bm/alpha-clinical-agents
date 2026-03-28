"""
Integration layer for Figure Processor with CSR pipeline.

Bridges Agent 12 (FigureProcessor) with Agent 2 (SectionWriter).
"""

import logging
from typing import Dict, List, Any
from pathlib import Path

from .models import ExtractedData
from .processor import FigureProcessor

logger = logging.getLogger(__name__)


class MultiModalCSRIntegration:
    """
    Integration layer for including figure narratives in CSR generation.
    
    This bridges the Figure Processor with the Section Writer agent.
    """
    
    SECTION_HEADERS = {
        "efficacy_results": "### 14.2 Efficacy Results\n\n",
        "safety_results": "### 13.2 Safety Results\n\n",
        "study_design": "### 9.2 Study Design\n\n",
        "demographics": "### 10.1 Demographics\n\n",
        "other": "### Additional Figures\n\n"
    }
    
    def __init__(self, figure_processor: FigureProcessor):
        self.figure_processor = figure_processor
        self.section_mapping = {
            "km_curve": "efficacy_results",  # Section 14.2
            "forest_plot": "efficacy_results",  # Section 14.2.1
            "consort": "study_design",  # Section 9.2
            "ae_waterfall": "safety_results",  # Section 13.2
            "table": "demographics"  # Section 10
        }
    
    def process_tlf_package(
        self,
        tlf_files: List[Dict[str, Any]],  # List of {path, caption, type}
        study_id: str
    ) -> Dict[str, List[ExtractedData]]:
        """
        Process complete TLF (Tables, Listings, Figures) package.
        
        Returns data organized by CSR section.
        """
        section_data = {
            "efficacy_results": [],
            "safety_results": [],
            "study_design": [],
            "demographics": [],
            "other": []
        }
        
        for tlf in tlf_files:
            try:
                # Read image file
                path = Path(tlf['path'])
                if not path.exists():
                    logger.error(f"File not found: {tlf['path']}")
                    continue
                    
                with open(path, 'rb') as f:
                    image_data = f.read()
                
                # Process figure
                result = self.figure_processor.process_figure(
                    image_data=image_data,
                    caption=tlf.get('caption', ''),
                    study_id=study_id,
                    source_file=str(path)
                )
                
                # Route to appropriate section
                section = self.section_mapping.get(result.figure_metadata.figure_type, "other")
                section_data[section].append(result)
                
            except Exception as e:
                logger.error(f"Error processing TLF {tlf.get('path', 'unknown')}: {e}")
                continue
        
        # Remove empty sections
        return {k: v for k, v in section_data.items() if v}
    
    def generate_section_narrative(
        self,
        section_name: str,
        figures: List[ExtractedData]
    ) -> str:
        """
        Generate complete narrative for a CSR section.
        
        Combines multiple figure narratives into coherent section text.
        """
        if not figures:
            return ""
        
        narratives = [f.narrative_description for f in figures]
        header = self.SECTION_HEADERS.get(section_name, f"### {section_name}\n\n")
        
        return header + "\n\n".join(narratives)
    
    def generate_full_csr_figures_section(self, section_data: Dict[str, List[ExtractedData]]) -> str:
        """
        Generate complete figures section for CSR.
        
        Args:
            section_data: Output from process_tlf_package()
            
        Returns:
            Complete formatted figures section text
        """
        sections = []
        
        # Order matters for CSR structure
        for section_name in ["study_design", "demographics", "efficacy_results", "safety_results", "other"]:
            if section_name in section_data and section_data[section_name]:
                section_text = self.generate_section_narrative(section_name, section_data[section_name])
                sections.append(section_text)
        
        return "\n\n".join(sections)
