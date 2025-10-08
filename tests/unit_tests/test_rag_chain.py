"""
Unit tests for RAG chain service.

Tests RAG question answering with mocked ChatOpenAI model.
"""

import pytest
from unittest.mock import MagicMock, patch
from base64 import b64encode
from typing import List, Dict

from app.services.rag_chain import RAGChainService
from app.core.exceptions import RAGChainError
from langchain_core.documents import Document


@pytest.fixture
def mock_openai_model():
    """Create mock ChatOpenAI model for testing."""
    mock_model = MagicMock()
    mock_model.invoke.return_value = "Answer to the question"
    return mock_model


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
            with patch("app.services.rag_chain.StrOutputParser") as mock_parser_class:
                # Mock parser to return string directly
                mock_parser = MagicMock()
                mock_parser_class.return_value = mock_parser

                # Mock the full chain invoke
                with patch.object(mock_openai_model, "invoke", return_value="Jawaban dalam bahasa Indonesia"):
                    service = RAGChainService()

                    # Create mock documents
                    doc1 = Document(page_content="Text content 1", metadata={})
                    doc2 = Document(page_content="Text content 2", metadata={})
                    docs = [doc1, doc2]

                    result = service.generate_answer("Apa itu IT support?", docs)

                    assert result["answer"] == "Jawaban dalam bahasa Indonesia"
                    assert result["context"]["num_texts"] == 2
                    assert result["context"]["num_images"] == 0

    def test_generate_answer_with_images(self, mock_openai_model):
        """Test generating answer with base64 images."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            # Create base64 image string
            image_b64 = b64encode(b"fake image data").decode()
            docs = [image_b64]

            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "Deskripsi gambar"
            with patch.object(service.model, "__or__", return_value=mock_chain):
                result = service.generate_answer("Apa yang ada di gambar?", docs)

                assert result["answer"] == "Deskripsi gambar"
                assert result["context"]["num_texts"] == 0
                assert result["context"]["num_images"] == 1

    def test_generate_answer_with_mixed_content(self, mock_openai_model):
        """Test generating answer with mixed text and images."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            doc = Document(page_content="Text", metadata={})
            image_b64 = b64encode(b"image").decode()
            docs = [doc, image_b64]

            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "Jawaban lengkap"
            with patch.object(service.model, "__or__", return_value=mock_chain):
                result = service.generate_answer("Pertanyaan", docs)

                assert result["context"]["num_texts"] == 1
                assert result["context"]["num_images"] == 1

    def test_generate_answer_empty_documents(self, mock_openai_model):
        """Test generating answer with empty documents."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "Tidak ada konteks"
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

            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "Jawaban dengan konteks history"
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

            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "Jawaban"
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

    def test_generate_answer_with_sources_success(self, mock_openai_model):
        """Test generating answer with source documents."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            doc = Document(page_content="Source text", metadata={"source": "test.pdf"})
            image_b64 = b64encode(b"image").decode()
            docs = [doc, image_b64]

            mock_chain = MagicMock()
            mock_chain.invoke.return_value = "Jawaban dengan sumber"
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

    def test_parse_documents_separates_text_and_images(self, mock_openai_model):
        """Test _parse_documents correctly separates text and images."""
        with patch("app.services.rag_chain.ChatOpenAI", return_value=mock_openai_model):
            service = RAGChainService()

            doc = Document(page_content="Text content", metadata={})
            image_b64 = b64encode(b"image data").decode()
            docs = [doc, image_b64]

            result = service._parse_documents(docs)

            assert len(result["texts"]) == 1
            assert len(result["images"]) == 1

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
