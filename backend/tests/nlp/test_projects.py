"""
Unit tests for Sprint 2 – Module D3: Project Extractor (NLP-08).

Covers:
- Title lines with tech and dates: "Title | Python, Flask | Jan 2024 - Mar 2024"
- Parenthesized tech stacks: "Title (React, Node.js, MongoDB)"
- Bullet-list projects: "- Title: description"
- Paragraph descriptions and "Tech Stack:" lines
- GitHub vs live-demo URL classification, link-only lines not kept as highlights
- Technology list parsing via the Module E taxonomy (canonical names)
- One-line project summaries and empty sections
"""

import pytest

from app.nlp.extractors.projects import ProjectExtractor
from app.nlp.sections import SectionMap, classify_sections


@pytest.fixture(scope="module")
def extractor():
    return ProjectExtractor()


def extract(extractor, body):
    return extractor.extract(classify_sections(f"Test Student\n\nPROJECTS\n{body}"))


def test_sample_resume_project(extractor, sample_resume_text):
    projects = extractor.extract(classify_sections(sample_resume_text))
    assert len(projects) == 1
    p = projects[0]
    assert p.title == "College Placement Portal & Resume Analyzer"
    assert p.github_url == "https://github.com/Tanvii13/Resume-Analyzer-for-College-Placements"
    assert {"FastAPI", "Python", "PostgreSQL", "C++", "Vue.js"} <= set(p.technologies)
    assert len(p.highlights) == 2  # the "Repository: <url>" bullet is not a highlight


def test_pipe_separated_title_line_and_parenthesized_stack(extractor):
    projects = extract(
        extractor,
        "Smart Attendance System | Python, OpenCV, Flask | Jan 2024 - Mar 2024\n"
        "- Built face-recognition attendance for 200 students.\n"
        "- Deployed on AWS EC2.\n"
        "Expense Tracker (React, Node.js, MongoDB)\n"
        "- Tracks monthly spending with charts.\n"
        "GitHub: github.com/rainman/expense-tracker\n",
    )
    assert [p.title for p in projects] == ["Smart Attendance System", "Expense Tracker"]
    attendance, tracker = projects
    assert {"Python", "OpenCV", "Flask"} <= set(attendance.technologies)
    assert (attendance.start_date, attendance.end_date) == ("2024-01", "2024-03")
    assert len(attendance.highlights) == 2
    assert {"React", "Node.js", "MongoDB"} <= set(tracker.technologies)
    assert tracker.github_url == "https://github.com/rainman/expense-tracker"
    assert tracker.highlights == ["Tracks monthly spending with charts."]


def test_bullet_list_projects(extractor):
    projects = extract(
        extractor,
        "- Chess Engine: Minimax with alpha-beta pruning written in C++.\n"
        "- Portfolio Website - Personal site built with Next.js and Tailwind CSS. https://rainman.vercel.app\n"
        "- Sentiment Analyzer: Fine-tuned BERT on tweets using PyTorch.\n",
    )
    assert [p.title for p in projects] == ["Chess Engine", "Portfolio Website", "Sentiment Analyzer"]
    assert projects[0].technologies == ["C++"]
    assert projects[1].project_url == "https://rainman.vercel.app"
    assert projects[1].github_url is None
    assert "PyTorch" in projects[2].technologies


def test_paragraph_description_and_tech_stack_line(extractor):
    projects = extract(
        extractor,
        "Library Management System\n"
        "A Java desktop app with MySQL backend to manage book issues and returns for the college library.\n"
        "Tech Stack: Java, MySQL\n",
    )
    assert len(projects) == 1
    p = projects[0]
    assert p.title == "Library Management System"
    assert p.description.startswith("A Java desktop app")
    assert set(p.technologies) == {"Java", "MySQL"}
    assert p.highlights == []


def test_one_line_project_summary(extractor):
    projects = extract(extractor, "Weather App - Shows forecasts using a public REST API in JavaScript.\n")
    assert len(projects) == 1
    assert projects[0].title == "Weather App"
    assert "JavaScript" in projects[0].technologies


def test_project_without_tech_keeps_empty_list(extractor):
    projects = extract(extractor, "Campus Event Planner\n- Planned the structure for a student club tool.\n")
    assert projects[0].title == "Campus Event Planner"
    assert projects[0].technologies == []
    assert projects[0].github_url is None and projects[0].project_url is None


def test_empty_and_missing_sections(extractor):
    assert extractor.extract(SectionMap()) == []
    assert extractor.extract(classify_sections("A Student\n\nSKILLS\nPython\n")) == []
