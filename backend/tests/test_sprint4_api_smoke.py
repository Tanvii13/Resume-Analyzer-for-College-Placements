"""
Sprint 4 API smoke tests: the real FastAPI app, real routers, auth and database stubbed.

Checks that every Sprint 4 endpoint is mounted and answers with its declared response model:
- /opportunities/recommended and /opportunities/evaluate-match   (US-12, US-13)
- /resume-insights/match-job-description                          (US-11, US-13)
- /dashboard/overview access control                              (Sprint 4 dashboard)

These guard against the integration problems found during Sprint 4 testing: the backend
failing to import (indentation error in resumes.py, dashboard module outside backend/), and
the opportunities router not being mounted.
"""

import pytest
from fastapi.testclient import TestClient

import app.routers.dashboard as dashboard_router_module
import app.routers.opportunities as opportunities_module
from app.routers.auth import UserResponse, get_current_user
from main import app

SPRINT4_PATHS = {
    "/opportunities/recommended",
    "/opportunities/evaluate-match",
    "/resume-insights/match-job-description",
    "/dashboard/overview",
    "/dashboard/skill-deficits",
    "/resumes/{resume_id}/compare-jd",
}


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def login_as(role: str):
    app.dependency_overrides[get_current_user] = lambda: UserResponse(email=f"{role}@college.edu", role=role)


def test_all_sprint4_routes_are_mounted(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    assert SPRINT4_PATHS <= paths, SPRINT4_PATHS - paths


def test_health(client):
    assert client.get("/health").status_code == 200


def test_opportunities_require_login(client):
    assert client.get("/opportunities/recommended").status_code == 401


def test_recommended_opportunities(client, monkeypatch):
    login_as("student")
    monkeypatch.setattr(opportunities_module, "get_student_resume_skills",
                        lambda user: ["Python", "FastAPI", "PostgreSQL", "SQL", "Docker", "Git"])
    res = client.get("/opportunities/recommended")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total_opportunities_evaluated"] >= 1
    scores = [o["match_percentage"] for o in body["recommended_opportunities"]]
    assert scores == sorted(scores, reverse=True)  # US-12 AC 2: ordered by relevance
    first = body["recommended_opportunities"][0]["skills_breakdown"]
    assert set(first) == {"matched_required", "related_required", "missing_required",
                          "matched_preferred", "related_preferred", "missing_preferred"}  # US-13 AC 1, 2


def test_evaluate_single_match(client, monkeypatch):
    login_as("student")
    monkeypatch.setattr(opportunities_module, "get_student_resume_skills", lambda user: ["Python", "SQL"])
    opp_id = opportunities_module.CAMPUS_OPPORTUNITIES_POOL[0]["id"]
    res = client.post("/opportunities/evaluate-match", json={"opportunity_id": opp_id})
    assert res.status_code == 200, res.text
    assert res.json()["opportunity_id"] == opp_id


def test_match_job_description(client):
    res = client.post("/resume-insights/match-job-description", json={
        "resume_skills": ["Python", "SQL", "Git"],
        "jd_text": "We need a backend intern with Python, SQL, Docker and REST API experience.",
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert "Python" in body["matched_skills"]
    assert body["missing_skills_count"] == len(body["missing_skills"])


def test_dashboard_blocks_students(client):
    login_as("student")
    assert client.get("/dashboard/overview", params={"batch_year": 2026}).status_code == 403


def test_dashboard_allows_placement_officer(client, monkeypatch):
    login_as("placement_officer")
    monkeypatch.setattr(dashboard_router_module, "calculate_batch_metrics",
                        lambda batch_year: {"batch_year": batch_year, "total_students": 0})
    res = client.get("/dashboard/overview", params={"batch_year": 2026})
    assert res.status_code == 200, res.text
    assert res.json()["batch_year"] == 2026
