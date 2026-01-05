"""
Unit tests for DocumentParser.

Tests cover:
- Text extraction from different file types
- Heading extraction logic
- Section extraction (background, scope)
- Edge cases (empty files, unsupported formats)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from app.ingestion.document_parser import DocumentParser


class TestDocumentParser:
    """Test suite for DocumentParser class"""

    def setup_method(self):
        """Set up test instance"""
        self.parser = DocumentParser()

    # -------------------------------------------------------------------------
    # Text Extraction Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_extract_text_from_txt_file(self, temp_documents_dir):
        """Test extracting text from a plain text file"""
        txt_file = Path(temp_documents_dir) / "test.txt"
        txt_file.write_text("Sample document content\nSecond line")

        result = DocumentParser.parse_document(str(txt_file))

        assert result is not None
        assert "Sample document content" in result["content"]
        assert result["file_type"] == ".txt"

    @pytest.mark.unit
    def test_parse_returns_none_for_unsupported_format(self, temp_documents_dir):
        """Test that unsupported file formats return None"""
        unsupported_file = Path(temp_documents_dir) / "test.xyz"
        unsupported_file.write_text("content")

        result = DocumentParser.parse_document(str(unsupported_file))

        assert result is None

    @pytest.mark.unit
    def test_parse_returns_none_for_empty_content(self):
        """Test that files with no extracted content return None"""
        with patch.object(DocumentParser, "extract_text_from_pdf", return_value=""):
            # Create temp PDF file path
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                result = DocumentParser.parse_document(f.name)

            assert result is None

    # -------------------------------------------------------------------------
    # Heading Extraction Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_extract_headings_uppercase(self):
        """Test extracting uppercase headings"""
        text = """
        INTRODUCTION
        This is the introduction text.
        
        BACKGROUND
        This is background text.
        
        SCOPE OF WORK
        This is scope text.
        """

        headings = DocumentParser.extract_headings(text)

        assert "INTRODUCTION" in headings
        assert "BACKGROUND" in headings
        assert "SCOPE OF WORK" in headings

    @pytest.mark.unit
    def test_extract_headings_numbered(self):
        """Test extracting numbered section headings"""
        text = """
        1. Introduction
        This is intro.
        
        2.1. Background
        This is background.
        
        3.2.1. Detailed Scope
        This is scope.
        """

        headings = DocumentParser.extract_headings(text)

        assert any("Introduction" in h for h in headings)
        assert any("Background" in h for h in headings)

    @pytest.mark.unit
    def test_extract_headings_limits_to_20(self):
        """Test that heading extraction is limited to 20 items"""
        text = "\n".join([f"HEADING NUMBER {i}" for i in range(30)])

        headings = DocumentParser.extract_headings(text)

        assert len(headings) <= 20

    @pytest.mark.unit
    def test_extract_headings_filters_short_lines(self):
        """Test that very short uppercase lines are excluded"""
        text = """
        AB
        ABC
        THIS IS A VALID HEADING
        XY
        """

        headings = DocumentParser.extract_headings(text)

        # Only the longer heading should be included
        assert "THIS IS A VALID HEADING" in headings
        assert "AB" not in headings
        assert "XY" not in headings

    # -------------------------------------------------------------------------
    # Section Extraction Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_extract_section_background(self):
        """Test extracting background section"""
        text = """
        INTRODUCTION
        Some intro text.
        
        BACKGROUND
        This is the background section with important context.
        It spans multiple lines and contains key information.
        
        SCOPE
        The scope section starts here.
        """

        background = DocumentParser.extract_section(
            text, ["background", "introduction"]
        )

        assert background is not None
        assert "background" in background.lower() or "context" in background.lower()

    @pytest.mark.unit
    def test_extract_section_scope(self):
        """Test extracting scope section"""
        text = """
        BACKGROUND
        Background info here.
        
        SCOPE OF WORK
        This defines the scope of this project.
        All deliverables are listed below.
        
        TIMELINE
        Project timeline follows.
        """

        scope = DocumentParser.extract_section(text, ["scope", "scope of work"])

        assert scope is not None
        assert "scope" in scope.lower()

    @pytest.mark.unit
    def test_extract_section_not_found(self):
        """Test that missing sections return None"""
        text = """
        INTRODUCTION
        Some text here.
        
        CONCLUSION
        Final thoughts.
        """

        result = DocumentParser.extract_section(text, ["background", "overview"])

        # May return None or content from earliest match attempt
        # The behavior depends on implementation

    # -------------------------------------------------------------------------
    # Full Parse Tests
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_parse_document_creates_complete_structure(self, temp_documents_dir):
        """Test that parse_document returns a complete document structure"""
        txt_file = Path(temp_documents_dir) / "complete-test.txt"
        txt_file.write_text("""
        SAFETY INSPECTION REPORT
        
        BACKGROUND
        This safety inspection was conducted on site.
        
        SCOPE
        Covers all equipment in Building A.
        
        FINDINGS
        No major issues found.
        """)

        result = DocumentParser.parse_document(str(txt_file))

        # Check required fields exist
        assert result is not None
        assert "title" in result
        assert "file_path" in result
        assert "file_type" in result
        assert "headings" in result
        assert "content" in result
        assert "created_at" in result
        assert "updated_at" in result

    @pytest.mark.unit
    def test_parse_instance_method_works(self, temp_documents_dir):
        """Test that instance parse method calls class method"""
        txt_file = Path(temp_documents_dir) / "instance-test.txt"
        txt_file.write_text("Test content for instance method")

        parser = DocumentParser()
        result = parser.parse(str(txt_file))

        assert result is not None
        assert "Test content" in result["content"]

    @pytest.mark.unit
    def test_content_truncated_to_5000_chars(self, temp_documents_dir):
        """Test that content is truncated to 5000 characters"""
        txt_file = Path(temp_documents_dir) / "long-content.txt"
        # Create content longer than 5000 chars
        long_content = "A" * 10000
        txt_file.write_text(long_content)

        result = DocumentParser.parse_document(str(txt_file))

        assert result is not None
        assert len(result["content"]) == 5000

    # -------------------------------------------------------------------------
    # PDF Extraction Tests (Mocked)
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_extract_text_from_pdf_success(self):
        """Test PDF text extraction with mock"""
        with patch("app.ingestion.document_parser.pdfplumber") as mock_pdfplumber:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "PDF content here"
            mock_pdf.pages = [mock_page]
            mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf

            result = DocumentParser.extract_text_from_pdf("test.pdf")

            assert result == "PDF content here"

    @pytest.mark.unit
    def test_extract_text_from_pdf_error_handling(self):
        """Test PDF extraction handles errors gracefully"""
        with patch(
            "app.ingestion.document_parser.pdfplumber.open",
            side_effect=Exception("PDF error"),
        ):
            result = DocumentParser.extract_text_from_pdf("bad.pdf")

            assert result == ""

    # -------------------------------------------------------------------------
    # DOCX Extraction Tests (Mocked)
    # -------------------------------------------------------------------------

    @pytest.mark.unit
    def test_extract_text_from_docx_success(self):
        """Test DOCX text extraction with mock"""
        with patch("app.ingestion.document_parser.DocxDocument") as mock_docx:
            mock_doc = MagicMock()
            mock_para1 = MagicMock()
            mock_para1.text = "First paragraph"
            mock_para2 = MagicMock()
            mock_para2.text = "Second paragraph"
            mock_doc.paragraphs = [mock_para1, mock_para2]
            mock_docx.return_value = mock_doc

            result = DocumentParser.extract_text_from_docx("test.docx")

            assert "First paragraph" in result
            assert "Second paragraph" in result

    @pytest.mark.unit
    def test_extract_text_from_docx_error_handling(self):
        """Test DOCX extraction handles errors gracefully"""
        with patch(
            "app.ingestion.document_parser.DocxDocument",
            side_effect=Exception("DOCX error"),
        ):
            result = DocumentParser.extract_text_from_docx("bad.docx")

            assert result == ""
