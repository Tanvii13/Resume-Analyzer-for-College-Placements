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
from app.nlp.sections import (
    CANONICAL_SECTIONS,
    ClassifiedSection,
    SectionMap,
    classify_heading,
    classify_sections,
)

__all__ = [
    # Preprocessing (Module A)
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
    # Section Classification (Module B)
    "classify_sections",
    "classify_heading",
    "ClassifiedSection",
    "SectionMap",
    "CANONICAL_SECTIONS",
]
