import pytest
from app.services.suggestion_service import SuggestionService
from app.services.jd_matcher import JDMatcherService


# =====================================================================
# US-09 TESTS: Suggestion & STAR Bullet Rewriter Engine
# =====================================================================

def test_bullet_point_weak_verb_detection():
    service = SuggestionService()
    weak_bullet = "Worked on Python backend development and helped with API design."
    analysis = service.analyze_bullet_point(weak_bullet)

    assert analysis["is_weak"] is True
    assert "worked on" in analysis["weak_verbs_found"]
    assert "helped" in analysis["weak_verbs_found"]
    assert "Replace weak verbs" in analysis["suggestion"]


def test_bullet_point_comma_metric_and_power_verb():
    service = SuggestionService()
    strong_bullet = "Engineered backend microservices serving 1,000 users with 99.9% uptime."
    analysis = service.analyze_bullet_point(strong_bullet)

    assert analysis["has_action_verb"] is True
    assert analysis["action_verb_used"] == "engineered"
    assert analysis["has_quantified_metric"] is True
    assert "1,000 users" in analysis["detected_metric"]
    assert analysis["is_weak"] is False


def test_bullet_rejects_project_count_as_metric():
    service = SuggestionService()
    bullet_without_impact = "Developed 3 projects using Python and Django."
    analysis = service.analyze_bullet_point(bullet_without_impact)

    # '3 projects' should NOT pass as quantifiable impact metric
    assert analysis["has_quantified_metric"] is False
    assert analysis["is_weak"] is True


def test_empty_bullet_raises_value_error():
    service = SuggestionService()
    with pytest.raises(ValueError):
        service.analyze_bullet_point("   ")


def test_generate_resume_suggestions_holistic():
    service = SuggestionService()
    sample_skills = {"technical_skills": ["Python", "SQL"], "soft_skills": []}
    sample_text = "Experienced in Python. Contact: test@gmail.com"

    suggestions = service.generate_resume_suggestions(sample_skills, sample_text)

    sections = [s["section"] for s in suggestions]
    assert "Skills" in sections
    assert "Projects" in sections
    assert len(suggestions) >= 2


# =====================================================================
# US-11 TESTS: JD Matcher, Alias Normalization & Skill Gap
# =====================================================================

def test_jd_skill_extraction_and_alias_normalization():
    matcher = JDMatcherService()
    jd_text = """
    Looking for a Backend Developer skilled in Python, FastAPI, and Postgres.
    Experience with k8s and Docker is required.
    """
    extracted_skills = matcher.extract_jd_skills(jd_text)

    # Aliases should be mapped to standard names
    assert "PostgreSQL" in extracted_skills    # Normalized from 'Postgres'
    assert "Kubernetes" in extracted_skills    # Normalized from 'k8s'
    assert "Python" in extracted_skills
    assert "FastAPI" in extracted_skills


def test_match_resume_with_jd_gap_calculation():
    matcher = JDMatcherService()
    resume_skills = ["Python", "FastAPI", "PostgreSQL", "Git"]
    jd_text = """
    Requirements:
    - Python, FastAPI, PostgreSQL
    - Docker, Kubernetes, AWS
    """
    result = matcher.match_resume_with_jd(resume_skills, jd_text)

    assert "Python" in result["matched_skills"]
    assert "FastAPI" in result["matched_skills"]
    assert "PostgreSQL" in result["matched_skills"]

    assert "Docker" in result["missing_skills"]
    assert "Kubernetes" in result["missing_skills"]
    assert "AWS" in result["missing_skills"]

    # 3 matched out of 6 JD skills = 50.0%
    assert result["matched_skills_count"] == 3
    assert result["missing_skills_count"] == 3
    assert result["match_percentage"] == 50.0
    assert len(result["gap_recommendations"]) > 0


def test_match_resume_with_empty_jd():
    matcher = JDMatcherService()
    result = matcher.match_resume_with_jd(["Python"], "")

    assert result["total_jd_skills_found"] == 0
    assert result["match_percentage"] == 0.0
    assert "No technical or soft skills could be detected" in result["gap_recommendations"][0]


def test_jd_matcher_invalid_types_raise_error():
    matcher = JDMatcherService()
    with pytest.raises(TypeError):
        matcher.match_resume_with_jd("not-a-list", "some jd text")
    with pytest.raises(TypeError):
        matcher.extract_jd_skills(12345)
