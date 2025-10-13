"""
Unit tests for PDF processor service.

Tests PDF extraction, text/table separation, and image extraction.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import List

from app.services.pdf_processor import PDFProcessor, ExtractedContent
from app.core.exceptions import PDFProcessingError


# Mock classes for testing
class MockCompositeElement:
    """Mock CompositeElement for testing."""
    def __init__(self, orig_elements=None):
        self.metadata = MagicMock()
        self.metadata.orig_elements = orig_elements or []


class MockTable:
    """Mock Table for testing."""
    def __init__(self):
        self.metadata = MagicMock()
        self.metadata.text_as_html = "<table></table>"


class MockImage:
    """Mock Image for testing."""
    def __init__(self, base64_data=None):
        self.metadata = MagicMock()
        self.metadata.image_base64 = base64_data


@pytest.mark.unit
class TestPDFProcessor:
    """Test suite for PDF processing service."""

    def test_process_pdf_success(self):
        """Test successful PDF processing with all content types."""
        processor = PDFProcessor()

        mock_text = MockCompositeElement()
        mock_table = MockTable()
        mock_chunks = [mock_text, mock_table]

        with patch("app.services.pdf_processor.partition_pdf") as mock_partition:
            mock_partition.return_value = mock_chunks

            result = processor.process_pdf("test.pdf")

            assert isinstance(result, ExtractedContent)
            assert len(result.texts) == 1
            assert len(result.tables) == 1
            assert isinstance(result.images, list)

    def test_process_pdf_with_images(self):
        """Test PDF processing with image extraction."""
        processor = PDFProcessor()

        mock_image_element = MockImage("base64encodedimage")
        mock_text = MockCompositeElement(orig_elements=[mock_image_element])

        with patch("app.services.pdf_processor.partition_pdf") as mock_partition:
            mock_partition.return_value = [mock_text]

            result = processor.process_pdf("test.pdf")

            assert len(result.images) == 1
            assert result.images[0] == "base64encodedimage"

    def test_process_pdf_empty_document(self):
        """Test processing PDF with no content."""
        processor = PDFProcessor()

        with patch("app.services.pdf_processor.partition_pdf") as mock_partition:
            mock_partition.return_value = []

            result = processor.process_pdf("empty.pdf")

            assert len(result.texts) == 0
            assert len(result.tables) == 0
            assert len(result.images) == 0

    def test_process_pdf_raises_error_on_failure(self):
        """Test that processing error raises PDFProcessingError."""
        processor = PDFProcessor()

        with patch("app.services.pdf_processor.partition_pdf") as mock_partition:
            mock_partition.side_effect = Exception("PDF is corrupted")

            with pytest.raises(PDFProcessingError, match="Failed to process PDF"):
                processor.process_pdf("corrupt.pdf")

    def test_separate_text_and_tables_only_texts(self):
        """Test separating chunks with only text elements."""
        processor = PDFProcessor()

        chunks = [MockCompositeElement(), MockCompositeElement()]
        texts, tables = processor._separate_text_and_tables(chunks)

        assert len(texts) == 2
        assert len(tables) == 0

    def test_separate_text_and_tables_only_tables(self):
        """Test separating chunks with only table elements."""
        processor = PDFProcessor()

        chunks = [MockTable(), MockTable()]
        texts, tables = processor._separate_text_and_tables(chunks)

        assert len(texts) == 0
        assert len(tables) == 2

    def test_separate_text_and_tables_mixed(self):
        """Test separating chunks with mixed text and table elements."""
        processor = PDFProcessor()

        chunks = [MockCompositeElement(), MockTable(), MockCompositeElement(), MockTable()]
        texts, tables = processor._separate_text_and_tables(chunks)

        assert len(texts) == 2
        assert len(tables) == 2

    def test_extract_images_no_images(self):
        """Test image extraction when no images present."""
        processor = PDFProcessor()

        chunks = [MockCompositeElement()]
        images = processor._extract_images(chunks)

        assert len(images) == 0

    def test_extract_images_multiple_images(self):
        """Test extracting multiple images from chunks."""
        processor = PDFProcessor()

        mock_image1 = MockImage("image1base64")
        mock_image2 = MockImage("image2base64")
        mock_text = MockCompositeElement(orig_elements=[mock_image1, mock_image2])

        chunks = [mock_text]
        images = processor._extract_images(chunks)

        assert len(images) == 2
        assert "image1base64" in images
        assert "image2base64" in images

    def test_extract_images_skips_none_base64(self):
        """Test that images with None base64 are skipped."""
        processor = PDFProcessor()

        mock_image_with_data = MockImage("validbase64")
        mock_image_without_data = MockImage(None)
        mock_text = MockCompositeElement(orig_elements=[mock_image_with_data, mock_image_without_data])

        chunks = [mock_text]
        images = processor._extract_images(chunks)

        assert len(images) == 1
        assert images[0] == "validbase64"

    def test_processor_initialization_uses_settings(self):
        """Test that processor initializes with correct settings."""
        processor = PDFProcessor()

        # Verify settings are loaded
        assert processor.chunking_strategy is not None
        assert processor.max_characters > 0
        assert processor.combine_text_under_n_chars > 0
        assert processor.new_after_n_chars > 0

    def test_process_pdf_calls_partition_with_correct_params(self):
        """Test that partition_pdf is called with correct parameters."""
        processor = PDFProcessor()

        with patch("app.services.pdf_processor.partition_pdf") as mock_partition:
            mock_partition.return_value = []

            processor.process_pdf("test.pdf")

            # Verify partition_pdf was called with correct arguments
            mock_partition.assert_called_once()
            call_kwargs = mock_partition.call_args.kwargs
            assert call_kwargs["filename"] == "test.pdf"
            assert call_kwargs["infer_table_structure"] is True
            assert call_kwargs["strategy"] == "hi_res"
            assert call_kwargs["extract_image_block_types"] == ["Image"]
