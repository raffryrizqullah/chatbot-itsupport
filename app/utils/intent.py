"""
Simple intent heuristics for chat messages.

Used to decide whether to include source links inline in answers.
"""

import re
from typing import Pattern


_SMALLTALK_PATTERNS = [
    r"\b(hai|halo|hello|hi)\b",
    r"\b(selamat\s+(pagi|siang|sore|malam))\b",
    r"\b(terima\s?kasi?h|makasih|thanks|thank\s+you)\b",
    r"\b(oke|okey|ok|sip|siap|noted)\b",
    r"\b(maaf|sorry)\b",
    r"\b(lanjut|lanjutan|follow\s*up)\b$",
]

_QUESTION_KEYWORDS = [
    "?",
    "apa",
    "bagaimana",
    "gimana",
    "mengapa",
    "kenapa",
    "dimana",
    "kapan",
    "berapa",
    "what",
    "how",
    "why",
    "where",
    "when",
    "which",
]

_SMALLTALK_REGEX: Pattern[str] = re.compile("|".join(_SMALLTALK_PATTERNS), re.IGNORECASE)


def is_smalltalk(text: str) -> bool:
    """
    Return True if message looks like small talk (greetings/thanks/ack), not an information query.

    Heuristic: matches smalltalk patterns and lacks question keywords, and message is short.
    """
    if not text:
        return False
    s = text.strip().lower()
    if len(s) > 80:
        return False
    if any(kw in s for kw in _QUESTION_KEYWORDS):
        return False
    return bool(_SMALLTALK_REGEX.search(s))


def wants_sources(text: str) -> bool:
    """
    Return True if the user explicitly asks for sources/links/references.
    """
    if not text:
        return False
    s = text.strip().lower()
    keywords = [
        "sumber",
        "referensi",
        "link",
        "tautan",
        "source",
        "citation",
        "bukti",
        "lihat dokumen",
        "lampiran",
        "dokumen",
    ]
    return any(k in s for k in keywords)

