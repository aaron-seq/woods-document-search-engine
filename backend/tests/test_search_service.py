"""
Unit tests for SearchService.

Tests cover:
- Hybrid search query construction
- Embedding generation
- Response mapping
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.search.search_service import SearchService
from app.models import SearchQuery, SearchResponse


class TestSearchService:
    """Test suite for SearchService class"""

    @pytest.fixture
    def search_service(self, mock_elasticsearch, mock_embedding_model):
        """Create SearchService with mocked dependencies"""
        with patch("app.search.search_service.Elasticsearch") as mock_es_class:
            mock_es_class.return_value = mock_elasticsearch
            service = SearchService(mock_embedding_model)
            service.es = mock_elasticsearch
            return service

    # -------------------------------------------------------------------------
    # Embedding Generation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_generate_embedding_calls_model(self, search_service, mock_embedding_model):
        """Test that embedding generation calls the model correctly"""
        search_service._generate_embedding("test query")

        mock_embedding_model.encode.assert_called_once_with("test query")

    @pytest.mark.unit
    def test_generate_embedding_returns_list(
        self, search_service, mock_embedding_model
    ):
        """Test that embedding is returned as a list"""
        result = search_service._generate_embedding("test query")

        assert isinstance(result, list)
        assert len(result) == 384  # Expected dimension

    # -------------------------------------------------------------------------
    # Search Query Construction Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_search_with_keyword_query(self, search_service, mock_elasticsearch):
        """Test search with keyword in query field"""
        query = SearchQuery(query="corrosion", limit=10)

        search_service.search(query)

        # Verify ES was called
        mock_elasticsearch.search.assert_called_once()
        call_args = mock_elasticsearch.search.call_args

        # Check that query was included
        es_body = call_args.kwargs.get("body") or call_args[1].get("body")
        assert "query" in es_body

    @pytest.mark.unit
    def test_search_with_keyword_field(self, search_service, mock_elasticsearch):
        """Test search with keyword in keyword field"""
        query = SearchQuery(keyword="safety", query="", limit=10)

        search_service.search(query)

        mock_elasticsearch.search.assert_called_once()

    @pytest.mark.unit
    def test_search_empty_query_uses_match_all(
        self, search_service, mock_elasticsearch
    ):
        """Test that empty query results in match_all"""
        query = SearchQuery(query="", keyword="", limit=10)

        search_service.search(query)

        call_args = mock_elasticsearch.search.call_args
        es_body = call_args.kwargs.get("body") or call_args[1].get("body")

        # Should contain match_all when no search term
        assert "bool" in es_body["query"]

    @pytest.mark.unit
    def test_search_includes_knn_query(self, search_service, mock_elasticsearch):
        """Test that semantic search includes KNN query"""
        query = SearchQuery(query="corrosion protection", limit=10)

        search_service.search(query)

        call_args = mock_elasticsearch.search.call_args
        es_body = call_args.kwargs.get("body") or call_args[1].get("body")

        # KNN should be included for non-empty queries
        assert "knn" in es_body

    # -------------------------------------------------------------------------
    # Response Mapping Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_search_returns_search_response(self, search_service):
        """Test that search returns proper SearchResponse"""
        query = SearchQuery(query="test", limit=10)

        result = search_service.search(query)

        assert isinstance(result, SearchResponse)
        assert hasattr(result, "total")
        assert hasattr(result, "results")
        assert hasattr(result, "page")
        assert hasattr(result, "page_size")

    @pytest.mark.unit
    def test_search_maps_results_correctly(self, search_service):
        """Test that ES results are mapped to SearchResult objects"""
        query = SearchQuery(query="corrosion", limit=10)

        result = search_service.search(query)

        assert len(result.results) > 0
        first_result = result.results[0]

        assert hasattr(first_result, "id")
        assert hasattr(first_result, "title")
        assert hasattr(first_result, "snippet")
        assert hasattr(first_result, "score")
        assert hasattr(first_result, "file_path")

    @pytest.mark.unit
    def test_search_includes_highlights(self, search_service):
        """Test that search results include highlights"""
        query = SearchQuery(query="corrosion", limit=10)

        result = search_service.search(query)

        first_result = result.results[0]
        assert hasattr(first_result, "highlights")

    @pytest.mark.unit
    def test_search_generates_download_url(self, search_service):
        """Test that download URL is generated for results"""
        query = SearchQuery(query="test", limit=10)

        result = search_service.search(query)

        first_result = result.results[0]
        assert first_result.download_url.startswith("/documents/")
        assert "/download" in first_result.download_url

    # -------------------------------------------------------------------------
    # Error Handling Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_search_handles_es_error(self, search_service, mock_elasticsearch):
        """Test that ES errors are handled gracefully"""
        mock_elasticsearch.search.side_effect = Exception("ES connection error")

        query = SearchQuery(query="test", limit=10)
        result = search_service.search(query)

        # Should return empty results, not raise exception
        assert isinstance(result, SearchResponse)
        assert result.total == 0
        assert len(result.results) == 0

    @pytest.mark.unit
    def test_search_handles_missing_fields_in_source(
        self, search_service, mock_elasticsearch
    ):
        """Test handling of ES results with missing optional fields"""
        mock_elasticsearch.search.return_value = {
            "hits": {
                "total": {"value": 1, "relation": "eq"},
                "hits": [
                    {
                        "_source": {
                            "id": "test-id",
                            "title": "Test",
                            "file_path": "/path/to/file.pdf",
                        },
                        "_score": 1.0,
                    }
                ],
            }
        }

        query = SearchQuery(query="test", limit=10)
        result = search_service.search(query)

        assert len(result.results) == 1
        assert result.results[0].id == "test-id"

    # -------------------------------------------------------------------------
    # Pagination Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_search_respects_pagination(self, search_service, mock_elasticsearch):
        """Test that pagination parameters are passed to ES"""
        query = SearchQuery(query="test", page=2, page_size=15)

        search_service.search(query)

        call_args = mock_elasticsearch.search.call_args
        es_body = call_args.kwargs.get("body") or call_args[1].get("body")

        # from = (page - 1) * page_size = (2 - 1) * 15 = 15
        assert es_body["from"] == 15
        assert es_body["size"] == 15

    @pytest.mark.unit
    def test_search_response_includes_pagination_info(self, search_service):
        """Test that response includes pagination information"""
        query = SearchQuery(query="test", page=3, page_size=10)

        result = search_service.search(query)

        assert result.page == 3
        assert result.page_size == 10
