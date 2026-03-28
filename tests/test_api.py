"""
API Tests for Alpha Clinical Agents FastAPI Application

Tests all endpoints, middleware, and audit trail functionality.
FDA 21 CFR Part 11 compliance testing.
"""

import pytest
import sys
from unittest.mock import Mock, patch

# Add api directory to path
sys.path.insert(0, '/root/.openclaw/workspace/alpha-clinical-agents/api')

from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestRootEndpoint:
    """Tests for root endpoint"""
    
    def test_root(self, client):
        """Test root endpoint returns API info"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Alpha Clinical Agents API"
        assert "version" in data
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"


class TestHealthEndpoint:
    """Tests for health check endpoint"""
    
    def test_health_check(self, client):
        """Test health endpoint returns system status"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert data["agents_ready"] == 12
        assert data["compliance_status"] == "FDA_21_CFR_Part_11_COMPLIANT"
        assert "uptime_seconds" in data


class TestRiskAssessmentEndpoint:
    """Tests for risk assessment endpoint"""
    
    def test_risk_assessment_success(self, client):
        """Test successful risk assessment"""
        payload = {
            "protocol_summary": "Phase III randomized study with 500 patients",
            "complexity_indicators": ["multi-arm", "adaptive"]
        }
        
        response = client.post("/v1/risk-assessment", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert 0 <= data["complexity_score"] <= 100
        assert data["estimated_hours"] > 0
        assert len(data["recommended_agents"]) > 0
    
    def test_risk_assessment_empty_payload(self, client):
        """Test risk assessment with empty payload"""
        response = client.post("/v1/risk-assessment", json={})
        
        assert response.status_code == 422  # Validation error


class TestProtocolAnalysisEndpoint:
    """Tests for protocol analysis endpoint"""
    
    def test_protocol_analysis_success(self, client):
        """Test successful protocol analysis"""
        payload = {
            "protocol_text": "A Phase III randomized study of Drug XYZ in breast cancer patients.",
            "study_id": "TEST123",
            "sponsor": "TestPharma"
        }
        
        response = client.post("/v1/protocol/analyze", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["study_id"] == "TEST123"
        assert "extracted_data" in data
        assert "audit_hash" in data
        assert "timestamp" in data
    
    def test_protocol_analysis_invalid_study_id(self, client):
        """Test protocol analysis with invalid study ID"""
        payload = {
            "protocol_text": "Test protocol",
            "study_id": "invalid-id-with-special-chars!!!",
            "sponsor": "Test"
        }
        
        response = client.post("/v1/protocol/analyze", json=payload)
        
        assert response.status_code == 422  # Validation error


class TestCSRGenerationEndpoint:
    """Tests for CSR generation endpoint"""
    
    def test_csr_generation_success(self, client):
        """Test successful CSR generation request"""
        payload = {
            "study_id": "TEST123",
            "protocol_data": {"title": "Phase III Study", "design": "Randomized"},
            "statistical_data": {"primary_endpoint": "OS", "p_value": 0.023},
            "safety_data": {"total_ae": 150, "serious_ae": 12},
            "template_version": "ICH-E3-v1"
        }
        
        response = client.post("/v1/csr/generate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["status"] == "IN_PROGRESS"
        assert "sections_completed" in data
        assert 0 <= data["quality_score"] <= 100
        assert "audit_hash" in data
        assert "generated_at" in data
    
    def test_csr_generation_missing_data(self, client):
        """Test CSR generation with missing required data"""
        payload = {
            "study_id": "TEST123"
            # Missing protocol_data, statistical_data, safety_data
        }
        
        response = client.post("/v1/csr/generate", json=payload)
        
        assert response.status_code == 422  # Validation error


class TestCSRStatusEndpoint:
    """Tests for CSR status endpoint"""
    
    def test_csr_status_success(self, client):
        """Test successful CSR status retrieval"""
        response = client.get("/v1/csr/test-document-id/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "test-document-id"
        assert data["status"] in ["IN_PROGRESS", "REVIEW_REQUIRED", "COMPLETED", "FAILED"]
        assert 0 <= data["progress_percent"] <= 100
        assert "sections_completed" in data
        assert "sections_pending" in data
        assert "quality_score" in data
    
    def test_csr_status_not_found(self, client):
        """Test CSR status for non-existent document"""
        response = client.get("/v1/csr/nonexistent/status")
        
        # May return 200 with status or 404 depending on implementation
        assert response.status_code in [200, 404]


class TestValidationEndpoint:
    """Tests for validation endpoint"""
    
    def test_validation_success(self, client):
        """Test successful validation request"""
        payload = {
            "document_id": "DOC123",
            "validation_type": "statistical"
        }
        
        response = client.post("/v1/validate/statistical", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "validation_id" in data
        assert isinstance(data["passed"], bool)
        assert "issues" in data
        assert 0 <= data["confidence"] <= 1.0
    
    def test_validation_invalid_type(self, client):
        """Test validation with invalid type"""
        payload = {
            "document_id": "DOC123",
            "validation_type": "invalid_type"
        }
        
        response = client.post("/v1/validate/invalid_type", json=payload)
        
        # Should accept any type, validation happens internally
        assert response.status_code == 200


class TestAgentsListEndpoint:
    """Tests for agents list endpoint"""
    
    def test_list_agents(self, client):
        """Test listing all agents"""
        response = client.get("/v1/agents")
        
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert data["total"] == 12
        assert data["ready"] == 12
        assert len(data["agents"]) == 12
        
        # Check agent structure
        agent = data["agents"][0]
        assert "id" in agent
        assert "name" in agent
        assert "status" in agent
        assert "type" in agent


class TestAgentMetricsEndpoint:
    """Tests for agent metrics endpoint"""
    
    def test_agent_metrics_success(self, client):
        """Test successful agent metrics retrieval"""
        response = client.get("/v1/agents/agent_1/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "agent_1"
        assert "requests_processed" in data
        assert "average_latency_ms" in data
        assert 0 <= data["success_rate"] <= 1.0
        assert 0 <= data["error_rate"] <= 1.0
        assert "last_active" in data


class TestAuditTrailMiddleware:
    """Tests for FDA 21 CFR Part 11 audit trail middleware"""
    
    def test_request_id_header(self, client):
        """Test that request ID is added to response headers"""
        response = client.get("/health")
        
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) == 16
    
    def test_audit_hash_header(self, client):
        """Test that audit hash is added to response headers"""
        response = client.get("/health")
        
        assert "X-Audit-Hash" in response.headers
        assert len(response.headers["X-Audit-Hash"]) == 64  # SHA-256 hex
    
    def test_audit_trail_logging(self, client):
        """Test that requests are logged for audit trail"""
        # Make a request
        response = client.get("/health")
        
        # Check that headers indicate logging occurred
        assert "X-Request-ID" in response.headers
        assert "X-Audit-Hash" in response.headers


class TestErrorHandling:
    """Tests for error handling"""
    
    def test_not_found(self, client):
        """Test 404 handling"""
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """Test method not allowed handling"""
        response = client.post("/health")  # GET only endpoint
        
        assert response.status_code == 405
    
    def test_validation_error(self, client):
        """Test validation error handling"""
        # Send invalid data type
        response = client.post(
            "/v1/risk-assessment",
            json={"protocol_summary": 123}  # Should be string
        )
        
        assert response.status_code == 422


class TestOpenAPISchema:
    """Tests for OpenAPI schema generation"""
    
    def test_openapi_schema_available(self, client):
        """Test that OpenAPI schema is available"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Alpha Clinical Agents API"
        assert "paths" in schema
        assert len(schema["paths"]) > 0
    
    def test_swagger_ui_available(self, client):
        """Test that Swagger UI is available"""
        response = client.get("/docs")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_available(self, client):
        """Test that ReDoc is available"""
        response = client.get("/redoc")
        
        # May be 200 if redoc is configured, or redirect
        assert response.status_code in [200, 307]
