"""
Custom exception classes for better error handling.

This module defines specific exception types for different components
of the application, allowing for more precise error handling and debugging.
"""


class RedisStoreError(Exception):
    """Exception raised for Redis docstore errors."""

    pass


class PDFProcessingError(Exception):
    """Exception raised for PDF processing errors."""

    pass


class SummarizerError(Exception):
    """Exception raised for summarization errors."""

    pass


class RAGChainError(Exception):
    """Exception raised for RAG chain errors."""

    pass


class VectorStoreError(Exception):
    """Exception raised for vector store errors."""

    pass


class ChatMemoryError(Exception):
    """Exception raised for chat memory errors."""

    pass


class AuthenticationError(Exception):
    """Exception raised for authentication errors."""

    pass


class APIKeyError(Exception):
    """Exception raised for API key operations errors."""

    pass


class StorageError(Exception):
    """Exception raised for storage operations errors."""

    pass
