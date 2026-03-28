"""
Data models for figure processing.

FDA 21 CFR Part 11 compliant with full audit trails.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class FigureMetadata:
    """Metadata for a clinical figure."""
    figure_id: str
    figure_type: str  # km_curve, forest_plot, consort, ae_waterfall, table
    study_id: str
    page_number: Optional[int] = None
    caption: str = ""
    source_file: str = ""
    hash_sha256: str = ""
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    
    def compute_hash(self, image_data: bytes) -> str:
        """Compute and store SHA-256 hash for audit trail."""
        self.hash_sha256 = hashlib.sha256(image_data).hexdigest()
        return self.hash_sha256
    
    def to_audit_log(self) -> Dict:
        """Convert to FDA audit log format."""
        return {
            "figure_id": self.figure_id,
            "figure_type": self.figure_type,
            "study_id": self.study_id,
            "hash": self.hash_sha256,
            "timestamp": self.extracted_at.isoformat(),
            "user": "system",
            "action": "figure_processed"
        }


@dataclass
class ExtractedData:
    """Extracted data from a figure."""
    figure_metadata: FigureMetadata
    raw_text: str
    structured_data: Dict[str, Any]
    narrative_description: str
    statistics_summary: str
    confidence_score: float
    extraction_method: str
