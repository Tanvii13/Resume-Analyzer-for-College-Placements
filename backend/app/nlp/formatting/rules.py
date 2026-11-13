"""
Deterministic rule implementations for Sprint 3 Module B: Formatting Quality Analyzer.

Provides four specialized checkers:
- SectionStructureChecker: Heading presence, casing consistency, boundaries, order.
- TextReadabilityChecker: Paragraph length, blank lines, whitespace, fragmentation.
- BulletStructureChecker: Bullet markers, empty bullets, length, duplication.
- ResumeConsistencyChecker: Date representations, punctuation, entry structure.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from app.nlp.preprocessing import (
    BlockType,
    LineType,
    SegmentedDocument,
    TextBlock,
    TextLine,
)
from app.nlp.schemas import CandidateProfile
from app.nlp.sections import (
    ClassifiedSection,
    SectionMap,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_INTERNSHIPS,
    SECTION_PERSONAL_INFO,
    SECTION_PROJECTS,
    SECTION_TECHNICAL_SKILLS,
)
from app.nlp.formatting.schemas import (
    FindingSeverity,
    FormattingCategory,
    FormattingFinding,
)

# Standard critical placement sections
CRITICAL_SECTIONS = [
    (SECTION_EDUCATION, "Education"),
    (SECTION_TECHNICAL_SKILLS, "Technical Skills"),
    (SECTION_PROJECTS, "Projects"),
]


# =============================================================================
# 1. Section Structure Checker
# =============================================================================
class SectionStructureChecker:
    """Evaluates section headings, casing consistency, boundaries, and logical sequence."""

    def check(
        self,
        doc: SegmentedDocument,
        section_map: SectionMap,
        profile: Optional[CandidateProfile] = None,
    ) -> Tuple[List[FormattingFinding], List[str]]:
        findings: List[FormattingFinding] = []
        strengths: List[str] = []

        identified_sections = section_map.sections
        identified_names = [sec.canonical_name for sec in identified_sections]

        # ---------------------------------------------------------------------
        # 1.1 Missing Critical Section Headings
        # ---------------------------------------------------------------------
        missing_critical: List[str] = []
        for canonical, display_name in CRITICAL_SECTIONS:
            has_sec = canonical in identified_names
            # If profile is supplied, also check if section was extracted
            if profile and not has_sec:
                if canonical == SECTION_EDUCATION and profile.education:
                    has_sec = True
                elif canonical == SECTION_TECHNICAL_SKILLS and profile.technical_skills:
                    has_sec = True
                elif canonical == SECTION_PROJECTS and profile.projects:
                    has_sec = True

            if not has_sec:
                missing_critical.append(display_name)

        if missing_critical:
            severity = (
                FindingSeverity.CRITICAL
                if len(missing_critical) >= 2
                else FindingSeverity.WARNING
            )
            findings.append(
                FormattingFinding(
                    issue_id="FMT_MISSING_SECTION_HEADING",
                    category=FormattingCategory.SECTION_STRUCTURE,
                    title="Missing Standard Section Headings",
                    description=(
                        f"Could not identify clear headings for: {', '.join(missing_critical)}. "
                        "Campus ATS systems rely on standard headers to categorize candidate qualifications."
                    ),
                    severity=severity,
                    confidence=0.95,
                    evidence=f"Missing sections: {', '.join(missing_critical)}",
                    affected_section=missing_critical[0].lower().replace(" ", "_"),
                    detection_rule="check_critical_section_headings",
                )
            )

        # ---------------------------------------------------------------------
        # 1.2 Inconsistent Section Heading Styles & Casing
        # ---------------------------------------------------------------------
        headings_with_lines: List[Tuple[str, int]] = []
        for sec in identified_sections:
            if sec.original_heading and sec.original_heading.strip():
                clean_heading = sec.original_heading.strip()
                line_no = sec.heading_line_number or (sec.start_line if sec.start_line > 0 else 1)
                headings_with_lines.append((clean_heading, line_no))

        if len(headings_with_lines) >= 3:
            upper_count = 0
            title_count = 0
            other_count = 0
            colon_count = 0

            for h_text, _ in headings_with_lines:
                # Disregard numbers or punctuation for casing check
                alpha_chars = [c for c in h_text if c.isalpha()]
                if alpha_chars:
                    if all(c.isupper() for c in alpha_chars):
                        upper_count += 1
                    elif h_text.istitle() or (h_text[0].isupper() and any(c.islower() for c in alpha_chars)):
                        title_count += 1
                    else:
                        other_count += 1

                if h_text.endswith(":"):
                    colon_count += 1

            total_h = len(headings_with_lines)
            # Mixed casing check (e.g. some ALL CAPS and some Title Case)
            if upper_count > 0 and title_count > 0 and min(upper_count, title_count) >= 1:
                findings.append(
                    FormattingFinding(
                        issue_id="FMT_INCONSISTENT_HEADING_CASING",
                        category=FormattingCategory.SECTION_STRUCTURE,
                        title="Inconsistent Heading Capitalization",
                        description=(
                            "Section headings mix uppercase and title case styles. "
                            "Choose one consistent styling across all section headers (e.g. ALL CAPS or Title Case)."
                        ),
                        severity=FindingSeverity.WARNING,
                        confidence=0.92,
                        evidence=(
                            f"Detected {upper_count} uppercase heading(s) and {title_count} title case heading(s) "
                            f"(e.g. '{headings_with_lines[0][0]}' vs '{headings_with_lines[1][0]}')."
                        ),
                        line_reference=headings_with_lines[0][1],
                        detection_rule="check_heading_casing_consistency",
                    )
                )
            elif (upper_count == total_h) or (title_count == total_h):
                strengths.append("Uniform section heading capitalization maintained throughout the resume.")

            # Inconsistent trailing punctuation in headings (e.g., some end with ':' and some don't)
            if 0 < colon_count < total_h:
                findings.append(
                    FormattingFinding(
                        issue_id="FMT_INCONSISTENT_HEADING_PUNCTUATION",
                        category=FormattingCategory.SECTION_STRUCTURE,
                        title="Inconsistent Heading Punctuation",
                        description="Some section headings end with a colon ':' while others do not. Standardize heading punctuation.",
                        severity=FindingSeverity.INFO,
                        confidence=0.88,
                        evidence=f"{colon_count} of {total_h} headings use trailing colons.",
                        line_reference=headings_with_lines[0][1],
                        detection_rule="check_heading_punctuation_consistency",
                    )
                )

        # ---------------------------------------------------------------------
        # 1.3 Repeated Section Headings
        # ---------------------------------------------------------------------
        seen_canonical: Dict[str, List[int]] = {}
        for sec in identified_sections:
            if sec.canonical_name not in seen_canonical:
                seen_canonical[sec.canonical_name] = []
            if sec.heading_line_number:
                seen_canonical[sec.canonical_name].append(sec.heading_line_number)

        for c_name, line_nums in seen_canonical.items():
            if len(line_nums) > 1 and c_name in (
                SECTION_EXPERIENCE,
                SECTION_PROJECTS,
                SECTION_EDUCATION,
                SECTION_TECHNICAL_SKILLS,
            ):
                findings.append(
                    FormattingFinding(
                        issue_id="FMT_REPEATED_SECTION_HEADING",
                        category=FormattingCategory.SECTION_STRUCTURE,
                        title="Repeated Section Heading",
                        description=(
                            f"Section '{c_name.replace('_', ' ').title()}' appears multiple times. "
                            "Consolidate related items into a single unified section for clarity."
                        ),
                        severity=FindingSeverity.WARNING,
                        confidence=0.95,
                        evidence=f"Heading repeated at lines: {', '.join(map(str, line_nums))}",
                        line_reference=line_nums[1],
                        affected_section=c_name,
                        detection_rule="check_repeated_section_headings",
                    )
                )

        # ---------------------------------------------------------------------
        # 1.4 Poor Section Organization (Contact Buried at Bottom)
        # ---------------------------------------------------------------------
        if SECTION_PERSONAL_INFO in identified_names:
            contact_idx = identified_names.index(SECTION_PERSONAL_INFO)
            # If contact section appears after experience, projects, or education
            core_indices = [
                identified_names.index(name)
                for name in (SECTION_EDUCATION, SECTION_EXPERIENCE, SECTION_PROJECTS)
                if name in identified_names
            ]
            if core_indices and contact_idx > max(core_indices):
                findings.append(
                    FormattingFinding(
                        issue_id="FMT_POOR_SECTION_ORDER",
                        category=FormattingCategory.SECTION_STRUCTURE,
                        title="Contact Information Placed at Bottom",
                        description="Personal and contact information appears after major qualification sections. Place contact details at the very top.",
                        severity=FindingSeverity.WARNING,
                        confidence=0.90,
                        evidence=f"Contact section position: #{contact_idx + 1} of {len(identified_names)} sections",
                        affected_section=SECTION_PERSONAL_INFO,
                        detection_rule="check_section_order",
                    )
                )
            elif contact_idx == 0:
                strengths.append("Logical section flow: Contact details lead the document.")

        if len(identified_sections) >= 4 and not missing_critical:
            strengths.append(f"Clear document structure with {len(identified_sections)} identifiable standard sections.")

        return findings, strengths


# =============================================================================
# 2. Text Readability Checker
# =============================================================================
class TextReadabilityChecker:
    """Evaluates paragraph density, excessive blank lines, whitespace, and text fragmentation."""

    def check(
        self,
        doc: SegmentedDocument,
        raw_text: str,
    ) -> Tuple[List[FormattingFinding], List[str]]:
        findings: List[FormattingFinding] = []
        strengths: List[str] = []

        # ---------------------------------------------------------------------
        # 2.1 Unsegmented Wall of Text (>150 continuous words without breaks)
        # ---------------------------------------------------------------------
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
        wall_of_text_found = False

        for p in paragraphs:
            # Check if this paragraph has no bullet points and is massive
            words = p.split()
            if len(words) > 140:
                wall_of_text_found = True
                findings.append(
                    FormattingFinding(
                        issue_id="FMT_UNSEGMENTED_WALL_OF_TEXT",
                        category=FormattingCategory.TEXT_READABILITY,
                        title="Unsegmented Wall of Text",
                        description=(
                            f"Detected a dense block of text with {len(words)} continuous words. "
                            "Recruiters scan in 6 seconds; dense text reduces readability. Break into bullet items."
                        ),
                        severity=FindingSeverity.CRITICAL,
                        confidence=0.95,
                        evidence=f"Text excerpt ({len(words)} words): '{' '.join(words[:12])}...'",
                        detection_rule="check_unsegmented_text_blocks",
                    )
                )
                break

        # ---------------------------------------------------------------------
        # 2.2 Excessively Long Paragraphs (>90 words in a single paragraph block)
        # ---------------------------------------------------------------------
        if not wall_of_text_found:
            for block in doc.blocks:
                if block.block_type == BlockType.PARAGRAPH:
                    words = block.text.split()
                    if len(words) > 90:
                        findings.append(
                            FormattingFinding(
                                issue_id="FMT_LONG_PARAGRAPH",
                                category=FormattingCategory.TEXT_READABILITY,
                                title="Excessively Long Paragraph",
                                description=(
                                    f"Paragraph contains {len(words)} words. "
                                    "Consider breaking lengthy prose into bullet points or 2-3 sentence blocks."
                                ),
                                severity=FindingSeverity.WARNING,
                                confidence=0.90,
                                evidence=f"Paragraph starting at line {block.start_line}: '{' '.join(words[:10])}...'",
                                line_reference=block.start_line,
                                detection_rule="check_long_paragraphs",
                            )
                        )
                        break

        # ---------------------------------------------------------------------
        # 2.3 Excessive Blank Lines (>= 3 consecutive empty lines)
        # ---------------------------------------------------------------------
        blank_streak = 0
        max_empty_streak = 0
        streak_start_line = None

        # Check raw_text directly to detect original un-normalized blank line clusters
        for idx, l in enumerate(raw_text.splitlines(), start=1):
            if not l.strip():
                blank_streak += 1
                if blank_streak > max_empty_streak:
                    max_empty_streak = blank_streak
                    streak_start_line = idx - blank_streak + 1
            else:
                blank_streak = 0

        if max_empty_streak >= 3:
            findings.append(
                FormattingFinding(
                    issue_id="FMT_EXCESSIVE_BLANK_LINES",
                    category=FormattingCategory.TEXT_READABILITY,
                    title="Excessive Blank Lines",
                    description=(
                        f"Detected {max_empty_streak} consecutive blank lines. "
                        "Excessive vertical whitespace reduces page density and may cause unwarranted page spillover."
                    ),
                    severity=FindingSeverity.WARNING,
                    confidence=1.0,
                    evidence=f"{max_empty_streak} consecutive blank lines near line {streak_start_line}.",
                    line_reference=streak_start_line,
                    detection_rule="check_blank_line_clustering",
                )
            )
        elif max_empty_streak <= 1:
            strengths.append("Optimal vertical spacing without disruptive blank line clusters.")

        # ---------------------------------------------------------------------
        # 2.4 Irregular Inline Whitespace (>= 4 consecutive spaces inside text)
        # ---------------------------------------------------------------------
        irregular_ws_count = 0
        sample_ws_line = None

        for line in doc.lines:
            if line.line_type not in (LineType.EMPTY, LineType.TABLE_ROW):
                # Search for 4+ spaces inside text that is NOT a table line
                if re.search(r"\S\s{4,}\S", line.raw_text):
                    irregular_ws_count += 1
                    if not sample_ws_line:
                        sample_ws_line = line.line_number

        if irregular_ws_count >= 3:
            findings.append(
                FormattingFinding(
                    issue_id="FMT_IRREGULAR_WHITESPACE",
                    category=FormattingCategory.TEXT_READABILITY,
                    title="Irregular Inline Whitespace",
                    description=(
                        f"Found {irregular_ws_count} lines with irregular space sequences (4+ consecutive spaces). "
                        "Use clean tab stops or standard separators rather than multiple manual spacebar presses."
                    ),
                    severity=FindingSeverity.INFO,
                    confidence=0.85,
                    evidence=f"{irregular_ws_count} lines affected; first detected at line {sample_ws_line}.",
                    line_reference=sample_ws_line,
                    detection_rule="check_irregular_whitespace",
                )
            )

        # ---------------------------------------------------------------------
        # 2.5 Fragmented Dangling Blocks (1-2 words on an isolated line)
        # ---------------------------------------------------------------------
        dangling_count = 0
        first_dangling_line = None

        for block in doc.blocks:
            if block.block_type == BlockType.PARAGRAPH:
                words = block.text.split()
                # 1-2 words that are not contact details, not headings, not labels
                if 1 <= len(words) <= 2:
                    text_lower = block.text.lower().strip()
                    if not (
                        "@" in text_lower
                        or "http" in text_lower
                        or ":" in text_lower
                        or text_lower in ("github", "linkedin", "portfolio", "leetcode", "codeforces")
                    ):
                        dangling_count += 1
                        if not first_dangling_line:
                            first_dangling_line = block.start_line

        if dangling_count >= 3:
            findings.append(
                FormattingFinding(
                    issue_id="FMT_FRAGMENTED_TEXT_BLOCKS",
                    category=FormattingCategory.TEXT_READABILITY,
                    title="Fragmented Text Blocks",
                    description=(
                        f"Detected {dangling_count} isolated 1-2 word text lines. "
                        "These often stem from premature line wraps or broken column extraction."
                    ),
                    severity=FindingSeverity.INFO,
                    confidence=0.75,
                    evidence=f"{dangling_count} fragmented blocks found (first at line {first_dangling_line}).",
                    line_reference=first_dangling_line,
                    detection_rule="check_dangling_fragments",
                )
            )

        if not findings:
            strengths.append("High text readability with balanced paragraph lengths and clean segmentation.")

        return findings, strengths


# =============================================================================
# 3. Bullet Structure Checker
# =============================================================================
class BulletStructureChecker:
    """Evaluates bullet point consistency, length, empty bullets, and duplicated entries."""

    def check(
        self,
        doc: SegmentedDocument,
        section_map: SectionMap,
        raw_text: str = "",
    ) -> Tuple[List[FormattingFinding], List[str]]:
        findings: List[FormattingFinding] = []
        strengths: List[str] = []

        bullet_blocks = doc.get_bullet_blocks()
        bullet_lines = [line for line in doc.lines if line.line_type == LineType.BULLET]

        # ---------------------------------------------------------------------
        # 3.1 Inconsistent Bullet Markers & Empty Bullets
        # ---------------------------------------------------------------------
        # Inspect raw lines so un-normalized markers (•, -, *, etc.) are visible
        raw_lines = raw_text.splitlines() if raw_text else [line.raw_text for line in doc.lines]
        bullet_re = re.compile(r"^\s*([•●○▪■□\-\*\+>»])(?:\s|$)")
        markers_used: Set[str] = set()
        empty_bullet_line: Optional[int] = None

        for idx, r_line in enumerate(raw_lines, start=1):
            m = bullet_re.match(r_line)
            if m:
                marker_char = m.group(1)
                markers_used.add(marker_char)
                rest = r_line[m.end():].strip()
                if not rest and empty_bullet_line is None:
                    empty_bullet_line = idx

        # Fallback to line.bullet_marker if markers_used is empty
        if not markers_used:
            for line in bullet_lines:
                if line.bullet_marker:
                    clean_marker = line.bullet_marker.strip()
                    if clean_marker:
                        markers_used.add(clean_marker)

        # Normalize markers into families: dash ('-', '–', '—'), bullet ('•', '●', '▪'), asterisk ('*')
        marker_families: Set[str] = set()
        for m in markers_used:
            if m in ("-", "–", "—"):
                marker_families.add("hyphen/dash")
            elif m in ("*", "+"):
                marker_families.add("asterisk/plus")
            elif m in ("•", "●", "○", "▪", "■", "□"):
                marker_families.add("bullet symbol")
            elif m in (">", "»"):
                marker_families.add("arrow")
            else:
                marker_families.add(f"custom '{m}'")

        if len(marker_families) > 1 and (len(bullet_lines) >= 3 or len(raw_lines) >= 3):
            findings.append(
                FormattingFinding(
                    issue_id="FMT_INCONSISTENT_BULLET_MARKERS",
                    category=FormattingCategory.BULLET_STRUCTURE,
                    title="Inconsistent Bullet Markers",
                    description=(
                        f"Mixed bullet marker styles detected ({', '.join(sorted(marker_families))}). "
                        "Standardize on a single bullet marker style throughout the document."
                    ),
                    severity=FindingSeverity.WARNING,
                    confidence=0.95,
                    evidence=f"Different bullet symbols found: {', '.join(sorted(markers_used))}",
                    detection_rule="check_bullet_marker_consistency",
                )
            )
        elif len(marker_families) == 1 and len(bullet_lines) >= 3:
            strengths.append(f"Consistent bullet marker style ({list(marker_families)[0]}) used uniformly.")

        # ---------------------------------------------------------------------
        # 3.2 Empty Bullet Points
        # ---------------------------------------------------------------------
        if empty_bullet_line is not None:
            findings.append(
                FormattingFinding(
                    issue_id="FMT_EMPTY_BULLET_POINT",
                    category=FormattingCategory.BULLET_STRUCTURE,
                    title="Empty Bullet Point",
                    description="Detected an empty bullet marker with no accompanying text.",
                    severity=FindingSeverity.WARNING,
                    confidence=1.0,
                    evidence=f"Empty bullet marker at line {empty_bullet_line}.",
                    line_reference=empty_bullet_line,
                    detection_rule="check_empty_bullets",
                )
            )
        else:
            for line in bullet_lines:
                content_after_marker = line.text.strip()
                # If line is just the bullet marker itself
                if not content_after_marker or content_after_marker == line.bullet_marker:
                    findings.append(
                        FormattingFinding(
                            issue_id="FMT_EMPTY_BULLET_POINT",
                            category=FormattingCategory.BULLET_STRUCTURE,
                            title="Empty Bullet Point",
                            description="Detected an empty bullet marker with no accompanying text.",
                            severity=FindingSeverity.WARNING,
                            confidence=1.0,
                            evidence=f"Empty bullet at line {line.line_number}: '{line.raw_text}'",
                            line_reference=line.line_number,
                            detection_rule="check_empty_bullets",
                        )
                    )
                    break  # Flag one instance per document

        # ---------------------------------------------------------------------
        # 3.3 Extremely Long Bullet Points (>60 words)
        # ---------------------------------------------------------------------
        long_bullet_count = 0
        first_long_bullet_line = None
        max_bullet_len = 0

        for block in bullet_blocks:
            word_count = len(block.text.split())
            if word_count > 60:
                long_bullet_count += 1
                if word_count > max_bullet_len:
                    max_bullet_len = word_count
                    first_long_bullet_line = block.start_line

        if long_bullet_count > 0:
            findings.append(
                FormattingFinding(
                    issue_id="FMT_EXCESSIVE_BULLET_LENGTH",
                    category=FormattingCategory.BULLET_STRUCTURE,
                    title="Overly Long Bullet Points",
                    description=(
                        f"Found {long_bullet_count} bullet item(s) exceeding 60 words (longest has {max_bullet_len} words). "
                        "Effective resume bullets should be concise, ideally 15 to 35 words."
                    ),
                    severity=FindingSeverity.WARNING,
                    confidence=0.92,
                    evidence=f"Long bullet item at line {first_long_bullet_line} contains {max_bullet_len} words.",
                    line_reference=first_long_bullet_line,
                    detection_rule="check_bullet_length",
                )
            )
        elif len(bullet_blocks) >= 4:
            strengths.append("Concise, scannable bullet points adhering to recommended word count guidelines.")

        # ---------------------------------------------------------------------
        # 3.4 Repeated or Duplicated Bullet Content
        # ---------------------------------------------------------------------
        seen_bullet_texts: Dict[str, int] = {}
        duplicate_text_sample = None
        duplicate_line = None

        for block in bullet_blocks:
            norm_b = " ".join(block.text.lower().split())
            if len(norm_b) > 20:  # Only check substantial bullets
                if norm_b in seen_bullet_texts:
                    duplicate_text_sample = block.text
                    duplicate_line = block.start_line
                    break
                seen_bullet_texts[norm_b] = block.start_line

        if duplicate_text_sample:
            findings.append(
                FormattingFinding(
                    issue_id="FMT_DUPLICATE_BULLET_CONTENT",
                    category=FormattingCategory.BULLET_STRUCTURE,
                    title="Duplicate Bullet Content",
                    description="Identical bullet text repeated in multiple places. Ensure each bullet communicates unique impact.",
                    severity=FindingSeverity.WARNING,
                    confidence=0.98,
                    evidence=f"Duplicate bullet near line {duplicate_line}: '{duplicate_text_sample[:60]}...'",
                    line_reference=duplicate_line,
                    detection_rule="check_duplicate_bullets",
                )
            )

        # ---------------------------------------------------------------------
        # 3.5 Unstructured Paragraphs in Projects or Experience
        # ---------------------------------------------------------------------
        for sec_name in (SECTION_PROJECTS, SECTION_EXPERIENCE, SECTION_INTERNSHIPS):
            sec = section_map.get_section(sec_name)
            if sec and sec.blocks:
                sec_paragraphs = [b for b in sec.blocks if b.block_type == BlockType.PARAGRAPH and len(b.text.split()) > 15]
                sec_bullets = [b for b in sec.blocks if b.is_bullet]
                if len(sec_paragraphs) >= 2 and len(sec_bullets) == 0:
                    findings.append(
                        FormattingFinding(
                            issue_id="FMT_UNSTRUCTURED_SECTION_DESCRIPTIONS",
                            category=FormattingCategory.BULLET_STRUCTURE,
                            title=f"Unstructured Paragraphs in {sec_name.title()}",
                            description=(
                                f"Section '{sec_name.title()}' uses continuous narrative paragraphs instead of bullet points. "
                                "Recruiters and ATS favor bulleted accomplishment statements."
                            ),
                            severity=FindingSeverity.WARNING,
                            confidence=0.90,
                            evidence=f"{len(sec_paragraphs)} paragraphs found with 0 bullet points.",
                            affected_section=sec_name,
                            detection_rule="check_unstructured_section_descriptions",
                        )
                    )

        return findings, strengths


# =============================================================================
# 4. Resume Consistency Checker
# =============================================================================
class ResumeConsistencyChecker:
    """Evaluates date formatting uniformity, punctuation habits, and entry structure."""

    # Common date representation patterns
    _MONTH_NAME_DATE = re.compile(
        r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}\b",
        re.IGNORECASE,
    )
    _NUMERIC_SLASH_DATE = re.compile(r"\b\d{1,2}/\d{2,4}\b")
    _NUMERIC_DASH_DATE = re.compile(r"\b\d{4}-\d{2}\b")
    _APOSTROPHE_DATE = re.compile(
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)['’]\s*\d{2}\b",
        re.IGNORECASE,
    )

    def check(
        self,
        doc: SegmentedDocument,
        raw_text: str,
        profile: Optional[CandidateProfile] = None,
    ) -> Tuple[List[FormattingFinding], List[str]]:
        findings: List[FormattingFinding] = []
        strengths: List[str] = []

        # ---------------------------------------------------------------------
        # 4.1 Inconsistent Date Representations
        # ---------------------------------------------------------------------
        has_month_name = bool(self._MONTH_NAME_DATE.search(raw_text))
        has_slash_numeric = bool(self._NUMERIC_SLASH_DATE.search(raw_text))
        has_dash_numeric = bool(self._NUMERIC_DASH_DATE.search(raw_text))
        has_apostrophe = bool(self._APOSTROPHE_DATE.search(raw_text))

        detected_date_styles = []
        if has_month_name:
            detected_date_styles.append("Month Name (e.g. 'May 2024')")
        if has_slash_numeric:
            detected_date_styles.append("Numeric Slash (e.g. '05/2024')")
        if has_dash_numeric:
            detected_date_styles.append("Numeric Dash (e.g. '2024-05')")
        if has_apostrophe:
            detected_date_styles.append("Apostrophe Short (e.g. 'May\\'24')")

        if len(detected_date_styles) >= 2:
            findings.append(
                FormattingFinding(
                    issue_id="FMT_INCONSISTENT_DATE_FORMATS",
                    category=FormattingCategory.RESUME_CONSISTENCY,
                    title="Inconsistent Date Representations",
                    description=(
                        f"Detected multiple competing date conventions: {', '.join(detected_date_styles)}. "
                        "Maintain a single, consistent date format throughout all timeline entries."
                    ),
                    severity=FindingSeverity.WARNING,
                    confidence=0.88,
                    evidence=f"Mixed date patterns: {', '.join(detected_date_styles)}",
                    detection_rule="check_date_formatting_consistency",
                )
            )
        elif len(detected_date_styles) == 1:
            strengths.append(f"Consistent date formatting ({detected_date_styles[0]}) used throughout.")

        # ---------------------------------------------------------------------
        # 4.2 Inconsistent Terminal Punctuation in Bullet Points
        # ---------------------------------------------------------------------
        bullet_lines = [
            line for line in doc.lines
            if line.line_type == LineType.BULLET and len(line.text.split()) >= 4
        ]

        if len(bullet_lines) >= 4:
            with_period = sum(1 for line in bullet_lines if line.text.strip().endswith("."))
            without_period = len(bullet_lines) - with_period

            # If both styles are significantly represented (e.g. both >= 25%)
            if with_period >= 2 and without_period >= 2:
                findings.append(
                    FormattingFinding(
                        issue_id="FMT_INCONSISTENT_BULLET_PUNCTUATION",
                        category=FormattingCategory.RESUME_CONSISTENCY,
                        title="Inconsistent Bullet Punctuation",
                        description=(
                            f"Mixed bullet terminal punctuation detected ({with_period} end with a period, "
                            f"{without_period} do not). Choose either periods or no periods consistently."
                        ),
                        severity=FindingSeverity.INFO,
                        confidence=0.90,
                        evidence=f"{with_period} with period vs {without_period} without period.",
                        detection_rule="check_bullet_punctuation_consistency",
                    )
                )
            else:
                strengths.append("Consistent terminal punctuation maintained across bullet points.")

        # ---------------------------------------------------------------------
        # 4.3 Inconsistent Inline Delimiters
        # ---------------------------------------------------------------------
        pipe_count = raw_text.count(" | ")
        bullet_sep_count = raw_text.count(" • ")
        tilde_sep_count = raw_text.count(" ~ ")

        active_separators = []
        if pipe_count >= 2:
            active_separators.append("pipe (' | ')")
        if bullet_sep_count >= 2:
            active_separators.append("bullet (' • ')")
        if tilde_sep_count >= 2:
            active_separators.append("tilde (' ~ ')")

        if len(active_separators) >= 2:
            findings.append(
                FormattingFinding(
                    issue_id="FMT_INCONSISTENT_INLINE_DELIMITERS",
                    category=FormattingCategory.RESUME_CONSISTENCY,
                    title="Mixed Inline Separators",
                    description=(
                        f"Detected multiple inline delimiter conventions ({', '.join(active_separators)}). "
                        "Stick to one delimiter (e.g. ' | ') for header and skill list separation."
                    ),
                    severity=FindingSeverity.INFO,
                    confidence=0.82,
                    evidence=f"Delimiters found: {', '.join(active_separators)}",
                    detection_rule="check_inline_delimiters",
                )
            )

        return findings, strengths


__all__ = [
    "SectionStructureChecker",
    "TextReadabilityChecker",
    "BulletStructureChecker",
    "ResumeConsistencyChecker",
]
