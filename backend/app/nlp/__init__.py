"""
Natural Language Processing (NLP) package for Resume Analyzer for College Placements.

Provides modular text preprocessing, section classification, entity extraction,
skill normalization, and candidate profile aggregation.
"""

from app.nlp.extractors import (
    BaseExtractor,
    ContactExtractor,
    ContactInfo,
    ExtractedSkill,
    SkillExtractor,
    SkillProfile,
)
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
from app.nlp.taxonomy import (
    get_all_canonical_skills,
    get_all_categories,
    get_canonical_skill,
    get_skill_category,
    get_skills_by_category,
    is_valid_skill,
    load_degrees,
    load_skill_aliases,
    load_skills_taxonomy,
    resolve_degree,
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
    # Entity Extractors (Module C & E2)
    "BaseExtractor",
    "ContactExtractor",
    "ContactInfo",
    "SkillExtractor",
    "ExtractedSkill",
    "SkillProfile",
    # Skill & Degree Taxonomy (Module E1)
    "load_skills_taxonomy",
    "load_skill_aliases",
    "load_degrees",
    "get_canonical_skill",
    "is_valid_skill",
    "get_skill_category",
    "get_skills_by_category",
    "get_all_canonical_skills",
    "get_all_categories",
    "resolve_degree",
]
