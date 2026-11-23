"""
Section classification engine for resume documents.

Module B (NLP-02) of Sprint 2 NLP pipeline.

Classifies resume text and pre-segmented blocks into 10 canonical sections using
a multi-tier heading detection hierarchy:
- Tier 1: Exact case-insensitive match
- Tier 2: Normalized alias & synonym match
- Tier 3: Regex-based heading patterns
- Tier 4: Typo-tolerant Levenshtein fuzzy matching
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from app.nlp.preprocessing import (
    BlockType,
    LineType,
    SegmentedDocument,
    TextBlock,
    TextLine,
    segment_text,
)
from app.nlp.sections.patterns import (
    CANONICAL_SECTIONS,
    HEADING_ALIASES,
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
    SECTION_REGEXES,
    levenshtein_distance,
    string_similarity,
)


@dataclass
class ClassifiedSection:
    """Represents a classified resume section preserving ordering and provenance."""
    canonical_name: str
    original_heading: Optional[str]
    content: str
    raw_content: str
    blocks: List[TextBlock] = field(default_factory=list)
    lines: List[TextLine] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    confidence: float = 1.0
    heading_line_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_name": self.canonical_name,
            "original_heading": self.original_heading,
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "confidence": self.confidence,
            "heading_line_number": self.heading_line_number,
            "block_count": len(self.blocks),
            "line_count": len(self.lines),
        }


@dataclass
class SectionMap:
    """Structured collection of classified sections preserving document order."""
    sections: List[ClassifiedSection] = field(default_factory=list)

    def get_section(self, canonical_name: str) -> Optional[ClassifiedSection]:
        """Return the first section matching canonical_name, or None."""
        for sec in self.sections:
            if sec.canonical_name == canonical_name:
                return sec
        return None

    def get_sections(self, canonical_name: str) -> List[ClassifiedSection]:
        """Return all sections matching canonical_name."""
        return [sec for sec in self.sections if sec.canonical_name == canonical_name]

    def has_section(self, canonical_name: str) -> bool:
        """Check if a section exists and has non-empty content."""
        sec = self.get_section(canonical_name)
        return sec is not None and bool(sec.content.strip())

    @property
    def section_names(self) -> List[str]:
        """List of all canonical section names in order of appearance."""
        return [sec.canonical_name for sec in self.sections]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sections": [sec.to_dict() for sec in self.sections],
            "section_order": self.section_names,
            "identified_count": len(self.sections),
        }


def _clean_heading_candidate(text: str) -> str:
    """Clean a heading candidate for normalized dictionary and regex matching."""
    stripped = text.strip()
    # Strip optional leading numbering like '1.', 'I.', '(A)'
    stripped = re.sub(r"^\s*(\[?\d+[\.\)\]]|\(?[a-zA-Z][\.\)]|\(?[ivxIVX]+[\.\)])\s+", "", stripped)
    # Strip trailing punctuation such as colons, dashes, or underlines
    stripped = stripped.rstrip(":-_#=").strip()
    # Normalize internal spaces
    return re.sub(r"\s+", " ", stripped).lower()


# Common non-heading words to reject from fuzzy matching to avoid false positives
_FALSE_POSITIVE_WORDS = {
    "and", "the", "for", "with", "from", "that", "this", "have", "were", "been",
    "will", "when", "what", "which", "about", "spills", "stills", "drills", "grills",
    "fills", "bills", "mills", "kills", "skills", "pills", "tills", "chills"
}


def classify_heading(text: str) -> Optional[Tuple[str, float]]:
    """
    Classify a candidate line as a resume section heading.

    Multi-tier hierarchy:
    - Tier 1: Exact case-insensitive match on canonical names
    - Tier 2: Normalized alias & synonym lookup
    - Tier 3: Regex pattern matching
    - Tier 4: Typo-tolerant Levenshtein distance matching

    Returns:
        (canonical_name, confidence) if classified as a heading, or None if regular text.
    """
    if not text:
        return None

    stripped = text.strip()
    if not stripped or len(stripped) > 55:
        return None

    # Never treat table rows or bullet points as section headers
    if " | " in stripped or stripped.startswith(("-", "*", "•", "+")):
        return None

    # Reject ordinary sentences ending with sentence-terminal punctuation
    if stripped.endswith((".", "!", "?", ",", ";")):
        return None

    words = stripped.split()
    if not (1 <= len(words) <= 6):
        return None

    cleaned = _clean_heading_candidate(stripped)
    if not cleaned:
        return None

    # Tier 1: Exact canonical match
    if cleaned in CANONICAL_SECTIONS:
        return cleaned, 1.0

    # Tier 2: Normalized Alias & Synonym Lookup
    if cleaned in HEADING_ALIASES:
        return HEADING_ALIASES[cleaned], 0.98

    # Tier 3: Regex Pattern Matching
    for section_key, patterns in SECTION_REGEXES.items():
        for pat in patterns:
            if pat.match(stripped) or pat.match(cleaned):
                return section_key, 0.95

    # Tier 4: Typo-Tolerant Levenshtein Matching
    # Protect ordinary short English words from false positives
    if len(cleaned) < 5 or cleaned in _FALSE_POSITIVE_WORDS:
        return None

    # Compare against canonical sections and high-frequency primary aliases
    best_match: Optional[str] = None
    best_dist = 999
    best_ratio = 0.0

    # Test against canonical headings and primary targets
    fuzzy_targets = [
        ("education", SECTION_EDUCATION),
        ("academics", SECTION_EDUCATION),
        ("qualifications", SECTION_EDUCATION),
        ("experience", SECTION_EXPERIENCE),
        ("employment", SECTION_EXPERIENCE),
        ("work experience", SECTION_EXPERIENCE),
        ("internships", SECTION_INTERNSHIPS),
        ("internship", SECTION_INTERNSHIPS),
        ("projects", SECTION_PROJECTS),
        ("technical skills", SECTION_TECHNICAL_SKILLS),
        ("programming skills", SECTION_TECHNICAL_SKILLS),
        ("technologies", SECTION_TECHNICAL_SKILLS),
        ("soft skills", SECTION_SOFT_SKILLS),
        ("certifications", SECTION_CERTIFICATIONS),
        ("certificates", SECTION_CERTIFICATIONS),
        ("achievements", SECTION_ACHIEVEMENTS),
        ("accomplishments", SECTION_ACHIEVEMENTS),
        ("extracurricular", SECTION_EXTRACURRICULAR),
        ("extracurricular activities", SECTION_EXTRACURRICULAR),
    ]

    for target_name, target_canonical in fuzzy_targets:
        dist = levenshtein_distance(cleaned, target_name)
        ratio = string_similarity(cleaned, target_name)

        # Allow distance <= 2 for words >= 7 chars, distance <= 1 for shorter words
        max_allowed_dist = 2 if len(target_name) >= 7 else 1

        if dist <= max_allowed_dist and ratio >= 0.82:
            if dist < best_dist or (dist == best_dist and ratio > best_ratio):
                best_dist = dist
                best_ratio = ratio
                best_match = target_canonical

    if best_match is not None:
        confidence = round(best_ratio * 0.95, 2)
        return best_match, confidence

    return None


def classify_sections(
    document: Union[SegmentedDocument, str]
) -> SectionMap:
    """
    Classify a resume into structured sections.

    - Content before the first recognized heading is assigned to 'personal_info'.
    - Subsequent blocks are grouped under their respective recognized heading.
    - Unsupported headings or orphan trailing text are assigned to 'general_body'.
    - If no headings exist, the entire content is assigned to 'personal_info'.
    - Empty sections are captured cleanly with empty content.

    Args:
        document: SegmentedDocument instance from Module A, or raw string.

    Returns:
        SectionMap containing ClassifiedSection instances in document order.
    """
    if isinstance(document, str):
        seg_doc = segment_text(document)
    else:
        seg_doc = document

    if not seg_doc.blocks:
        return SectionMap(sections=[])

    sections: List[ClassifiedSection] = []

    # State tracking
    preamble_blocks: List[TextBlock] = []
    current_section: Optional[ClassifiedSection] = None

    def finalize_section():
        nonlocal current_section
        if current_section is not None:
            # Build consolidated text from blocks
            text_parts = [b.text for b in current_section.blocks if b.text.strip()]
            raw_parts = [b.raw_text for b in current_section.blocks if b.raw_text.strip()]
            current_section.content = "\n\n".join(text_parts).strip()
            current_section.raw_content = "\n\n".join(raw_parts).strip()

            if current_section.blocks:
                current_section.start_line = current_section.blocks[0].start_line
                current_section.end_line = current_section.blocks[-1].end_line
                # Flatten lines
                all_lines: List[TextLine] = []
                for b in current_section.blocks:
                    all_lines.extend(b.lines)
                current_section.lines = all_lines
            elif current_section.heading_line_number is not None:
                current_section.start_line = current_section.heading_line_number
                current_section.end_line = current_section.heading_line_number

            sections.append(current_section)
            current_section = None

    for block in seg_doc.blocks:
        # Check if this block is a section heading
        is_heading_block = False
        classified_heading = None

        # Only evaluate non-bullet, non-table blocks as prospective section headers
        if not block.is_bullet and not block.is_table_row:
            classified_heading = classify_heading(block.text)
            if classified_heading is not None:
                is_heading_block = True

        if is_heading_block and classified_heading is not None:
            canonical_name, confidence = classified_heading

            # If this is the first heading detected, finalize preamble into 'personal_info'
            if current_section is None and preamble_blocks:
                preamble_text = "\n\n".join(b.text for b in preamble_blocks if b.text.strip())
                preamble_raw = "\n\n".join(b.raw_text for b in preamble_blocks if b.raw_text.strip())
                p_lines: List[TextLine] = []
                for b in preamble_blocks:
                    p_lines.extend(b.lines)

                p_sec = ClassifiedSection(
                    canonical_name=SECTION_PERSONAL_INFO,
                    original_heading=None,
                    content=preamble_text,
                    raw_content=preamble_raw,
                    blocks=list(preamble_blocks),
                    lines=p_lines,
                    start_line=preamble_blocks[0].start_line,
                    end_line=preamble_blocks[-1].end_line,
                    confidence=1.0,
                    heading_line_number=None,
                )
                sections.append(p_sec)
                preamble_blocks.clear()
            else:
                finalize_section()

            # Start the new section
            current_section = ClassifiedSection(
                canonical_name=canonical_name,
                original_heading=block.text,
                content="",
                raw_content="",
                blocks=[],
                lines=[],
                start_line=block.start_line,
                end_line=block.end_line,
                confidence=confidence,
                heading_line_number=block.start_line,
            )
            continue

        # If not a heading block:
        if current_section is not None:
            current_section.blocks.append(block)
        else:
            preamble_blocks.append(block)

    finalize_section()

    # If document had no recognized headings at all, entire content is personal_info
    if not sections and preamble_blocks:
        preamble_text = "\n\n".join(b.text for b in preamble_blocks if b.text.strip())
        preamble_raw = "\n\n".join(b.raw_text for b in preamble_blocks if b.raw_text.strip())
        p_lines = []
        for b in preamble_blocks:
            p_lines.extend(b.lines)

        sections.append(
            ClassifiedSection(
                canonical_name=SECTION_PERSONAL_INFO,
                original_heading=None,
                content=preamble_text,
                raw_content=preamble_raw,
                blocks=list(preamble_blocks),
                lines=p_lines,
                start_line=preamble_blocks[0].start_line,
                end_line=preamble_blocks[-1].end_line,
                confidence=0.50,
                heading_line_number=None,
            )
        )

    return SectionMap(sections=sections)
