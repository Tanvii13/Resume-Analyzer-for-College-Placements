"""
Unit tests for Sprint 2 – Module D2: Experience & Internship Extractor (NLP-07).

Covers:
- Layouts: Title / Company | Dates, Company | Location | Dates / Title,
  "Title at Company | Dates", "Title, Company (Dates)", one-line entries
- Date ranges, "Present" roles, duration in months
- Internship vs. full-time distinction (section heading and title keywords)
- Responsibilities from bullets, including wrapped bullet lines
- Splitting several roles that have no blank lines or bullets between them
- Technologies linked through the Module E skill taxonomy
- Partial entries and missing sections handled without errors
"""

from datetime import date

import pytest

from app.nlp.extractors.experience import ExperienceExtractor
from app.nlp.sections import SectionMap, classify_sections


@pytest.fixture(scope="module")
def extractor():
    return ExperienceExtractor(today=date(2026, 11, 6))


def extract(extractor, body, heading="EXPERIENCE"):
    return extractor.extract(classify_sections(f"Test Student\n\n{heading}\n{body}"))


def test_title_then_company_dates(extractor, sample_resume_text):
    entries = extractor.extract(classify_sections(sample_resume_text))
    assert len(entries) == 1
    e = entries[0]
    assert e.job_title == "Software Engineering Intern"
    assert e.company_name == "Credence Analytics"
    assert (e.start_date, e.end_date) == ("2024-05", "2024-07")
    assert e.duration_months == 3
    assert e.is_internship is True
    assert len(e.responsibilities) == 3
    assert e.responsibilities[0].endswith("async connection pooling.")  # wrapped line re-joined
    assert {"FastAPI", "PostgreSQL", "Redis", "GitHub Actions"} <= set(e.technologies_used)


def test_company_dates_then_title_with_location(extractor):
    entries = extract(
        extractor,
        "Google | Bengaluru, India | May 2024 - Jul 2024\n"
        "Software Development Engineer Intern\n"
        "- Built a ranking service.\n"
        "- Wrote unit tests with pytest.\n"
        "Infosys Ltd. | Pune | Jun 2025 - Present\n"
        "Systems Engineer\n"
        "- Maintained Java Spring Boot microservices on AWS.\n",
    )
    assert [(e.job_title, e.company_name) for e in entries] == [
        ("Software Development Engineer Intern", "Google"),
        ("Systems Engineer", "Infosys Ltd."),
    ]
    assert entries[0].location == "Bengaluru"
    google, infosys = entries
    assert google.is_internship is True
    assert infosys.is_internship is False
    assert infosys.is_current is True
    assert infosys.end_date is None
    assert infosys.duration_months == 18
    assert {"Java", "Spring Boot"} <= set(infosys.technologies_used)


def test_title_at_company(extractor):
    entries = extract(
        extractor,
        "Backend Developer Intern at Razorpay | Jan 2025 - Mar 2025\n"
        "- Designed REST APIs in Node.js and MongoDB\n"
        "Teaching Assistant, DA-IICT (Aug 2024 - Dec 2024)\n"
        "- Conducted labs for the software engineering course\n",
    )
    assert len(entries) == 2  # the TA line must not be glued onto the previous bullet
    assert (entries[0].job_title, entries[0].company_name) == ("Backend Developer Intern", "Razorpay")
    assert (entries[1].job_title, entries[1].company_name) == ("Teaching Assistant", "DA-IICT")
    assert entries[1].start_date == "2024-08"
    assert entries[1].is_internship is False


def test_back_to_back_one_line_roles_are_split(extractor):
    entries = extract(
        extractor,
        "Web Developer, Freelance, 2023\n"
        "Frontend Developer, Startup Inc., Jan'24 - Mar'24\n",
        heading="INTERNSHIPS",
    )
    assert [e.job_title for e in entries] == ["Web Developer", "Frontend Developer"]
    assert entries[1].company_name == "Startup Inc."
    assert all(e.is_internship for e in entries)  # listed under INTERNSHIPS
    assert all(e.source_section == "internships" for e in entries)


def test_summer_research_intern(extractor):
    entries = extract(
        extractor,
        "Summer Research Intern\n"
        "IIT Gandhinagar | May 2025 – July 2025\n"
        "- Trained PyTorch models for image segmentation\n",
        heading="WORK EXPERIENCE",
    )
    e = entries[0]
    assert e.job_title == "Summer Research Intern"
    assert e.company_name == "IIT Gandhinagar"
    assert e.is_internship is True
    assert "PyTorch" in e.technologies_used


@pytest.mark.parametrize(
    "title, expected",
    [
        ("Software Engineer", False),
        ("SDE Intern", True),
        ("Summer Internship", True),
        ("Data Analyst", False),
        ("Industrial Training", True),
    ],
)
def test_internship_detection_from_title(extractor, title, expected):
    entries = extract(extractor, f"{title}\nAcme Technologies | Jan 2024 - Jun 2024\n- Did work.\n")
    assert entries[0].is_internship is expected


def test_entry_without_dates_still_returned(extractor):
    entries = extract(extractor, "Open Source Contributor, Mozilla\n- Fixed accessibility bugs in Firefox.\n")
    e = entries[0]
    assert e.job_title == "Open Source Contributor"
    assert e.company_name == "Mozilla"
    assert e.start_date is None and e.end_date is None and e.duration_months is None
    assert e.confidence < 1.0


def test_no_experience_section(extractor):
    sections = classify_sections("Fresher Student\n\nEDUCATION\nB.Tech, DA-IICT, 2024 - 2028\n")
    assert extractor.extract(sections) == []
    assert extractor.extract(SectionMap()) == []


def test_tech_from_prose_avoids_false_positives(extractor):
    entries = extract(
        extractor,
        "Sales Associate\nRetail Store | Jan 2023 - Mar 2023\n"
        "- I will go to every customer and help them in choosing digital products.\n",
    )
    tech = entries[0].technologies_used
    assert "Go" not in tech and "Git" not in tech and "C" not in tech
