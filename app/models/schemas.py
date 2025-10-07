"""
Pydantic schemas for API request and response models.

This module defines all data models used in API endpoints for validation
and serialization.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")
    version: str = Field(..., description="API version")


class UploadResponse(BaseModel):
    """Response schema for document upload endpoint."""

    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    filename: str = Field(..., description="Name of the uploaded file")
    source_link: Optional[str] = Field(default=None, description="Source link provided by user")
    custom_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Custom metadata provided by user")
    status: str = Field(..., description="Processing status")
    metadata: Dict[str, Any] = Field(..., description="Document metadata and statistics")
    message: str = Field(..., description="Status message")


class BatchUploadResponse(BaseModel):
    """Response schema for batch document upload."""

    total_uploaded: int = Field(..., description="Total number of documents uploaded")
    successful: int = Field(..., description="Number of successfully processed documents")
    failed: int = Field(..., description="Number of failed documents")
    results: List[UploadResponse] = Field(..., description="Individual upload results")
    message: str = Field(..., description="Overall status message")


class QueryRequest(BaseModel):
    """Request schema for query endpoint."""

    question: str = Field(..., min_length=1, description="Question to ask about documents")
    include_sources: bool = Field(
        default=False, description="Whether to include source documents in response"
    )
    top_k: Optional[int] = Field(
        default=None, ge=1, le=20, description="Number of documents to retrieve (1-20)"
    )


class QueryResponse(BaseModel):
    """Response schema for query endpoint."""

    answer: str = Field(..., description="Generated answer to the question")
    metadata: Dict[str, Any] = Field(..., description="Response metadata")


class QueryWithSourcesResponse(BaseModel):
    """Response schema for query endpoint with sources included."""

    answer: str = Field(..., description="Generated answer to the question")
    sources: Dict[str, Any] = Field(..., description="Source documents used for answer")
    metadata: Dict[str, Any] = Field(..., description="Response metadata")


class DocumentMetadata(BaseModel):
    """Schema for document metadata."""

    document_id: str = Field(..., description="Document unique identifier")
    filename: str = Field(..., description="Original filename")
    upload_timestamp: datetime = Field(..., description="Upload time")
    num_texts: int = Field(..., description="Number of text chunks")
    num_tables: int = Field(..., description="Number of tables")
    num_images: int = Field(..., description="Number of images")
    total_chunks: int = Field(..., description="Total number of chunks indexed")


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
