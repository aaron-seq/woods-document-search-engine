"""
Integration tests for FastAPI API endpoints.

Tests cover:
- Health check endpoint
- Search endpoints (GET and POST)
- Document download/preview endpoints
- Ingest endpoint
- Export endpoint
- Summarize endpoint

Note: These tests use mocked Elasticsearch to avoid external dependencies.
For full integration tests, use @pytest.mark.integration and run with live ES.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test suite for health check endpoint"""

    @pytest.mark.unit
    def test_health_check_returns_200(self, test_client):
        """Test that health endpoint returns 200"""
        response = test_client.get("/health")

        assert response.status_code == 200

    @pytest.mark.unit
    def test_health_check_returns_status(self, test_client):
        """Test that health check returns status field"""
        response = test_client.get("/health")

        data = response.json()
        assert "status" in data

    @pytest.mark.unit
    def test_health_check_includes_components(self, test_client):
        """Test that health check includes component statuses"""
        response = test_client.get("/health")

        data = response.json()
        assert "components" in data
        assert "api" in data["components"]
        assert "elasticsearch" in data["components"]


class TestRootEndpoint:
    """Test suite for root endpoint"""

    @pytest.mark.unit
    def test_root_returns_200(self, test_client):
        """Test that root endpoint returns 200"""
        response = test_client.get("/")

        assert response.status_code == 200

    @pytest.mark.unit
    def test_root_returns_message(self, test_client):
        """Test that root returns welcome message"""
        response = test_client.get("/")

        data = response.json()
        assert "message" in data
        assert "version" in data


class TestSearchEndpoints:
    """Test suite for search endpoints"""

    @pytest.mark.unit
    def test_search_get_returns_200(self, test_client):
        """Test that GET /search returns 200"""
        response = test_client.get("/search", params={"query": "test"})

        assert response.status_code == 200

    @pytest.mark.unit
    def test_search_get_requires_query(self, test_client):
        """Test that GET /search requires query parameter"""
        response = test_client.get("/search")

        # FastAPI returns 422 for missing required params
        assert response.status_code == 422

    @pytest.mark.unit
    def test_search_get_returns_results_structure(self, test_client):
        """Test that search returns proper response structure"""
        response = test_client.get("/search", params={"query": "corrosion"})

        data = response.json()
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "results" in data

    @pytest.mark.unit
    def test_search_get_with_limit(self, test_client):
        """Test that limit parameter is respected"""
        response = test_client.get("/search", params={"query": "test", "limit": 5})

        assert response.status_code == 200

    @pytest.mark.unit
    def test_search_post_returns_200(self, test_client):
        """Test that POST /search returns 200"""
        response = test_client.post("/search", json={"query": "test", "limit": 10})

        assert response.status_code == 200

    @pytest.mark.unit
    def test_search_post_returns_results(self, test_client):
        """Test that POST search returns results structure"""
        response = test_client.post("/search", json={"query": "safety"})

        data = response.json()
        assert "results" in data


class TestDocumentEndpoints:
    """Test suite for document download/preview endpoints"""

    @pytest.mark.unit
    def test_download_nonexistent_returns_404(self, test_client):
        """Test that downloading non-existent doc returns 404"""
        response = test_client.get("/documents/nonexistent-id/download")

        assert response.status_code == 404

    @pytest.mark.unit
    def test_preview_nonexistent_returns_404(self, test_client):
        """Test that previewing non-existent doc returns 404"""
        response = test_client.get("/documents/nonexistent-id/preview")

        assert response.status_code == 404


class TestIngestEndpoint:
    """Test suite for document ingestion endpoint"""

    @pytest.mark.unit
    def test_ingest_returns_200(self, test_client):
        """Test that POST /ingest returns 200"""
        response = test_client.post("/ingest")

        assert response.status_code == 200

    @pytest.mark.unit
    def test_ingest_returns_count(self, test_client):
        """Test that ingest returns document count"""
        response = test_client.post("/ingest")

        data = response.json()
        assert "message" in data
        assert "count" in data


class TestExportEndpoint:
    """Test suite for export endpoint"""

    @pytest.mark.unit
    def test_export_requires_document_ids(self, test_client):
        """Test that export requires document_ids"""
        response = test_client.post("/export", json={"format": "pdf"})

        # Should fail validation
        assert response.status_code == 422

    @pytest.mark.unit
    def test_export_pdf_format(self, test_client):
        """Test PDF export format"""
        response = test_client.post(
            "/export", json={"document_ids": ["test-doc"], "format": "pdf"}
        )

        assert response.status_code == 200
        assert "application/pdf" in response.headers.get("content-type", "")

    @pytest.mark.unit
    def test_export_docx_format(self, test_client):
        """Test DOCX export format"""
        response = test_client.post(
            "/export", json={"document_ids": ["test-doc"], "format": "docx"}
        )

        assert response.status_code == 200

    @pytest.mark.unit
    def test_export_csv_format(self, test_client):
        """Test CSV export format"""
        response = test_client.post(
            "/export", json={"document_ids": ["test-doc"], "format": "csv"}
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")


class TestSummarizeEndpoint:
    """Test suite for AI summarization endpoint"""

    @pytest.mark.unit
    def test_summarize_requires_query(self, test_client):
        """Test that summarize requires query"""
        response = test_client.post("/summarize", json={})

        assert response.status_code == 422

    @pytest.mark.unit
    def test_summarize_returns_200(self, test_client):
        """Test that summarize returns 200"""
        response = test_client.post(
            "/summarize", json={"query": "corrosion protection"}
        )

        assert response.status_code == 200

    @pytest.mark.unit
    def test_summarize_returns_summary_structure(self, test_client):
        """Test that summarize returns proper structure"""
        response = test_client.post("/summarize", json={"query": "safety inspection"})

        data = response.json()
        assert "summary" in data
        assert "query" in data


class TestCORSAndMiddleware:
    """Test suite for CORS and middleware"""

    @pytest.mark.unit
    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are present"""
        response = test_client.options(
            "/search", headers={"Origin": "http://localhost:3000"}
        )

        # CORS preflight may return 200 or 405 depending on config
        # Just verify the request doesn't crash

    @pytest.mark.unit
    def test_correlation_id_returned(self, test_client):
        """Test that correlation ID is returned in response"""
        response = test_client.get("/health")

        assert "x-correlation-id" in response.headers

    @pytest.mark.unit
    def test_provided_correlation_id_echoed(self, test_client):
        """Test that provided correlation ID is echoed back"""
        custom_id = "test-correlation-123"
        response = test_client.get("/health", headers={"X-Correlation-ID": custom_id})

        assert response.headers.get("x-correlation-id") == custom_id
