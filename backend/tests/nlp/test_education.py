"""
Unit tests for Sprint 2 – Module D1: Education Entity Extractor (NLP-06).

Covers:
- Degree detection and canonicalization via taxonomy/degrees.json
- Ambiguous short aliases (BE, ME, MS, X) not matched inside plain English
- CGPA formats: "8.7/10", "8.5 CGPA", "CPI: 9.12", "GPA 3.9/4.0", "8.74 / 10"
- Percentage formats: "85.6%", "88 percent", "Percentage: 85.4"
- Year ranges, two-digit shorthand, expected / pursuing graduation
- Institution, field of study and school board extraction
- Table layouts with a header row, multi-line layouts, one-line layouts
- Dual qualifications (Diploma + B.E.), school entries, partial entries
- Empty / missing education section handled gracefully
"""

import pytest

from app.nlp.extractors.education import EducationExtractor, find_degree, parse_cgpa, parse_percentage
from app.nlp.sections import classify_sections


@pytest.fixture
def extractor():
    return EducationExtractor()


def extract(extractor, body):
    return extractor.extract(classify_sections(f"Test Student\n\nEDUCATION\n{body}"))


# ============================================================================
# Score parsing
# ============================================================================

@pytest.mark.parametrize(
    "text, expected",
    [
        ("CGPA: 8.74/10", (8.74, 10.0)),
        ("8.7/10", (8.7, 10.0)),
        ("8.5 CGPA", (8.5, 10.0)),
        ("CPI - 9.12", (9.12, 10.0)),
        ("SPI 8.2 / 10", (8.2, 10.0)),
        ("GPA 3.9/4.0", (3.9, 4.0)),
        ("GPA: 3.8", (3.8, 4.0)),
        ("8.74 / 10", (8.74, 10.0)),
        ("C.G.P.A. 7.95", (7.95, 10.0)),
    ],
)
def test_parse_cgpa_formats(text, expected):
    assert parse_cgpa(text) == expected


@pytest.mark.parametrize("text", ["2021 - 2025", "05/2023", "Rank 12/300", "CGPA 11.2/10", ""])
def test_parse_cgpa_rejects_non_scores(text):
    assert parse_cgpa(text) is None


@pytest.mark.parametrize(
    "text, expected",
    [("94.6%", 94.6), ("88 percent", 88.0), ("Percentage: 85.4", 85.4), ("85.6 %", 85.6)],
)
def test_parse_percentage_formats(text, expected):
    assert parse_percentage(text) == expected


def test_parse_percentage_rejects_over_100():
    assert parse_percentage("scored 150%") is None


# ============================================================================
# Degree detection
# ============================================================================

@pytest.mark.parametrize(
    "text, name, level",
    [
        ("B.Tech in ICT", "B.Tech", "bachelors"),
        ("Bachelor of Technology", "B.Tech", "bachelors"),
        ("BTech CSE", "B.Tech", "bachelors"),
        ("BE Computer Engineering", "B.E.", "bachelors"),
        ("M.S. in Computer Science", "M.S.", "masters"),
        ("MCA", "MCA", "masters"),
        ("Ph.D. in Physics", "Ph.D.", "doctorate"),
        ("Class XII (CBSE)", "12th (HSC)", "secondary"),
        ("HSC", "12th (HSC)", "secondary"),
        ("Class X", "10th (SSC)", "secondary"),
        ("SSC 2019", "10th (SSC)", "secondary"),
        ("Diploma in Computer Engineering", "Diploma", "diploma"),
    ],
)
def test_find_degree(text, name, level):
    record, _ = find_degree(text)
    assert record["name"] == name
    assert record["level"] == level


@pytest.mark.parametrize(
    "text",
    ["I will be joining soon", "Tell me about it", "x = 5 in the equation", "ms word and excel"],
)
def test_ambiguous_aliases_not_matched_in_prose(text):
    assert find_degree(text) is None


# ============================================================================
# Entry extraction
# ============================================================================

def test_table_layout_with_header_row(extractor):
    entries = extract(
        extractor,
        "Degree | Institution | Year | CGPA\n"
        "B.Tech in ICT | DA-IICT | 2021 - 2025 | 8.74 / 10\n"
        "Class XII (CBSE) | Delhi Public School | 2021 | 94.6%\n",
    )
    assert len(entries) == 2
    btech, school = entries
    assert btech.degree == "B.Tech"
    assert btech.institution == "DA-IICT"
    assert btech.field_of_study == "ICT"
    assert (btech.start_year, btech.graduation_year) == (2021, 2025)
    assert (btech.cgpa, btech.cgpa_scale) == (8.74, 10.0)
    assert btech.percentage is None
    assert school.degree == "12th (HSC)"
    assert school.institution == "Delhi Public School"
    assert school.board == "CBSE"
    assert school.percentage == 94.6


def test_table_bare_score_column_interpreted_by_size(extractor):
    entries = extract(
        extractor,
        "Qualification | Institute | Year | Score\n"
        "B.E. | Nirma University | 2024 | 8.1\n"
        "HSC | St. Xavier's School | 2020 | 89\n",
    )
    assert entries[0].cgpa == 8.1 and entries[0].percentage is None
    assert entries[1].percentage == 89.0 and entries[1].cgpa is None


def test_multiline_layout(extractor):
    entries = extract(
        extractor,
        "Dhirubhai Ambani Institute of Information and Communication Technology, Gandhinagar\n"
        "B.Tech in Information and Communication Technology | CPI: 8.12/10 | 2022 - 2026\n"
        "Kendriya Vidyalaya, Ahmedabad\n"
        "Class XII (CBSE) - 92.4% | 2022\n",
    )
    assert len(entries) == 2
    assert entries[0].institution.startswith("Dhirubhai Ambani Institute")
    assert entries[0].degree == "B.Tech"
    assert entries[0].field_of_study == "Information and Communication Technology"
    assert entries[0].cgpa == 8.12
    assert entries[0].graduation_year == 2026
    assert entries[1].institution == "Kendriya Vidyalaya"
    assert entries[1].percentage == 92.4


def test_diploma_plus_btech_dual_qualification(extractor):
    entries = extract(
        extractor,
        "B.E. in Computer Engineering, L.D. College of Engineering, Ahmedabad, 2019-23, CGPA 8.9\n"
        "Diploma in Computer Engineering, Government Polytechnic, 2016 - 2019, 85.6%\n",
    )
    assert [e.degree for e in entries] == ["B.E.", "Diploma"]
    assert entries[0].institution == "L.D. College of Engineering"
    assert (entries[0].start_year, entries[0].graduation_year) == (2019, 2023)
    assert entries[0].cgpa == 8.9
    assert entries[1].degree_level == "diploma"
    assert entries[1].percentage == 85.6


def test_expected_graduation(extractor):
    entries = extract(
        extractor,
        "Indian Institute of Technology Bombay    Expected May 2026\n"
        "M.Tech, Computer Science and Engineering    GPA: 9.1/10\n"
        "- Relevant coursework: Machine Learning, Distributed Systems\n",
    )
    assert len(entries) == 1
    e = entries[0]
    assert e.institution == "Indian Institute of Technology Bombay"
    assert e.degree == "M.Tech"
    assert e.graduation_year == 2026
    assert e.is_expected is True
    assert e.cgpa == 9.1


def test_pursuing_degree_marked_expected(extractor):
    entries = extract(extractor, "B.Tech (CSE), Nirma University, 2023 - Present, CGPA 8.0\n")
    assert entries[0].is_expected is True
    assert entries[0].start_year == 2023
    assert entries[0].graduation_year is None
    assert entries[0].field_of_study == "CSE"


def test_partial_entry_keeps_missing_fields_none(extractor):
    entries = extract(extractor, "B.Sc in Physics\n")
    assert len(entries) == 1
    e = entries[0]
    assert e.degree == "B.Sc"
    assert e.field_of_study == "Physics"
    assert e.institution is None
    assert e.graduation_year is None
    assert e.cgpa is None and e.percentage is None
    assert e.confidence < 1.0


def test_no_education_section_returns_empty(extractor):
    sections = classify_sections("Test Student\n\nSKILLS\nPython, Java\n")
    assert extractor.extract(sections) == []


def test_empty_section_map(extractor):
    from app.nlp.sections import SectionMap
    assert extractor.extract(SectionMap()) == []


def test_sample_resume(extractor, sample_resume_text):
    entries = extractor.extract(classify_sections(sample_resume_text))
    assert [e.degree for e in entries] == ["B.Tech", "12th (HSC)"]
    assert entries[0].cgpa == 8.74
