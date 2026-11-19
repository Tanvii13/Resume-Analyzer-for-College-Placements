

from fastapi.testclient import TestClient

from main import app
from app.routers import resume_insights


client = TestClient(app)


def test_analyze_bullet_endpoint(monkeypatch):
    def mock_analyze(bullet):
        return {
            "original_text": bullet,
            "is_weak": False,
            "weak_verbs_found": [],
            "has_action_verb": True,
            "action_verb_used": "Developed",
            "has_quantified_metric": True,
            "detected_metric": "30%",
            "suggestion": "Keep the bullet concise.",
            "star_template_example": "Developed a project using Python."
        }

    monkeypatch.setattr(
        resume_insights.suggestion_service,
        "analyze_bullet_point",
        mock_analyze
    )

    response = client.post(
        "/resume-insights/analyze-bullet",
        json={"bullet": "Developed a Python application"}
    )

    assert response.status_code == 200
    assert response.json()["original_text"] == (
        "Developed a Python application"
    )


def test_analyze_bullet_rejects_empty_input():
    response = client.post(
        "/resume-insights/analyze-bullet",
        json={"bullet": ""}
    )

    assert response.status_code == 422


def test_resume_suggestions_endpoint(monkeypatch):
    def mock_suggestions(**kwargs):
        return [
            {
                "section": "Projects",
                "priority": "High",
                "issue": "Project description is unclear.",
                "recommendation": "Include measurable outcomes."
            }
        ]

    monkeypatch.setattr(
        resume_insights.suggestion_service,
        "generate_resume_suggestions",
        mock_suggestions
    )

    response = client.post(
        "/resume-insights/suggestions",
        json={
            "extracted_skills": {
                "technical_skills": ["Python"],
                "soft_skills": ["Communication"]
            },
            "raw_text": "Python developer with project experience."
        }
    )

    assert response.status_code == 200
    assert len(response.json()["suggestions"]) == 1


def test_job_description_matching_endpoint(monkeypatch):
    def mock_match(resume_skills, jd_text):
        return {
            "total_jd_skills_found": 3,
            "matched_skills_count": 2,
            "missing_skills_count": 1,
            "match_percentage": 66.7,
            "matched_skills": ["Python", "SQL"],
            "missing_skills": ["Docker"],
            "gap_recommendations": [
                "Consider learning Docker."
            ]
        }

    monkeypatch.setattr(
        resume_insights.jd_matcher_service,
        "match_resume_with_jd",
        mock_match
    )

    response = client.post(
        "/resume-insights/match-job-description",
        json={
            "resume_skills": ["Python", "SQL"],
            "jd_text": "Python, SQL and Docker required."
        }
    )

    assert response.status_code == 200
    assert response.json()["match_percentage"] == 66.7
    assert response.json()["missing_skills"] == ["Docker"]


def test_job_matching_rejects_empty_jd():
    response = client.post(
        "/resume-insights/match-job-description",
        json={
            "resume_skills": ["Python"],
            "jd_text": ""
        }
    )

    assert response.status_code == 422
