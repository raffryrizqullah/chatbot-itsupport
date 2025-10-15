"""
Unit tests for LangGraphRAGService.

Tests the LangGraph-based conversational RAG implementation.
Note: Complex integration tests (query execution, tool calling) should be
tested manually via API endpoint or integration tests.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.services.langgraph_rag import LangGraphRAGService


@pytest.fixture
def mock_vectorstore():
    """Create a mock vectorstore for testing."""
    mock = MagicMock()
    return mock


@pytest.fixture
def langgraph_service(mock_vectorstore):
    """Create LangGraphRAGService instance with mocked vectorstore."""
    with patch("app.services.langgraph_rag.VectorStoreService", return_value=mock_vectorstore):
        service = LangGraphRAGService(vectorstore=mock_vectorstore, enable_memory=False)
        return service


def test_langgraph_service_initialization(langgraph_service):
    """Test that LangGraphRAGService initializes correctly."""
    assert langgraph_service is not None
    assert langgraph_service.llm is not None
    assert langgraph_service.graph is not None
    assert langgraph_service.vectorstore is not None
    assert langgraph_service._current_metadata_filter is None


def test_conversation_history_placeholder(langgraph_service):
    """Test conversation history retrieval placeholder."""
    history = langgraph_service.get_conversation_history("test_thread")

    # Should return empty list (placeholder implementation)
    assert history == []


def test_graph_compilation_with_memory(mock_vectorstore):
    """Test graph compilation with MemorySaver checkpointer."""
    with patch("app.services.langgraph_rag.VectorStoreService", return_value=mock_vectorstore):
        service = LangGraphRAGService(vectorstore=mock_vectorstore, enable_memory=True)

        assert service.graph is not None


def test_graph_compilation_without_memory(mock_vectorstore):
    """Test graph compilation without memory."""
    with patch("app.services.langgraph_rag.VectorStoreService", return_value=mock_vectorstore):
        service = LangGraphRAGService(vectorstore=mock_vectorstore, enable_memory=False)

        assert service.graph is not None
