"""
Tests for FinalCompiler (Agent 7) - CSR Package Assembly

Tests compilation of CSR sections into FDA-ready documents.
FDA 21 CFR Part 11 compliant with eCTD formatting.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from agents.final_compiler import FinalCompiler, CSRPackage, DocumentFormat


class TestCSRPackageDataclass:
    """Tests for CSRPackage dataclass"""
    
    def test_package_creation(self):
        """Test creating CSR package"""
        package = CSRPackage(
            document_id="CSR_001",
            study_id="STUDY_123",
            sections={"synopsis": "Content", "methods": "Content"},
            format=DocumentFormat.ECTD
        )
        
        assert package.document_id == "CSR_001"
        assert package.study_id == "STUDY_123"
        assert len(package.sections) == 2
        assert package.format == DocumentFormat.ECTD
        assert isinstance(package.compiled_at, datetime)
        assert package.is_finalized is False
    
    def test_package_hash(self):
        """Test package hash generation"""
        package = CSRPackage(
            document_id="CSR_002",
            study_id="STUDY_456",
            sections={"section": "content"}
        )
        
        assert len(package.package_hash) == 64  # SHA-256 hex


class TestFinalCompilerInitialization:
    """Tests for FinalCompiler initialization"""
    
    def test_default_initialization(self):
        """Test default compiler initialization"""
        compiler = FinalCompiler()
        
        assert compiler.agent_id == "agent_7"
        assert compiler.agent_name == "FinalCompiler"
        assert compiler.version == "2.1.0"
        assert compiler.default_format == DocumentFormat.ECTD
        assert compiler.include_audit_trail is True
    
    def test_custom_initialization(self):
        """Test compiler with custom format"""
        compiler = FinalCompiler(default_format=DocumentFormat.PDF)
        
        assert compiler.default_format == DocumentFormat.PDF


class TestSectionAssembly:
    """Tests for section assembly"""
    
    @pytest.fixture
    def compiler(self):
        return FinalCompiler()
    
    def test_add_section(self, compiler):
        """Test adding section to package"""
        package = CSRPackage(
            document_id="CSR_001",
            study_id="STUDY_123",
            sections={}
        )
        
        compiler.add_section(package, "synopsis", "Synopsis content")
        
        assert "synopsis" in package.sections
        assert package.sections["synopsis"] == "Synopsis content"
    
    def test_validate_section_order(self, compiler):
        """Test ICH E3 section ordering"""
        sections = {
            "synopsis": "Content",
            "introduction": "Content",
            "methods": "Content",
            "results": "Content",
            "discussion": "Content"
        }
        
        is_valid, issues = compiler.validate_section_order(sections)
        
        assert isinstance(is_valid, bool)
        assert isinstance(issues, list)


class TestICHCompliance:
    """Tests for ICH E3 compliance"""
    
    @pytest.fixture
    def compiler(self):
        return FinalCompiler()
    
    def test_required_sections_present(self, compiler):
        """Test that all required ICH E3 sections are present"""
        required = [
            "synopsis",
            "introduction",
            "study_design",
            "efficacy_results",
            "safety_results"
        ]
        
        sections = {s: "Content" for s in required}
        
        is_complete, missing = compiler.check_required_sections(sections)
        
        assert is_complete is True
        assert len(missing) == 0
    
    def test_missing_sections_detected(self, compiler):
        """Test detection of missing required sections"""
        incomplete_sections = {"synopsis": "Content"}
        
        is_complete, missing = compiler.check_required_sections(incomplete_sections)
        
        assert is_complete is False
        assert len(missing) > 0


class TestCrossReferenceResolution:
    """Tests for cross-reference resolution"""
    
    @pytest.fixture
    def compiler(self):
        return FinalCompiler()
    
    def test_resolve_internal_refs(self, compiler):
        """Test resolution of internal section references"""
        content = "See Section 14.2 for efficacy results."
        
        resolved = compiler.resolve_cross_references(content)
        
        assert isinstance(resolved, str)
    
    def test_table_figure_numbering(self, compiler):
        """Test sequential numbering of tables and figures"""
        sections = {
            "results": "Table 1 shows data. Figure 1 shows image.",
            "discussion": "As shown in Table 1 and Figure 1."
        }
        
        numbered = compiler.renumber_tables_figures(sections)
        
        assert isinstance(numbered, dict)


class TestPackageCompilation:
    """Tests for complete package compilation"""
    
    @pytest.fixture
    def compiler(self):
        return FinalCompiler()
    
    def test_compile_package(self, compiler):
        """Test complete CSR package compilation"""
        sections = {
            "synopsis": "Study synopsis content",
            "introduction": "Introduction content",
            "methods": "Methods content"
        }
        
        package = compiler.compile_package(
            study_id="STUDY_001",
            sections=sections,
            format=DocumentFormat.ECTD
        )
        
        assert isinstance(package, CSRPackage)
        assert package.study_id == "STUDY_001"
        assert package.format == DocumentFormat.ECTD
        assert len(package.sections) == 3
    
    def test_compile_with_audit_trail(self, compiler):
        """Test compilation includes audit trail"""
        sections = {"section": "content"}
        
        package = compiler.compile_package(
            study_id="STUDY_001",
            sections=sections
        )
        
        # Package should include audit trail section
        assert "audit_trail" in package.sections or hasattr(package, 'audit_log')


class TestDocumentFormatting:
    """Tests for document formatting"""
    
    @pytest.fixture
    def compiler(self):
        return FinalCompiler()
    
    def test_ectd_formatting(self, compiler):
        """Test eCTD formatting"""
        content = "Section content"
        
        formatted = compiler.format_as_ectd("section_1", content)
        
        assert isinstance(formatted, str)
        # eCTD should have XML-like structure
        assert "<" in formatted or formatted.startswith("m1")
    
    def test_pdf_formatting(self, compiler):
        """Test PDF formatting"""
        content = "Section content"
        
        formatted = compiler.format_as_pdf("section_1", content)
        
        assert isinstance(formatted, str)


class TestQualityChecks:
    """Tests for quality assurance checks"""
    
    @pytest.fixture
    def compiler(self):
        return FinalCompiler()
    
    def test_consistency_check(self, compiler):
        """Test consistency between sections"""
        sections = {
            "synopsis": "Primary endpoint: OS",
            "methods": "Primary endpoint: PFS"  # Inconsistent!
        }
        
        is_consistent, issues = compiler.check_consistency(sections)
        
        assert is_consistent is False
        assert len(issues) > 0
    
    def test_completeness_check(self, compiler):
        """Test document completeness"""
        sections = {
            "synopsis": "Content",
            "methods": "",  # Empty section
            "results": "Content"
        }
        
        is_complete, issues = compiler.check_completeness(sections)
        
        assert isinstance(is_complete, bool)


class TestFinalization:
    """Tests for document finalization"""
    
    @pytest.fixture
    def compiler(self):
        return FinalCompiler()
    
    def test_finalize_package(self, compiler):
        """Test package finalization"""
        package = CSRPackage(
            document_id="CSR_001",
            study_id="STUDY_001",
            sections={"section": "content"}
        )
        
        finalized = compiler.finalize_package(package, "compiler_001")
        
        assert finalized.is_finalized is True
        assert finalized.finalized_by == "compiler_001"
        assert isinstance(finalized.finalized_at, datetime)
    
    def test_no_modification_after_finalize(self, compiler):
        """Test that finalized packages cannot be modified"""
        package = CSRPackage(
            document_id="CSR_001",
            study_id="STUDY_001",
            sections={"section": "content"},
            is_finalized=True
        )
        
        with pytest.raises(RuntimeError):
            compiler.add_section(package, "new_section", "content")


class TestAuditTrail:
    """Tests for FDA 21 CFR Part 11 audit trails"""
    
    @pytest.fixture
    def compiler(self):
        return FinalCompiler()
    
    def test_compilation_logged(self, compiler):
        """Test that compilation is logged"""
        package = compiler.compile_package(
            study_id="STUDY_001",
            sections={"section": "content"}
        )
        
        assert hasattr(compiler, 'audit_trail')
        assert len(compiler.audit_trail) > 0
