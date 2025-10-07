"""
Query endpoints for RAG-based question answering.

Handles user queries against indexed documents using retrieval-augmented generation.
"""

from fastapi import APIRouter, HTTPException, status
from app.models.schemas import (
    QueryRequest,
    QueryResponse,
    QueryWithSourcesResponse,
    ErrorResponse,
)
from app.services.vectorstore import VectorStoreService
from app.services.rag_chain import RAGChainService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy initialization to avoid startup errors
_vectorstore = None
_rag_chain = None


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


@router.post(
    "/query",
    response_model=QueryResponse,
    tags=["query"],
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def query_documents(request: QueryRequest) -> QueryResponse:
    """
    Query indexed documents with a question.

    Retrieves relevant document chunks and generates an answer using RAG.

    Args:
        request: Query request with question and optional parameters.

    Returns:
        QueryResponse with generated answer and metadata.

    Raises:
        HTTPException: If query processing fails.
    """
    try:
        logger.info(f"Processing query: {request.question[:50]}...")

        # Get service instances
        vectorstore = get_vectorstore()
        rag_chain = get_rag_chain()

        # Retrieve relevant documents
        k = request.top_k if request.top_k is not None else None
        retrieved_docs = vectorstore.search(request.question, k=k)

        if not retrieved_docs:
            logger.warning("No relevant documents found")
            return QueryResponse(
                answer="I couldn't find any relevant information to answer your question.",
                metadata={
                    "num_documents_retrieved": 0,
                    "include_sources": request.include_sources,
                },
            )

        # Generate answer
        if request.include_sources:
            result = rag_chain.generate_answer_with_sources(
                request.question, retrieved_docs
            )
            return QueryWithSourcesResponse(
                answer=result["answer"],
                sources=result["sources"],
                metadata={
                    **result["metadata"],
                    "num_documents_retrieved": len(retrieved_docs),
                },
            )
        else:
            result = rag_chain.generate_answer(request.question, retrieved_docs)
            return QueryResponse(
                answer=result["answer"],
                metadata={
                    **result["context"],
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
