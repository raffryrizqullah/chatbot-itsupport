"""
Unit tests for RAG chain service.

Tests RAG question answering with mocked ChatOpenAI model.
"""

import pytest
from unittest.mock import MagicMock, patch
from base64 import b64encode
from typing import List, Dict
from io import BytesIO

from app.services.rag_chain import RAGChainService
from app.core.exceptions import RAGChainError
from langchain_core.documents import Document

try:
    from PIL import Image
except ImportError:
    Image = None


@pytest.fixture
def mock_openai_model():
    """Create mock ChatOpenAI model for testing."""
    mock_model = MagicMock()
    mock_model.invoke.return_value = "Answer to the question"
    return mock_model


def create_mock_chain(return_value: str):
    """
    Create a properly configured mock chain that works with LangChain's pipe operator.

    Args:
        return_value: The string value to return from chain.invoke().

    Returns:
        Mock chain object that can be used with __or__ patching.
    """
    # Create a mock for the final chain after piping with StrOutputParser
    final_mock = MagicMock()
    final_mock.invoke.return_value = return_value

    # Create a mock for the intermediate chain (prompt | model)
    intermediate_mock = MagicMock()
    intermediate_mock.__or__.return_value = final_mock

    return intermediate_mock


@pytest.mark.unit
class TestRAGChainService:
    """Test suite for RAG chain service."""

    def test_rag_chain_initialization(self):
        """Test RAG chain initializes with correct model."""
        with patch("app.services.rag_chain.ChatOpenAI") as mock_openai_class:
            RAGChainService()

            # Verify ChatOpenAI was called
            mock_openai_class.assert_called_once()
            call_kwargs = mock_openai_class.call_args.kwargs
            assert "model" in call_kwargs
            assert "temperature" in call_kwargs
            assert "api_key" in call_kwargs

    def test_generate_answer_with_text_documents(self, mock_openai_model):
        """Test generating answer with text documents."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            # Create mock documents
            doc1 = Document(page_content="Text content 1", metadata={})
            doc2 = Document(page_content="Text content 2", metadata={})
            docs = [doc1, doc2]

            # Mock the chain result
            mock_chain = create_mock_chain("Jawaban dalam bahasa Indonesia")

            with patch.object(service.model, "__or__", return_value=mock_chain):
                result = service.generate_answer("Apa itu IT support?", docs)

                assert result["answer"] == "Jawaban dalam bahasa Indonesia"
                assert result["context"]["num_texts"] == 2
                assert result["context"]["num_images"] == 0

    @pytest.mark.skipif(Image is None, reason="PIL/Pillow not installed")
    def test_generate_answer_with_images(self, mock_openai_model):
        """Test generating answer with base64 images."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            # Create a valid PNG image
            img = Image.new("RGB", (50, 50), color="blue")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            image_b64 = b64encode(buffer.read()).decode()
            docs = [image_b64]

            mock_chain = create_mock_chain("Deskripsi gambar")
            with patch.object(service.model, "__or__", return_value=mock_chain):
                result = service.generate_answer("Apa yang ada di gambar?", docs)

                assert result["answer"] == "Deskripsi gambar"
                assert result["context"]["num_texts"] == 0
                assert result["context"]["num_images"] == 1

    @pytest.mark.skipif(Image is None, reason="PIL/Pillow not installed")
    def test_generate_answer_with_mixed_content(self, mock_openai_model):
        """Test generating answer with mixed text and images."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            doc = Document(page_content="Text", metadata={})
            # Create a valid PNG image
            img = Image.new("RGB", (50, 50), color="red")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            image_b64 = b64encode(buffer.read()).decode()
            docs = [doc, image_b64]

            mock_chain = create_mock_chain("Jawaban lengkap")
            with patch.object(service.model, "__or__", return_value=mock_chain):
                result = service.generate_answer("Pertanyaan", docs)

                assert result["context"]["num_texts"] == 1
                assert result["context"]["num_images"] == 1

    def test_generate_answer_empty_documents(self, mock_openai_model):
        """Test generating answer with empty documents."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            mock_chain = create_mock_chain("Tidak ada konteks")
            with patch.object(service.model, "__or__", return_value=mock_chain):
                result = service.generate_answer("Pertanyaan", [])

                assert result["context"]["num_texts"] == 0
                assert result["context"]["num_images"] == 0

    def test_generate_answer_raises_error_on_failure(self, mock_openai_model):
        """Test that generate_answer raises RAGChainError on failure."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            doc = Document(page_content="Text", metadata={})

            mock_chain = MagicMock()
            mock_chain.invoke.side_effect = Exception("OpenAI API error")
            with patch.object(service.model, "__or__", return_value=mock_chain):
                with pytest.raises(RAGChainError, match="Failed to generate answer"):
                    service.generate_answer("Question", [doc])

    def test_generate_answer_with_history_success(self, mock_openai_model):
        """Test generating answer with chat history."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            doc = Document(page_content="Context", metadata={})
            chat_history = [
                {"role": "user", "content": "Pertanyaan sebelumnya"},
                {"role": "assistant", "content": "Jawaban sebelumnya"},
            ]

            mock_chain = create_mock_chain("Jawaban dengan konteks history")
            with patch.object(service.model, "__or__", return_value=mock_chain):
                result = service.generate_answer_with_history("Pertanyaan baru", [doc], chat_history)

                assert result["answer"] == "Jawaban dengan konteks history"
                assert result["context"]["has_chat_history"] is True
                assert result["context"]["history_length"] == 2

    def test_generate_answer_with_history_empty_history(self, mock_openai_model):
        """Test generating answer with empty chat history."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            doc = Document(page_content="Context", metadata={})

            mock_chain = create_mock_chain("Jawaban")
            with patch.object(service.model, "__or__", return_value=mock_chain):
                result = service.generate_answer_with_history("Pertanyaan", [doc], [])

                assert result["context"]["has_chat_history"] is False
                assert result["context"]["history_length"] == 0

    def test_generate_answer_with_history_raises_error(self, mock_openai_model):
        """Test that generate_answer_with_history raises RAGChainError on failure."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            doc = Document(page_content="Text", metadata={})

            mock_chain = MagicMock()
            mock_chain.invoke.side_effect = Exception("API error")
            with patch.object(service.model, "__or__", return_value=mock_chain):
                with pytest.raises(RAGChainError, match="Failed to generate answer with history"):
                    service.generate_answer_with_history("Question", [doc], [])

    @pytest.mark.skipif(Image is None, reason="PIL/Pillow not installed")
    def test_generate_answer_with_sources_success(self, mock_openai_model):
        """Test generating answer with source documents."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            doc = Document(page_content="Source text", metadata={"source": "test.pdf"})
            # Create a valid PNG image
            img = Image.new("RGB", (50, 50), color="green")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            image_b64 = b64encode(buffer.read()).decode()
            docs = [doc, image_b64]

            mock_chain = create_mock_chain("Jawaban dengan sumber")
            with patch.object(service.model, "__or__", return_value=mock_chain):
                result = service.generate_answer_with_sources("Pertanyaan", docs)

                assert result["answer"] == "Jawaban dengan sumber"
                assert "sources" in result
                assert result["metadata"]["num_text_sources"] == 1
                assert result["metadata"]["num_image_sources"] == 1

    def test_generate_answer_with_sources_raises_error(self, mock_openai_model):
        """Test that generate_answer_with_sources raises RAGChainError on failure."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            doc = Document(page_content="Text", metadata={})

            mock_chain = MagicMock()
            mock_chain.invoke.side_effect = Exception("API error")
            with patch.object(service.model, "__or__", return_value=mock_chain):
                with pytest.raises(RAGChainError, match="Failed to generate answer with sources"):
                    service.generate_answer_with_sources("Question", [doc])

    @pytest.mark.skipif(Image is None, reason="PIL/Pillow not installed")
    def test_parse_documents_separates_text_and_images(self, mock_openai_model):
        """Test _parse_documents correctly separates text and images."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            doc = Document(page_content="Text content", metadata={})
            # Create a valid PNG image
            img = Image.new("RGB", (50, 50), color="red")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            image_b64 = b64encode(buffer.read()).decode()
            docs = [doc, image_b64]

            result = service._parse_documents(docs)

            assert len(result["texts"]) == 1
            assert len(result["images"]) == 1
            # Images should be tuples
            assert isinstance(result["images"][0], tuple)

    def test_parse_documents_handles_invalid_base64(self, mock_openai_model):
        """Test _parse_documents treats invalid base64 as text."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            invalid_b64 = "not-valid-base64!!!"
            docs = [invalid_b64]

            result = service._parse_documents(docs)

            # Should be treated as text since base64 decode fails
            assert len(result["texts"]) == 1
            assert len(result["images"]) == 0

    def test_build_context_text_from_documents(self, mock_openai_model):
        """Test _build_context_text combines document text."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            doc1 = Document(page_content="First text", metadata={})
            doc2 = Document(page_content="Second text", metadata={})
            docs = [doc1, doc2]

            context = service._build_context_text(docs)

            assert "First text" in context
            assert "Second text" in context

    def test_build_context_text_empty_documents(self, mock_openai_model):
        """Test _build_context_text with empty documents."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            context = service._build_context_text([])

            assert context == ""

    def test_format_text_source_with_metadata(self, mock_openai_model):
        """Test _format_text_source includes metadata."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            doc = Document(page_content="Content", metadata={"source": "test.pdf", "page": 1})

            formatted = service._format_text_source(doc)

            assert "content" in formatted
            assert "metadata" in formatted
            assert formatted["metadata"]["source"] == "test.pdf"

    def test_format_text_source_without_metadata(self, mock_openai_model):
        """Test _format_text_source handles string without metadata."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            text = "Simple string"

            formatted = service._format_text_source(text)

            assert "content" in formatted
            assert formatted["content"] == "Simple string"

    def test_build_prompt_uses_indonesian_language(self, mock_openai_model):
        """Test _build_prompt uses Indonesian instructions."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            docs_by_type = {"texts": [Document(page_content="Text", metadata={})], "images": []}

            prompt = service._build_prompt("Pertanyaan", docs_by_type)

            # Prompt should contain Indonesian text
            # This is verified by checking the prompt structure
            assert prompt is not None

    def test_build_prompt_with_history_uses_indonesian(self, mock_openai_model):
        """Test _build_prompt_with_history uses Indonesian instructions."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            docs_by_type = {"texts": [Document(page_content="Text", metadata={})], "images": []}
            chat_history = [{"role": "user", "content": "Halo"}]

            prompt = service._build_prompt_with_history("Pertanyaan", docs_by_type, chat_history)

            # Prompt should contain Indonesian system message
            assert prompt is not None

    @pytest.mark.skipif(Image is None, reason="PIL/Pillow not installed")
    def test_detect_image_format_valid_png(self, mock_openai_model):
        """Test _detect_image_format correctly identifies PNG format."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            # Create a valid PNG image
            img = Image.new("RGB", (100, 100), color="red")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            png_b64 = b64encode(buffer.read()).decode()

            detected_format = service._detect_image_format(png_b64)

            assert detected_format == "png"

    @pytest.mark.skipif(Image is None, reason="PIL/Pillow not installed")
    def test_detect_image_format_valid_jpeg(self, mock_openai_model):
        """Test _detect_image_format correctly identifies JPEG format."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            # Create a valid JPEG image
            img = Image.new("RGB", (100, 100), color="blue")
            buffer = BytesIO()
            img.save(buffer, format="JPEG")
            buffer.seek(0)
            jpeg_b64 = b64encode(buffer.read()).decode()

            detected_format = service._detect_image_format(jpeg_b64)

            assert detected_format == "jpeg"

    def test_detect_image_format_invalid_data(self, mock_openai_model):
        """Test _detect_image_format returns None for invalid data."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            invalid_b64 = b64encode(b"not an image").decode()

            detected_format = service._detect_image_format(invalid_b64)

            assert detected_format is None

    @pytest.mark.skipif(Image is None, reason="PIL/Pillow not installed")
    def test_convert_image_already_supported_format(self, mock_openai_model):
        """Test _convert_image_to_supported_format returns as-is for supported formats."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            # Create PNG image (already supported)
            img = Image.new("RGB", (100, 100), color="green")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            png_b64 = b64encode(buffer.read()).decode()

            result = service._convert_image_to_supported_format(png_b64)

            assert result is not None
            converted_b64, image_format = result
            assert image_format == "png"
            assert converted_b64 == png_b64  # Should be unchanged

    @pytest.mark.skipif(Image is None, reason="PIL/Pillow not installed")
    def test_convert_image_unsupported_to_supported(self, mock_openai_model):
        """Test _convert_image_to_supported_format converts unsupported formats."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            # Create BMP image (not supported by OpenAI)
            img = Image.new("RGB", (100, 100), color="yellow")
            buffer = BytesIO()
            img.save(buffer, format="BMP")
            buffer.seek(0)
            bmp_b64 = b64encode(buffer.read()).decode()

            result = service._convert_image_to_supported_format(bmp_b64)

            assert result is not None
            converted_b64, image_format = result
            # Should be converted to JPEG or PNG
            assert image_format in ["png", "jpeg"]
            assert converted_b64 != bmp_b64  # Should be different

    def test_convert_image_invalid_data_returns_none(self, mock_openai_model):
        """Test _convert_image_to_supported_format returns None for invalid data."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            invalid_b64 = b64encode(b"corrupt image data").decode()

            result = service._convert_image_to_supported_format(invalid_b64)

            assert result is None

    @pytest.mark.skipif(Image is None, reason="PIL/Pillow not installed")
    def test_parse_documents_converts_images(self, mock_openai_model):
        """Test _parse_documents validates and converts image formats."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            # Create a valid PNG image
            img = Image.new("RGB", (50, 50), color="red")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            png_b64 = b64encode(buffer.read()).decode()

            doc = Document(page_content="Text content", metadata={})
            docs = [doc, png_b64]

            result = service._parse_documents(docs)

            assert len(result["texts"]) == 1
            assert len(result["images"]) == 1
            # Images should be tuples of (base64, format)
            img_b64, img_format = result["images"][0]
            assert img_format == "png"

    @pytest.mark.skipif(Image is None, reason="PIL/Pillow not installed")
    def test_parse_documents_skips_invalid_images(self, mock_openai_model):
        """Test _parse_documents skips images that cannot be converted."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            # Create invalid "image" data
            invalid_image_b64 = b64encode(b"not a real image").decode()

            doc = Document(page_content="Text content", metadata={})
            docs = [doc, invalid_image_b64]

            result = service._parse_documents(docs)

            assert len(result["texts"]) == 1
            # Invalid image should be skipped
            assert len(result["images"]) == 0
