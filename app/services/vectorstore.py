"""
Pinecone vector store service for document storage and retrieval.

This module manages the Pinecone vector database, handling document
embeddings, storage, and similarity search operations.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import uuid
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.schema.document import Document
from langchain.retrievers.multi_vector import MultiVectorRetriever
from unstructured.documents.elements import CompositeElement, Table
from app.core.config import settings
from app.services.redis_store import RedisDocStore
from app.core.exceptions import VectorStoreError
import logging

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Service for managing Pinecone vector store operations.

    Implements multi-vector retrieval pattern where summaries are stored
    in Pinecone for search, while original content is stored in Redis docstore.
    """

<<<<<<< HEAD
    def __init__(self):
=======
    def __init__(self) -> None:
>>>>>>> bb677be (feat : update logging error)
        """Initialize Pinecone client, vector store, and Redis docstore."""
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model="text-embedding-3-large"
        )
        self.docstore = RedisDocStore()
        self.id_key = "doc_id"

        # Initialize index if it doesn't exist
        self._ensure_index_exists()

        # Initialize vector store
        self.vectorstore = PineconeVectorStore(
            index_name=self.index_name,
            embedding=self.embeddings,
            pinecone_api_key=settings.pinecone_api_key,
        )

        # Initialize multi-vector retriever
        self.retriever = MultiVectorRetriever(
            vectorstore=self.vectorstore,
            docstore=self.docstore,
            id_key=self.id_key,
            search_kwargs={"k": settings.rag_top_k}
        )

        logger.info(f"Initialized Pinecone vector store with index: {self.index_name}")
        logger.info("Using Redis for persistent document storage")

    def _ensure_index_exists(self) -> None:
        """
        Create Pinecone index if it doesn't exist.

        Creates a serverless index with the configured dimension and metric.
        """
        existing_indexes = [index.name for index in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            logger.info(f"Creating Pinecone index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=settings.pinecone_dimension,
                metric=settings.pinecone_metric,
                spec=ServerlessSpec(
                    cloud="aws",
                    region=settings.pinecone_environment
                )
            )
            logger.info(f"Index {self.index_name} created successfully")
        else:
            logger.info(f"Using existing Pinecone index: {self.index_name}")

    def add_documents(
        self,
        text_chunks: List[CompositeElement],
        text_summaries: List[str],
        tables: List[Table],
        table_summaries: List[str],
        images: List[str],
        image_summaries: List[str],
        document_id: str,
        source_link: Optional[str] = None,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, int]:
        """
        Add documents and their summaries to the vector store.

        Args:
            text_chunks: Original CompositeElement text chunks.
            text_summaries: Summaries of text chunks.
            tables: Original Table elements.
            table_summaries: Summaries of tables.
            images: Base64-encoded images.
            image_summaries: Summaries/descriptions of images.
            document_id: Unique identifier for the source document.
            source_link: Optional source link URL provided by user.
            custom_metadata: Optional custom metadata dict to add to all chunks.

        Returns:
            Dictionary with counts of added items.
        """
        try:
            logger.info(f"Adding documents for document_id: {document_id}")

            # Add text chunks
            text_ids = self._add_content_type(
                text_chunks, text_summaries, document_id, "text", source_link, custom_metadata
            )

            # Add tables
            table_ids = self._add_content_type(
                tables, table_summaries, document_id, "table", source_link, custom_metadata
            )

            # Add images
            image_ids = self._add_content_type(
                images, image_summaries, document_id, "image", source_link, custom_metadata
            )

            counts = {
                "texts": len(text_ids),
                "tables": len(table_ids),
                "images": len(image_ids),
                "total": len(text_ids) + len(table_ids) + len(image_ids),
            }

            logger.info(f"Added {counts['total']} items to vector store")
            return counts

        except Exception as e:
            msg = f"Failed to add documents to vector store: {str(e)}"
            logger.error(msg)
            raise VectorStoreError(msg)

    def _add_content_type(
        self,
        content_items: List[Union[CompositeElement, Table, str]],
        summaries: List[str],
        document_id: str,
        content_type: str,
        source_link: Optional[str] = None,
        custom_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Add a specific content type to the vector store.

        Args:
            content_items: Original content items (CompositeElement, Table, or base64 strings).
            summaries: Summaries of content items.
            document_id: Source document identifier.
            content_type: Type of content (``'text'``, ``'table'``, ``'image'``).
            source_link: Optional source link URL provided by user.
            custom_metadata: Optional custom metadata dict to merge into chunk metadata.

        Returns:
            List of generated content IDs.
        """
        if not content_items:
            return []

        # Generate unique IDs for each content item
        content_ids = [str(uuid.uuid4()) for _ in content_items]

        # Create summary documents with metadata
        summary_docs = []
        for i, summary in enumerate(summaries):
            metadata = {
                self.id_key: content_ids[i],
                "document_id": document_id,
                "content_type": content_type,
            }
            # Add source_link to metadata if provided
            if source_link:
                metadata["source_link"] = source_link

            # Merge custom_metadata if provided
            if custom_metadata:
                metadata.update(custom_metadata)

            summary_docs.append(
                Document(page_content=summary, metadata=metadata)
            )

        # Add summaries to vector store
        self.vectorstore.add_documents(summary_docs)

        # Store original content in docstore
        self.docstore.mset(list(zip(content_ids, content_items)))

        logger.info(f"Added {len(content_ids)} {content_type} items")
        return content_ids

    def search(
        self,
        query: str,
        k: Optional[int] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        return_metadata: bool = False,
<<<<<<< HEAD
=======
        include_scores: bool = False,
>>>>>>> bb677be (feat : update logging error)
    ) -> Union[
        List[Union[CompositeElement, Table, str, Document]],
        Tuple[
            List[Union[CompositeElement, Table, str, Document]],
            List[Document],
        ],
    ]:
        """
        Search for relevant documents based on query.

        Args:
            query: Search query string.
            k: Number of results to return (defaults to settings.rag_top_k).
            metadata_filter: Optional metadata filter for Pinecone search (e.g., ``{'sensitivity': 'public'}``).

        Returns:
            If ``return_metadata`` is False (default), returns list of retrieved
            documents (CompositeElement, Table, base64 image strings, or Document fallback).

            If ``return_metadata`` is True, returns a tuple of:
                - List of retrieved documents (original content when available).
                - List of summary ``Document`` objects containing metadata.
        """
        try:
            # Determine number of results
            effective_k = k or settings.rag_top_k

            # Retrieve summary documents (with metadata) from vector store
<<<<<<< HEAD
            summary_docs = self.vectorstore.similarity_search(
                query,
                k=effective_k,
                filter=metadata_filter,
            )
=======
            if include_scores:
                summary_with_scores = self.vectorstore.similarity_search_with_score(
                    query,
                    k=effective_k,
                    filter=metadata_filter,
                )
                summary_docs = [doc for doc, _ in summary_with_scores]
                scores = [score for _, score in summary_with_scores]
            else:
                summary_docs = self.vectorstore.similarity_search(
                    query,
                    k=effective_k,
                    filter=metadata_filter,
                )
                scores = None
>>>>>>> bb677be (feat : update logging error)

            # Collect document IDs to fetch originals from Redis
            doc_ids: List[Optional[str]] = []
            fetch_ids: List[str] = []
            for doc in summary_docs:
                doc_id = (doc.metadata or {}).get(self.id_key)
                doc_ids.append(doc_id)
                if doc_id:
                    fetch_ids.append(doc_id)

            # Fetch original documents from Redis docstore
            fetched_docs: Dict[str, Any] = {}
            if fetch_ids:
                docstore_results = self.docstore.mget(fetch_ids)
                fetched_docs = {
                    doc_id: value
                    for doc_id, value in zip(fetch_ids, docstore_results)
                    if value is not None
                }

            # Build final list of documents, falling back to summary doc if needed
            retrieved_docs: List[Union[CompositeElement, Table, str, Document]] = []
            for doc_id, summary_doc in zip(doc_ids, summary_docs):
                original_doc = fetched_docs.get(doc_id) if doc_id else None
                retrieved_docs.append(original_doc if original_doc is not None else summary_doc)

            logger.info(
                f"Retrieved {len(retrieved_docs)} documents for query: {query[:50]}... (filter: {metadata_filter})"
            )

<<<<<<< HEAD
=======
            if include_scores and scores is not None:
                # Attach scores to metadata for downstream usage
                for doc, score in zip(summary_docs, scores):
                    doc.metadata = doc.metadata or {}
                    doc.metadata["similarity_score"] = score

>>>>>>> bb677be (feat : update logging error)
            if return_metadata:
                return retrieved_docs, summary_docs
            return retrieved_docs

        except Exception as e:
            msg = f"Search failed: {str(e)}"
            logger.error(msg)
            raise VectorStoreError(msg)

    def delete_by_document_id(self, document_id: str) -> None:
        """
        Delete all vectors associated with a document ID.

        Note:
            This method is currently not fully implemented.
            Pinecone metadata-based deletion requires additional setup
            with filtering support. Consider implementing this feature
            based on your Pinecone plan and index configuration.

        Args:
            document_id: Document identifier to delete.

        Raises:
            VectorStoreError: If deletion operation fails.
        """
        try:
            # Metadata-based deletion requires Pinecone filter support
<<<<<<< HEAD
            logger.warning(
                f"Delete operation for document_id {document_id} not fully implemented. "
                f"Metadata-based deletion requires Pinecone filtering configuration."
            )
=======
            msg = (
                f"Delete operation for document_id {document_id} not fully implemented. "
                f"Metadata-based deletion requires Pinecone filtering configuration."
            )
            logger.warning(msg)
>>>>>>> bb677be (feat : update logging error)
        except Exception as e:
            msg = f"Failed to delete document: {str(e)}"
            logger.error(msg)
            raise VectorStoreError(msg)
