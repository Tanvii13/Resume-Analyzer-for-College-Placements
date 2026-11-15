"""
Shared date and date-range parser for resume entity extraction.

Used by Module D (education, experience, projects) of the Sprint 2 NLP pipeline.

Handles common resume date formats:
    - "May 2023 - July 2023", "Jun 2022 – Present", "Jan'24 - Mar'24"
    - "05/2023 - 07/2023", "2023-05 to 2023-07"
    - "2021 - 2025", "2021-25", "Expected 2025", "Class of 2026"

Parsing is deterministic and never raises on malformed input: anything that
cannot be understood is returned as None.
"""

from dataclasses import dataclass
from datetime import date
import re
from typing import List, Optional, Tuple

MIN_YEAR = 1950
MAX_YEAR = 2100

MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

PRESENT_WORDS = ("present", "current", "currently", "now", "ongoing", "till date", "to date", "date")

_MONTH_ALT = "|".join(sorted(MONTHS.keys(), key=len, reverse=True))

# A single date point: "May 2023", "May, 2023", "Jan'24", "05/2023", "2023-05", "2023"
_DATE_POINT = (
    rf"(?:(?:{_MONTH_ALT})\.?,?\s*(?:'\s?\d{{2}}|\d{{4}})"   # Month Year / Month 'YY
    r"|(?:0?[1-9]|1[0-2])[/.-](?:\d{4})"                     # MM/YYYY
    r"|(?:\d{4})[/.-](?:0?[1-9]|1[0-2])(?!\d)"               # YYYY-MM
    r"|(?:19|20)\d{2})"                                      # YYYY
)
_PRESENT = r"(?:present|current(?:ly)?|now|ongoing|till\s+date|to\s+date)"
_SEPARATOR = r"\s*(?:-|–|—|to|till|until|→)\s*"

DATE_RANGE_RE = re.compile(
    rf"(?P<start>{_DATE_POINT}){_SEPARATOR}(?P<end>{_DATE_POINT}|{_PRESENT}|\d{{2}}(?!\d))",
    re.IGNORECASE,
)
DATE_POINT_RE = re.compile(rf"(?<![\w/]){_DATE_POINT}(?![\w/])", re.IGNORECASE)
YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")


@dataclass
class ParsedDate:
    """A partially specified calendar date (month may be unknown)."""
    year: int
    month: Optional[int] = None

    def to_iso(self) -> str:
        """Return 'YYYY-MM' when the month is known, else 'YYYY'."""
        if self.month:
            return f"{self.year:04d}-{self.month:02d}"
        return f"{self.year:04d}"


@dataclass
class DateRange:
    """A start/end range extracted from resume text."""
    start: Optional[ParsedDate]
    end: Optional[ParsedDate]
    is_current: bool = False
    matched_text: str = ""
    span: Tuple[int, int] = (0, 0)

    def duration_months(self, today: Optional[date] = None) -> Optional[int]:
        """
        Inclusive month count between start and end.

        Ongoing ranges are measured up to `today`. Returns None when either
        endpoint is missing or when the end precedes the start.
        """
        if self.start is None:
            return None
        if self.is_current:
            today = today or date.today()
            end_year, end_month = today.year, today.month
        elif self.end is not None:
            if self.start.month is None and self.end.month is None:
                # Year-only ranges ("2021 - 2025") count whole years
                years = self.end.year - self.start.year
                return years * 12 if years > 0 else None
            end_year = self.end.year
            end_month = self.end.month or 12
        else:
            return None
        start_month = self.start.month or 1
        months = (end_year - self.start.year) * 12 + (end_month - start_month) + 1
        return months if months > 0 else None


def _valid_year(year: int) -> bool:
    return MIN_YEAR <= year <= MAX_YEAR


def _expand_two_digit_year(yy: int, reference_year: Optional[int] = None) -> int:
    if reference_year is not None:
        century = (reference_year // 100) * 100
        year = century + yy
        if year < reference_year:
            year += 100
        return year
    return 2000 + yy


def parse_date(text: Optional[str]) -> Optional[ParsedDate]:
    """
    Parse a single date expression into a ParsedDate.

    Examples:
        parse_date("May 2023") -> ParsedDate(2023, 5)
        parse_date("Jan'24")   -> ParsedDate(2024, 1)
        parse_date("05/2023")  -> ParsedDate(2023, 5)
        parse_date("2021")     -> ParsedDate(2021, None)
        parse_date("garbage")  -> None
    """
    if not text:
        return None
    s = text.strip().lower().rstrip(".,")

    m = re.fullmatch(rf"({_MONTH_ALT})\.?,?\s*(?:'\s?(\d{{2}})|(\d{{4}}))", s)
    if m:
        month = MONTHS[m.group(1)]
        year = int(m.group(3)) if m.group(3) else _expand_two_digit_year(int(m.group(2)))
        return ParsedDate(year, month) if _valid_year(year) else None

    m = re.fullmatch(r"(0?[1-9]|1[0-2])[/.-](\d{4})", s)
    if m:
        year = int(m.group(2))
        return ParsedDate(year, int(m.group(1))) if _valid_year(year) else None

    m = re.fullmatch(r"(\d{4})[/.-](0?[1-9]|1[0-2])", s)
    if m:
        year = int(m.group(1))
        return ParsedDate(year, int(m.group(2))) if _valid_year(year) else None

    m = re.fullmatch(r"(\d{4})", s)
    if m:
        year = int(m.group(1))
        return ParsedDate(year) if _valid_year(year) else None

    return None


def _is_present(text: str) -> bool:
    return re.fullmatch(_PRESENT, text.strip(), re.IGNORECASE) is not None


def find_date_ranges(text: Optional[str]) -> List[DateRange]:
    """
    Find all date ranges in a string, in order of appearance.

    "Jun 2022 - Present" -> [DateRange(start=2022-06, end=None, is_current=True)]
    "2021-25"            -> [DateRange(start=2021, end=2025)]
    """
    if not text:
        return []
    results: List[DateRange] = []
    for m in DATE_RANGE_RE.finditer(text):
        start = parse_date(m.group("start"))
        if start is None:
            continue
        end_raw = m.group("end")
        if _is_present(end_raw):
            results.append(DateRange(start, None, True, m.group(0), m.span()))
            continue
        if re.fullmatch(r"\d{2}", end_raw):
            # "2021-25" shorthand: only valid after a bare year
            if start.month is not None:
                continue
            end = ParsedDate(_expand_two_digit_year(int(end_raw), start.year))
        else:
            end = parse_date(end_raw)
        if end is None:
            continue
        # Reject reversed ranges ("2025 - 2021") as not being date ranges
        if (end.year, end.month or 12) < (start.year, start.month or 1):
            continue
        results.append(DateRange(start, end, False, m.group(0), m.span()))
    return results


def find_date_range(text: Optional[str]) -> Optional[DateRange]:
    """Return the first date range found in `text`, or None."""
    ranges = find_date_ranges(text)
    return ranges[0] if ranges else None


def find_years(text: Optional[str]) -> List[int]:
    """Return all plausible 4-digit years in `text`, in order of appearance."""
    if not text:
        return []
    return [int(y) for y in YEAR_RE.findall(text) if _valid_year(int(y))]


def find_single_date(text: Optional[str]) -> Optional[ParsedDate]:
    """Return the first standalone date expression in `text`, or None."""
    if not text:
        return None
    for m in DATE_POINT_RE.finditer(text):
        parsed = parse_date(m.group(0))
        if parsed:
            return parsed
    return None


def has_date(text: Optional[str]) -> bool:
    """True if the text contains a date range or a standalone date."""
    return bool(find_date_ranges(text)) or find_single_date(text) is not None
