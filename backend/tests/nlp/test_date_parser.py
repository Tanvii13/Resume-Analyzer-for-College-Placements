"""
Unit tests for the shared date parser (app.nlp.utils.date_parser), used by Module D.

Covers:
- Single dates: "May 2023", "Jan'24", "05/2023", "2023-05", bare years
- Ranges with month names, numeric months, two-digit year shorthand ("2021-25")
- "Present" / "Current" / "Till Date" ranges and the is_current flag
- Duration in months (inclusive, year-only, ongoing)
- Rejection of reversed ranges, phone numbers and out-of-range years
"""

from datetime import date

import pytest

from app.nlp.utils import find_date_range, find_date_ranges, find_single_date, find_years, parse_date

TODAY = date(2026, 11, 6)


@pytest.mark.parametrize(
    "text, iso",
    [
        ("May 2023", "2023-05"),
        ("September 2022", "2022-09"),
        ("Sept 2022", "2022-09"),
        ("Jan'24", "2024-01"),
        ("Jan '24", "2024-01"),
        ("Dec, 2021", "2021-12"),
        ("05/2023", "2023-05"),
        ("2023-05", "2023-05"),
        ("2021", "2021"),
    ],
)
def test_parse_single_date(text, iso):
    assert parse_date(text).to_iso() == iso


@pytest.mark.parametrize("text", ["", None, "hello", "13/2023", "1890", "May"])
def test_parse_date_rejects_garbage(text):
    assert parse_date(text) is None


@pytest.mark.parametrize(
    "text, start, end, months",
    [
        ("May 2024 - July 2024", "2024-05", "2024-07", 3),
        ("May 2024 – July 2024", "2024-05", "2024-07", 3),
        ("Aug 2023 to Dec 2023", "2023-08", "2023-12", 5),
        ("Jan'24 - Mar'24", "2024-01", "2024-03", 3),
        ("05/2023 - 07/2023", "2023-05", "2023-07", 3),
        ("2021 - 2025", "2021", "2025", 48),
        ("2021-25", "2021", "2025", 48),
        ("Dec 2023 - Feb 2024", "2023-12", "2024-02", 3),
    ],
)
def test_closed_ranges(text, start, end, months):
    r = find_date_range(text)
    assert r is not None
    assert r.start.to_iso() == start
    assert r.end.to_iso() == end
    assert r.is_current is False
    assert r.duration_months(TODAY) == months


@pytest.mark.parametrize("text", ["Jun 2022 - Present", "Jun 2022 – Current", "Jun 2022 - Till Date", "June 2022 to now"])
def test_open_ranges_are_current(text):
    r = find_date_range(text)
    assert r.is_current is True
    assert r.end is None
    assert r.start.to_iso() == "2022-06"
    assert r.duration_months(TODAY) == 54


def test_range_found_inside_longer_line():
    r = find_date_range("Credence Analytics | Pune | May 2024 - July 2024")
    assert r.matched_text.startswith("May 2024")


def test_multiple_ranges_in_order():
    ranges = find_date_ranges("2019 - 2021 then 2021 - 2025")
    assert [(r.start.year, r.end.year) for r in ranges] == [(2019, 2021), (2021, 2025)]


@pytest.mark.parametrize("text", ["2025 - 2021", "+91 98250 12345", "Rank 312 of 4500", "50k-100k requests"])
def test_non_ranges_rejected(text):
    assert find_date_range(text) is None


def test_find_years_and_single_date():
    assert find_years("Expected 2025, joined 2021") == [2025, 2021]
    assert find_years("Scored 3000 points") == []
    assert find_single_date("Graduated in May 2025").to_iso() == "2025-05"
    assert find_single_date("no dates here") is None
