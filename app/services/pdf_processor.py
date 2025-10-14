"""
PDF processing service for extracting text, tables, and images.

This module handles the extraction and parsing of multi-modal content
from PDF documents using the unstructured library.
"""

from typing import List, Dict, Any, Tuple, Union, BinaryIO, Optional
from dataclasses import dataclass
from io import BytesIO
from base64 import b64decode, b64encode
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import CompositeElement, Table, Image
from app.core.config import settings
from app.core.exceptions import PDFProcessingError
import logging

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

logger = logging.getLogger(__name__)

# Supported image formats by OpenAI Vision API
SUPPORTED_IMAGE_FORMATS = {"png", "jpeg", "jpg", "gif", "webp"}


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

    def __init__(self) -> None:
        """Initialize PDF processor with configuration from settings."""
        self.chunking_strategy = settings.pdf_chunking_strategy
        self.max_characters = settings.pdf_max_characters
        self.combine_text_under_n_chars = settings.pdf_combine_text_under_n_chars
        self.new_after_n_chars = settings.pdf_new_after_n_chars
        # OCR languages for Tesseract (e.g., "eng", "ind", "eng+ind"). Must be a list for unstructured
        # Accept comma or plus separated values in .env and normalize to List[str]
        try:
            import re

            langs_str = (settings.ocr_languages or "eng").strip()
            # Split on '+' or ',' or whitespace and filter empties
            self.ocr_languages = [s for s in re.split(r"[+,\s]+", langs_str) if s]
        except Exception:
            # Fallback to English if parsing fails
            self.ocr_languages = ["eng"]

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
                languages=self.ocr_languages,
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
                languages=self.ocr_languages,
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

    @staticmethod
    def _detect_image_format(image_b64: str) -> Optional[str]:
        """
        Detect image format from base64 string.

        Args:
            image_b64: Base64-encoded image string.

        Returns:
            Image format (e.g., ``'png'``, ``'jpeg'``, ``'gif'``, ``'webp'``) or None if detection fails.
        """
        if not PILImage:
            logger.warning("PIL not available, cannot detect image format")
            return None

        try:
            image_data = b64decode(image_b64)
            img = PILImage.open(BytesIO(image_data))
            format_lower = img.format.lower() if img.format else None
            return format_lower
        except Exception as e:
            logger.warning(f"Failed to detect image format: {e}")
            return None

    @staticmethod
    def _convert_image_to_supported_format(image_b64: str) -> Optional[str]:
        """
        Convert image to a format supported by OpenAI Vision API.

        Converts images to PNG (for transparency) or JPEG (for RGB images)
        if the current format is not supported.

        Args:
            image_b64: Base64-encoded image string in any format.

        Returns:
            Converted base64-encoded image string in supported format, or None if conversion fails.
        """
        if not PILImage:
            logger.warning("PIL not available, cannot convert image")
            return None

        try:
            # Decode and open image
            image_data = b64decode(image_b64)
            img = PILImage.open(BytesIO(image_data))

            # Check current format
            current_format = img.format.lower() if img.format else None

            # If already in supported format, return as-is
            if current_format in SUPPORTED_IMAGE_FORMATS:
                logger.debug(f"Image already in supported format: {current_format}")
                return image_b64

            # Convert to appropriate format
            logger.info(f"Converting image from {current_format} to supported format")
            output_buffer = BytesIO()

            # Handle RGBA and palette images (need transparency support)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                img.save(output_buffer, format="PNG")
                target_format = "PNG"
            else:
                # Convert to RGB for JPEG (smaller size)
                img = img.convert("RGB")
                img.save(output_buffer, format="JPEG", quality=95)
                target_format = "JPEG"

            # Encode to base64
            output_buffer.seek(0)
            converted_b64 = b64encode(output_buffer.read()).decode("utf-8")

            logger.info(f"Successfully converted image to {target_format}")
            return converted_b64

        except Exception as e:
            msg = f"Failed to convert image: {e}"
            logger.error(msg)
            return None

    def _extract_images(self, chunks: List[Any]) -> List[str]:
        """
        Extract and validate base64-encoded images from CompositeElement objects.

        Automatically converts images to OpenAI-supported formats (PNG/JPEG).
        Skips images that cannot be converted with a warning.

        Args:
            chunks: List of elements extracted from PDF.

        Returns:
            List of base64-encoded image strings in supported formats only.
        """
        images_b64 = []
        skipped_count = 0

        for chunk in chunks:
            if "CompositeElement" in str(type(chunk)):
                chunk_elements = chunk.metadata.orig_elements
                for element in chunk_elements:
                    if "Image" in str(type(element)):
                        image_b64 = element.metadata.image_base64
                        if image_b64:
                            # Validate and convert image format
                            converted_image = self._convert_image_to_supported_format(image_b64)
                            if converted_image:
                                images_b64.append(converted_image)
                            else:
                                skipped_count += 1
                                logger.warning("Skipping image: conversion to supported format failed")

        if skipped_count > 0:
            logger.warning(f"Skipped {skipped_count} invalid or unsupported images")

        return images_b64
