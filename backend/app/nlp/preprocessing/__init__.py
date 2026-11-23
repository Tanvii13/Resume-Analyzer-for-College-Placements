"""
Text preprocessing and structure normalization for resume documents.

Module A (NLP-01) of Sprint 2 NLP pipeline.
"""

from app.nlp.preprocessing.normalizer import (
    PROTECTED_TECHNICAL_PATTERNS,
    is_bullet,
    normalize_line,
    normalize_text,
    split_bullet,
)
from app.nlp.preprocessing.segmenter import (
    BlockType,
    LineType,
    SegmentedDocument,
    TextBlock,
    TextLine,
    segment_text,
)

__all__ = [
    "normalize_text",
    "normalize_line",
    "is_bullet",
    "split_bullet",
    "PROTECTED_TECHNICAL_PATTERNS",
    "segment_text",
    "SegmentedDocument",
    "TextBlock",
    "TextLine",
    "LineType",
    "BlockType",
]
