"""
Education entity extractor.

Module D1 (NLP-06) of the Sprint 2 NLP pipeline.

Extracts degrees, institutions, fields of study, years, CGPA and percentage
from the EDUCATION section. Handles:
    - Table layouts with a header row ("Degree | Institution | Year | CGPA")
    - Line layouts ("B.Tech in Computer Science, DA-IICT, 2021 - 2025, CPI: 8.4")
    - Multi-line layouts (institution on one line, degree + score on the next)
    - School entries (Class XII / HSC / 10th with board and percentage)

Partial entries are returned with whatever fields were found; missing fields
stay None. Nothing is guessed.
"""

from functools import lru_cache
import re
from typing import Dict, List, Optional, Tuple

from app.nlp.extractors._entries import (
    clean_text,
    is_detail_block,
    is_location,
    section_blocks,
    sections_named,
    split_fragments,
)
from app.nlp.extractors.base import BaseExtractor
from app.nlp.preprocessing import BlockType, SegmentedDocument, TextBlock
from app.nlp.schemas import EducationEntry
from app.nlp.sections import SECTION_EDUCATION, SectionMap
from app.nlp.taxonomy import load_degrees
from app.nlp.utils import find_date_range, find_years
from app.nlp.utils.date_parser import MONTHS

_MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))

# ---------------------------------------------------------------------------
# Degree detection
# ---------------------------------------------------------------------------

# Aliases that are also ordinary words/letters ("be", "me", "x", "ms" ...).
# These only match when written in upper case in the source text ("BE", "MS").
_AMBIGUOUS_ALIASES = {"be", "me", "ms", "bs", "x", "xii", "b e", "m e", "m s", "intermediate"}

_LEVEL_RANK = {"doctorate": 5, "masters": 4, "bachelors": 3, "diploma": 2, "secondary": 1}


@lru_cache(maxsize=1)
def _degree_patterns() -> List[Tuple[re.Pattern, Dict[str, str]]]:
    """Compile one boundary-safe regex per degree alias, longest alias first."""
    data = load_degrees()
    entries: List[Tuple[str, Dict[str, str]]] = []
    for level_key, level in data.get("levels", {}).items():
        for deg in level.get("degrees", []):
            record = {"name": deg["name"], "full_name": deg.get("full_name", deg["name"]), "level": level_key}
            for alias in set(deg.get("aliases", []) + [deg["name"].lower()]):
                entries.append((alias, record))
    entries.sort(key=lambda e: len(e[0]), reverse=True)

    patterns: List[Tuple[re.Pattern, Dict[str, str]]] = []
    for alias, record in entries:
        body = re.escape(alias).replace(r"\ ", r"\s*")
        body = body.replace(r"\.", r"\.?") if not alias.endswith(".") else body[:-2] + r"\.?"
        bounded = rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])"
        if alias in _AMBIGUOUS_ALIASES:
            # Case-sensitive upper-case form only ("BE", "M.S", "XII")
            upper = re.escape(alias.upper()).replace(r"\ ", r"\s*")
            patterns.append((re.compile(rf"(?<![A-Za-z0-9]){upper}(?![A-Za-z0-9])"), record))
        else:
            patterns.append((re.compile(bounded, re.IGNORECASE), record))
    return patterns


_EXTRA_SECONDARY = [
    (re.compile(r"(?<![A-Za-z0-9])(?:class|std\.?|standard|grade)\s*(?:xii|12(?:th)?)(?![A-Za-z0-9])", re.I), "12th (HSC)"),
    (re.compile(r"(?<![A-Za-z0-9])(?:class|std\.?|standard|grade)\s*(?:x|10(?:th)?)(?![A-Za-z0-9])", re.I), "10th (SSC)"),
    (re.compile(r"(?<![A-Za-z0-9])(?:12th|xiith|hsc|senior secondary)(?![A-Za-z0-9])", re.I), "12th (HSC)"),
    (re.compile(r"(?<![A-Za-z0-9])(?:10th|xth|ssc|matriculation)(?![A-Za-z0-9])", re.I), "10th (SSC)"),
]


def find_degree(text: str) -> Optional[Tuple[Dict[str, str], Tuple[int, int]]]:
    """Return (degree_record, span) for the earliest degree mention in `text`."""
    if not text:
        return None
    best: Optional[Tuple[Dict[str, str], Tuple[int, int]]] = None
    for pattern, record in _degree_patterns():
        m = pattern.search(text)
        if m and (best is None or m.start() < best[1][0] or
                  (m.start() == best[1][0] and m.end() > best[1][1])):
            best = (record, m.span())
    for pattern, name in _EXTRA_SECONDARY:
        m = pattern.search(text)
        if m and (best is None or m.start() < best[1][0] or
                  (m.start() == best[1][0] and m.end() > best[1][1])):
            best = ({"name": name, "full_name": name, "level": "secondary"}, m.span())
    return best


# ---------------------------------------------------------------------------
# Institution, field and board detection
# ---------------------------------------------------------------------------

_INSTITUTION_WORDS = [
    "university", "institute", "college", "school", "academy", "vidyalaya", "vidyapeeth",
    "vidyapith", "mahavidyalaya", "polytechnic", "iit", "nit", "iiit", "iisc", "bits",
    "da-iict", "daiict", "dau", "dhirubhai ambani", "gtu", "nirma", "pdeu", "pdpu",
    "ldce", "svnit", "msu", "charusat", "ahmedabad university", "kendriya", "high school",
]
_INSTITUTION_RE = re.compile(
    r"(?<![A-Za-z])(?:" + "|".join(re.escape(w) for w in _INSTITUTION_WORDS) + r")(?![A-Za-z])",
    re.IGNORECASE,
)

_FIELDS = [
    "Computer Science and Engineering", "Computer Science & Engineering",
    "Information and Communication Technology", "Information & Communication Technology",
    "Electronics and Communication Engineering", "Electronics & Communication Engineering",
    "Electrical and Electronics Engineering", "Artificial Intelligence and Machine Learning",
    "Artificial Intelligence and Data Science", "Mathematics and Computing",
    "Computer Science", "Computer Engineering", "Information Technology",
    "Electrical Engineering", "Electronics Engineering", "Mechanical Engineering",
    "Civil Engineering", "Chemical Engineering", "Data Science", "Artificial Intelligence",
    "Mathematics", "Physics", "Chemistry", "Biotechnology", "Commerce", "Economics",
    "Computer Applications", "Mechatronics", "Instrumentation", "Statistics",
    "ICT", "CSE", "CS", "IT", "ECE", "EE", "ME", "EEE", "AIML", "AI&DS",
    "Science", "PCM", "PCB",
]
# Abbreviations that are only trusted in upper case.
_UPPER_ONLY_FIELDS = {"ICT", "CSE", "CS", "IT", "ECE", "EE", "ME", "EEE", "AIML", "AI&DS", "PCM", "PCB"}

_BOARDS = ["CBSE", "ICSE", "ISC", "GSEB", "GSHSEB", "HSC Board", "State Board", "IB", "NIOS", "Maharashtra State Board"]
_BOARD_RE = re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(b) for b in _BOARDS) + r")(?![A-Za-z])")

# ---------------------------------------------------------------------------
# Score detection
# ---------------------------------------------------------------------------

_NUM = r"(\d{1,2}(?:\.\d{1,3})?)"
_CGPA_WORDS = r"(?:c\.?g\.?p\.?a|s\.?g\.?p\.?a|c\.?p\.?i|s\.?p\.?i|g\.?p\.?a|grade point average)\.?"
_CGPA_KEYWORD_RE = re.compile(
    rf"{_CGPA_WORDS}\s*(?:of|is|was)?\s*[:=\-–]?\s*{_NUM}(?:\s*(?:/|out of)\s*(\d{{1,2}}(?:\.\d+)?))?",
    re.IGNORECASE,
)
_CGPA_TRAILING_RE = re.compile(
    rf"(?<![\d.]){_NUM}(?:\s*/\s*(\d{{1,2}}(?:\.\d+)?))?\s*{_CGPA_WORDS}(?![a-z])", re.IGNORECASE
)
_CGPA_FRACTION_RE = re.compile(r"(?<![\d./])(\d{1,2}(?:\.\d{1,3})?)\s*/\s*(10|4|4\.0|4\.00|5|5\.0)(?![\d/])")
_PERCENT_RE = re.compile(
    r"(?<![\d.])(\d{2,3}(?:\.\d{1,2})?)\s*(?:%|percent(?:age)?\b)"
    r"|percent(?:age)?\s*[:=\-–]?\s*(\d{2,3}(?:\.\d{1,2})?)",
    re.IGNORECASE,
)


def parse_cgpa(text: str) -> Optional[Tuple[float, Optional[float]]]:
    """
    Find a CGPA / GPA / CPI in text. Returns (value, scale) or None.

    "CGPA: 8.74/10" -> (8.74, 10.0); "8.5 CGPA" -> (8.5, 10.0);
    "GPA 3.9/4.0" -> (3.9, 4.0); "8.74 / 10" -> (8.74, 10.0)
    """
    if not text:
        return None
    for regex in (_CGPA_KEYWORD_RE, _CGPA_TRAILING_RE, _CGPA_FRACTION_RE):
        for m in regex.finditer(text):
            value = float(m.group(1))
            scale = float(m.group(2)) if m.group(2) else None
            if scale is None:
                # Plain "GPA 3.8" is a US-style 4-point scale; CGPA/CPI default to 10.
                plain_gpa = re.search(r"(?<![a-z.])g\.?p\.?a", m.group(0), re.I)
                scale = 4.0 if plain_gpa and value <= 4.0 else 10.0
            if 0 < value <= scale and scale in (4.0, 5.0, 10.0):
                return value, scale
    return None


def parse_percentage(text: str) -> Optional[float]:
    """Find a percentage score ("94.6%", "88 percent", "Percentage: 85.4")."""
    if not text:
        return None
    for m in _PERCENT_RE.finditer(text):
        value = float(m.group(1) or m.group(2))
        if 0 < value <= 100:
            return value
    return None


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

_HEADER_KEYWORDS = {
    "degree": "degree", "qualification": "degree", "course": "degree", "program": "degree",
    "programme": "degree", "examination": "degree", "exam": "degree", "class": "degree",
    "institution": "institution", "institute": "institution", "college": "institution",
    "school": "institution", "university": "institution", "board": "board",
    "board/university": "institution", "school/college": "institution",
    "year": "year", "years": "year", "duration": "year", "passing year": "year",
    "year of passing": "year", "batch": "year",
    "cgpa": "score", "cpi": "score", "gpa": "score", "grade": "score", "marks": "score",
    "score": "score", "percentage": "score", "%": "score", "cgpa/percentage": "score",
    "result": "score", "performance": "score",
}


def _header_columns(line: str) -> Optional[List[Optional[str]]]:
    """If `line` is a table header ("Degree | Institution | Year | CGPA"), map columns."""
    if re.search(r"\d", line):
        return None
    cells = [c.strip().lower() for c in line.split("|")]
    if len(cells) < 2:
        return None
    mapped = [_HEADER_KEYWORDS.get(c.rstrip(":")) for c in cells]
    if sum(1 for m in mapped if m) >= 2:
        return mapped
    return None


class EducationExtractor(BaseExtractor):
    """Extracts a list of EducationEntry objects from the education section."""

    def extract(
        self,
        sections: SectionMap,
        document: Optional[SegmentedDocument] = None,
    ) -> List[EducationEntry]:
        entries: List[EducationEntry] = []
        for section in sections_named(sections, SECTION_EDUCATION):
            entries.extend(self._extract_from_blocks(section_blocks(section)))
        return entries

    def extract_from_text(self, text: str) -> List[EducationEntry]:
        """Convenience: extract from a raw education section body."""
        from app.nlp.extractors._entries import section_blocks as _sb
        from app.nlp.sections import ClassifiedSection
        fake = ClassifiedSection(canonical_name=SECTION_EDUCATION, original_heading=None,
                                 content=text or "", raw_content=text or "")
        return self._extract_from_blocks(_sb(fake))

    # -- grouping ----------------------------------------------------------

    def _extract_from_blocks(self, blocks: List[TextBlock]) -> List[EducationEntry]:
        columns: Optional[List[Optional[str]]] = None
        groups: List[List[str]] = []
        current: List[str] = []
        has_degree = has_inst = False

        for block in blocks:
            text = block.text.strip()
            if not text:
                continue
            header = _header_columns(text)
            if header:
                columns = header
                continue

            if columns and "|" in text and not is_detail_block(block):
                # Table row: always its own entry
                if current:
                    groups.append(current)
                current, has_degree, has_inst = [], False, False
                groups.append(["\x00TABLE\x00" + text])
                continue

            if is_detail_block(block):
                current.append(text)
                continue

            line_degree = find_degree(text) is not None
            line_inst = _INSTITUTION_RE.search(text) is not None
            # Start a new entry when this header line repeats a field the
            # current entry already has (a second degree or second institution).
            if current and ((line_degree and has_degree) or (line_inst and has_inst and not line_degree)):
                groups.append(current)
                current, has_degree, has_inst = [], False, False
            current.append(text)
            has_degree = has_degree or line_degree
            has_inst = has_inst or line_inst

        if current:
            groups.append(current)

        entries: List[EducationEntry] = []
        for group in groups:
            if len(group) == 1 and group[0].startswith("\x00TABLE\x00"):
                entry = self._parse_table_row(group[0][len("\x00TABLE\x00"):], columns or [])
            else:
                entry = self._parse_lines(group)
            if entry is not None:
                entries.append(entry)
        return entries

    # -- parsing -----------------------------------------------------------

    def _parse_table_row(self, row: str, columns: List[Optional[str]]) -> Optional[EducationEntry]:
        cells = [c.strip() for c in row.split("|")]
        by_role: Dict[str, str] = {}
        for idx, cell in enumerate(cells):
            role = columns[idx] if idx < len(columns) else None
            if role and cell:
                by_role[role] = cell
        entry = self._parse_lines([row])
        if entry is None:
            entry = EducationEntry(raw_text=row)

        if "institution" in by_role and not _looks_like_degree_only(by_role["institution"]):
            entry.institution = clean_text(by_role["institution"])
        if "score" in by_role:
            score = by_role["score"]
            cgpa = parse_cgpa(score)
            pct = parse_percentage(score)
            if cgpa is None and pct is None:
                m = re.fullmatch(r"\s*(\d{1,3}(?:\.\d{1,3})?)\s*", score)
                if m:
                    value = float(m.group(1))
                    if value <= 10:
                        cgpa = (value, 10.0)
                    elif value <= 100:
                        pct = value
            if cgpa:
                entry.cgpa, entry.cgpa_scale = cgpa
                entry.percentage = None
            elif pct is not None:
                entry.percentage = pct
                entry.cgpa = entry.cgpa_scale = None
        if "board" in by_role and not entry.board:
            entry.board = clean_text(by_role["board"])
        return entry

    def _parse_lines(self, lines: List[str]) -> Optional[EducationEntry]:
        text = "\n".join(lines)
        if not text.strip():
            return None

        entry = EducationEntry(raw_text=text)
        found = 0

        degree = find_degree(text)
        if degree:
            record, span = degree
            entry.degree = record["name"]
            entry.degree_level = record["level"]
            entry.field_of_study = _find_field(text, span)
            found += 1

        entry.institution = _find_institution(lines, degree[1] if degree else None, text)
        if entry.institution:
            found += 1

        board = _BOARD_RE.search(text)
        if board:
            entry.board = board.group(1)

        # Years. Look for a range first, then an "expected" year, then any year.
        date_range = find_date_range(text)
        if date_range:
            entry.start_year = date_range.start.year if date_range.start else None
            if date_range.is_current:
                entry.is_expected = True
            elif date_range.end:
                entry.graduation_year = date_range.end.year
            found += 1
        expected = re.search(r"(?:expected|anticipated|exp\.?|class of|batch of|graduating)\s*(?:in\s*)?[:\-]?\s*(?:[A-Za-z]{3,9}\.?\s*)?((?:19|20)\d{2})", text, re.I)
        if expected:
            entry.graduation_year = int(expected.group(1))
            entry.is_expected = True
        if entry.graduation_year is None and not date_range:
            years = find_years(text)
            if years:
                entry.graduation_year = max(years)
                found += 1
        if re.search(r"\b(?:pursuing|ongoing|present|current)\b", text, re.I):
            entry.is_expected = True

        cgpa = parse_cgpa(text)
        if cgpa:
            entry.cgpa, entry.cgpa_scale = cgpa
            found += 1
        pct = parse_percentage(text)
        if pct is not None:
            entry.percentage = pct
            found += 1

        if not degree and not entry.institution:
            # A line with only a score or year is not an education entry on its own.
            return None if found <= 1 else _with_confidence(entry, 0.4)

        score = 0.35 * bool(entry.degree) + 0.3 * bool(entry.institution) \
            + 0.2 * bool(entry.graduation_year) + 0.15 * bool(entry.cgpa or entry.percentage)
        return _with_confidence(entry, round(min(1.0, score), 2))


def _with_confidence(entry: EducationEntry, value: float) -> EducationEntry:
    entry.confidence = value
    return entry


def _looks_like_degree_only(text: str) -> bool:
    return find_degree(text) is not None and not _INSTITUTION_RE.search(text)


def _find_field(text: str, degree_span: Tuple[int, int]) -> Optional[str]:
    """Field of study: prefer the phrase right after the degree ("B.Tech in CSE")."""
    after = text[degree_span[1]:]
    m = re.match(r"\s*(?:\(|in|of|-|–|,|:)?\s*(?:in\s+)?([A-Z][A-Za-z&,.\s]{1,60}?)(?=\s*(?:\||\)|,\s*[A-Z][a-z]+\s+(?:University|Institute|College)|\n|\s[-–—]\s|\d|$|from|at\b))", after)
    candidates = [m.group(1)] if m else []
    candidates.append(text)
    for chunk in candidates:
        for field in _FIELDS:
            flags = 0 if field in _UPPER_ONLY_FIELDS else re.IGNORECASE
            if re.search(rf"(?<![A-Za-z]){re.escape(field)}(?![A-Za-z])", chunk, flags):
                # Don't report "ME" / "EE" when it is actually the degree itself
                if field in _UPPER_ONLY_FIELDS and chunk is text:
                    pos = re.search(rf"(?<![A-Za-z]){re.escape(field)}(?![A-Za-z])", text).start()
                    if degree_span[0] <= pos < degree_span[1]:
                        continue
                return field
    return None


def _find_institution(lines: List[str], degree_span: Optional[Tuple[int, int]], text: str) -> Optional[str]:
    """The fragment that names a school/college/university."""
    candidates: List[str] = []
    for line in lines:
        for frag in split_fragments(line) or [line]:
            # "B.Tech in ICT, DA-IICT" -> look at comma pieces too
            pieces = [p.strip() for p in re.split(r",\s*(?=[A-Z])", frag)] if "," in frag else [frag]
            candidates.extend(pieces)
    for frag in candidates:
        if not _INSTITUTION_RE.search(frag) or is_location(frag):
            continue
        # Strip the degree / years / scores that may share this fragment
        cleaned = re.sub(r"\b(?:19|20)\d{2}\b(?:\s*[-–]\s*(?:\d{2,4}|present))?", "", frag, flags=re.I)
        cleaned = re.sub(rf"{_CGPA_WORDS}\s*[:\-]?\s*\d+(?:\.\d+)?(?:\s*/\s*\d+)?", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\d+(?:\.\d+)?\s*%", "", cleaned)
        deg = find_degree(cleaned)
        if deg and not re.search(r"(?i)university|institute|college|school", cleaned[: deg[1][0]] or ""):
            # Degree text is before the institution name: keep what follows it
            tail = cleaned[deg[1][1]:]
            m = re.search(r"(?:,|from|at|-|–)\s*(.+)$", tail)
            if m and _INSTITUTION_RE.search(m.group(1)):
                cleaned = m.group(1)
        cleaned = re.sub(r"\(\s*(?:CBSE|ICSE|GSEB|ISC|IB|NIOS)\s*\)", "", cleaned)
        cleaned = re.sub(r"(?i)\b(?:expected|anticipated|graduating|pursuing|ongoing|present)\b.*$", "", cleaned)
        cleaned = re.sub(rf"(?i)\b(?:{_MONTH_ALT})\b\.?\s*$", "", cleaned.strip())
        result = clean_text(cleaned)
        if result and _INSTITUTION_RE.search(result):
            return result
    return None


__all__ = ["EducationExtractor", "find_degree", "parse_cgpa", "parse_percentage"]
