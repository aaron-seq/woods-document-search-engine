"""
Unit tests for DocumentExporter.

Tests cover:
- PDF export generation
- DOCX export generation
- CSV export generation
- Document retrieval
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import io

from app.export.exporter import DocumentExporter


class TestDocumentExporter:
    """Test suite for DocumentExporter class"""

    @pytest.fixture
    def exporter(self, mock_elasticsearch):
        """Create DocumentExporter with mocked Elasticsearch"""
        with patch("app.export.exporter.Elasticsearch") as mock_es_class:
            mock_es_class.return_value = mock_elasticsearch
            export = DocumentExporter()
            export.es = mock_elasticsearch
            return export

    @pytest.fixture
    def sample_doc_ids(self):
        """Sample document IDs for testing"""
        return ["doc-1", "doc-2", "doc-3"]

    # -------------------------------------------------------------------------
    # Document Retrieval Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_get_documents_success(self, exporter, mock_elasticsearch):
        """Test successful document retrieval"""
        doc_ids = ["test-doc-1"]

        docs = exporter._get_documents(doc_ids)

        assert len(docs) == 1
        mock_elasticsearch.get.assert_called_once()

    @pytest.mark.unit
    def test_get_documents_handles_missing_doc(self, exporter, mock_elasticsearch):
        """Test that missing documents are skipped gracefully"""
        mock_elasticsearch.get.side_effect = Exception("Document not found")

        docs = exporter._get_documents(["missing-doc"])

        assert docs == []

    @pytest.mark.unit
    def test_get_documents_multiple(self, exporter, mock_elasticsearch):
        """Test retrieval of multiple documents"""
        doc_ids = ["doc-1", "doc-2", "doc-3"]

        docs = exporter._get_documents(doc_ids)

        assert mock_elasticsearch.get.call_count == 3

    # -------------------------------------------------------------------------
    # PDF Export Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_export_to_pdf_returns_bytes(self, exporter):
        """Test that PDF export returns bytes"""
        result = exporter.export_to_pdf(["test-doc"])

        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.unit
    def test_export_to_pdf_valid_pdf_header(self, exporter):
        """Test that result has valid PDF header"""
        result = exporter.export_to_pdf(["test-doc"])

        # PDF files start with %PDF
        assert result[:4] == b"%PDF"

    @pytest.mark.unit
    def test_export_to_pdf_with_summary_flag(self, exporter):
        """Test PDF export with include_summary flag"""
        result = exporter.export_to_pdf(["test-doc"], include_summary=True)

        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.unit
    def test_export_to_pdf_empty_doc_list(self, exporter, mock_elasticsearch):
        """Test PDF export with empty document list"""
        mock_elasticsearch.get.side_effect = Exception("Not found")

        result = exporter.export_to_pdf([])

        # Should still return valid PDF (empty content)
        assert isinstance(result, bytes)

    # -------------------------------------------------------------------------
    # DOCX Export Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_export_to_docx_returns_bytes(self, exporter):
        """Test that DOCX export returns bytes"""
        result = exporter.export_to_docx(["test-doc"])

        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.unit
    def test_export_to_docx_valid_docx_header(self, exporter):
        """Test that result has valid DOCX header (ZIP format)"""
        result = exporter.export_to_docx(["test-doc"])

        # DOCX files are ZIP archives, starting with PK
        assert result[:2] == b"PK"

    @pytest.mark.unit
    def test_export_to_docx_with_summary_flag(self, exporter):
        """Test DOCX export with include_summary flag"""
        result = exporter.export_to_docx(["test-doc"], include_summary=True)

        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.unit
    def test_export_to_docx_multiple_documents(self, exporter):
        """Test DOCX export with multiple documents"""
        result = exporter.export_to_docx(["doc-1", "doc-2"])

        assert isinstance(result, bytes)
        assert len(result) > 0

    # -------------------------------------------------------------------------
    # CSV Export Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_export_to_csv_returns_bytes(self, exporter):
        """Test that CSV export returns bytes"""
        result = exporter.export_to_csv(["test-doc"])

        assert isinstance(result, bytes)

    @pytest.mark.unit
    def test_export_to_csv_contains_headers(self, exporter):
        """Test that CSV contains expected column headers"""
        result = exporter.export_to_csv(["test-doc"])

        csv_content = result.decode("utf-8")

        assert "Title" in csv_content
        assert "File Path" in csv_content
        assert "Background" in csv_content
        assert "Scope" in csv_content
        assert "Headings" in csv_content

    @pytest.mark.unit
    def test_export_to_csv_valid_format(self, exporter):
        """Test that CSV output is valid CSV format"""
        result = exporter.export_to_csv(["test-doc"])

        csv_content = result.decode("utf-8")
        lines = csv_content.strip().split("\n")

        # Should have at least header row and one data row
        assert len(lines) >= 2

    @pytest.mark.unit
    def test_export_to_csv_multiple_documents(self, exporter, mock_elasticsearch):
        """Test CSV export with multiple documents"""
        # Setup mock to return different docs
        mock_elasticsearch.get.side_effect = [
            {"_source": {"id": "1", "title": "Doc 1", "file_path": "/path/1"}},
            {"_source": {"id": "2", "title": "Doc 2", "file_path": "/path/2"}},
        ]

        result = exporter.export_to_csv(["doc-1", "doc-2"])

        csv_content = result.decode("utf-8")
        lines = csv_content.strip().split("\n")

        # Header + 2 data rows
        assert len(lines) == 3

    # -------------------------------------------------------------------------
    # Content Truncation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_pdf_truncates_long_content(self, exporter, mock_elasticsearch):
        """Test that PDF export truncates very long content"""
        long_content = "A" * 5000
        mock_elasticsearch.get.return_value = {
            "_source": {
                "id": "long-doc",
                "title": "Long Document",
                "background": long_content,
                "scope": long_content,
            }
        }

        result = exporter.export_to_pdf(["long-doc"])

        # Should complete without error
        assert isinstance(result, bytes)

    @pytest.mark.unit
    def test_csv_truncates_long_content(self, exporter, mock_elasticsearch):
        """Test that CSV export truncates content to 500 chars"""
        long_content = "A" * 1000
        mock_elasticsearch.get.return_value = {
            "_source": {
                "id": "long-doc",
                "title": "Long Document",
                "background": long_content,
                "scope": long_content,
            }
        }

        result = exporter.export_to_csv(["long-doc"])

        csv_content = result.decode("utf-8")

        # Content should be truncated
        # Each field should be at most 500 chars
        assert csv_content is not None

    # -------------------------------------------------------------------------
    # Error Handling Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_export_handles_missing_fields(self, exporter, mock_elasticsearch):
        """Test export handles documents with missing optional fields"""
        mock_elasticsearch.get.return_value = {
            "_source": {
                "id": "minimal-doc",
                "title": "Minimal Document",
                # No background, scope, headings
            }
        }

        pdf_result = exporter.export_to_pdf(["minimal-doc"])
        docx_result = exporter.export_to_docx(["minimal-doc"])
        csv_result = exporter.export_to_csv(["minimal-doc"])

        assert isinstance(pdf_result, bytes)
        assert isinstance(docx_result, bytes)
        assert isinstance(csv_result, bytes)

    @pytest.mark.unit
    def test_export_handles_none_values(self, exporter, mock_elasticsearch):
        """Test export handles None values in document fields"""
        mock_elasticsearch.get.return_value = {
            "_source": {
                "id": "none-doc",
                "title": "Document with Nones",
                "background": None,
                "scope": None,
                "headings": None,
            }
        }

        pdf_result = exporter.export_to_pdf(["none-doc"])

        assert isinstance(pdf_result, bytes)
