"""
Query endpoints for RAG-based question answering.

Handles user queries against indexed documents using retrieval-augmented generation.
"""

from typing import Union
import uuid
from fastapi import APIRouter, HTTPException, status
from app.models.schemas import (
    QueryRequest,
    QueryResponse,
    QueryWithSourcesResponse,
    ErrorResponse,
)
from app.services.vectorstore import VectorStoreService
from app.services.rag_chain import RAGChainService
from app.services.chat_memory import ChatMemoryService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy initialization to avoid startup errors
_vectorstore = None
_rag_chain = None
_chat_memory = None


def get_vectorstore() -> VectorStoreService:
    """Get or create vectorstore service instance."""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = VectorStoreService()
    return _vectorstore


def get_rag_chain() -> RAGChainService:
    """Get or create RAG chain service instance."""
    global _rag_chain
    if _rag_chain is None:
        _rag_chain = RAGChainService()
    return _rag_chain


def get_chat_memory() -> ChatMemoryService:
    """Get or create chat memory service instance."""
    global _chat_memory
    if _chat_memory is None:
        _chat_memory = ChatMemoryService()
    return _chat_memory


@router.post(
    "/query",
    response_model=Union[QueryResponse, QueryWithSourcesResponse],
    tags=["query"],
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def query_documents(request: QueryRequest) -> Union[QueryResponse, QueryWithSourcesResponse]:
    """
    Query indexed documents with a question.

    Retrieves relevant document chunks and generates an answer using RAG.
    Supports conversation history via session_id for multi-turn conversations.

    Args:
        request: Query request with question and optional parameters.

    Returns:
        QueryResponse with generated answer and metadata.

    Raises:
        HTTPException: If query processing fails.
    """
    try:
        logger.info(f"Processing query: {request.question[:50]}...")

        # Get or generate session_id for conversation tracking
        session_id = request.session_id or f"anon_{uuid.uuid4()}"
        logger.info(f"Using session_id: {session_id}")

        # Get service instances
        vectorstore = get_vectorstore()
        rag_chain = get_rag_chain()
        chat_memory = get_chat_memory()

        # Load chat history from Redis
        chat_history = chat_memory.get_history(session_id)
        logger.info(f"Loaded {len(chat_history)} messages from chat history")

        # Retrieve relevant documents
        k = request.top_k if request.top_k is not None else None
        retrieved_docs = vectorstore.search(request.question, k=k)

        if not retrieved_docs:
            logger.warning("No relevant documents found")
            answer = "I couldn't find any relevant information to answer your question."

            # Save to chat history even for no results
            chat_memory.add_exchange(session_id, request.question, answer)

            return QueryResponse(
                answer=answer,
                session_id=session_id,
                metadata={
                    "num_documents_retrieved": 0,
                    "include_sources": request.include_sources,
                    "has_chat_history": len(chat_history) > 0,
                },
            )

        # Generate answer with or without chat history
        if chat_history:
            # Use history-aware generation
            result = rag_chain.generate_answer_with_history(
                request.question, retrieved_docs, chat_history
            )
        else:
            # First message in conversation
            if request.include_sources:
                result = rag_chain.generate_answer_with_sources(
                    request.question, retrieved_docs
                )
            else:
                result = rag_chain.generate_answer(request.question, retrieved_docs)

        # Save conversation exchange to Redis
        chat_memory.add_exchange(session_id, request.question, result["answer"])
        logger.info(f"Saved conversation exchange to session {session_id}")

        # Return response based on include_sources
        if request.include_sources and "sources" in result:
            return QueryWithSourcesResponse(
                answer=result["answer"],
                session_id=session_id,
                sources=result["sources"],
                metadata={
                    **result["metadata"],
                    "num_documents_retrieved": len(retrieved_docs),
                },
            )
        else:
            return QueryResponse(
                answer=result["answer"],
                session_id=session_id,
                metadata={
                    **result.get("context", result.get("metadata", {})),
                    "num_documents_retrieved": len(retrieved_docs),
                },
            )

    except Exception as e:
        msg = f"Query processing failed: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )
