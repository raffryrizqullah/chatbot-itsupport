"""
Document upload and management endpoints.

Handles PDF document uploads, processing, and metadata retrieval.
"""

from typing import List, Union, Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from app.models.schemas import UploadResponse, BatchUploadResponse, ErrorResponse
from app.services.pdf_processor import PDFProcessor
from app.services.summarizer import SummarizerService
from app.services.vectorstore import VectorStoreService
from app.core.config import settings
import uuid
import os
import json
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

# Lazy initialization to avoid startup errors
_pdf_processor = None
_summarizer = None
_vectorstore = None


def get_pdf_processor() -> PDFProcessor:
    """Get or create PDF processor instance."""
    global _pdf_processor
    if _pdf_processor is None:
        _pdf_processor = PDFProcessor()
    return _pdf_processor


def get_summarizer() -> SummarizerService:
    """Get or create summarizer service instance."""
    global _summarizer
    if _summarizer is None:
        _summarizer = SummarizerService()
    return _summarizer


def get_vectorstore() -> VectorStoreService:
    """Get or create vectorstore service instance."""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = VectorStoreService()
    return _vectorstore


@router.post(
    "/documents/upload",
    response_model=Union[UploadResponse, BatchUploadResponse],
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def upload_document(
    files: List[UploadFile] = File(...),
    source_links: Optional[List[str]] = Form(None),
    custom_metadata: Optional[str] = Form(None)
) -> Union[UploadResponse, BatchUploadResponse]:
    """
    Upload and process one or more PDF documents.

    Extracts text, tables, and images from PDFs, generates summaries,
    and stores them in the vector database for retrieval.

    Args:
        files: One or more PDF files to upload and process.
        source_links: Optional source links for each file (must match number of files).
        custom_metadata: Optional custom metadata as JSON string (applies to all files).

    Returns:
        UploadResponse for single file or BatchUploadResponse for multiple files.

    Raises:
        HTTPException: If file validation or processing fails.
    """
    # Validate source_links count matches files count
    if source_links is not None and len(source_links) != len(files):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Number of source_links ({len(source_links)}) must match number of files ({len(files)})",
        )

    # Parse and validate custom_metadata
    metadata_dict: Optional[Dict[str, Any]] = None
    if custom_metadata:
        try:
            metadata_dict = json.loads(custom_metadata)
            if not isinstance(metadata_dict, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="custom_metadata must be a JSON object",
                )

            # Validate reserved keys
            reserved_keys = {"doc_id", "document_id", "content_type", "source_link"}
            forbidden_keys = reserved_keys.intersection(metadata_dict.keys())
            if forbidden_keys:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot use reserved keys in custom_metadata: {forbidden_keys}",
                )
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON in custom_metadata: {str(e)}",
            )

    # Get service instances
    pdf_processor = get_pdf_processor()
    summarizer = get_summarizer()
    vectorstore = get_vectorstore()

    results = []
    successful = 0
    failed = 0

    # Process each file
    for idx, file in enumerate(files):
        source_link = source_links[idx] if source_links else None

        try:
            # Validate file type
            if not file.filename.endswith(".pdf"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File {file.filename}: Only PDF files are supported",
                )

            # Generate unique document ID
            document_id = str(uuid.uuid4())

            # Save uploaded file
            file_path = os.path.join(settings.pdf_upload_dir, f"{document_id}.pdf")
            os.makedirs(settings.pdf_upload_dir, exist_ok=True)

            with open(file_path, "wb") as f:
                content = await file.read()

                # Check file size
                if len(content) > settings.pdf_max_file_size:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File {file.filename}: File size exceeds maximum allowed size of {settings.pdf_max_file_size} bytes",
                    )

                f.write(content)

            logger.info(f"Saved uploaded file: {file_path}")

            # Process PDF
            extracted_content = pdf_processor.process_pdf(file_path)

            # Generate summaries
            text_summaries = summarizer.summarize_texts(extracted_content.texts)
            table_summaries = summarizer.summarize_tables(extracted_content.tables)
            image_summaries = summarizer.summarize_images(extracted_content.images)

            # Add to vector store with source_link and custom_metadata
            counts = vectorstore.add_documents(
                text_chunks=extracted_content.texts,
                text_summaries=text_summaries,
                tables=extracted_content.tables,
                table_summaries=table_summaries,
                images=extracted_content.images,
                image_summaries=image_summaries,
                document_id=document_id,
                source_link=source_link,
                custom_metadata=metadata_dict,
            )

            logger.info(f"Document {document_id} processed successfully")

            # Create success response
            result = UploadResponse(
                document_id=document_id,
                filename=file.filename,
                source_link=source_link,
                custom_metadata=metadata_dict,
                status="completed",
                metadata={
                    "num_texts": counts["texts"],
                    "num_tables": counts["tables"],
                    "num_images": counts["images"],
                    "total_chunks": counts["total"],
                    "upload_timestamp": datetime.utcnow().isoformat(),
                },
                message="Document processed and indexed successfully",
            )
            results.append(result)
            successful += 1

        except HTTPException as e:
            # Create error response for this file
            result = UploadResponse(
                document_id="",
                filename=file.filename,
                source_link=source_link,
                custom_metadata=metadata_dict,
                status="failed",
                metadata={"error": e.detail},
                message=f"Failed to process: {e.detail}",
            )
            results.append(result)
            failed += 1
            logger.error(f"Failed to process {file.filename}: {e.detail}")

        except Exception as e:
            # Create error response for this file
            msg = f"Failed to process document: {str(e)}"
            result = UploadResponse(
                document_id="",
                filename=file.filename,
                source_link=source_link,
                custom_metadata=metadata_dict,
                status="failed",
                metadata={"error": msg},
                message=msg,
            )
            results.append(result)
            failed += 1
            logger.error(f"Failed to process {file.filename}: {msg}")

    # Return single result or batch result
    if len(files) == 1:
        # Return single UploadResponse for backward compatibility
        return results[0]
    else:
        # Return BatchUploadResponse for multiple files
        return BatchUploadResponse(
            total_uploaded=len(files),
            successful=successful,
            failed=failed,
            results=results,
            message=f"Processed {successful} of {len(files)} documents successfully",
        )
