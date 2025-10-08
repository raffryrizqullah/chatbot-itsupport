"""
PDF processing service for extracting text, tables, and images.

This module handles the extraction and parsing of multi-modal content
from PDF documents using the unstructured library.
"""

from typing import List, Dict, Any, Tuple, Union, BinaryIO
from dataclasses import dataclass
from io import BytesIO
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import CompositeElement, Table, Image
from app.core.config import settings
from app.core.exceptions import PDFProcessingError
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContent:
    """Container for extracted PDF content."""

    texts: List[CompositeElement]
    tables: List[Table]
    images: List[str]  # Base64 encoded images


class PDFProcessor:
    """
    Service for processing PDF documents and extracting multi-modal content.

    Extracts text chunks, tables, and images from PDF files using the
    unstructured library with high-resolution strategy.
    """

    def __init__(self):
        """Initialize PDF processor with configuration from settings."""
        self.chunking_strategy = settings.pdf_chunking_strategy
        self.max_characters = settings.pdf_max_characters
        self.combine_text_under_n_chars = settings.pdf_combine_text_under_n_chars
        self.new_after_n_chars = settings.pdf_new_after_n_chars

    def process_pdf(self, file_path: str) -> ExtractedContent:
        """
        Extract text, tables, and images from a PDF file.

        Args:
            file_path: Path to the PDF file to process.

        Returns:
            ExtractedContent containing separated text chunks, tables, and images.

        Raises:
            PDFProcessingError: If PDF processing fails.
        """
        try:
            logger.info(f"Processing PDF: {file_path}")

            # Partition PDF into elements
            chunks = partition_pdf(
                filename=file_path,
                infer_table_structure=True,
                strategy="hi_res",
                extract_image_block_types=["Image"],
                extract_image_block_to_payload=True,
                chunking_strategy=self.chunking_strategy,
                max_characters=self.max_characters,
                combine_text_under_n_chars=self.combine_text_under_n_chars,
                new_after_n_chars=self.new_after_n_chars,
            )

            # Separate elements by type
            texts, tables = self._separate_text_and_tables(chunks)
            images = self._extract_images(chunks)

            logger.info(
                f"Extracted {len(texts)} text chunks, "
                f"{len(tables)} tables, {len(images)} images"
            )

            return ExtractedContent(texts=texts, tables=tables, images=images)

        except Exception as e:
            msg = f"Failed to process PDF: {str(e)}"
            logger.error(msg)
            raise PDFProcessingError(msg)

    def process_pdf_from_bytes(
        self, file_obj: Union[BytesIO, BinaryIO], filename: str = "document.pdf"
    ) -> ExtractedContent:
        """
        Extract text, tables, and images from a PDF file object (in-memory).

        Args:
            file_obj: File-like object containing PDF data.
            filename: Original filename for logging purposes.

        Returns:
            ExtractedContent containing separated text chunks, tables, and images.

        Raises:
            PDFProcessingError: If PDF processing fails.
        """
        try:
            logger.info(f"Processing PDF from memory: {filename}")

            # Partition PDF into elements from file object
            chunks = partition_pdf(
                file=file_obj,
                infer_table_structure=True,
                strategy="hi_res",
                extract_image_block_types=["Image"],
                extract_image_block_to_payload=True,
                chunking_strategy=self.chunking_strategy,
                max_characters=self.max_characters,
                combine_text_under_n_chars=self.combine_text_under_n_chars,
                new_after_n_chars=self.new_after_n_chars,
            )

            # Separate elements by type
            texts, tables = self._separate_text_and_tables(chunks)
            images = self._extract_images(chunks)

            logger.info(
                f"Extracted {len(texts)} text chunks, "
                f"{len(tables)} tables, {len(images)} images from {filename}"
            )

            return ExtractedContent(texts=texts, tables=tables, images=images)

        except Exception as e:
            msg = f"Failed to process PDF from memory: {str(e)}"
            logger.error(msg)
            raise PDFProcessingError(msg)

    def _separate_text_and_tables(
        self, chunks: List[Any]
    ) -> Tuple[List[CompositeElement], List[Table]]:
        """
        Separate text chunks and tables from extracted elements.

        Args:
            chunks: List of elements extracted from PDF.

        Returns:
            Tuple of (text_chunks, tables).
        """
        texts: List[CompositeElement] = []
        tables: List[Table] = []

        for chunk in chunks:
            chunk_type = str(type(chunk))
            if "Table" in chunk_type:
                tables.append(chunk)
            elif "CompositeElement" in chunk_type:
                texts.append(chunk)

        return texts, tables

    def _extract_images(self, chunks: List[Any]) -> List[str]:
        """
        Extract base64-encoded images from CompositeElement objects.

        Args:
            chunks: List of elements extracted from PDF.

        Returns:
            List of base64-encoded image strings.
        """
        images_b64 = []

        for chunk in chunks:
            if "CompositeElement" in str(type(chunk)):
                chunk_elements = chunk.metadata.orig_elements
                for element in chunk_elements:
                    if "Image" in str(type(element)):
                        image_b64 = element.metadata.image_base64
                        if image_b64:
                            images_b64.append(image_b64)

        return images_b64
