"""
Line and block segmenter for normalized resume text.

Module A (NLP-01) of Sprint 2 NLP pipeline.

Converts normalized resume text into structured lines and coherent semantic blocks
(paragraphs, bullet items with multiline continuations, table rows, and heading candidates)
without losing structural information or tabular data.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional

from app.nlp.preprocessing.normalizer import (
    is_bullet,
    normalize_line,
    normalize_text,
    split_bullet,
)


class LineType(str, Enum):
    """Classification of an individual line within the document."""
    EMPTY = "EMPTY"
    HEADING_CANDIDATE = "HEADING_CANDIDATE"
    BULLET = "BULLET"
    TABLE_ROW = "TABLE_ROW"
    CONTINUATION = "CONTINUATION"
    REGULAR = "REGULAR"


class BlockType(str, Enum):
    """Classification of a consolidated semantic text block."""
    PARAGRAPH = "PARAGRAPH"
    BULLET_ITEM = "BULLET_ITEM"
    TABLE_ROW = "TABLE_ROW"
    HEADING_CANDIDATE = "HEADING_CANDIDATE"


@dataclass
class TextLine:
    """Represents a single line of text in the document with structural metadata."""
    line_number: int
    text: str
    raw_text: str
    line_type: LineType
    bullet_marker: Optional[str] = None
    indent_level: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line_number": self.line_number,
            "text": self.text,
            "raw_text": self.raw_text,
            "line_type": self.line_type.value,
            "bullet_marker": self.bullet_marker,
            "indent_level": self.indent_level,
        }


@dataclass
class TextBlock:
    """
    Represents a coherent semantic block of text.

    May span multiple lines, such as a multiline bullet item description
    or a paragraph.
    """
    block_id: int
    block_type: BlockType
    text: str
    raw_text: str
    lines: List[TextLine] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    bullet_marker: Optional[str] = None
    table_cells: List[str] = field(default_factory=list)

    @property
    def is_bullet(self) -> bool:
        return self.block_type == BlockType.BULLET_ITEM

    @property
    def is_table_row(self) -> bool:
        return self.block_type == BlockType.TABLE_ROW

    @property
    def is_heading(self) -> bool:
        return self.block_type == BlockType.HEADING_CANDIDATE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_id": self.block_id,
            "block_type": self.block_type.value,
            "text": self.text,
            "raw_text": self.raw_text,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "is_bullet": self.is_bullet,
            "bullet_marker": self.bullet_marker,
            "is_table_row": self.is_table_row,
            "table_cells": self.table_cells,
            "line_count": len(self.lines),
        }


@dataclass
class SegmentedDocument:
    """
    Complete structured representation of a segmented resume document.
    """
    raw_text: str
    normalized_text: str
    lines: List[TextLine] = field(default_factory=list)
    blocks: List[TextBlock] = field(default_factory=list)

    def get_non_empty_lines(self) -> List[TextLine]:
        """Return all non-empty lines in document order."""
        return [line for line in self.lines if line.line_type != LineType.EMPTY]

    def get_bullet_blocks(self) -> List[TextBlock]:
        """Return all blocks classified as bullet items."""
        return [block for block in self.blocks if block.is_bullet]

    def get_table_blocks(self) -> List[TextBlock]:
        """Return all blocks classified as table rows."""
        return [block for block in self.blocks if block.is_table_row]

    def get_heading_candidate_blocks(self) -> List[TextBlock]:
        """Return all blocks identified as potential section headers."""
        return [block for block in self.blocks if block.is_heading]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_lines": len(self.lines),
            "non_empty_lines": len(self.get_non_empty_lines()),
            "total_blocks": len(self.blocks),
            "bullet_blocks_count": len(self.get_bullet_blocks()),
            "table_blocks_count": len(self.get_table_blocks()),
            "heading_candidates_count": len(self.get_heading_candidate_blocks()),
            "blocks": [b.to_dict() for b in self.blocks],
        }


# Keywords frequently found in resume section headers
_COMMON_HEADER_KEYWORDS = {
    "education", "academic", "academics", "qualifications",
    "experience", "employment", "internship", "internships", "work",
    "projects", "project",
    "skills", "technical skills", "tech stack", "competencies", "tools",
    "certifications", "certificates", "licenses",
    "achievements", "awards", "honors", "honours", "accomplishments",
    "extracurricular", "activities", "leadership", "volunteering",
    "summary", "objective", "profile", "about me",
    "publications", "courses", "coursework", "profiles",
}


def _is_table_row(line_text: str) -> bool:
    """Determine if a line is a tabular row generated by Sprint 1 (' | ' delimiter)."""
    if " | " not in line_text:
        return False
    cells = [c.strip() for c in line_text.split(" | ")]
    return len(cells) >= 2 and sum(bool(c) for c in cells) >= 2


def _parse_table_cells(line_text: str) -> List[str]:
    """Extract trimmed cell values from a table row string."""
    return [cell.strip() for cell in line_text.split(" | ") if cell.strip()]


def _is_heading_candidate(line_text: str) -> bool:
    """
    Check if a line matches characteristics of a resume section header.

    Heuristics:
    - 1 to 7 words, under 60 characters.
    - No pipe delimiters (not a table row).
    - Does not end with terminal punctuation ('.', '!', '?', ',').
    - Strong cues:
      - All uppercase letters (e.g., 'EDUCATION', 'TECHNICAL SKILLS').
      - Ends with a colon (e.g., 'Education:', 'Work Experience:').
      - Matches known section title keywords.
    """
    cleaned = line_text.strip()
    if not cleaned or len(cleaned) > 60:
        return False

    if " | " in cleaned:
        return False

    if cleaned.startswith(("-", "*", "•", "+")):
        return False

    words = cleaned.split()
    if not (1 <= len(words) <= 7):
        return False

    # Avoid lines ending with terminal punctuation (except optional colon)
    if cleaned.endswith((".", "!", "?", ",", ";")):
        return False

    bare_title = cleaned.rstrip(":").strip()
    lower_title = bare_title.lower()

    # 1. Matches common header keyword directly
    if lower_title in _COMMON_HEADER_KEYWORDS:
        return True

    # 2. Ends with a colon and has 1 to 5 words
    if cleaned.endswith(":") and len(words) <= 5:
        return True

    # 3. All uppercase with at least 3 letters
    letters = [ch for ch in bare_title if ch.isalpha()]
    if letters and all(ch.isupper() for ch in letters) and len(letters) >= 3:
        # Ignore common non-header uppercase strings like 'CGPA: 9.0' or 'SQL, C++, JAVA'
        if not re.search(r"[,/]", bare_title) and len(words) <= 5:
            return True

    return False


def segment_text(raw_text: Optional[str]) -> SegmentedDocument:
    """
    Segment raw resume text into structured lines and semantic blocks.

    Pipeline:
    1. Normalizes the full document using Module A's non-destructive normalizer.
    2. Classifies each line into LineType (BULLET, TABLE_ROW, HEADING_CANDIDATE, REGULAR, EMPTY).
    3. Groups lines into coherent semantic TextBlocks, consolidating multiline bullet
       continuation descriptions and preserving table rows and paragraph boundaries.

    Args:
        raw_text: Extracted raw resume text (e.g., from ResumeParseResult.text).

    Returns:
        SegmentedDocument containing typed lines and consolidated blocks.
    """
    if not raw_text or not raw_text.strip():
        return SegmentedDocument(
            raw_text=raw_text or "",
            normalized_text="",
            lines=[],
            blocks=[],
        )

    norm_text = normalize_text(raw_text)
    raw_lines = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    norm_lines = norm_text.split("\n")

    # Step 1: Parse and classify individual lines
    parsed_lines: List[TextLine] = []
    for idx, n_line in enumerate(norm_lines):
        line_num = idx + 1
        r_line = raw_lines[idx] if idx < len(raw_lines) else n_line
        indent = len(r_line) - len(r_line.lstrip(" "))

        if not n_line.strip():
            parsed_lines.append(
                TextLine(
                    line_number=line_num,
                    text="",
                    raw_text=r_line,
                    line_type=LineType.EMPTY,
                    bullet_marker=None,
                    indent_level=indent,
                )
            )
            continue

        if _is_table_row(n_line):
            parsed_lines.append(
                TextLine(
                    line_number=line_num,
                    text=n_line,
                    raw_text=r_line,
                    line_type=LineType.TABLE_ROW,
                    bullet_marker=None,
                    indent_level=indent,
                )
            )
        elif is_bullet(n_line):
            marker, _ = split_bullet(n_line)
            parsed_lines.append(
                TextLine(
                    line_number=line_num,
                    text=n_line,
                    raw_text=r_line,
                    line_type=LineType.BULLET,
                    bullet_marker=marker,
                    indent_level=indent,
                )
            )
        elif _is_heading_candidate(n_line):
            parsed_lines.append(
                TextLine(
                    line_number=line_num,
                    text=n_line,
                    raw_text=r_line,
                    line_type=LineType.HEADING_CANDIDATE,
                    bullet_marker=None,
                    indent_level=indent,
                )
            )
        else:
            parsed_lines.append(
                TextLine(
                    line_number=line_num,
                    text=n_line,
                    raw_text=r_line,
                    line_type=LineType.REGULAR,
                    bullet_marker=None,
                    indent_level=indent,
                )
            )

    # Step 2: Consolidate lines into coherent semantic blocks
    blocks: List[TextBlock] = []
    current_block: Optional[TextBlock] = None

    def finalize_current_block():
        nonlocal current_block
        if current_block is not None:
            blocks.append(current_block)
            current_block = None

    for line in parsed_lines:
        if line.line_type == LineType.EMPTY:
            # Blank lines strictly close the current block (preserve paragraph boundaries)
            finalize_current_block()
            continue

        if line.line_type == LineType.HEADING_CANDIDATE:
            finalize_current_block()
            block_id = len(blocks)
            blocks.append(
                TextBlock(
                    block_id=block_id,
                    block_type=BlockType.HEADING_CANDIDATE,
                    text=line.text,
                    raw_text=line.raw_text,
                    lines=[line],
                    start_line=line.line_number,
                    end_line=line.line_number,
                    bullet_marker=None,
                )
            )
            continue

        if line.line_type == LineType.TABLE_ROW:
            finalize_current_block()
            cells = _parse_table_cells(line.text)
            block_id = len(blocks)
            blocks.append(
                TextBlock(
                    block_id=block_id,
                    block_type=BlockType.TABLE_ROW,
                    text=line.text,
                    raw_text=line.raw_text,
                    lines=[line],
                    start_line=line.line_number,
                    end_line=line.line_number,
                    bullet_marker=None,
                    table_cells=cells,
                )
            )
            continue

        if line.line_type == LineType.BULLET:
            finalize_current_block()
            block_id = len(blocks)
            _, content = split_bullet(line.text)
            current_block = TextBlock(
                block_id=block_id,
                block_type=BlockType.BULLET_ITEM,
                text=content,
                raw_text=line.raw_text,
                lines=[line],
                start_line=line.line_number,
                end_line=line.line_number,
                bullet_marker=line.bullet_marker,
            )
            continue

        # Handling REGULAR lines: Check if this is a continuation of an open bullet item
        if current_block is not None and current_block.block_type == BlockType.BULLET_ITEM:
            # Mark line as continuation and append to open bullet block
            line.line_type = LineType.CONTINUATION
            current_block.lines.append(line)
            current_block.text = f"{current_block.text} {line.text}".strip()
            current_block.raw_text = f"{current_block.raw_text}\n{line.raw_text}"
            current_block.end_line = line.line_number
            continue

        # Handling regular text outside of bullets (standard paragraphs)
        if current_block is not None and current_block.block_type == BlockType.PARAGRAPH:
            current_block.lines.append(line)
            current_block.text = f"{current_block.text} {line.text}".strip()
            current_block.raw_text = f"{current_block.raw_text}\n{line.raw_text}"
            current_block.end_line = line.line_number
        else:
            finalize_current_block()
            block_id = len(blocks)
            current_block = TextBlock(
                block_id=block_id,
                block_type=BlockType.PARAGRAPH,
                text=line.text,
                raw_text=line.raw_text,
                lines=[line],
                start_line=line.line_number,
                end_line=line.line_number,
                bullet_marker=None,
            )

    finalize_current_block()

    return SegmentedDocument(
        raw_text=raw_text,
        normalized_text=norm_text,
        lines=parsed_lines,
        blocks=blocks,
    )
