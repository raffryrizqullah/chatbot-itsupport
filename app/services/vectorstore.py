"""
Pinecone vector store service for document storage and retrieval.

This module manages the Pinecone vector database, handling document
embeddings, storage, and similarity search operations.
"""

from typing import List, Dict, Any, Optional, Union
import uuid
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.schema.document import Document
from langchain.retrievers.multi_vector import MultiVectorRetriever
from unstructured.documents.elements import CompositeElement, Table
from app.core.config import settings
from app.services.redis_store import RedisDocStore
import logging

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Service for managing Pinecone vector store operations.

    Implements multi-vector retrieval pattern where summaries are stored
    in Pinecone for search, while original content is stored in Redis docstore.
    """

    def __init__(self):
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

        Returns:
            Dictionary with counts of added items.
        """
        try:
            logger.info(f"Adding documents for document_id: {document_id}")

            # Add text chunks
            text_ids = self._add_content_type(
                text_chunks, text_summaries, document_id, "text"
            )

            # Add tables
            table_ids = self._add_content_type(
                tables, table_summaries, document_id, "table"
            )

            # Add images
            image_ids = self._add_content_type(
                images, image_summaries, document_id, "image"
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
            raise Exception(msg)

    def _add_content_type(
        self,
        content_items: List[Union[CompositeElement, Table, str]],
        summaries: List[str],
        document_id: str,
        content_type: str,
    ) -> List[str]:
        """
        Add a specific content type to the vector store.

        Args:
            content_items: Original content items (CompositeElement, Table, or base64 strings).
            summaries: Summaries of content items.
            document_id: Source document identifier.
            content_type: Type of content (``'text'``, ``'table'``, ``'image'``).

        Returns:
            List of generated content IDs.
        """
        if not content_items:
            return []

        # Generate unique IDs for each content item
        content_ids = [str(uuid.uuid4()) for _ in content_items]

        # Create summary documents with metadata
        summary_docs = [
            Document(
                page_content=summary,
                metadata={
                    self.id_key: content_ids[i],
                    "document_id": document_id,
                    "content_type": content_type,
                },
            )
            for i, summary in enumerate(summaries)
        ]

        # Add summaries to vector store
        self.vectorstore.add_documents(summary_docs)

        # Store original content in docstore
        self.docstore.mset(list(zip(content_ids, content_items)))

        logger.info(f"Added {len(content_ids)} {content_type} items")
        return content_ids

    def search(self, query: str, k: Optional[int] = None) -> List[Union[CompositeElement, Table, str]]:
        """
        Search for relevant documents based on query.

        Args:
            query: Search query string.
            k: Number of results to return (defaults to settings.rag_top_k).

        Returns:
            List of retrieved documents (CompositeElement, Table, or base64 image strings).
        """
        try:
            if k is not None:
                self.retriever.search_kwargs = {"k": k}

            results = self.retriever.invoke(query)
            logger.info(f"Retrieved {len(results)} documents for query: {query[:50]}...")
            return results

        except Exception as e:
            msg = f"Search failed: {str(e)}"
            logger.error(msg)
            raise Exception(msg)

    def delete_by_document_id(self, document_id: str) -> None:
        """
        Delete all vectors associated with a document ID.

        Args:
            document_id: Document identifier to delete.
        """
        try:
            # Note: Pinecone deletion by metadata requires filter support
            # This is a simplified implementation
            logger.warning(
                f"Delete operation for document_id {document_id} not fully implemented"
            )
            # TODO: Implement metadata-based deletion when available
        except Exception as e:
            msg = f"Failed to delete document: {str(e)}"
            logger.error(msg)
            raise Exception(msg)
