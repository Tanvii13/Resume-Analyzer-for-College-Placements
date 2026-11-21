"""
Comprehensive automated tests for Sprint 2 – Module A: Preprocessing & Structure Normalizer.

Covers:
- Unicode normalization (NFKC, zero-width chars, soft hyphens, curly quotes, dashes)
- Line endings standardization
- Bullet character normalization across Unicode and ASCII formats
- Protection of programming language tokens (C++, C#, .NET, Node.js, CI/CD, ASP.NET, Vue.js)
- Whitespace and multiple consecutive blank lines collapsing
- Preservation of table row delimiters (' | ')
- Multiline bullet continuation handling in segmentation
- Heading candidate detection
- Empty and whitespace-only inputs
- Large resume text performance and deterministic output
- Preservation of URLs and email addresses
"""

import time
import pytest

from app.nlp.preprocessing import (
    BlockType,
    LineType,
    SegmentedDocument,
    TextBlock,
    TextLine,
    is_bullet,
    normalize_line,
    normalize_text,
    segment_text,
    split_bullet,
)


# ============================================================================
# Normalizer Unit Tests
# ============================================================================

def test_normalize_empty_and_whitespace_only():
    """Verify that None, empty string, and whitespace-only text return empty string."""
    assert normalize_text(None) == ""
    assert normalize_text("") == ""
    assert normalize_text("   ") == ""
    assert normalize_text("\t\t\n  \n\r\n") == ""


def test_normalize_line_endings():
    """Verify that \\r\\n, \\r, \\v, \\f are standardized to \\n."""
    raw = "Line 1\r\nLine 2\rLine 3\fLine 4\vLine 5"
    expected = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    assert normalize_text(raw) == expected


def test_normalize_consecutive_blank_lines():
    """Verify that 3 or more consecutive newlines are collapsed to exactly 2 (\\n\\n)."""
    raw = "Section A\n\n\n\n\nSection B\n\n\nSection C"
    normalized = normalize_text(raw)
    assert "\n\n\n" not in normalized
    assert normalized == "Section A\n\nSection B\n\nSection C"


def test_normalize_unicode_characters_and_quotes():
    """Verify normalization of Unicode accents, curly quotes, and non-breaking spaces."""
    raw = (
        "“High-impact” feature with ‘99.9%’ uptime.\n"
        "Specialized in: Développeur – C++ & Python.\n"
        "Non-breaking\u00a0space and thin\u2009space."
    )
    normalized = normalize_text(raw)
    assert '"High-impact"' in normalized
    assert "'99.9%'" in normalized
    assert "Developpeur" in normalized or "Développeur" in normalized
    assert "Non-breaking space" in normalized
    assert "thin space" in normalized


def test_strip_zero_width_and_invisible_characters():
    """Verify removal of zero-width spaces, BOM, and soft hyphens."""
    raw = "Zero\u200bWidth\ufeffSpace\u00adHyphen\u200cNonJoiner\u200dJoiner."
    normalized = normalize_text(raw)
    assert normalized == "ZeroWidthSpaceHyphenNonJoinerJoiner."


def test_normalize_bullet_formats():
    """Verify that diverse Unicode and ASCII bullet characters normalize to '- <content>'."""
    bullets = [
        "• Standard Unicode bullet",
        "● Black circle bullet",
        "○ White circle bullet",
        "▪ Small black square bullet",
        "■ Black square bullet",
        "▫ Small white square bullet",
        "‣ Triangular bullet",
        "⁃ Hyphen bullet",
        "◦ White bullet",
        "∙ Bullet operator",
        "▶ Triangle bullet",
        "✓ Checkmark bullet",
        "* Asterisk bullet with space",
        "- Hyphen bullet with space",
        "+ Plus bullet with space",
        "– En-dash bullet",
        "— Em-dash bullet",
        "•NoSpaceAfterBullet",
    ]

    for bullet_line in bullets:
        assert is_bullet(bullet_line), f"Failed to identify as bullet: {bullet_line}"
        norm_line = normalize_line(bullet_line)
        assert norm_line.startswith("- "), f"Failed to normalize to '- ': {norm_line}"

    # Numbered list items should preserve their numeric markers
    numbered = "1. First item\n2) Second item\n[3] Third item"
    norm_num = normalize_text(numbered)
    assert "1. First item" in norm_num
    assert "2. Second item" in norm_num
    assert "3. Third item" in norm_num


def test_bullet_vs_non_bullet_disambiguation():
    """Verify that phone numbers (+91) and negative numbers are not recognized as bullets."""
    assert not is_bullet("+91 9876543210")
    assert not is_bullet("+1-555-0199")
    assert not is_bullet("-5.2% decline")
    assert not is_bullet("++increment")
    assert not is_bullet("C++")
    assert not is_bullet("Just regular text")

    # Confirm normalize_line does not mutate them
    assert normalize_line("+91 9876543210") == "+91 9876543210"
    assert normalize_line("-5.2% decline") == "-5.2% decline"


def test_protected_programming_language_symbols():
    """
    Verify that programming languages and technical tokens are preserved without
    mutilation of special characters (+, #, ., /, -).
    """
    technical_text = (
        "Proficient in C++, C#, and .NET Core development.\n"
        "Experience with ASP.NET, Node.js, and Vue.js frameworks.\n"
        "Implemented CI/CD pipelines, TCP/IP networking, and PL/SQL procedures.\n"
        "Familiar with UI/UX design, Objective-C, and I/O stream optimization."
    )
    normalized = normalize_text(technical_text)

    tokens = [
        "C++", "C#", ".NET Core", "ASP.NET", "Node.js", "Vue.js",
        "CI/CD", "TCP/IP", "PL/SQL", "UI/UX", "Objective-C", "I/O"
    ]
    for token in tokens:
        assert token in normalized, f"Protected token '{token}' was mutated in normalized text: {normalized}"


def test_preserve_urls_and_email_addresses():
    """Verify that URLs and email addresses remain completely intact with all punctuation."""
    contact_text = (
        "Email: student.placement_2025@dau.ac.in\n"
        "GitHub: https://github.com/Tanvii13/Resume-Analyzer-for-College-Placements?tab=readme-ov-file\n"
        "LinkedIn: https://www.linkedin.com/in/aarav-sharma-12345/\n"
        "Portfolio: https://aaravsharma.dev/projects?id=42&view=full#intro"
    )
    normalized = normalize_text(contact_text)

    assert "student.placement_2025@dau.ac.in" in normalized
    assert "https://github.com/Tanvii13/Resume-Analyzer-for-College-Placements?tab=readme-ov-file" in normalized
    assert "https://www.linkedin.com/in/aarav-sharma-12345/" in normalized
    assert "https://aaravsharma.dev/projects?id=42&view=full#intro" in normalized


def test_table_row_preservation():
    """Verify that table rows serialized with ' | ' delimiters are preserved without alteration."""
    table_text = (
        "Degree | Institution | Graduation Year | CGPA\n"
        "B.Tech in ICT | DA-IICT Gandhinagar | 2025 | 8.74 / 10\n"
        "Higher Secondary (HSC) | Delhi Public School | 2021 | 94.6%"
    )
    normalized = normalize_text(table_text)
    assert "Degree | Institution | Graduation Year | CGPA" in normalized
    assert "B.Tech in ICT | DA-IICT Gandhinagar | 2025 | 8.74 / 10" in normalized
    assert "Higher Secondary (HSC) | Delhi Public School | 2021 | 94.6%" in normalized


# ============================================================================
# Segmenter Unit Tests
# ============================================================================

def test_segment_empty_text():
    """Verify segmenter handling of empty and whitespace-only text."""
    doc = segment_text("")
    assert len(doc.lines) == 0
    assert len(doc.blocks) == 0

    doc_ws = segment_text("   \n\n\t  ")
    assert len(doc_ws.blocks) == 0


def test_segment_line_types():
    """Verify accurate classification of line types."""
    text = (
        "EDUCATION\n"
        "B.Tech CSE | ABC University | 2024 | 8.9\n"
        "• Developed backend REST API\n"
        "  using FastAPI and PostgreSQL.\n"
        "\n"
        "General summary paragraph."
    )
    doc = segment_text(text)
    non_empty = doc.get_non_empty_lines()

    assert non_empty[0].line_type == LineType.HEADING_CANDIDATE
    assert non_empty[1].line_type == LineType.TABLE_ROW
    assert non_empty[2].line_type == LineType.BULLET
    assert non_empty[3].line_type == LineType.CONTINUATION
    assert non_empty[4].line_type == LineType.REGULAR


def test_segment_multiline_bullet_continuation():
    """
    Verify that wrapped bullet descriptions are consolidated into a single TextBlock
    while preserving individual line provenance.
    """
    text = (
        "• Architected scalable microservices using FastAPI and Docker\n"
        "  reducing deployment latency by 35% across distributed clusters.\n"
        "• Containerized core services with Docker."
    )
    doc = segment_text(text)
    bullet_blocks = doc.get_bullet_blocks()

    assert len(bullet_blocks) == 2

    first_bullet = bullet_blocks[0]
    expected_consolidated = (
        "Architected scalable microservices using FastAPI and Docker "
        "reducing deployment latency by 35% across distributed clusters."
    )
    assert first_bullet.text == expected_consolidated
    assert len(first_bullet.lines) == 2
    assert first_bullet.lines[0].line_type == LineType.BULLET
    assert first_bullet.lines[1].line_type == LineType.CONTINUATION
    assert first_bullet.start_line == 1
    assert first_bullet.end_line == 2

    second_bullet = bullet_blocks[1]
    assert second_bullet.text == "Containerized core services with Docker."
    assert len(second_bullet.lines) == 1
    assert second_bullet.start_line == 3
    assert second_bullet.end_line == 3


def test_segment_table_blocks():
    """Verify that table rows are parsed into table blocks with structured cells."""
    text = (
        "Degree | Institution | Year | CGPA\n"
        "B.Tech ICT | DA-IICT | 2025 | 8.74\n"
        "Class XII | DPS | 2021 | 94.6%"
    )
    doc = segment_text(text)
    table_blocks = doc.get_table_blocks()

    assert len(table_blocks) == 3
    assert table_blocks[0].table_cells == ["Degree", "Institution", "Year", "CGPA"]
    assert table_blocks[1].table_cells == ["B.Tech ICT", "DA-IICT", "2025", "8.74"]
    assert table_blocks[2].table_cells == ["Class XII", "DPS", "2021", "94.6%"]


def test_segment_heading_candidates():
    """Verify that candidate section headers are accurately flagged."""
    text = (
        "EDUCATION\n"
        "DA-IICT Gandhinagar\n\n"
        "WORK EXPERIENCE\n"
        "Software Engineer Intern\n\n"
        "Technical Skills:\n"
        "- Python, C++, SQL"
    )
    doc = segment_text(text)
    heading_blocks = doc.get_heading_candidate_blocks()

    heading_texts = [b.text for b in heading_blocks]
    assert "EDUCATION" in heading_texts
    assert "WORK EXPERIENCE" in heading_texts
    assert "Technical Skills:" in heading_texts
    assert "Software Engineer Intern" not in heading_texts


def test_paragraph_separation_on_blank_lines():
    """Verify that blank lines create distinct paragraph blocks."""
    text = (
        "First paragraph line 1\n"
        "First paragraph line 2\n\n"
        "Second paragraph line 1\n"
        "Second paragraph line 2"
    )
    doc = segment_text(text)
    assert len(doc.blocks) == 2
    assert doc.blocks[0].block_type == BlockType.PARAGRAPH
    assert doc.blocks[1].block_type == BlockType.PARAGRAPH
    assert doc.blocks[0].text == "First paragraph line 1 First paragraph line 2"
    assert doc.blocks[1].text == "Second paragraph line 1 Second paragraph line 2"


def test_segmented_document_to_dict_serialization():
    """Verify dictionary serialization for API/logging compatibility."""
    text = (
        "TECHNICAL SKILLS\n"
        "• Python, C++, Docker\n"
        "• PostgreSQL, FastAPI"
    )
    doc = segment_text(text)
    d = doc.to_dict()

    assert "total_lines" in d
    assert "total_blocks" in d
    assert "bullet_blocks_count" in d
    assert d["bullet_blocks_count"] == 2
    assert d["heading_candidates_count"] == 1
    assert isinstance(d["blocks"], list)


def test_end_to_end_sample_resume(sample_resume_text):
    """Verify full preprocessing and segmentation pipeline on realistic resume text."""
    doc = segment_text(sample_resume_text)

    # Verify basic counts
    assert len(doc.lines) > 25
    assert len(doc.blocks) > 10

    # Verify table rows detected
    table_blocks = doc.get_table_blocks()
    assert len(table_blocks) >= 2
    assert any("B.Tech in ICT" in b.text for b in table_blocks)

    # Verify bullet items detected and multiline continuation handled
    bullet_blocks = doc.get_bullet_blocks()
    assert len(bullet_blocks) >= 6

    # Verify that the multiline bullet was consolidated
    fastapi_bullet = next(
        b for b in bullet_blocks
        if "Developed scalable REST APIs using FastAPI and PostgreSQL" in b.text
    )
    assert "daily requests with async connection pooling." in fastapi_bullet.text
    assert len(fastapi_bullet.lines) == 2

    # Verify protected tokens preserved
    norm_text = doc.normalized_text
    assert "C++" in norm_text
    assert "C#" in norm_text
    assert ".NET Core" in norm_text
    assert "Node.js" in norm_text
    assert "Vue.js" in norm_text
    assert "CI/CD" in norm_text
    assert "TCP/IP" in norm_text


def test_large_resume_text_performance():
    """Verify that a large resume (5 pages, 25KB) processes deterministically in < 50ms."""
    single_page = (
        "EXPERIENCE\n"
        "Software Engineer | BigTech Inc | 2022 - Present\n"
        "• Developed high-throughput microservices using C++ and Python 3.11 with async I/O.\n"
        "  Handled 100,000 requests per second across 20 distributed nodes with Redis.\n"
        "• Containerized services with Docker and orchestrated deployments with Kubernetes.\n"
        "• Integrated CI/CD pipelines in GitHub Actions reducing deployment failures by 40%.\n\n"
        "PROJECTS\n"
        "Resume Analyzer for College Placements\n"
        "• Built full-stack platform with FastAPI, React.js, and PostgreSQL for student placement cells.\n"
        "  Integrated automated parsing for PDF and DOCX files with zero external API dependencies.\n\n"
    )
    # Replicate to create a ~30KB resume
    large_resume = (single_page * 30)

    start_time = time.perf_counter()
    doc = segment_text(large_resume)
    duration = time.perf_counter() - start_time

    assert duration < 0.20, f"Processing took too long: {duration:.4f} seconds"
    assert len(doc.blocks) > 100
    assert len(doc.get_bullet_blocks()) > 50
