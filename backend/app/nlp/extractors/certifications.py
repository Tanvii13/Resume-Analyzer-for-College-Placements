"""
Certifications, achievements and extracurricular extractor.

Module D4 (NLP-09) of the Sprint 2 NLP pipeline.

These sections are plain lists, so each bullet (or each non-bullet line) becomes
one item. Wrapped lines are already re-joined by `section_blocks`. Bare URLs are
kept on the item they belong to rather than turned into items of their own.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.nlp.extractors._entries import (
    URL_RE,
    clean_text,
    dedupe,
    section_blocks,
    sections_named,
)
from app.nlp.extractors.base import BaseExtractor
from app.nlp.preprocessing import SegmentedDocument
from app.nlp.sections import (
    SECTION_ACHIEVEMENTS,
    SECTION_CERTIFICATIONS,
    SECTION_EXTRACURRICULAR,
    SectionMap,
)


@dataclass
class ListSections:
    """Plain list items from the certification-style sections."""
    certifications: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    extracurricular: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, List[str]]:
        return {
            "certifications": self.certifications,
            "achievements": self.achievements,
            "extracurricular": self.extracurricular,
        }


class CertificationsExtractor(BaseExtractor):
    """Extracts list items from certifications, achievements and extracurricular sections."""

    def extract(
        self,
        sections: SectionMap,
        document: Optional[SegmentedDocument] = None,
    ) -> ListSections:
        return ListSections(
            certifications=self._items(sections, SECTION_CERTIFICATIONS),
            achievements=self._items(sections, SECTION_ACHIEVEMENTS),
            extracurricular=self._items(sections, SECTION_EXTRACURRICULAR),
        )

    @staticmethod
    def _items(sections: SectionMap, name: str) -> List[str]:
        items: List[str] = []
        for section in sections_named(sections, name):
            for block in section_blocks(section):
                text = clean_text(block.text)
                if not text:
                    continue
                if URL_RE.fullmatch(text) and items:
                    # A credential link on its own line belongs to the previous item
                    items[-1] = f"{items[-1]} ({text})"
                    continue
                # A link wrapped onto the bullet: "Certificate https://..." -> "Certificate (https://...)"
                m = URL_RE.search(text)
                if m and m.end() == len(text) and m.start() > 0 and text[m.start() - 1] == " ":
                    text = f"{text[:m.start()].rstrip()} ({m.group(0)})"
                items.append(text)
        return dedupe(items)


__all__ = ["CertificationsExtractor", "ListSections"]
