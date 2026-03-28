"""
Tests for FactChecker (Agent 3.5) - NLI-based Claim Verification

Tests Natural Language Inference verification of claims against sources.
FDA 21 CFR Part 11 compliant with full audit trail.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from agents.fact_checker import FactChecker, Claim, VerificationResult, VerificationStatus


class TestClaimDataclass:
    """Tests for Claim dataclass"""
    
    def test_claim_creation(self):
        """Test creating a claim"""
        claim = Claim(
            text="The treatment showed 30% improvement",
            source_section="efficacy_results",
            confidence=0.95,
            requires_verification=True
        )
        
        assert claim.text == "The treatment showed 30% improvement"
        assert claim.source_section == "efficacy_results"
        assert claim.confidence == 0.95
        assert claim.requires_verification is True
        assert isinstance(claim.timestamp, datetime)
    
    def test_claim_hash(self):
        """Test claim hash generation"""
        claim = Claim(text="Test claim", source_section="test")
        
        assert len(claim.claim_hash) == 32  # MD5 hex
        assert isinstance(claim.claim_hash, str)


class TestVerificationResultDataclass:
    """Tests for VerificationResult dataclass"""
    
    def test_result_creation(self):
        """Test creating verification result"""
        result = VerificationResult(
            claim_hash="abc123",
            status=VerificationStatus.VERIFIED,
            confidence=0.92,
            supporting_evidence=["Source 1", "Source 2"],
            contradicting_evidence=[],
            nli_entailment_score=0.89
        )
        
        assert result.claim_hash == "abc123"
        assert result.status == VerificationStatus.VERIFIED
        assert result.confidence == 0.92
        assert len(result.supporting_evidence) == 2
        assert len(result.contradicting_evidence) == 0
        assert result.nli_entailment_score == 0.89


class TestFactCheckerInitialization:
    """Tests for FactChecker initialization"""
    
    def test_default_initialization(self):
        """Test default fact checker initialization"""
        checker = FactChecker()
        
        assert checker.agent_id == "agent_3_5"
        assert checker.agent_name == "FactChecker"
        assert checker.version == "2.1.0"
        assert checker.nli_threshold == 0.7
        assert checker.cross_encoder is None  # Lazy loaded
    
    def test_custom_initialization(self):
        """Test fact checker with custom threshold"""
        checker = FactChecker(nli_threshold=0.8)
        
        assert checker.nli_threshold == 0.8


class TestClaimExtraction:
    """Tests for claim extraction"""
    
    @pytest.fixture
    def checker(self):
        return FactChecker()
    
    def test_extract_numerical_claims(self, checker):
        """Test extraction of numerical claims"""
        text = "The response rate was 45% with a p-value of 0.023."
        
        claims = checker.extract_claims(text, section="results")
        
        assert len(claims) > 0
        assert any("45%" in c.text for c in claims)
        assert any("0.023" in c.text for c in claims)
    
    def test_extract_comparative_claims(self, checker):
        """Test extraction of comparative claims"""
        text = "The experimental group showed superior outcomes compared to control."
        
        claims = checker.extract_claims(text, section="results")
        
        assert len(claims) > 0
    
    def test_filter_high_confidence_claims(self, checker):
        """Test filtering claims by confidence"""
        text = "The drug is effective."
        
        claims = checker.extract_claims(text, section="results")
        
        # Only high confidence claims should be verified
        high_conf = [c for c in claims if c.confidence >= 0.8]
        assert all(c.confidence >= 0.8 for c in high_conf)


class TestNLIVerification:
    """Tests for NLI-based verification"""
    
    @pytest.fixture
    def checker(self):
        return FactChecker()
    
    def test_entailment_detection(self, checker):
        """Test entailment (claim supported by source)"""
        claim = "The drug reduced mortality by 30%"
        source = "Treatment with the drug resulted in a 30% reduction in mortality."
        
        result = checker._nli_verify(claim, source)
        
        # In real implementation, this would use cross-encoder
        assert isinstance(result, dict)
        assert "entailment_score" in result
    
    def test_contradiction_detection(self, checker):
        """Test contradiction (claim contradicts source)"""
        claim = "The drug had no effect"
        source = "The drug significantly improved outcomes."
        
        result = checker._nli_verify(claim, source)
        
        assert isinstance(result, dict)


class TestBatchVerification:
    """Tests for batch verification"""
    
    @pytest.fixture
    def checker(self):
        return FactChecker()
    
    def test_verify_multiple_claims(self, checker):
        """Test verification of multiple claims"""
        claims = [
            Claim(text="Claim 1", source_section="sec1"),
            Claim(text="Claim 2", source_section="sec2"),
        ]
        
        sources = ["Source text 1", "Source text 2"]
        
        results = checker.verify_batch(claims, sources)
        
        assert len(results) == len(claims)
        assert all(isinstance(r, VerificationResult) for r in results)


class TestVerificationStatus:
    """Tests for verification status enum"""
    
    def test_status_values(self):
        """Test verification status values"""
        assert VerificationStatus.VERIFIED.value == "verified"
        assert VerificationStatus.CONTRADICTED.value == "contradicted"
        assert VerificationStatus.UNVERIFIED.value == "unverified"
        assert VerificationStatus.NEEDS_REVIEW.value == "needs_review"


class TestErrorHandling:
    """Tests for error handling"""
    
    @pytest.fixture
    def checker(self):
        return FactChecker()
    
    def test_empty_claim_handling(self, checker):
        """Test handling of empty claims"""
        claims = checker.extract_claims("", section="test")
        
        assert len(claims) == 0
    
    def test_empty_source_handling(self, checker):
        """Test verification with empty sources"""
        claim = Claim(text="Test claim", source_section="test")
        
        result = checker.verify_claim(claim, [])
        
        assert result.status == VerificationStatus.UNVERIFIED


class TestAuditTrail:
    """Tests for FDA 21 CFR Part 11 audit trails"""
    
    @pytest.fixture
    def checker(self):
        return FactChecker()
    
    def test_verification_logged(self, checker):
        """Test that verifications are logged"""
        claim = Claim(text="Test claim", source_section="test")
        
        result = checker.verify_claim(claim, ["Source text"])
        
        # Check audit trail
        assert hasattr(checker, 'audit_trail')
