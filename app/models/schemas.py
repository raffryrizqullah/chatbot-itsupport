"""
Pydantic schemas for API request and response models.

This module defines all data models used in API endpoints for validation
and serialization.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class WelcomeResponse(BaseModel):
    """Welcome message response schema for root endpoint."""

    message: str = Field(..., description="Welcome message")
    version: str = Field(..., description="API version")
    status: str = Field(..., description="Service status")
    docs_url: str = Field(..., description="API documentation URL")


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")
    version: str = Field(..., description="API version")


<<<<<<< HEAD
=======
class ServiceHealthResponse(BaseModel):
    """Health response schema for external services (e.g., OpenAI, Pinecone)."""

    provider: str = Field(..., description="Service provider name")
    status: str = Field(..., description="Health status (healthy/unhealthy/configuration_error)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")
    version: str = Field(..., description="API version")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional diagnostic details")


class HealthSummaryResponse(BaseModel):
    """Aggregated health summary across services."""

    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")
    version: str = Field(..., description="API version")
    services: Dict[str, ServiceHealthResponse] = Field(..., description="Per-service health details")


class DocumentListItem(BaseModel):
    """Aggregated info for a single document_id in Pinecone."""

    document_id: str = Field(..., description="Document identifier")
    document_name: Optional[str] = Field(default=None, description="Human-readable document name (e.g., original filename)")
    author: Optional[str] = Field(default=None, description="Author metadata if provided at upload")
    client_upload_timestamp: Optional[str] = Field(default=None, description="Client-side upload timestamp if provided")
    sensitivity: Optional[str] = Field(default=None, description="Sensitivity level metadata if provided (e.g., public/internal)")
    total_chunks: int = Field(..., description="Total vectors/chunks for this document")
    counts: Dict[str, int] = Field(..., description="Counts by content_type (text/table/image)")
    source_links: Optional[List[str]] = Field(default=None, description="Unique source links associated with the document")


class DocumentListResponse(BaseModel):
    """Listing response for documents stored in Pinecone."""

    total_documents: int = Field(..., description="Unique document_id count")
    total_vectors: int = Field(..., description="Total vectors matched by filter and limit")
    documents: List[DocumentListItem] = Field(..., description="Per-document aggregated details")


>>>>>>> bb677be (feat : update logging error)
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
    session_id: Optional[str] = Field(
        default=None, description="Session ID for conversation history (auto-generated if not provided)"
    )
    include_sources: bool = Field(
        default=False, description="Whether to include source documents in response"
    )
    top_k: Optional[int] = Field(
        default=None, ge=1, le=20, description="Number of documents to retrieve (1-20)"
    )


class QueryResponse(BaseModel):
    """Response schema for query endpoint."""

    answer: str = Field(..., description="Generated answer to the question")
    session_id: str = Field(..., description="Session ID for this conversation")
    metadata: Dict[str, Any] = Field(..., description="Response metadata")


class QueryWithSourcesResponse(BaseModel):
    """Response schema for query endpoint with sources included."""

    answer: str = Field(..., description="Generated answer to the question")
    session_id: str = Field(..., description="Session ID for this conversation")
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


# Authentication Schemas

class LoginRequest(BaseModel):
    """Request schema for user login."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=6, description="Password")


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    full_name: str = Field(..., min_length=1, max_length=255, description="Full name")
    role: Optional[str] = Field(default="student", description="User role (admin, lecturer, student)")


class TokenResponse(BaseModel):
    """Response schema for authentication token."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: Dict[str, Any] = Field(..., description="User information")


class UserResponse(BaseModel):
    """Response schema for user information."""

    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    full_name: str = Field(..., description="Full name")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: datetime = Field(..., description="Account creation timestamp")


# API Key Schemas

class APIKeyCreate(BaseModel):
    """Request schema for creating an API key."""

    user_id: str = Field(..., description="UUID of user who will own this API key")
    name: str = Field(..., min_length=1, max_length=255, description="Descriptive name for the API key")


class APIKeyResponse(BaseModel):
    """Response schema for API key information."""

    id: str = Field(..., description="API key ID")
    key_prefix: str = Field(..., description="Key prefix for display (e.g., 'sk-proj-abc...')")
    name: str = Field(..., description="API key name")
    user_id: str = Field(..., description="Owner user ID")
    username: str = Field(..., description="Owner username")
    is_active: bool = Field(..., description="Whether API key is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_used_at: Optional[datetime] = Field(default=None, description="Last usage timestamp")


class APIKeyCreateResponse(APIKeyResponse):
    """Response schema for API key creation (includes full key)."""

    api_key: str = Field(..., description="Full API key (only shown once!)")


class APIKeyListResponse(BaseModel):
    """Response schema for listing API keys."""

    total: int = Field(..., description="Total number of API keys")
    api_keys: List[APIKeyResponse] = Field(..., description="List of API keys")
<<<<<<< HEAD
=======


class UserListResponse(BaseModel):
    """Response schema for listing users (admin)."""

    total: int = Field(..., description="Total matched users")
    users: List[UserResponse] = Field(..., description="Users page items")
>>>>>>> bb677be (feat : update logging error)
