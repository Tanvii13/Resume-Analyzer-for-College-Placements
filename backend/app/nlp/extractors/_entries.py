"""
Shared helpers for Module D extractors (education, experience, projects,
certifications).

Module B gives each section as a list of TextBlocks. Bullet blocks are details
of whatever entry came before them; non-bullet blocks (paragraphs and table
rows) are the "header" lines that introduce an entry. These helpers turn that
block list into raw entries and split header lines into fragments.
"""

from dataclasses import dataclass, field
import re
from typing import Iterable, List, Optional, Sequence

from app.nlp.preprocessing import BlockType, LineType, TextBlock, split_bullet
from app.nlp.sections import ClassifiedSection, SectionMap

URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s|,;()<>]+"
    r"|(?<![@\w.])(?:github\.com|gitlab\.com|bitbucket\.org|[a-z0-9-]+\.(?:vercel\.app|netlify\.app|herokuapp\.com|github\.io))(?:/[^\s|,;()<>]*)?",
    re.IGNORECASE,
)

# Separators commonly used inside resume header lines. Hyphens only count when
# surrounded by spaces so "Full-Stack" and "DA-IICT" stay intact.
FRAGMENT_SPLIT_RE = re.compile(r"\s*(?:\||•|·|\s[-–—]\s|\t|\s{3,})\s*")

COMMON_LOCATIONS = {
    "remote", "hybrid", "on-site", "onsite", "work from home", "wfh", "india", "usa",
    "ahmedabad", "gandhinagar", "vadodara", "surat", "rajkot", "mumbai", "pune",
    "bengaluru", "bangalore", "hyderabad", "chennai", "delhi", "new delhi", "noida",
    "gurugram", "gurgaon", "kolkata", "jaipur", "indore", "bhopal", "chandigarh",
    "kochi", "nagpur", "lucknow", "mysuru", "mysore", "coimbatore", "goa",
    "singapore", "london", "dubai", "san francisco", "seattle", "new york",
}


@dataclass
class RawEntry:
    """A group of blocks believed to describe one entry."""
    header_blocks: List[TextBlock] = field(default_factory=list)
    detail_blocks: List[TextBlock] = field(default_factory=list)
    section_name: Optional[str] = None

    @property
    def header_lines(self) -> List[str]:
        return [b.text.strip() for b in self.header_blocks if b.text and b.text.strip()]

    @property
    def details(self) -> List[str]:
        return [b.text.strip() for b in self.detail_blocks if b.text and b.text.strip()]

    @property
    def text(self) -> str:
        return "\n".join(self.header_lines + self.details)

    def is_empty(self) -> bool:
        return not self.header_blocks and not self.detail_blocks


def is_detail_block(block: TextBlock) -> bool:
    return block.block_type == BlockType.BULLET_ITEM


def sections_named(sections: Optional[SectionMap], *names: str) -> List[ClassifiedSection]:
    """All classified sections whose canonical name is in `names`, in document order."""
    if not sections or not sections.sections:
        return []
    return [s for s in sections.sections if s.canonical_name in names]


_DATE_HINT_RE = re.compile(
    r"(?<!\d)(?:19|20)\d{2}(?!\d)|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*'?\d{2}",
    re.IGNORECASE,
)


def _starts_new_line_entry(text: str, previous_bullet: str) -> bool:
    """
    Decide whether an unindented line after a bullet is a new header line
    rather than the wrapped tail of that bullet.
    """
    if not text or not text[0].isupper():
        return False
    if "|" in text or _DATE_HINT_RE.search(text):
        return True
    return previous_bullet.rstrip().endswith((".", "!", "?"))


def section_blocks(section: ClassifiedSection) -> List[TextBlock]:
    """
    Blocks of a section for entry extraction.

    Rebuilt from `section.lines` so that each header line stays separate.
    Module A's general-purpose block merger joins any unindented line after a
    bullet onto that bullet, which fuses two roles together when a resume has
    no blank line between them. Here a line only continues a bullet when it is
    indented, starts in lower case, or the bullet is clearly unfinished.
    """
    if section.lines:
        blocks: List[TextBlock] = []
        last_bullet: Optional[TextBlock] = None
        for line in section.lines:
            text = (line.text or "").strip()
            if line.line_type == LineType.EMPTY or not text:
                continue
            if line.line_type == LineType.BULLET:
                _, content = split_bullet(text)
                last_bullet = TextBlock(len(blocks), BlockType.BULLET_ITEM, content.strip(), line.raw_text,
                                        lines=[line], start_line=line.line_number, end_line=line.line_number,
                                        bullet_marker=line.bullet_marker)
                blocks.append(last_bullet)
                continue
            if (line.line_type == LineType.CONTINUATION and last_bullet is not None
                    and (line.indent_level > 0 or not _starts_new_line_entry(text, last_bullet.text))):
                last_bullet.text = f"{last_bullet.text} {text}".strip()
                last_bullet.lines.append(line)
                last_bullet.end_line = line.line_number
                continue
            last_bullet = None
            kind = BlockType.TABLE_ROW if line.line_type == LineType.TABLE_ROW else BlockType.PARAGRAPH
            blocks.append(TextBlock(len(blocks), kind, text, line.raw_text, lines=[line],
                                    start_line=line.line_number, end_line=line.line_number))
        if blocks:
            return blocks

    if section.blocks:
        return [b for b in section.blocks if b.text and b.text.strip()]
    blocks = []
    for i, line in enumerate((section.content or "").splitlines()):
        line = line.strip()
        if not line:
            continue
        if line.startswith(("- ", "* ", "• ")):
            blocks.append(TextBlock(i, BlockType.BULLET_ITEM, line[2:].strip(), line))
        else:
            blocks.append(TextBlock(i, BlockType.PARAGRAPH, line, line))
    return blocks


def split_fragments(line: str) -> List[str]:
    """Split a header line on resume separators, dropping empty pieces."""
    parts = FRAGMENT_SPLIT_RE.split(line or "")
    return [p.strip(" ,;:()[]") for p in parts if p and p.strip(" ,;:()[]")]


def is_location(fragment: str) -> bool:
    """True if a fragment looks like a place ('Pune', 'Bengaluru, India', 'Remote')."""
    if not fragment:
        return False
    pieces = [p.strip().lower() for p in fragment.split(",") if p.strip()]
    return bool(pieces) and all(p in COMMON_LOCATIONS for p in pieces)


def find_urls(text: str) -> List[str]:
    """All URLs in text, normalized with an https:// scheme and no trailing punctuation."""
    urls: List[str] = []
    for m in URL_RE.finditer(text or ""):
        url = m.group(0).rstrip(".,;:)]")
        if not url.lower().startswith("http"):
            url = "https://" + url
        if url not in urls:
            urls.append(url)
    return urls


def strip_urls(text: str) -> str:
    return URL_RE.sub("", text or "").strip()


def clean_text(text: Optional[str]) -> Optional[str]:
    """Collapse whitespace and trim separators; None if nothing is left."""
    if text is None:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip(" \t|,;:-–—")
    # Drop brackets only when unbalanced ("(May 2024" -> "May 2024", "Intern (Contract)" stays)
    while cleaned and cleaned[-1] in ")]" and cleaned.count("(") + cleaned.count("[") < cleaned.count(")") + cleaned.count("]"):
        cleaned = cleaned[:-1].rstrip(" \t|,;:-–—")
    while cleaned and cleaned[0] in "([" and cleaned.count("(") + cleaned.count("[") > cleaned.count(")") + cleaned.count("]"):
        cleaned = cleaned[1:].lstrip(" \t|,;:-–—")
    cleaned = re.sub(r"\(\s*\)|\[\s*\]", "", cleaned).strip()
    return cleaned or None


def dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def contains_any(text: str, words: Sequence[str]) -> bool:
    lowered = (text or "").lower()
    return any(re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", lowered) for w in words)
