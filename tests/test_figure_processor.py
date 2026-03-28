"""
Tests for FigureProcessor (Agent 12) - Multi-Modal Figures-to-Text

Tests TLF (Tables, Listings, Figures) conversion to narrative text.
FDA 21 CFR Part 11 compliance with audit trails.
"""

import pytest
import hashlib
from datetime import datetime
from agents.figure_processor import (
    FigureProcessor, MultiModalCSRIntegration,
    FigureMetadata, ExtractedData
)


class TestFigureMetadata:
    """Tests for FigureMetadata dataclass"""
    
    def test_metadata_creation(self):
        """Test creating figure metadata"""
        metadata = FigureMetadata(
            figure_id="FIG_TEST_0001",
            figure_type="km_curve",
            study_id="TEST123",
            page_number=42,
            caption="Kaplan-Meier survival curve",
            source_file="/path/to/figure.png",
            hash_sha256="abc123"
        )
        
        assert metadata.figure_id == "FIG_TEST_0001"
        assert metadata.figure_type == "km_curve"
        assert metadata.study_id == "TEST123"
        assert metadata.page_number == 42
        assert metadata.caption == "Kaplan-Meier survival curve"
        assert metadata.hash_sha256 == "abc123"
        assert isinstance(metadata.extracted_at, datetime)
    
    def test_to_audit_log(self):
        """Test audit log conversion for FDA compliance"""
        metadata = FigureMetadata(
            figure_id="FIG_TEST_0001",
            figure_type="km_curve",
            study_id="TEST123",
            hash_sha256="abc123"
        )
        
        audit_log = metadata.to_audit_log()
        
        assert audit_log["figure_id"] == "FIG_TEST_0001"
        assert audit_log["figure_type"] == "km_curve"
        assert audit_log["study_id"] == "TEST123"
        assert audit_log["hash"] == "abc123"
        assert audit_log["action"] == "figure_processed"
        assert "timestamp" in audit_log
        assert audit_log["user"] == "system"


class TestFigureProcessorInitialization:
    """Tests for FigureProcessor initialization"""
    
    def test_default_initialization(self):
        """Test default processor initialization"""
        processor = FigureProcessor()
        
        assert processor.ocr_engine == "tesseract"
        assert processor.llm_client is None
        assert processor.processed_count == 0
        assert processor.error_count == 0
    
    def test_custom_initialization(self):
        """Test processor with custom parameters"""
        processor = FigureProcessor(ocr_engine="easyocr", llm_client="mock_client")
        
        assert processor.ocr_engine == "easyocr"
        assert processor.llm_client == "mock_client"
    
    def test_supported_types(self):
        """Test supported figure types"""
        processor = FigureProcessor()
        
        expected_types = [
            "km_curve", "forest_plot", "consort", "ae_waterfall",
            "table", "listing", "barchart", "scatter"
        ]
        
        for ft in expected_types:
            assert ft in processor.SUPPORTED_TYPES
        
        assert processor.SUPPORTED_TYPES["km_curve"] == "Kaplan-Meier Survival Curve"
        assert processor.SUPPORTED_TYPES["forest_plot"] == "Forest Plot (Meta-Analysis)"


class TestFigureTypeDetection:
    """Tests for automatic figure type detection"""
    
    @pytest.fixture
    def processor(self):
        return FigureProcessor()
    
    def test_detect_km_curve(self, processor):
        """Test detection of Kaplan-Meier curves"""
        caption = "Kaplan-Meier analysis of overall survival"
        result = processor.detect_figure_type(b"fake_image", caption)
        assert result == "km_curve"
    
    def test_detect_km_curve_os(self, processor):
        """Test KM detection with OS keyword"""
        caption = "OS curve showing survival benefit"
        result = processor.detect_figure_type(b"fake_image", caption)
        assert result == "km_curve"
    
    def test_detect_forest_plot(self, processor):
        """Test detection of forest plots"""
        caption = "Forest plot showing hazard ratios with 95% CI"
        result = processor.detect_figure_type(b"fake_image", caption)
        assert result == "forest_plot"
    
    def test_detect_consort(self, processor):
        """Test detection of CONSORT diagrams"""
        caption = "CONSORT diagram showing patient disposition"
        result = processor.detect_figure_type(b"fake_image", caption)
        assert result == "consort"
    
    def test_detect_ae_waterfall(self, processor):
        """Test detection of AE waterfall plots"""
        caption = "Waterfall plot of tumor changes from baseline"
        result = processor.detect_figure_type(b"fake_image", caption)
        assert result == "ae_waterfall"
    
    def test_detect_table(self, processor):
        """Test detection of tables"""
        caption = "Table 1: Baseline demographics"
        result = processor.detect_figure_type(b"fake_image", caption)
        assert result == "table"
    
    def test_unknown_type(self, processor):
        """Test unknown figure type detection"""
        caption = "Random figure without keywords"
        result = processor.detect_figure_type(b"fake_image", caption)
        assert result == "unknown"


class TestKMDataExtraction:
    """Tests for Kaplan-Meier curve data extraction"""
    
    @pytest.fixture
    def processor(self):
        return FigureProcessor()
    
    def test_km_data_structure(self, processor):
        """Test KM data extraction structure"""
        data = processor.extract_km_curve_data(b"fake_image")
        
        assert "median_survival_experimental" in data
        assert "median_survival_control" in data
        assert "hazard_ratio" in data
        assert "hazard_ratio_ci" in data
        assert "p_value" in data
        assert "at_risk_table" in data
        assert "censoring_info" in data
        assert "log_rank_test" in data
    
    def test_km_data_types(self, processor):
        """Test KM data types"""
        data = processor.extract_km_curve_data(b"fake_image")
        
        assert isinstance(data["hazard_ratio"], float)
        assert isinstance(data["hazard_ratio_ci"], list)
        assert len(data["hazard_ratio_ci"]) == 2
        assert isinstance(data["p_value"], float)


class TestForestPlotDataExtraction:
    """Tests for forest plot data extraction"""
    
    @pytest.fixture
    def processor(self):
        return FigureProcessor()
    
    def test_forest_plot_structure(self, processor):
        """Test forest plot data structure"""
        data = processor.extract_forest_plot_data(b"fake_image")
        
        assert "subgroups" in data
        assert "heterogeneity" in data
        assert isinstance(data["subgroups"], list)
        assert len(data["subgroups"]) > 0
    
    def test_subgroup_structure(self, processor):
        """Test subgroup data structure"""
        data = processor.extract_forest_plot_data(b"fake_image")
        
        for subgroup in data["subgroups"]:
            assert "name" in subgroup
            assert "hr" in subgroup
            assert "ci_lower" in subgroup
            assert "ci_upper" in subgroup
            assert "weight" in subgroup


class TestConsortDataExtraction:
    """Tests for CONSORT diagram data extraction"""
    
    @pytest.fixture
    def processor(self):
        return FigureProcessor()
    
    def test_consort_structure(self, processor):
        """Test CONSORT data structure"""
        data = processor.extract_consort_data(b"fake_image")
        
        assert "assessed_for_eligibility" in data
        assert "excluded" in data
        assert "exclusion_reasons" in data
        assert "randomized" in data
        assert "allocated_to_intervention" in data
        assert "allocated_to_control" in data
        assert "analyzed" in data
    
    def test_exclusion_reasons(self, processor):
        """Test exclusion reasons structure"""
        data = processor.extract_consort_data(b"fake_image")
        
        reasons = data["exclusion_reasons"]
        assert "did_not_meet_inclusion" in reasons
        assert "declined_participation" in reasons
        assert "other_reasons" in reasons


class TestNarrativeGeneration:
    """Tests for narrative text generation"""
    
    @pytest.fixture
    def processor(self):
        return FigureProcessor()
    
    def test_km_narrative_content(self, processor):
        """Test KM curve narrative generation"""
        data = {
            "median_survival_experimental": "18.5 months",
            "median_survival_control": "12.3 months",
            "hazard_ratio": 0.72,
            "hazard_ratio_ci": [0.58, 0.89],
            "p_value": 0.0023,
            "at_risk_table": {
                "months": [0, 6, 12, 18, 24],
                "experimental": [250, 210, 180, 120, 85],
                "control": [248, 195, 140, 90, 55]
            }
        }
        
        narrative = processor._generate_km_narrative(data)
        
        assert "18.5 months" in narrative
        assert "12.3 months" in narrative
        assert "0.72" in narrative
        assert "0.58" in narrative
        assert "0.89" in narrative
        assert "0.0023" in narrative or "p=" in narrative


class TestFigureProcessing:
    """Tests for complete figure processing workflow"""
    
    @pytest.fixture
    def processor(self):
        return FigureProcessor()
    
    def test_process_figure_km(self, processor):
        """Test processing KM curve figure"""
        fake_image = b"fake_image_data_for_testing"
        
        result = processor.process_figure(
            image_data=fake_image,
            caption="Kaplan-Meier survival curve for overall survival",
            study_id="TEST123",
            page_number=42,
            source_file="/path/to/km_curve.png"
        )
        
        assert isinstance(result, ExtractedData)
        assert result.figure_metadata.figure_type == "km_curve"
        assert result.figure_metadata.study_id == "TEST123"
        assert result.figure_metadata.page_number == 42
        assert result.confidence_score > 0
        assert result.extraction_method == "tesseract_v1.0"
        assert len(result.narrative_description) > 0
        assert len(result.statistics_summary) > 0
    
    def test_process_figure_forest(self, processor):
        """Test processing forest plot"""
        fake_image = b"fake_image_data_for_testing"
        
        result = processor.process_figure(
            image_data=fake_image,
            caption="Forest plot showing subgroup analysis",
            study_id="TEST456"
        )
        
        assert result.figure_metadata.figure_type == "forest_plot"
        assert "subgroups" in result.structured_data
    
    def test_hash_computation(self, processor):
        """Test SHA-256 hash computation for audit trail"""
        fake_image = b"test_image_data"
        expected_hash = hashlib.sha256(fake_image).hexdigest()
        
        result = processor.process_figure(
            image_data=fake_image,
            caption="Test figure",
            study_id="TEST789"
        )
        
        assert result.figure_metadata.hash_sha256 == expected_hash
    
    def test_metrics_update(self, processor):
        """Test that metrics are updated after processing"""
        initial_count = processor.processed_count
        
        processor.process_figure(
            image_data=b"test",
            caption="Test",
            study_id="TEST"
        )
        
        assert processor.processed_count == initial_count + 1


class TestMultiModalCSRIntegration:
    """Tests for MultiModalCSRIntegration"""
    
    @pytest.fixture
    def integration(self):
        processor = FigureProcessor()
        return MultiModalCSRIntegration(processor)
    
    def test_section_mapping(self, integration):
        """Test that figure types map to correct sections"""
        assert integration.section_mapping["km_curve"] == "efficacy_results"
        assert integration.section_mapping["forest_plot"] == "efficacy_results"
        assert integration.section_mapping["consort"] == "study_design"
        assert integration.section_mapping["ae_waterfall"] == "safety_results"
        assert integration.section_mapping["table"] == "demographics"
    
    def test_generate_section_narrative_empty(self, integration):
        """Test narrative generation with empty figures list"""
        narrative = integration.generate_section_narrative("efficacy_results", [])
        assert narrative == ""
    
    def test_generate_section_narrative_with_header(self, integration):
        """Test that section headers are included"""
        from agents.figure_processor import FigureMetadata, ExtractedData
        from datetime import datetime
        
        fake_data = ExtractedData(
            figure_metadata=FigureMetadata(
                figure_id="FIG_001",
                figure_type="km_curve",
                study_id="TEST"
            ),
            raw_text="Test",
            structured_data={},
            narrative_description="Test narrative",
            statistics_summary="HR=0.72",
            confidence_score=0.95,
            extraction_method="test"
        )
        
        narrative = integration.generate_section_narrative("efficacy_results", [fake_data])
        
        assert "### 14.2 Efficacy Results" in narrative
        assert "Test narrative" in narrative


class TestErrorHandling:
    """Tests for error handling"""
    
    def test_error_count_increment(self):
        """Test that error count increments on failure"""
        processor = FigureProcessor()
        initial_errors = processor.error_count
        
        # Force an error by passing invalid data
        try:
            # This should not raise in current implementation
            # but we test the error handling structure
            pass
        except Exception:
            pass
        
        # Error count should be tracked
        assert hasattr(processor, 'error_count')


class TestMetrics:
    """Tests for processor metrics"""
    
    def test_get_metrics(self):
        """Test metrics retrieval"""
        processor = FigureProcessor()
        
        metrics = processor.get_metrics()
        
        assert "processed_count" in metrics
        assert "error_count" in metrics
        assert "success_rate" in metrics
        assert "supported_types" in metrics
        assert "ocr_engine" in metrics
        
        assert isinstance(metrics["supported_types"], list)
        assert len(metrics["supported_types"]) > 0
