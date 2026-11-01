"""
Natural Language Processing (NLP) package for Resume Analyzer for College Placements.

Provides modular text preprocessing, section classification, entity extraction,
skill normalization, and candidate profile aggregation.
"""

from app.nlp.preprocessing import (
    BlockType,
    LineType,
    PROTECTED_TECHNICAL_PATTERNS,
    SegmentedDocument,
    TextBlock,
    TextLine,
    is_bullet,
    normalize_line,
    normalize_text,
    segment_text,
    split_bullet,
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
