"""
Pytest fixtures and configuration for Woods Document Search Engine tests.

This module provides shared fixtures for:
- Mocked Elasticsearch client
- Test documents and parsed data
- Mock embedding model
- FastAPI test client
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile
import os


# Sample test document content
SAMPLE_PDF_CONTENT = """
CORROSION PROTECTION GUIDELINES

1. BACKGROUND

This document outlines the corrosion protection standards for offshore structures.
Corrosion is a significant concern for equipment in marine environments.

2. SCOPE

This guideline applies to all offshore platforms and subsea equipment.
Regular inspection schedules must be maintained.

3. PROCEDURES

3.1 Visual Inspection
Conduct quarterly visual inspections of all exposed surfaces.

3.2 Coating Application
Apply protective coatings according to manufacturer specifications.
"""

SAMPLE_PARSED_DOCUMENT = {
    "id": "corrosion-test",
    "title": "CORROSION PROTECTION GUIDELINES",
    "file_path": "/app/documents/corrosion-test.pdf",
    "file_type": ".pdf",
    "headings": [
        "CORROSION PROTECTION GUIDELINES",
        "1. BACKGROUND",
        "2. SCOPE",
        "3. PROCEDURES",
    ],
    "background": "This document outlines the corrosion protection standards...",
    "scope": "This guideline applies to all offshore platforms...",
    "content": SAMPLE_PDF_CONTENT,
    "category": None,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
}


@pytest.fixture
def sample_document():
    """Return a sample parsed document for testing"""
    return SAMPLE_PARSED_DOCUMENT.copy()


@pytest.fixture
def sample_documents():
    """Return multiple sample documents for testing"""
    docs = []
    for i in range(3):
        doc = SAMPLE_PARSED_DOCUMENT.copy()
        doc["id"] = f"test-doc-{i}"
        doc["title"] = f"Test Document {i}"
        docs.append(doc)
    return docs


@pytest.fixture
def mock_embedding_model():
    """Create a mock embedding model that returns consistent vectors"""
    model = Mock()
    # Return a 384-dimensional vector (matching all-MiniLM-L6-v2)
    model.encode.return_value = [0.1] * 384
    return model


@pytest.fixture
def mock_elasticsearch():
    """Create a mock Elasticsearch client"""
    es = Mock()

    # Mock ping
    es.ping.return_value = True

    # Mock indices
    es.indices = Mock()
    es.indices.exists.return_value = True
    es.indices.create.return_value = {"acknowledged": True}

    # Mock search
    es.search.return_value = {
        "hits": {
            "total": {"value": 1, "relation": "eq"},
            "hits": [
                {
                    "_source": SAMPLE_PARSED_DOCUMENT,
                    "_score": 1.5,
                    "highlight": {"content": ["<mark>corrosion</mark> protection"]},
                }
            ],
        }
    }

    # Mock get
    es.get.return_value = {"_source": SAMPLE_PARSED_DOCUMENT}

    # Mock index
    es.index.return_value = {"result": "created", "_id": "test-doc"}

    return es


@pytest.fixture
def temp_documents_dir():
    """Create a temporary directory with test documents"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple text file for testing
        test_file = Path(tmpdir) / "test-document.txt"
        test_file.write_text(SAMPLE_PDF_CONTENT)
        yield tmpdir


@pytest.fixture
def mock_settings():
    """Override settings for testing"""
    with patch("app.config.settings") as mock_settings:
        mock_settings.ELASTICSEARCH_HOST = "localhost"
        mock_settings.ELASTICSEARCH_PORT = 9200
        mock_settings.ELASTICSEARCH_INDEX = "test_wood_ai_documents"
        mock_settings.EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
        mock_settings.EMBEDDING_DIMENSION = 384
        mock_settings.DOCUMENTS_PATH = "/tmp/test_documents"
        mock_settings.LOG_LEVEL = "DEBUG"
        mock_settings.LOG_FORMAT = "text"
        mock_settings.VERSION = "1.0.0-test"
        mock_settings.ENVIRONMENT = "test"
        yield mock_settings


@pytest.fixture
def test_client():
    """Create a FastAPI test client"""
    # Import here to avoid import errors during collection
    from fastapi.testclient import TestClient

    # We need to mock ES before importing main
    with (
        patch("app.search.search_service.Elasticsearch") as mock_es_class,
        patch("app.ingestion.indexer.Elasticsearch") as mock_es_class2,
        patch("app.export.exporter.Elasticsearch") as mock_es_class3,
    ):
        # Configure mock
        mock_es = Mock()
        mock_es.ping.return_value = True
        mock_es.indices.exists.return_value = True
        mock_es_class.return_value = mock_es
        mock_es_class2.return_value = mock_es
        mock_es_class3.return_value = mock_es

        from app.main import app

        client = TestClient(app)
        yield client
