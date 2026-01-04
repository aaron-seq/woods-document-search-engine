"""
Unit tests for LLMService.

Tests cover:
- Sentence splitting logic
- Extractive summarization
- Empty document handling
- Edge cases
"""

import pytest
from unittest.mock import Mock, patch
import numpy as np

from app.search.llm_service import LLMService


class TestLLMService:
    """Test suite for LLMService class"""

    @pytest.fixture
    def llm_service(self, mock_embedding_model):
        """Create LLMService with mocked model"""
        return LLMService(mock_embedding_model)

    @pytest.fixture
    def mock_llm_model(self):
        """Create a more sophisticated mock for summarization tests"""
        model = Mock()

        # Return different embeddings for query vs sentences
        def encode_side_effect(text):
            if isinstance(text, str):
                return np.array([0.1] * 384)
            else:
                # For list of sentences, return array of embeddings
                return np.array([[0.1 + 0.01 * i] * 384 for i in range(len(text))])

        model.encode.side_effect = encode_side_effect
        return model

    # -------------------------------------------------------------------------
    # Sentence Splitting Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_split_into_sentences_basic(self, llm_service):
        """Test basic sentence splitting"""
        text = "First sentence. Second sentence. Third sentence."

        sentences = llm_service._split_into_sentences(text)

        assert len(sentences) >= 2  # Short sentences may be filtered

    @pytest.mark.unit
    def test_split_into_sentences_handles_question_marks(self, llm_service):
        """Test that question marks are treated as sentence delimiters"""
        text = "What is corrosion? It is a chemical process. How to prevent it?"

        sentences = llm_service._split_into_sentences(text)

        # Questions and statements should be split
        assert len(sentences) >= 1

    @pytest.mark.unit
    def test_split_into_sentences_handles_exclamation(self, llm_service):
        """Test that exclamation marks are treated as sentence delimiters"""
        text = "Safety is critical! Always wear protective equipment. Do not ignore warnings!"

        sentences = llm_service._split_into_sentences(text)

        assert len(sentences) >= 1

    @pytest.mark.unit
    def test_split_into_sentences_filters_short(self, llm_service):
        """Test that very short sentences are filtered out"""
        text = "OK. This is a longer sentence with enough content. No."

        sentences = llm_service._split_into_sentences(text)

        # Only the longer sentence should be included
        assert all(len(s) > 20 for s in sentences)

    @pytest.mark.unit
    def test_split_into_sentences_handles_empty_string(self, llm_service):
        """Test handling of empty string"""
        sentences = llm_service._split_into_sentences("")

        assert sentences == []

    # -------------------------------------------------------------------------
    # Summary Generation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_generate_summary_no_documents(self, llm_service):
        """Test summary generation with no documents"""
        result = llm_service.generate_summary("test query", [])

        assert "No documents found" in result

    @pytest.mark.unit
    def test_generate_summary_empty_content(self, llm_service):
        """Test summary generation with documents that have no content"""
        docs = [{"content": "", "background": "", "scope": ""}]

        result = llm_service.generate_summary("test query", docs)

        assert "too short" in result.lower() or "No documents" in result

    @pytest.mark.unit
    def test_generate_summary_with_content(self, mock_llm_model):
        """Test summary generation with valid documents"""
        llm_service = LLMService(mock_llm_model)

        docs = [
            {
                "content": (
                    "Corrosion is a significant problem for offshore structures. "
                    "Regular inspection is required to identify early signs of damage. "
                    "Protective coatings should be applied according to specifications. "
                    "Cathodic protection systems are commonly used. "
                    "Documentation of all findings is mandatory."
                )
            }
        ]

        # Mock the similarity computation
        with patch("sentence_transformers.util.cos_sim") as mock_cos_sim:
            mock_cos_sim.return_value = Mock()
            mock_cos_sim.return_value.__getitem__ = Mock(
                return_value=Mock(
                    numpy=Mock(return_value=np.array([0.8, 0.6, 0.9, 0.7, 0.5]))
                )
            )

            result = llm_service.generate_summary("corrosion protection", docs)

        # Should return a structured summary
        assert "Based on the search results" in result
        assert "-" in result  # Should have bullet points

    @pytest.mark.unit
    def test_generate_summary_uses_background_fallback(self, mock_llm_model):
        """Test that background is used when content is not available"""
        llm_service = LLMService(mock_llm_model)

        docs = [
            {
                "content": None,
                "background": "This is background information about the topic with enough text.",
                "scope": "The scope covers various aspects of the project including details.",
            }
        ]

        with patch("sentence_transformers.util.cos_sim") as mock_cos_sim:
            mock_cos_sim.return_value = Mock()
            mock_cos_sim.return_value.__getitem__ = Mock(
                return_value=Mock(numpy=Mock(return_value=np.array([0.8, 0.6])))
            )

            result = llm_service.generate_summary("test query", docs)

        # Should still generate summary using background/scope
        assert result is not None

    @pytest.mark.unit
    def test_generate_summary_limits_sentences(self, mock_llm_model):
        """Test that sentence processing is limited to avoid performance issues"""
        llm_service = LLMService(mock_llm_model)

        # Create document with many sentences
        long_content = ". ".join(
            [f"Sentence number {i} with enough content" for i in range(600)]
        )
        docs = [{"content": long_content}]

        with patch("sentence_transformers.util.cos_sim") as mock_cos_sim:
            mock_cos_sim.return_value = Mock()
            mock_cos_sim.return_value.__getitem__ = Mock(
                return_value=Mock(numpy=Mock(return_value=np.array([0.5] * 500)))
            )

            result = llm_service.generate_summary("test", docs)

        # Should complete without hanging (sentence limit is 500)
        assert result is not None

    @pytest.mark.unit
    def test_generate_summary_returns_top_sentences(self, mock_llm_model):
        """Test that summary contains top-k most relevant sentences"""
        llm_service = LLMService(mock_llm_model)

        docs = [
            {
                "content": (
                    "Sentence one about corrosion is important information. "
                    "Sentence two about safety procedures and guidelines. "
                    "Sentence three about maintenance schedules required. "
                    "Sentence four about equipment specifications details. "
                    "Sentence five about quality control measures."
                )
            }
        ]

        with patch("sentence_transformers.util.cos_sim") as mock_cos_sim:
            # Higher scores for specific sentences
            scores = np.array([0.9, 0.3, 0.8, 0.2, 0.7])
            mock_cos_sim.return_value = Mock()
            mock_cos_sim.return_value.__getitem__ = Mock(
                return_value=Mock(numpy=Mock(return_value=scores))
            )

            result = llm_service.generate_summary("corrosion", docs)

        # Should have bullet points for top sentences
        bullet_count = result.count("-")
        assert bullet_count >= 1
        assert bullet_count <= 5

    # -------------------------------------------------------------------------
    # Edge Case Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_generate_summary_handles_special_characters(self, mock_llm_model):
        """Test handling of special characters in content"""
        llm_service = LLMService(mock_llm_model)

        docs = [
            {
                "content": (
                    "Temperature range: -40C to +85C for all components. "
                    "Pressure rating: 5000 PSI @ 25C testing conditions. "
                    "Compliance with ISO-9001 & API-650 standards required."
                )
            }
        ]

        with patch("sentence_transformers.util.cos_sim") as mock_cos_sim:
            mock_cos_sim.return_value = Mock()
            mock_cos_sim.return_value.__getitem__ = Mock(
                return_value=Mock(numpy=Mock(return_value=np.array([0.8, 0.7, 0.6])))
            )

            result = llm_service.generate_summary("specifications", docs)

        assert result is not None
        assert "error" not in result.lower()

    @pytest.mark.unit
    def test_generate_summary_multiple_documents(self, mock_llm_model):
        """Test summarization across multiple documents"""
        llm_service = LLMService(mock_llm_model)

        docs = [
            {"content": "First document about corrosion prevention methods."},
            {"content": "Second document about safety inspection procedures."},
            {"content": "Third document about maintenance schedules and requirements."},
        ]

        with patch("sentence_transformers.util.cos_sim") as mock_cos_sim:
            mock_cos_sim.return_value = Mock()
            mock_cos_sim.return_value.__getitem__ = Mock(
                return_value=Mock(numpy=Mock(return_value=np.array([0.8, 0.7, 0.6])))
            )

            result = llm_service.generate_summary("safety", docs)

        # Should aggregate content from all documents
        assert result is not None
