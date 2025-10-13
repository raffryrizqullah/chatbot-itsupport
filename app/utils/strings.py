"""
String utilities for filename normalization and display names.
"""

from urllib.parse import unquote
import os
import re
from typing import Optional


def to_document_name(filename: str) -> str:
    """
    Convert an uploaded filename into a human‑readable document name.

    Rules:
    - Remove path and extension
    - URL-decode (handle %20 etc.)
    - Replace underscores with spaces; keep hyphens (e.g., "EAP-TLS")
    - Collapse multiple spaces
    - Trim leading/trailing spaces

    Args:
        filename: Original filename from upload.

    Returns:
        Clean, human‑readable document name.
    """
    # Strip any path components and extension
    base = os.path.basename(filename or "")
    name, _ = os.path.splitext(base)

    # URL-decode (e.g., %20 -> space)
    name = unquote(name)

    # Replace underscores with spaces (keep hyphens as-is)
    name = name.replace("_", " ")

    # Normalize whitespace
    name = re.sub(r"\s+", " ", name).strip()

    return name or base or "Document"

