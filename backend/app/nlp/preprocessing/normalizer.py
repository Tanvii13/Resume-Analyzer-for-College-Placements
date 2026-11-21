"""
Non-destructive text normalization for resume documents.

Module A (NLP-01) of Sprint 2 NLP pipeline.

Preserves critical resume structure, paragraph boundaries, and technical tokens
(such as C++, C#, .NET, Node.js, CI/CD, ASP.NET, Vue.js), while standardizing
Unicode, line endings, whitespace, and bullet representations.
"""

import re
import unicodedata
from typing import Optional, Tuple

# Technical terms and language tokens that must be preserved exactly
PROTECTED_TECHNICAL_PATTERNS = [
    r"\bC\+\+",
    r"\bC#",
    r"\.NET\b",
    r"\bASP\.NET\b",
    r"\bNode\.js\b",
    r"\bVue\.js\b",
    r"\bReact\.js\b",
    r"\bNext\.js\b",
    r"\bExpress\.js\b",
    r"\bAngular\.js\b",
    r"\bCI/CD\b",
    r"\bTCP/IP\b",
    r"\bPL/SQL\b",
    r"\bUI/UX\b",
    r"\bObjective-C\b",
    r"\bI/O\b",
]

# Zero-width, invisible, and soft hyphen formatting characters
_ZERO_WIDTH_CHARS = re.compile(
    r"[\u200b-\u200d\ufeff\u00ad\u200e\u200f\u2060\u180e]"
)

# Non-standard Unicode spaces
_NON_STANDARD_SPACES = re.compile(
    r"[\u00a0\u2002-\u200a\u202f\u205f\u3000]"
)

# Typographic curly quotes to standard ASCII quotes
_SINGLE_CURLY_QUOTES = re.compile(r"[\u2018\u2019\u201a\u201b\u2032]")
_DOUBLE_CURLY_QUOTES = re.compile(r"[\u201c\u201d\u201e\u201f\u2033\u00ab\u00bb]")

# Typographic dashes and hyphens
_SPECIAL_DASHES = re.compile(r"[\u2011\u2012\u2015\u2212]")
_EN_EM_DASH_RANGE = re.compile(r"(?<=\S)\s*[\u2013\u2014]\s*(?=\S)")

# Unicode bullet characters (can appear with or without trailing space)
_UNICODE_BULLET_CHARS = (
    "\u2022"  # • Bullet
    "\u25cf"  # ● Black circle
    "\u25cb"  # ○ White circle
    "\u25aa"  # ▪ Black small square
    "\u25a0"  # ■ Black square
    "\u25a1"  # □ White square
    "\u25ab"  # ▫ White small square
    "\u2023"  # ‣ Triangular bullet
    "\u2043"  # ⁃ Hyphen bullet
    "\u25e6"  # ◦ White bullet
    "\u2219"  # ∙ Bullet operator
    "\u25b6"  # ▶ Black right-pointing triangle
    "\u27a4"  # ➤ Black rightwards arrowhead
    "\u2713"  # ✓ Check mark
    "\u2714"  # ✔ Heavy check mark
)

# Regex matching a line starting with a Unicode bullet
_UNICODE_BULLET_RE = re.compile(
    rf"^\s*([{re.escape(_UNICODE_BULLET_CHARS)}]|[\u2013\u2014])\s*(.*)$"
)

# Regex matching ASCII bullet symbols at the start of a line
# Note: '+' requires whitespace following it to protect phone numbers like '+91'
_ASCII_BULLET_RE = re.compile(
    r"^\s*([*\-]|\+(?=\s))\s+(.*)$"
)

# Regex matching numbered list bullets, e.g., '1.', '1)', '[1]'
_NUMBERED_BULLET_RE = re.compile(
    r"^\s*(\[?\d+[\.\)\]])\s+(.*)$"
)


def is_bullet(line: str) -> bool:
    """
    Check if a line begins with any bullet or list item marker.

    Recognizes Unicode glyphs (•, ●, ▪, etc.), ASCII bullets (*, -, + with space),
    and numbered list items (1., 1), [1]).
    """
    if not line or not line.strip():
        return False
    stripped = line.strip()
    return bool(
        _UNICODE_BULLET_RE.match(stripped)
        or _ASCII_BULLET_RE.match(stripped)
        or _NUMBERED_BULLET_RE.match(stripped)
    )


def split_bullet(line: str) -> Tuple[Optional[str], str]:
    """
    Split a line into its bullet marker and content.

    Returns:
        (marker, content):
            - If bullet: marker string (e.g., '-', '1.') and stripped content string.
            - If not bullet: (None, stripped content).
    """
    if not line:
        return None, ""

    stripped = line.strip()

    # 1. Unicode bullets
    m_uni = _UNICODE_BULLET_RE.match(stripped)
    if m_uni:
        return "-", m_uni.group(2).strip()

    # 2. ASCII bullets (*, -, +)
    m_asc = _ASCII_BULLET_RE.match(stripped)
    if m_asc:
        return "-", m_asc.group(2).strip()

    # 3. Numbered list items
    m_num = _NUMBERED_BULLET_RE.match(stripped)
    if m_num:
        marker = m_num.group(1).rstrip(". )]")
        return f"{marker}.", m_num.group(2).strip()

    return None, stripped


def normalize_line(line: str) -> str:
    """
    Normalize a single line of text:
    - Normalizes Unicode spaces and zero-width characters.
    - Standardizes quotes and dashes.
    - Normalizes bullet markers to canonical '- <content>' (preserving numbered items).
    - Preserves internal words, technical symbols, and table delimiters (' | ').
    """
    if not line:
        return ""

    # Strip zero-width characters
    cleaned = _ZERO_WIDTH_CHARS.sub("", line)

    # Standardize spaces
    cleaned = _NON_STANDARD_SPACES.sub(" ", cleaned)

    # Standardize quotes
    cleaned = _SINGLE_CURLY_QUOTES.sub("'", cleaned)
    cleaned = _DOUBLE_CURLY_QUOTES.sub('"', cleaned)

    # Standardize dashes within words or date ranges (e.g., 2021 – 2025 -> 2021 - 2025)
    cleaned = _SPECIAL_DASHES.sub("-", cleaned)
    cleaned = _EN_EM_DASH_RANGE.sub(" - ", cleaned)

    # Collapse multiple horizontal whitespace runs
    cleaned = re.sub(r"[ \t\f\v]+", " ", cleaned).strip()

    if not cleaned:
        return ""

    # Normalize bullet format if line starts with a bullet
    marker, content = split_bullet(cleaned)
    if marker is not None:
        if marker == "-":
            return f"- {content}"
        # Keep numbered items like '1. Content'
        return f"{marker} {content}"

    return cleaned


def normalize_text(text: Optional[str]) -> str:
    """
    Normalize extracted resume text non-destructively:
    - Normalizes Unicode to NFKC form.
    - Standardizes line endings to '\\n'.
    - Removes zero-width and invisible control characters.
    - Normalizes quotes, dashes, and bullet symbols consistently.
    - Collapses redundant spaces while preserving line structure and table columns (' | ').
    - Preserves paragraph separations (limiting consecutive line breaks to at most '\\n\\n').
    - Fully protects programming tokens (C++, C#, .NET, Node.js, CI/CD, etc.).

    Args:
        text: Raw resume text string.

    Returns:
        Cleaned, standardized text string ready for segmentation and NLP classification.
    """
    if not text:
        return ""

    # 1. Normalize line endings
    normalized = (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\v", "\n")
        .replace("\f", "\n")
    )

    # 2. Unicode NFKC normalization
    normalized = unicodedata.normalize("NFKC", normalized)

    # 3. Strip zero-width and soft-hyphen characters
    normalized = _ZERO_WIDTH_CHARS.sub("", normalized)

    # 4. Standardize non-standard spaces
    normalized = _NON_STANDARD_SPACES.sub(" ", normalized)

    # 5. Standardize quotes
    normalized = _SINGLE_CURLY_QUOTES.sub("'", normalized)
    normalized = _DOUBLE_CURLY_QUOTES.sub('"', normalized)

    # 6. Standardize dashes and date ranges
    normalized = _SPECIAL_DASHES.sub("-", normalized)
    normalized = _EN_EM_DASH_RANGE.sub(" - ", normalized)

    # 7. Normalize line-by-line while preserving paragraph and line structure
    raw_lines = normalized.split("\n")
    cleaned_lines = []

    for raw_line in raw_lines:
        norm_line = normalize_line(raw_line)
        cleaned_lines.append(norm_line)

    # Rejoin lines
    rejoined = "\n".join(cleaned_lines)

    # 8. Collapse 3 or more consecutive newlines into exactly 2 (\n\n)
    rejoined = re.sub(r"\n{3,}", "\n\n", rejoined)

    return rejoined.strip()
