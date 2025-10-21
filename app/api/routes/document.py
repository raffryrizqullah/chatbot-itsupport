"""
Document upload and management endpoints.

Handles PDF document uploads, processing, and metadata retrieval.
"""

from typing import List, Union, Optional, Dict, Any
from functools import lru_cache
from io import BytesIO
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends, Request, Query
from app.models.schemas import UploadResponse, BatchUploadResponse, ErrorResponse, DocumentListResponse, DocumentListItem
from app.services.pdf_processor import PDFProcessor
from app.services.summarizer import SummarizerService
from app.services.vectorstore import VectorStoreService
from app.services.r2_storage import R2StorageService
from app.services.metadata_extractor import MetadataExtractorService
from app.utils.strings import to_document_name
from app.core.config import settings
from app.core.dependencies import require_role
from app.core.rate_limit import limiter, RATE_LIMITS
from app.core.exceptions import StorageError
from app.db.models import UserRole, User
import uuid
import json
import logging
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)


@lru_cache()
def get_pdf_processor() -> PDFProcessor:
    """Get or create PDF processor instance (cached)."""
    return PDFProcessor()


@lru_cache()
def get_summarizer() -> SummarizerService:
    """Get or create summarizer service instance (cached)."""
    return SummarizerService()


@lru_cache()
def get_vectorstore() -> VectorStoreService:
    """Get or create vectorstore service instance (cached)."""
    return VectorStoreService()


@lru_cache()
def get_r2_storage() -> R2StorageService:
    """Get or create R2 storage service instance (cached)."""
    return R2StorageService()


@lru_cache()
def get_metadata_extractor() -> MetadataExtractorService:
    """Get or create metadata extractor service instance (cached)."""
    return MetadataExtractorService()


def _validate_upload_request(
    files: List[UploadFile],
    source_links: Optional[List[str]],
    custom_metadata: Optional[str],
) -> Optional[Dict[str, Any]]:
    """
    Validate upload request parameters.

    Args:
        files: List of uploaded files.
        source_links: Optional list of source links.
        custom_metadata: Optional JSON string with custom metadata.

    Returns:
        Parsed custom metadata dictionary, or None if not provided.

    Raises:
        HTTPException: If validation fails.
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

    return metadata_dict


async def _process_single_file(
    file: UploadFile,
    source_link: Optional[str],
    metadata_dict: Optional[Dict[str, Any]],
    pdf_processor: PDFProcessor,
    summarizer: SummarizerService,
    vectorstore: VectorStoreService,
    r2_storage: R2StorageService,
    auto_extract: bool = False,
    metadata_extractor: Optional[MetadataExtractorService] = None,
) -> UploadResponse:
    """
    Process a single uploaded PDF file.

    Args:
        file: Uploaded PDF file.
        source_link: Optional source link for this file.
        metadata_dict: Optional custom metadata.
        pdf_processor: PDF processor service instance.
        summarizer: Summarizer service instance.
        vectorstore: Vector store service instance.
        r2_storage: R2 storage service instance.

    Returns:
        UploadResponse with processing results.

    Raises:
        HTTPException: If file validation or processing fails.
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File {file.filename}: Only PDF files are supported",
        )

    # Generate unique document ID
    document_id = str(uuid.uuid4())

    # Read file content into memory
    content = await file.read()

    # Check file size
    if len(content) > settings.pdf_max_file_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File {file.filename}: File size exceeds maximum allowed size of {settings.pdf_max_file_size} bytes",
        )

    # Upload to R2 storage
    try:
        storage_key = f"pdfs/{document_id}.pdf"
        file_obj = BytesIO(content)
        r2_storage.upload_file(file_obj, storage_key, content_type="application/pdf")
        logger.info(f"Uploaded file to R2: {storage_key}")
    except StorageError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to storage: {str(e)}",
        )

    # Process PDF from memory
    file_obj = BytesIO(content)
    extracted_content = pdf_processor.process_pdf_from_bytes(file_obj, file.filename)

    # Generate summaries
    text_summaries = summarizer.summarize_texts(extracted_content.texts)
    table_summaries = summarizer.summarize_tables(extracted_content.tables)
    image_summaries = summarizer.summarize_images(extracted_content.images)

    # Auto-extract metadata if requested and no manual metadata provided
    if auto_extract and metadata_extractor:
        # Check if enrichment fields are already provided
        has_manual_enrichment = any(
            key in (metadata_dict or {})
            for key in ["category", "keywords", "faq_questions", "platform"]
        )

        if not has_manual_enrichment:
            logger.info("Auto-extracting metadata using LLM...")
            # Combine first 5 text chunks for extraction
            combined_text = "\n\n".join(
                [chunk.text for chunk in extracted_content.texts[:5] if hasattr(chunk, "text")]
            )

            if combined_text:
                try:
                    auto_metadata = await metadata_extractor.extract_metadata(combined_text)
                    if auto_metadata:
                        logger.info(f"Auto-extracted metadata: {auto_metadata}")
                        # Merge auto-extracted with existing metadata
                        if metadata_dict is None:
                            metadata_dict = {}
                        # Only add auto-extracted fields that don't exist
                        for key, value in auto_metadata.items():
                            if key not in metadata_dict and value:
                                metadata_dict[key] = value
                except Exception as e:
                    logger.error(f"Auto-extraction failed: {str(e)}")
                    # Continue without auto-extracted metadata
        else:
            logger.info("Manual enrichment metadata provided, skipping auto-extraction")

    # Add to vector store with source_link and custom_metadata
    # Ensure document_name stored in metadata for listing (auto-generated per file)
    enriched_metadata = dict(metadata_dict or {})
    auto_name = to_document_name(file.filename)
    # Respect user-provided document_name in custom_metadata; otherwise use auto_name
    enriched_metadata.setdefault("document_name", auto_name)

    counts = vectorstore.add_documents(
        text_chunks=extracted_content.texts,
        text_summaries=text_summaries,
        tables=extracted_content.tables,
        table_summaries=table_summaries,
        images=extracted_content.images,
        image_summaries=image_summaries,
        document_id=document_id,
        source_link=source_link,
        custom_metadata=enriched_metadata,
    )

    logger.info(f"Document {document_id} processed successfully")

    # Create success response
    return UploadResponse(
        document_id=document_id,
        filename=file.filename,
        source_link=source_link,
        custom_metadata=enriched_metadata,
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


@router.post(
    "/documents/upload",
    response_model=Union[UploadResponse, BatchUploadResponse],
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
    dependencies=[Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@limiter.limit(RATE_LIMITS["upload"])
async def upload_document(
    request: Request,
    files: List[UploadFile] = File(...),
    source_links: Optional[List[str]] = Form(None),
    custom_metadata: Optional[str] = Form(None),
    # Enrichment metadata fields (optional)
    category: Optional[str] = Form(None),
    subcategory: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None),
    faq_questions: Optional[str] = Form(None),
    platform: Optional[str] = Form(None),
    problem_type: Optional[str] = Form(None),
    difficulty_level: Optional[str] = Form(None),
    auto_extract_metadata: bool = Form(False),
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
) -> Union[UploadResponse, BatchUploadResponse]:
    """
    Upload and process one or more PDF documents (Admin only).

    Extracts text, tables, and images from PDFs, generates summaries,
    and stores them in the vector database for retrieval.

    **Metadata Enrichment (Optional)**:
    - category: Document category (vpn, network, email, hardware, software, other)
    - subcategory: Subcategory (installation, troubleshooting, configuration, how-to)
    - keywords: 3-5 keywords (JSON array or comma-separated)
    - faq_questions: Common questions this doc answers (JSON array or newline-separated)
    - platform: Target platform (windows, mac, linux, android, ios, all)
    - problem_type: Content type (installation, error, configuration, guide, reference)
    - difficulty_level: Difficulty level (beginner, intermediate, advanced)
    - auto_extract_metadata: Use LLM to auto-extract metadata (default: False, costs ~$0.008/doc)

    Requires admin authentication via Bearer token.

    Args:
        files: One or more PDF files to upload and process.
        source_links: Optional source links for each file (must match number of files).
        custom_metadata: Optional custom metadata as JSON string (applies to all files).
        category: Document category for filtering.
        subcategory: Document subcategory.
        keywords: Keywords for search boost (JSON array or comma-separated).
        faq_questions: FAQ questions this document answers (JSON array or newline-separated).
        platform: Target platform.
        problem_type: Type of content.
        difficulty_level: Difficulty level.
        auto_extract_metadata: Enable LLM-based metadata extraction.
        current_user: Current authenticated admin user.

    Returns:
        UploadResponse for single file or BatchUploadResponse for multiple files.

    Raises:
        HTTPException: If file validation or processing fails.
    """
    # Validate request parameters
    metadata_dict = _validate_upload_request(files, source_links, custom_metadata)

    # Parse enrichment metadata
    enrichment_metadata = {}

    if category:
        enrichment_metadata["category"] = category
    if subcategory:
        enrichment_metadata["subcategory"] = subcategory
    if platform:
        enrichment_metadata["platform"] = platform
    if problem_type:
        enrichment_metadata["problem_type"] = problem_type
    if difficulty_level:
        enrichment_metadata["difficulty_level"] = difficulty_level

    # Parse keywords (accept JSON array or comma-separated)
    if keywords:
        try:
            enrichment_metadata["keywords"] = json.loads(keywords)
        except json.JSONDecodeError:
            # Fallback: comma-separated string
            enrichment_metadata["keywords"] = [k.strip() for k in keywords.split(",") if k.strip()]

    # Parse FAQ questions (accept JSON array or newline-separated)
    if faq_questions:
        try:
            enrichment_metadata["faq_questions"] = json.loads(faq_questions)
        except json.JSONDecodeError:
            # Fallback: newline-separated string
            enrichment_metadata["faq_questions"] = [
                q.strip() for q in faq_questions.split("\n") if q.strip()
            ]

    # Merge enrichment metadata with custom_metadata
    if metadata_dict is None:
        metadata_dict = {}
    metadata_dict.update(enrichment_metadata)

    if enrichment_metadata:
        logger.info(f"Document enrichment metadata: {enrichment_metadata}")

    # Get service instances
    pdf_processor = get_pdf_processor()
    summarizer = get_summarizer()
    vectorstore = get_vectorstore()
    r2_storage = get_r2_storage()
    metadata_extractor = get_metadata_extractor() if auto_extract_metadata else None

    results = []
    successful = 0
    failed = 0

    # Process each file
    for idx, file in enumerate(files):
        source_link = source_links[idx] if source_links else None

        try:
            result = await _process_single_file(
                file=file,
                source_link=source_link,
                metadata_dict=metadata_dict,
                pdf_processor=pdf_processor,
                summarizer=summarizer,
                vectorstore=vectorstore,
                r2_storage=r2_storage,
                auto_extract=auto_extract_metadata,
                metadata_extractor=metadata_extractor,
            )
            results.append(result)
            successful += 1

        except HTTPException as e:
            # Create error response for this file
            msg = f"Failed to process {file.filename}: {e.detail}"
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
            logger.error(msg)

        except Exception as e:
            # Create error response for this file
            msg = f"Failed to process {file.filename}: {str(e)}"
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
            logger.error(msg)

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


@router.get(
    "/documents/list",
    response_model=DocumentListResponse,
    tags=["documents"],
    dependencies=[Depends(require_role(UserRole.SUPER_ADMIN, UserRole.ADMIN))],
    responses={
        400: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def list_documents(
    request: Request,
    filter: Optional[str] = Query(
        default=None,
        description="URL-encoded JSON metadata filter using Pinecone operators (e.g., {\"content_type\": {\"$eq\": \"text\"}})",
    ),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of vectors to scan (approximate listing)"),
    namespace: Optional[str] = Query(None, description="Pinecone namespace (default namespace if omitted)"),
) -> DocumentListResponse:
    """
    List indexed documents from Pinecone, aggregated by `document_id`.

    Notes:
    - This performs a filtered query to fetch up to `limit` vectors (not a full table scan) and groups them by `document_id`.
    - Use the `filter` parameter to narrow by metadata (supports $eq, $in, $exists, etc.).
    - Returns unique document count and per-document chunk counts by content type.
    """
    try:
        metadata_filter: Optional[Dict[str, Any]] = None
        if filter:
            try:
                metadata_filter = json.loads(filter)
                if not isinstance(metadata_filter, dict):
                    raise ValueError("filter must be a JSON object")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid filter JSON: {e}")

        # Initialize Pinecone index client
        from pinecone import Pinecone  # type: ignore

        pc = Pinecone(api_key=settings.pinecone_api_key)
        try:
            index = pc.Index(name=settings.pinecone_index_name)
        except Exception:
            # Fallback for SDK variants that require host
            indexes = pc.list_indexes()
            host = None
            for idx in indexes:
                try:
                    if getattr(idx, "name", None) == settings.pinecone_index_name:
                        host = getattr(idx, "host", None)
                        break
                except Exception:
                    # indexes might be dict-like
                    if idx.get("name") == settings.pinecone_index_name:
                        host = idx.get("host")
                        break
            if not host:
                raise HTTPException(status_code=500, detail=f"Pinecone index not found: {settings.pinecone_index_name}")
            index = pc.Index(host=host)

        # Query using a zero vector to retrieve any matches filtered by metadata
        # This is an approximate listing constrained by `limit`.
        query_params: Dict[str, Any] = {
            "vector": [0.0] * settings.pinecone_dimension,
            "top_k": limit,
            "include_metadata": True,
        }
        if metadata_filter:
            query_params["filter"] = metadata_filter
        if namespace:
            query_params["namespace"] = namespace

        result = index.query(**query_params)

        matches = getattr(result, "matches", None) or result.get("matches", [])  # type: ignore[attr-defined]

        # Aggregate by document_id
        by_doc: Dict[str, Dict[str, Any]] = {}
        total_vectors = 0
        for m in matches:
            md = getattr(m, "metadata", None) or m.get("metadata", {})  # type: ignore[attr-defined]
            doc_id = (md or {}).get("document_id")
            ctype = (md or {}).get("content_type", "unknown")
            if not doc_id:
                # Skip vectors without document_id (shouldn't happen in this app)
                continue
            total_vectors += 1
            if doc_id not in by_doc:
                by_doc[doc_id] = {
                    "total_chunks": 0,
                    "counts": {},
                    "source_links": set(),
                    "document_name": None,
                    "author": None,
                    "client_upload_timestamp": None,
                    "sensitivity": None,
                }
            agg = by_doc[doc_id]
            agg["total_chunks"] += 1
            agg["counts"][ctype] = agg["counts"].get(ctype, 0) + 1
            src = (md or {}).get("source_link")
            if src:
                agg["source_links"].add(src)
            # Prefer explicit document_name, fallback to filename if present
            name = (md or {}).get("document_name") or (md or {}).get("filename")
            if name and not agg["document_name"]:
                agg["document_name"] = str(name)
            # Optional metadata fields: author, client_upload_timestamp, sensitivity
            author = (md or {}).get("author")
            if author and not agg["author"]:
                agg["author"] = str(author)
            client_ts = (md or {}).get("client_upload_timestamp")
            if client_ts and not agg["client_upload_timestamp"]:
                agg["client_upload_timestamp"] = str(client_ts)
            sensitivity = (md or {}).get("sensitivity") or (md or {}).get("Sensitivitas")
            if sensitivity and not agg["sensitivity"]:
                agg["sensitivity"] = str(sensitivity)

        # Build response items
        items: List[DocumentListItem] = []
        for doc_id, agg in by_doc.items():
            links = list(agg["source_links"]) if agg["source_links"] else None
            items.append(
                DocumentListItem(
                    document_id=doc_id,
                    document_name=agg.get("document_name"),
                    author=agg.get("author"),
                    client_upload_timestamp=agg.get("client_upload_timestamp"),
                    sensitivity=agg.get("sensitivity"),
                    total_chunks=agg["total_chunks"],
                    counts=agg["counts"],
                    source_links=links,
                )
            )

        return DocumentListResponse(
            total_documents=len(items),
            total_vectors=total_vectors,
            documents=sorted(items, key=lambda x: x.document_id),
        )

    except HTTPException:
        raise
    except Exception as e:
        msg = f"Failed to list documents: {e}"
        logger.error(msg)
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {e}")
