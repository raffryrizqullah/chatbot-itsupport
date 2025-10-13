"""
Unit tests for summarization service.

Tests text, table, and image summarization using mocked GPT-4o-mini.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from typing import List

from app.services.summarizer import SummarizerService
from app.core.exceptions import SummarizerError


@pytest.fixture
def mock_openai_model():
    """Create mock ChatOpenAI model for testing."""
    mock_model = MagicMock()
    mock_model.invoke.return_value = "Summary of the content"
    return mock_model


@pytest.mark.unit
class TestSummarizerService:
    """Test suite for summarization service."""

    def test_summarize_texts_success(self, mock_openai_model):
        """Test successful text summarization."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            # Create mock text elements
            mock_text1 = MagicMock()
            mock_text1.__str__ = lambda self: "First text chunk"
            mock_text2 = MagicMock()
            mock_text2.__str__ = lambda self: "Second text chunk"

            texts = [mock_text1, mock_text2]

            # Mock the chain batch
            mock_chain = MagicMock()
            mock_chain.batch.return_value = ["Summary 1", "Summary 2"]
            with patch.object(summarizer.model, "__or__", return_value=mock_chain):
                summaries = summarizer.summarize_texts(texts)

                assert len(summaries) == 2
                assert summaries[0] == "Summary 1"
                assert summaries[1] == "Summary 2"

    def test_summarize_texts_empty_input(self, mock_openai_model):
        """Test summarizing empty text list returns empty list."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            summaries = summarizer.summarize_texts([])

            assert summaries == []

    def test_summarize_texts_raises_error_on_failure(self, mock_openai_model):
        """Test that summarization error raises SummarizerError."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            mock_text = MagicMock()
            texts = [mock_text]

            mock_chain = MagicMock()
            mock_chain.batch.side_effect = Exception("API error")
            with patch.object(summarizer.model, "__or__", return_value=mock_chain):
                with pytest.raises(SummarizerError, match="Failed to summarize texts"):
                    summarizer.summarize_texts(texts)

    def test_summarize_tables_success(self, mock_openai_model):
        """Test successful table summarization."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            # Create mock table elements
            mock_table1 = MagicMock()
            mock_table1.metadata.text_as_html = "<table><tr><td>Data 1</td></tr></table>"
            mock_table2 = MagicMock()
            mock_table2.metadata.text_as_html = "<table><tr><td>Data 2</td></tr></table>"

            tables = [mock_table1, mock_table2]

            mock_chain = MagicMock()
            mock_chain.batch.return_value = ["Table summary 1", "Table summary 2"]
            with patch.object(summarizer.model, "__or__", return_value=mock_chain):
                summaries = summarizer.summarize_tables(tables)

                assert len(summaries) == 2
                assert summaries[0] == "Table summary 1"
                assert summaries[1] == "Table summary 2"

    def test_summarize_tables_empty_input(self, mock_openai_model):
        """Test summarizing empty table list returns empty list."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            summaries = summarizer.summarize_tables([])

            assert summaries == []

    def test_summarize_tables_raises_error_on_failure(self, mock_openai_model):
        """Test that table summarization error raises SummarizerError."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            mock_table = MagicMock()
            mock_table.metadata.text_as_html = "<table></table>"
            tables = [mock_table]

            mock_chain = MagicMock()
            mock_chain.batch.side_effect = Exception("API error")
            with patch.object(summarizer.model, "__or__", return_value=mock_chain):
                with pytest.raises(SummarizerError, match="Failed to summarize tables"):
                    summarizer.summarize_tables(tables)

    def test_summarize_images_success(self, mock_openai_model):
        """Test successful image summarization."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            images = ["base64image1", "base64image2"]

            mock_chain = MagicMock()
            mock_chain.batch.return_value = ["Image description 1", "Image description 2"]
            with patch.object(summarizer.model, "__or__", return_value=mock_chain):
                summaries = summarizer.summarize_images(images)

                assert len(summaries) == 2
                assert summaries[0] == "Image description 1"
                assert summaries[1] == "Image description 2"

    def test_summarize_images_empty_input(self, mock_openai_model):
        """Test summarizing empty image list returns empty list."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            summaries = summarizer.summarize_images([])

            assert summaries == []

    def test_summarize_images_raises_error_on_failure(self, mock_openai_model):
        """Test that image summarization error raises SummarizerError."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            images = ["base64image"]

            mock_chain = MagicMock()
            mock_chain.batch.side_effect = Exception("Vision API error")
            with patch.object(summarizer.model, "__or__", return_value=mock_chain):
                with pytest.raises(SummarizerError, match="Failed to summarize images"):
                    summarizer.summarize_images(images)

    def test_summarizer_initializes_with_correct_model(self):
        """Test that summarizer initializes with GPT-4o-mini model."""
        with patch("app.services.summarizer.ChatOpenAI") as mock_openai_class:
            SummarizerService()

            # Verify ChatOpenAI was called with correct parameters
            mock_openai_class.assert_called_once()
            call_kwargs = mock_openai_class.call_args.kwargs
            assert "model" in call_kwargs
            assert "temperature" in call_kwargs
            assert "api_key" in call_kwargs

    def test_summarize_texts_uses_batch_concurrency(self, mock_openai_model):
        """Test that text summarization uses batch concurrency setting."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            mock_text = MagicMock()
            texts = [mock_text]

            mock_chain = MagicMock()
            mock_chain.batch.return_value = ["Summary"]
            with patch.object(summarizer.model, "__or__", return_value=mock_chain):
                summarizer.summarize_texts(texts)

                # Verify batch was called with max_concurrency
                mock_chain.batch.assert_called_once()
                call_kwargs = mock_chain.batch.call_args[1]
                assert "max_concurrency" in call_kwargs

    def test_summarize_tables_uses_batch_concurrency(self, mock_openai_model):
        """Test that table summarization uses batch concurrency setting."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            mock_table = MagicMock()
            mock_table.metadata.text_as_html = "<table></table>"
            tables = [mock_table]

            mock_chain = MagicMock()
            mock_chain.batch.return_value = ["Summary"]
            with patch.object(summarizer.model, "__or__", return_value=mock_chain):
                summarizer.summarize_tables(tables)

                # Verify batch was called with max_concurrency
                mock_chain.batch.assert_called_once()
                call_kwargs = mock_chain.batch.call_args[1]
                assert "max_concurrency" in call_kwargs

    def test_summarize_images_uses_batch_concurrency(self, mock_openai_model):
        """Test that image summarization uses batch concurrency setting."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            images = ["base64image"]

            mock_chain = MagicMock()
            mock_chain.batch.return_value = ["Description"]
            with patch.object(summarizer.model, "__or__", return_value=mock_chain):
                summarizer.summarize_images(images)

                # Verify batch was called with max_concurrency
                mock_chain.batch.assert_called_once()
                call_kwargs = mock_chain.batch.call_args[1]
                assert "max_concurrency" in call_kwargs

    def test_summarize_texts_single_item(self, mock_openai_model):
        """Test summarizing single text item."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            mock_text = MagicMock()
            texts = [mock_text]

            mock_chain = MagicMock()
            mock_chain.batch.return_value = ["Single summary"]
            with patch.object(summarizer.model, "__or__", return_value=mock_chain):
                summaries = summarizer.summarize_texts(texts)

                assert len(summaries) == 1
                assert summaries[0] == "Single summary"

    def test_summarize_tables_single_item(self, mock_openai_model):
        """Test summarizing single table item."""
        with patch("app.services.summarizer.ChatOpenAI", return_value=mock_openai_model):
            summarizer = SummarizerService()

            mock_table = MagicMock()
            mock_table.metadata.text_as_html = "<table></table>"
            tables = [mock_table]

            mock_chain = MagicMock()
            mock_chain.batch.return_value = ["Single table summary"]
            with patch.object(summarizer.model, "__or__", return_value=mock_chain):
                summaries = summarizer.summarize_tables(tables)

                assert len(summaries) == 1
                assert summaries[0] == "Single table summary"
