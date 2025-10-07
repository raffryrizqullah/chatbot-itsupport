"""
Document upload and management endpoints.

Handles PDF document uploads, processing, and metadata retrieval.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.models.schemas import UploadResponse, ErrorResponse
from app.services.pdf_processor import PDFProcessor
from app.services.summarizer import SummarizerService
from app.services.vectorstore import VectorStoreService
from app.core.config import settings
import uuid
import os
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
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload and process a PDF document.

    Extracts text, tables, and images from the PDF, generates summaries,
    and stores them in the vector database for retrieval.

    Args:
        file: PDF file to upload and process.

    Returns:
        UploadResponse with document ID and processing metadata.

    Raises:
        HTTPException: If file validation or processing fails.
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    # Generate unique document ID
    document_id = str(uuid.uuid4())

    try:
        # Save uploaded file
        file_path = os.path.join(settings.pdf_upload_dir, f"{document_id}.pdf")
        os.makedirs(settings.pdf_upload_dir, exist_ok=True)

        with open(file_path, "wb") as f:
            content = await file.read()

            # Check file size
            if len(content) > settings.pdf_max_file_size:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File size exceeds maximum allowed size of {settings.pdf_max_file_size} bytes",
                )

            f.write(content)

        logger.info(f"Saved uploaded file: {file_path}")

        # Get service instances
        pdf_processor = get_pdf_processor()
        summarizer = get_summarizer()
        vectorstore = get_vectorstore()

        # Process PDF
        extracted_content = pdf_processor.process_pdf(file_path)

        # Generate summaries
        text_summaries = summarizer.summarize_texts(extracted_content.texts)
        table_summaries = summarizer.summarize_tables(extracted_content.tables)
        image_summaries = summarizer.summarize_images(extracted_content.images)

        # Add to vector store
        counts = vectorstore.add_documents(
            text_chunks=extracted_content.texts,
            text_summaries=text_summaries,
            tables=extracted_content.tables,
            table_summaries=table_summaries,
            images=extracted_content.images,
            image_summaries=image_summaries,
            document_id=document_id,
        )

        logger.info(f"Document {document_id} processed successfully")

        return UploadResponse(
            document_id=document_id,
            filename=file.filename,
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

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        msg = f"Failed to process document: {str(e)}"
        logger.error(msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=msg,
        )
