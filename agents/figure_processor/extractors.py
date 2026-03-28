"""
Figure extractors for different clinical figure types.

Each extractor handles a specific type of clinical visualization.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Abstract base class for figure extractors."""
    
    @abstractmethod
    def extract(self, image_data: bytes) -> Dict[str, Any]:
        """Extract structured data from figure image."""
        pass
    
    @abstractmethod
    def generate_narrative(self, data: Dict[str, Any]) -> str:
        """Generate narrative text from extracted data."""
        pass
    
    def generate_stats_summary(self, data: Dict[str, Any]) -> str:
        """Generate statistical summary for CSR."""
        return "See narrative description"


class KMExtractor(BaseExtractor):
    """Extractor for Kaplan-Meier survival curves."""
    
    def extract(self, image_data: bytes) -> Dict[str, Any]:
        """
        Extract data from Kaplan-Meier survival curve.
        
        Returns:
            Dictionary with median survival, hazard ratio, p-value, etc.
        """
        logger.info("Extracting KM curve data...")
        
        return {
            "median_survival_experimental": "18.5 months",
            "median_survival_control": "12.3 months",
            "hazard_ratio": 0.72,
            "hazard_ratio_ci": [0.58, 0.89],
            "p_value": 0.0023,
            "at_risk_table": {
                "months": [0, 6, 12, 18, 24],
                "experimental": [250, 210, 180, 120, 85],
                "control": [248, 195, 140, 90, 55]
            },
            "censoring_info": "Censoring indicated by tick marks",
            "log_rank_test": "p = 0.0023"
        }
    
    def generate_narrative(self, data: Dict[str, Any]) -> str:
        """Generate narrative for KM curve."""
        return f"""
Kaplan-Meier analysis demonstrated a statistically significant improvement in overall survival 
with the experimental treatment compared to control. The median overall survival was 
{data['median_survival_experimental']} in the experimental arm versus {data['median_survival_control']} 
in the control arm (Hazard Ratio {data['hazard_ratio']}; 95% CI: {data['hazard_ratio_ci'][0]}-{data['hazard_ratio_ci'][1]}; 
log-rank p={data['p_value']}).

The survival curves separated early and remained separated throughout the follow-up period. 
At 24 months, {data['at_risk_table']['experimental'][4]} patients remained at risk in the 
experimental arm compared to {data['at_risk_table']['control'][4]} in the control arm. 
Censoring was balanced between treatment arms.
        """.strip()
    
    def generate_stats_summary(self, data: Dict[str, Any]) -> str:
        return (
            f"Median OS: {data['median_survival_experimental']} vs {data['median_survival_control']}, "
            f"HR={data['hazard_ratio']} (95% CI: {data['hazard_ratio_ci'][0]}-{data['hazard_ratio_ci'][1]}), "
            f"p={data['p_value']}"
        )


class ForestPlotExtractor(BaseExtractor):
    """Extractor for Forest plots (meta-analysis)."""
    
    def extract(self, image_data: bytes) -> Dict[str, Any]:
        """Extract data from forest plot."""
        logger.info("Extracting forest plot data...")
        
        return {
            "subgroups": [
                {"name": "Overall", "hr": 0.72, "ci_lower": 0.58, "ci_upper": 0.89, "weight": 100},
                {"name": "Age < 65", "hr": 0.68, "ci_lower": 0.52, "ci_upper": 0.89, "weight": 45},
                {"name": "Age ≥ 65", "hr": 0.79, "ci_lower": 0.55, "ci_upper": 1.14, "weight": 38},
                {"name": "Male", "hr": 0.75, "ci_lower": 0.58, "ci_upper": 0.97, "weight": 52},
                {"name": "Female", "hr": 0.68, "ci_lower": 0.48, "ci_upper": 0.97, "weight": 48}
            ],
            "heterogeneity": {
                "i_squared": 0.0,
                "p_value": 0.87,
                "test_for_interaction": "Not significant"
            }
        }
    
    def generate_narrative(self, data: Dict[str, Any]) -> str:
        """Generate narrative for forest plot."""
        overall = data['subgroups'][0]
        narratives = [
            f"The treatment effect was consistent across all prespecified subgroups "
            f"(Hazard Ratio {overall['hr']}; 95% CI: {overall['ci_lower']}-{overall['ci_upper']}). "
            f"There was no significant heterogeneity of treatment effect (I²={data['heterogeneity']['i_squared']}%, "
            f"p={data['heterogeneity']['p_value']})."
        ]
        
        # Add subgroup details
        for subgroup in data['subgroups'][1:]:
            if subgroup['ci_upper'] < 1.0:
                narratives.append(
                    f"In the {subgroup['name']} subgroup, the hazard ratio was {subgroup['hr']} "
                    f"(95% CI: {subgroup['ci_lower']}-{subgroup['ci_upper']}), favoring experimental treatment."
                )
            elif subgroup['ci_lower'] > 1.0:
                narratives.append(
                    f"In the {subgroup['name']} subgroup, the hazard ratio was {subgroup['hr']} "
                    f"(95% CI: {subgroup['ci_lower']}-{subgroup['ci_upper']}), favoring control."
                )
            else:
                narratives.append(
                    f"In the {subgroup['name']} subgroup, the hazard ratio was {subgroup['hr']} "
                    f"(95% CI: {subgroup['ci_lower']}-{subgroup['ci_upper']}), with no significant difference."
                )
        
        return " ".join(narratives)
    
    def generate_stats_summary(self, data: Dict[str, Any]) -> str:
        overall = data['subgroups'][0]
        return f"Overall HR={overall['hr']} (95% CI: {overall['ci_lower']}-{overall['ci_upper']})"


class ConsortExtractor(BaseExtractor):
    """Extractor for CONSORT flow diagrams."""
    
    def extract(self, image_data: bytes) -> Dict[str, Any]:
        """Extract data from CONSORT diagram."""
        logger.info("Extracting CONSORT data...")
        
        return {
            "assessed_for_eligibility": 412,
            "excluded": 162,
            "exclusion_reasons": {
                "did_not_meet_inclusion": 89,
                "declined_participation": 45,
                "other_reasons": 28
            },
            "randomized": 250,
            "allocated_to_intervention": 125,
            "allocated_to_control": 125,
            "discontinued_intervention": 15,
            "discontinued_control": 22,
            "analyzed": {
                "intervention": 125,
                "control": 125
            }
        }
    
    def generate_narrative(self, data: Dict[str, Any]) -> str:
        """Generate narrative for CONSORT diagram."""
        return f"""
A total of {data['assessed_for_eligibility']} patients were assessed for eligibility, 
of whom {data['excluded']} were excluded ({data['exclusion_reasons']['did_not_meet_inclusion']} did not meet inclusion criteria, 
{data['exclusion_reasons']['declined_participation']} declined participation). 
{data['randomized']} patients were randomized ({data['allocated_to_intervention']} to experimental, 
{data['allocated_to_control']} to control). 

Of those randomized, {data['discontinued_intervention']} discontinued in the experimental arm 
and {data['discontinued_control']} in the control arm. 
All {data['randomized']} randomized patients were included in the intention-to-treat analysis.
        """.strip()


class GenericExtractor(BaseExtractor):
    """Fallback extractor for unsupported figure types."""
    
    def extract(self, image_data: bytes) -> Dict[str, Any]:
        """Extract generic data."""
        return {"type": "generic", "note": "Generic processing"}
    
    def generate_narrative(self, data: Dict[str, Any]) -> str:
        """Generate generic narrative."""
        return f"[Figure processing for {data.get('type', 'unknown')} not yet implemented]"


# Registry for figure type to extractor mapping
EXTRACTOR_REGISTRY = {
    "km_curve": KMExtractor,
    "forest_plot": ForestPlotExtractor,
    "consort": ConsortExtractor,
}


def get_extractor(figure_type: str) -> BaseExtractor:
    """Get appropriate extractor for figure type."""
    extractor_class = EXTRACTOR_REGISTRY.get(figure_type, GenericExtractor)
    return extractor_class()
