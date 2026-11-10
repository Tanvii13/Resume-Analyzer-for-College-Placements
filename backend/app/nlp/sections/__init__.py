"""
Section classification package for resume documents.

Module B (NLP-02) of Sprint 2 NLP pipeline.
"""

from app.nlp.sections.classifier import (
    ClassifiedSection,
    SectionMap,
    classify_heading,
    classify_sections,
)
from app.nlp.sections.patterns import (
    CANONICAL_SECTIONS,
    SECTION_ACHIEVEMENTS,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_EXTRACURRICULAR,
    SECTION_GENERAL_BODY,
    SECTION_INTERNSHIPS,
    SECTION_PERSONAL_INFO,
    SECTION_PROJECTS,
    SECTION_SOFT_SKILLS,
    SECTION_TECHNICAL_SKILLS,
)

__all__ = [
    "classify_sections",
    "classify_heading",
    "ClassifiedSection",
    "SectionMap",
    "CANONICAL_SECTIONS",
    "SECTION_PERSONAL_INFO",
    "SECTION_EDUCATION",
    "SECTION_EXPERIENCE",
    "SECTION_INTERNSHIPS",
    "SECTION_PROJECTS",
    "SECTION_TECHNICAL_SKILLS",
    "SECTION_SOFT_SKILLS",
    "SECTION_CERTIFICATIONS",
    "SECTION_ACHIEVEMENTS",
    "SECTION_EXTRACURRICULAR",
    "SECTION_GENERAL_BODY",
]
