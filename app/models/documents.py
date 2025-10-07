"""
Document data models for internal use.

This module defines data structures for managing document metadata
and processing state.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DocumentRecord:
    """Internal record for tracking uploaded documents."""

    document_id: str
    filename: str
    upload_timestamp: datetime
    num_texts: int
    num_tables: int
    num_images: int
    total_chunks: int
    status: str = "completed"
    error_message: Optional[str] = None
