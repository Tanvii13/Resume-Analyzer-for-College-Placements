
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from app.routers import resumes as resumes_router


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_resume_auth():
    """
    Override authentication for these API tests.

    This prevents the tests from requiring a real database
    registration or login.
    """
    app.dependency_overrides[
        resumes_router.get_current_user
    ] = lambda: SimpleNamespace(
        email="member1-test@example.com"
    )

    yield

    app.dependency_overrides.pop(
        resumes_router.get_current_user,
        None,
    )


SAMPLE_RESUME_TEXT = """
Shlok Topaliya
shlok@example.com
+91 9876543210
https://www.linkedin.com/in/shlok
https://github.com/shlok

EDUCATION
B.Tech Computer Science
DA-IICT
CGPA: 8.5

SKILLS
Python, C, C++, SQL, FastAPI, Git

PROJECTS
Resume Analyzer
Developed a resume analysis application using Python and FastAPI.
Improved processing efficiency by 30%.

EXPERIENCE
Software Engineering Intern
Worked on backend development.
"""


SAMPLE_JD = """
Software Engineer

We are looking for a Software Engineer to join our development team.

Requirements:
Bachelor degree in Computer Science or Information Technology.
Experience with Python, Java, SQL, Git and REST APIs.
Knowledge of FastAPI, databases, data structures and algorithms.
Strong communication, teamwork and problem solving skills.

The candidate should be able to develop, test and maintain
software applications and collaborate with other engineers.
"""


def test_improvement_areas_endpoint(monkeypatch):
    """
    Verify that the improvement areas endpoint returns
    the improvement report for an owned resume.
    """
    resume_id = str(uuid4())

    monkeypatch.setattr(
        resumes_router,
        "get_owned_resume_data",
        lambda resume_id, current_user: (
            {
                "skills": ["Python", "C++", "SQL"],
                "education": [],
                "projects": [],
                "experience": [],
            },
            SAMPLE_RESUME_TEXT,
        ),
    )

    response = client.get(
        f"/resumes/{resume_id}/improvement-areas"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["resume_id"] == resume_id
    assert "total_issues_count" in data
    assert "priority_breakdown" in data
    assert "improvement_areas" in data

    assert isinstance(data["improvement_areas"], list)
    assert isinstance(data["priority_breakdown"], dict)


def test_improvement_areas_rejects_invalid_resume_id():
    """
    Verify that an invalid resume ID is rejected.
    """
    response = client.get(
        "/resumes/not-a-valid-uuid/improvement-areas"
    )

    assert response.status_code == 400


def test_jd_comparison_endpoint_uses_parser_and_matcher(
    monkeypatch,
):
    """
    Verify that JD comparison parses the job description
    and passes the sanitized text to the matcher.
    """
    resume_id = str(uuid4())

    monkeypatch.setattr(
        resumes_router,
        "get_owned_resume_data",
        lambda resume_id, current_user: (
            {
                "skills": [
                    "Python",
                    "SQL",
                    "FastAPI",
                ],
                "education": [],
                "projects": [],
                "experience": [],
            },
            SAMPLE_RESUME_TEXT,
        ),
    )

    matcher_called = {}

    def fake_match_resume_with_jd(
        resume_skills,
        jd_text,
    ):
        matcher_called["resume_skills"] = resume_skills
        matcher_called["jd_text"] = jd_text

        return {
            "total_jd_skills_found": 5,
            "matched_skills_count": 3,
            "missing_skills_count": 2,
            "match_percentage": 60.0,
            "matched_skills": [
                "Python",
                "SQL",
                "FastAPI",
            ],
            "missing_skills": [
                "Java",
                "REST APIs",
            ],
            "gap_recommendations": [
                "Learn Java",
                "Practice REST API development",
            ],
        }

    monkeypatch.setattr(
        resumes_router.jd_matcher_service,
        "match_resume_with_jd",
        fake_match_resume_with_jd,
    )

    response = client.post(
        f"/resumes/{resume_id}/compare-jd",
        json={
            "jd_text": SAMPLE_JD,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["resume_id"] == resume_id
    assert data["match_percentage"] == 60.0
    assert data["matched_skills_count"] == 3
    assert data["missing_skills_count"] == 2

    assert "jd_metadata" in data
    assert data["jd_metadata"]["word_count"] >= 50

    assert "Python" in matcher_called["jd_text"]
    assert matcher_called["resume_skills"] == [
        "Python",
        "SQL",
        "FastAPI",
    ]


def test_jd_comparison_rejects_short_description(
    monkeypatch,
):
    """
    Verify that a job description below the minimum
    word count is rejected.
    """
    resume_id = str(uuid4())

    monkeypatch.setattr(
        resumes_router,
        "get_owned_resume_data",
        lambda resume_id, current_user: (
            {
                "skills": ["Python", "SQL"],
                "education": [],
                "projects": [],
                "experience": [],
            },
            SAMPLE_RESUME_TEXT,
        ),
    )

    response = client.post(
        f"/resumes/{resume_id}/compare-jd",
        json={
            "jd_text": "Python developer required with SQL knowledge."
        },
    )

    assert response.status_code == 400
