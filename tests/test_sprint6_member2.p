import pytest
from uuid import uuid4
from app.schemas.fairness_schemas import (
    FactorContribution,
    ScoreFactorBreakdown,
    FairnessAuditRequest,
    FairnessAuditReport,
)
from app.services.fairness_audit_service import FairnessAuditService


def test_factor_attribution_decomposition():
    skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]
    raw_text = (
        "Developed microservices as backend engineering intern. Achieved 99.9% uptime across 50,000 requests. "
        "Education: B.Tech in ICT. Skills: Python, FastAPI, Docker. "
        "Experience: Intern at TechCorp. Projects: Scalable API."
    )
    resume_id = str(uuid4())

    breakdown = FairnessAuditService.compute_factor_attribution(
        resume_id=resume_id,
        skills=skills,
        raw_text=raw_text,
    )

    assert breakdown.resume_id == resume_id
    assert len(breakdown.factors) == 4

    factor_names = [f.factor_name for f in breakdown.factors]
    assert "Technical Skills Alignment" in factor_names
    assert "Experience & Domain Depth" in factor_names
    assert "Project Quantification & Impact" in factor_names
    assert "ATS Readability & Section Structure" in factor_names

    # Total weight percentage must sum to 100%
    total_weight = sum(f.weight_percentage for f in breakdown.factors)
    assert total_weight == 100.0

    # Positive drivers should be identified
    tech_factor = next(f for f in breakdown.factors if f.factor_name == "Technical Skills Alignment")
    assert len(tech_factor.positive_drivers) > 0


def test_advisory_notice_enforcement():
    breakdown = FairnessAuditService.compute_factor_attribution(
        resume_id=str(uuid4()),
        skills=["Python"],
        raw_text="Education: B.Tech. Skills: Python.",
    )

    # Mandatory advisory notice per US-18 / US-19
    assert "supporting information only" in breakdown.advisory_notice.lower()
    assert "human decision makers" in breakdown.advisory_notice.lower()
    assert breakdown.is_fairness_certified is True


def test_demographic_neutrality_invariance():
    text = "He is a backend developer with expertise in Python, FastAPI, and Docker. He built scalable microservices."

    def skill_scoring(t: str) -> float:
        # Evaluates purely technical keywords
        tokens = ["python", "fastapi", "docker", "microservices", "developer"]
        return sum(20.0 for token in tokens if token in t.lower())

    is_neutral, delta = FairnessAuditService.verify_demographic_invariance(
        text=text,
        scoring_fn=skill_scoring
    )

    assert is_neutral is True
    assert delta == 0.0


def test_demographic_token_detection():
    resume_text = "Candidate is single. Marital Status: Unmarried. DOB: 12/05/2002. He has proficiency in Python and SQL."
    detected = FairnessAuditService.scan_demographic_tokens(resume_text)

    assert "gender_pronouns" in detected
    assert "marital_status" in detected
    assert "age_indicators" in detected


def test_fairness_audit_report_generation():
    raw_text = "Experienced engineer proficient in Python and React. Demonstrated 40% latency reduction."
    skills = ["Python", "React"]

    report = FairnessAuditService.generate_fairness_audit(
        raw_text=raw_text,
        skills=skills,
    )

    assert report.fairness_audit_passed is True
    assert report.advisory_status == "SUPPORTING_INFORMATION_ONLY"
    assert report.score_disparity_detected is False
    assert report.disparity_delta == 0.0


def test_counterfactual_disparity_detection():
    # Verifies that a biased scoring function correctly triggers a disparity alert
    text = "He is an engineer with Python proficiency."

    def biased_scoring(t: str) -> float:
        # Intentionally unfair scorer that gives 50 extra points if female pronoun is present
        base = 50.0 if "python" in t.lower() else 0.0
        if "she" in t.lower() or "her" in t.lower():
            base += 50.0
        return base

    is_neutral, delta = FairnessAuditService.verify_demographic_invariance(
        text=text,
        scoring_fn=biased_scoring
    )

    # Must detect the unfair disparity
    assert is_neutral is False
    assert delta > 0.0


def test_fairness_schemas_validation():
    factor = FactorContribution(
        factor_name="Technical Skills Alignment",
        weight_percentage=40.0,
        points_awarded=35.0,
        max_points=40.0,
        description="Evaluates technical stack overlap",
        positive_drivers=["Strong Python proficiency"],
        negative_penalties=[]
    )
    assert factor.points_awarded == 35.0

    request = FairnessAuditRequest(
        raw_text="Candidate with Python skills",
        extracted_skills=["Python"]
    )
    assert request.extracted_skills == ["Python"]

    report = FairnessAuditReport(
        is_demographically_neutral=True,
        fairness_audit_passed=True,
        flags=["Neutrality certified"]
    )
    assert report.is_demographically_neutral is True
    assert report.advisory_status == "SUPPORTING_INFORMATION_ONLY"
