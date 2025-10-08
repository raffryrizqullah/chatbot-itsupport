"""
Unit tests for Pinecone vector store service.

Tests document storage, retrieval, and vector store operations with mocked dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from typing import List, Dict, Any
import uuid

from app.services.vectorstore import VectorStoreService
from app.core.exceptions import VectorStoreError


@pytest.fixture
def mock_pinecone_client():
    """Create mock Pinecone client for testing."""
    mock_client = MagicMock()
    mock_client.list_indexes.return_value = []
    mock_client.create_index.return_value = None
    return mock_client


@pytest.fixture
def mock_redis_docstore():
    """Create mock Redis docstore for testing."""
    mock_store = MagicMock()
    mock_store.mset.return_value = None
    mock_store.mget.return_value = []
    return mock_store


@pytest.fixture
def mock_vectorstore():
    """Create mock PineconeVectorStore for testing."""
    mock_vs = MagicMock()
    mock_vs.add_documents.return_value = None
    return mock_vs


@pytest.mark.unit
class TestVectorStoreService:
    """Test suite for vector store service."""

    def test_ensure_index_exists_creates_new_index(self, mock_pinecone_client):
        """Test that _ensure_index_exists creates index when it doesn't exist."""
        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings"):
                with patch("app.services.vectorstore.RedisDocStore"):
                    with patch("app.services.vectorstore.PineconeVectorStore"):
                        with patch("app.services.vectorstore.MultiVectorRetriever"):
                            VectorStoreService()

                            # Verify index creation was called
                            mock_pinecone_client.create_index.assert_called_once()

    def test_ensure_index_exists_uses_existing_index(self, mock_pinecone_client):
        """Test that _ensure_index_exists uses existing index."""
        # Mock existing index
        mock_index = MagicMock()
        mock_index.name = "rag-chatbot"
        mock_pinecone_client.list_indexes.return_value = [mock_index]

        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings"):
                with patch("app.services.vectorstore.RedisDocStore"):
                    with patch("app.services.vectorstore.PineconeVectorStore"):
                        with patch("app.services.vectorstore.MultiVectorRetriever"):
                            VectorStoreService()

                            # Verify index creation was NOT called
                            mock_pinecone_client.create_index.assert_not_called()

    def test_add_documents_success(self, mock_pinecone_client, mock_redis_docstore, mock_vectorstore):
        """Test successful document addition."""
        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings"):
                with patch("app.services.vectorstore.RedisDocStore", return_value=mock_redis_docstore):
                    with patch("app.services.vectorstore.PineconeVectorStore", return_value=mock_vectorstore):
                        with patch("app.services.vectorstore.MultiVectorRetriever"):
                            service = VectorStoreService()
                            service.vectorstore = mock_vectorstore
                            service.docstore = mock_redis_docstore

                            # Create mock content
                            mock_text = MagicMock()
                            mock_table = MagicMock()

                            result = service.add_documents(
                                text_chunks=[mock_text],
                                text_summaries=["Text summary"],
                                tables=[mock_table],
                                table_summaries=["Table summary"],
                                images=["base64image"],
                                image_summaries=["Image description"],
                                document_id="doc123",
                            )

                            assert result["texts"] == 1
                            assert result["tables"] == 1
                            assert result["images"] == 1
                            assert result["total"] == 3

    def test_add_documents_with_source_link(self, mock_pinecone_client, mock_redis_docstore, mock_vectorstore):
        """Test adding documents with source link metadata."""
        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings"):
                with patch("app.services.vectorstore.RedisDocStore", return_value=mock_redis_docstore):
                    with patch("app.services.vectorstore.PineconeVectorStore", return_value=mock_vectorstore):
                        with patch("app.services.vectorstore.MultiVectorRetriever"):
                            service = VectorStoreService()
                            service.vectorstore = mock_vectorstore
                            service.docstore = mock_redis_docstore

                            mock_text = MagicMock()

                            result = service.add_documents(
                                text_chunks=[mock_text],
                                text_summaries=["Summary"],
                                tables=[],
                                table_summaries=[],
                                images=[],
                                image_summaries=[],
                                document_id="doc123",
                                source_link="https://example.com/doc.pdf",
                            )

                            # Verify vectorstore.add_documents was called
                            mock_vectorstore.add_documents.assert_called()

    def test_add_documents_with_custom_metadata(self, mock_pinecone_client, mock_redis_docstore, mock_vectorstore):
        """Test adding documents with custom metadata."""
        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings"):
                with patch("app.services.vectorstore.RedisDocStore", return_value=mock_redis_docstore):
                    with patch("app.services.vectorstore.PineconeVectorStore", return_value=mock_vectorstore):
                        with patch("app.services.vectorstore.MultiVectorRetriever"):
                            service = VectorStoreService()
                            service.vectorstore = mock_vectorstore
                            service.docstore = mock_redis_docstore

                            mock_text = MagicMock()
                            custom_metadata = {"sensitivity": "public", "category": "IT"}

                            result = service.add_documents(
                                text_chunks=[mock_text],
                                text_summaries=["Summary"],
                                tables=[],
                                table_summaries=[],
                                images=[],
                                image_summaries=[],
                                document_id="doc123",
                                custom_metadata=custom_metadata,
                            )

                            # Verify documents were added
                            mock_vectorstore.add_documents.assert_called()

    def test_add_documents_empty_content(self, mock_pinecone_client, mock_redis_docstore, mock_vectorstore):
        """Test adding documents with empty content."""
        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings"):
                with patch("app.services.vectorstore.RedisDocStore", return_value=mock_redis_docstore):
                    with patch("app.services.vectorstore.PineconeVectorStore", return_value=mock_vectorstore):
                        with patch("app.services.vectorstore.MultiVectorRetriever"):
                            service = VectorStoreService()
                            service.vectorstore = mock_vectorstore
                            service.docstore = mock_redis_docstore

                            result = service.add_documents(
                                text_chunks=[],
                                text_summaries=[],
                                tables=[],
                                table_summaries=[],
                                images=[],
                                image_summaries=[],
                                document_id="doc123",
                            )

                            assert result["total"] == 0

    def test_add_documents_raises_error_on_failure(self, mock_pinecone_client, mock_redis_docstore, mock_vectorstore):
        """Test that add_documents raises VectorStoreError on failure."""
        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings"):
                with patch("app.services.vectorstore.RedisDocStore", return_value=mock_redis_docstore):
                    with patch("app.services.vectorstore.PineconeVectorStore", return_value=mock_vectorstore):
                        with patch("app.services.vectorstore.MultiVectorRetriever"):
                            service = VectorStoreService()
                            service.vectorstore = mock_vectorstore
                            service.docstore = mock_redis_docstore

                            # Make vectorstore.add_documents raise error
                            mock_vectorstore.add_documents.side_effect = Exception("Pinecone error")

                            mock_text = MagicMock()

                            with pytest.raises(VectorStoreError, match="Failed to add documents"):
                                service.add_documents(
                                    text_chunks=[mock_text],
                                    text_summaries=["Summary"],
                                    tables=[],
                                    table_summaries=[],
                                    images=[],
                                    image_summaries=[],
                                    document_id="doc123",
                                )

    def test_add_content_type_generates_unique_ids(self, mock_pinecone_client, mock_redis_docstore, mock_vectorstore):
        """Test that _add_content_type generates unique UUIDs for content."""
        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings"):
                with patch("app.services.vectorstore.RedisDocStore", return_value=mock_redis_docstore):
                    with patch("app.services.vectorstore.PineconeVectorStore", return_value=mock_vectorstore):
                        with patch("app.services.vectorstore.MultiVectorRetriever"):
                            service = VectorStoreService()
                            service.vectorstore = mock_vectorstore
                            service.docstore = mock_redis_docstore

                            mock_text1 = MagicMock()
                            mock_text2 = MagicMock()

                            content_ids = service._add_content_type(
                                content_items=[mock_text1, mock_text2],
                                summaries=["Summary 1", "Summary 2"],
                                document_id="doc123",
                                content_type="text",
                            )

                            # Verify UUIDs were generated
                            assert len(content_ids) == 2
                            assert content_ids[0] != content_ids[1]

    def test_search_success(self, mock_pinecone_client, mock_redis_docstore):
        """Test successful document search."""
        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings"):
                with patch("app.services.vectorstore.RedisDocStore", return_value=mock_redis_docstore):
                    with patch("app.services.vectorstore.PineconeVectorStore"):
                        mock_retriever = MagicMock()
                        mock_retriever.invoke.return_value = ["result1", "result2"]

                        with patch("app.services.vectorstore.MultiVectorRetriever", return_value=mock_retriever):
                            service = VectorStoreService()
                            service.retriever = mock_retriever

                            results = service.search("test query")

                            assert len(results) == 2
                            mock_retriever.invoke.assert_called_once_with("test query")

    def test_search_with_custom_k(self, mock_pinecone_client, mock_redis_docstore):
        """Test search with custom k parameter."""
        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings"):
                with patch("app.services.vectorstore.RedisDocStore", return_value=mock_redis_docstore):
                    with patch("app.services.vectorstore.PineconeVectorStore"):
                        mock_retriever = MagicMock()
                        mock_retriever.invoke.return_value = ["result"]

                        with patch("app.services.vectorstore.MultiVectorRetriever", return_value=mock_retriever):
                            service = VectorStoreService()
                            service.retriever = mock_retriever

                            results = service.search("test query", k=5)

                            # Verify search_kwargs was updated
                            assert service.retriever.search_kwargs["k"] == 5

    def test_search_with_metadata_filter(self, mock_pinecone_client, mock_redis_docstore):
        """Test search with metadata filter."""
        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings"):
                with patch("app.services.vectorstore.RedisDocStore", return_value=mock_redis_docstore):
                    with patch("app.services.vectorstore.PineconeVectorStore"):
                        mock_retriever = MagicMock()
                        mock_retriever.invoke.return_value = ["filtered_result"]

                        with patch("app.services.vectorstore.MultiVectorRetriever", return_value=mock_retriever):
                            service = VectorStoreService()
                            service.retriever = mock_retriever

                            metadata_filter = {"sensitivity": "public"}
                            results = service.search("test query", metadata_filter=metadata_filter)

                            # Verify filter was applied
                            assert service.retriever.search_kwargs["filter"] == metadata_filter

    def test_search_raises_error_on_failure(self, mock_pinecone_client, mock_redis_docstore):
        """Test that search raises VectorStoreError on failure."""
        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings"):
                with patch("app.services.vectorstore.RedisDocStore", return_value=mock_redis_docstore):
                    with patch("app.services.vectorstore.PineconeVectorStore"):
                        mock_retriever = MagicMock()
                        mock_retriever.invoke.side_effect = Exception("Search failed")

                        with patch("app.services.vectorstore.MultiVectorRetriever", return_value=mock_retriever):
                            service = VectorStoreService()
                            service.retriever = mock_retriever

                            with pytest.raises(VectorStoreError, match="Search failed"):
                                service.search("test query")

    def test_vectorstore_initializes_with_correct_settings(self, mock_pinecone_client):
        """Test that vector store initializes with correct configuration."""
        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings") as mock_embeddings:
                with patch("app.services.vectorstore.RedisDocStore"):
                    with patch("app.services.vectorstore.PineconeVectorStore"):
                        with patch("app.services.vectorstore.MultiVectorRetriever"):
                            VectorStoreService()

                            # Verify OpenAIEmbeddings was called with correct model
                            mock_embeddings.assert_called_once()
                            call_kwargs = mock_embeddings.call_args.kwargs
                            assert call_kwargs["model"] == "text-embedding-3-large"

    def test_delete_by_document_id_logs_warning(self, mock_pinecone_client, mock_redis_docstore):
        """Test that delete_by_document_id logs warning (not fully implemented)."""
        with patch("app.services.vectorstore.Pinecone", return_value=mock_pinecone_client):
            with patch("app.services.vectorstore.OpenAIEmbeddings"):
                with patch("app.services.vectorstore.RedisDocStore", return_value=mock_redis_docstore):
                    with patch("app.services.vectorstore.PineconeVectorStore"):
                        with patch("app.services.vectorstore.MultiVectorRetriever"):
                            service = VectorStoreService()

                            # Should not raise error, just log warning
                            service.delete_by_document_id("doc123")
