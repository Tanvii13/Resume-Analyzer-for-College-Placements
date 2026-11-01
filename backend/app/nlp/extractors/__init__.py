"""
Domain entity extractors for structured resume profile generation.

Module C, D, and E of Sprint 2 NLP pipeline.
"""

from app.nlp.extractors.base import BaseExtractor
from app.nlp.extractors.contact import ContactExtractor, ContactInfo

__all__ = [
    "BaseExtractor",
    "ContactExtractor",
    "ContactInfo",
]
