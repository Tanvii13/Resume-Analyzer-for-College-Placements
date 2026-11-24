"""Sprint 5 Module A tests for the read-only staff analysis adapter."""

import pytest

from app.nlp.analysis import ResumeAnalysisPipeline
from app.nlp.job_matching import ResumeJobMatcher
from app.nlp.job_matching.schemas import JobSkillRequirement, ParsedJobDescription
from app.nlp.schemas import CandidateProfile, ProjectEntry, SkillItem
from app.nlp.staff_insights import (
    StaffAnalysisBuilder,
    UnsupportedSchemaVersionError,
    build_staff_analysis,
)


def profile() -> CandidateProfile:
    return CandidateProfile(
        filename="student.pdf",
        technical_skills=[
            SkillItem(canonical_name="Python", matched_alias="python", category="Programming Languages"),
            SkillItem(canonical_name="Docker", matched_alias="docker", category="DevOps"),
        ],
        soft_skills=[SkillItem(canonical_name="Communication", matched_alias="communication", category="Soft Skills")],
        projects=[ProjectEntry(title="Placement API", technologies=["Python"], description="Built an API that improved processing by 25%.")],
    )


def test_complete_student_analysis_preserves_upstream_scores_and_evidence():
    candidate = profile()
    analysis = ResumeAnalysisPipeline().analyze(candidate)
    job = ParsedJobDescription(
        title="Backend Intern",
        required_technical_skills=[
            JobSkillRequirement(canonical_name="Python", matched_alias="python", category="Programming Languages", is_required=True),
            JobSkillRequirement(canonical_name="React", matched_alias="react", category="Frontend Development", is_required=True),
        ],
    )
    match = ResumeJobMatcher().match(candidate, job)
    result = build_staff_analysis(candidate, analysis, [match])

    assert result.resume_overview.overall_score.overall_score == analysis.overall_score
    assert result.job_matching_overview.best_matching_opportunities[0].matching_score == match.overall_score
    assert result.skills_overview.supported_skills[0].name == "Python"
    assert "Docker" in result.summary.skills_requiring_evidence
    assert result.model_dump()["improvement_overview"]["actionable_recommendations"]


def test_missing_analysis_and_job_matches_are_unavailable_not_negative_findings():
    result = build_staff_analysis(profile())

    assert result.resume_overview.overall_score.overall_score is None
    assert result.resume_overview.overall_score.availability.status == "unavailable"
    assert result.job_matching_overview.availability.status == "unavailable"
    assert result.improvement_overview.missing_measurable_achievements.detected is None


def test_empty_candidate_profile_and_partial_analysis_are_serializable():
    empty = CandidateProfile(filename="empty.pdf")
    analysis = ResumeAnalysisPipeline().analyze(empty)
    result = StaffAnalysisBuilder().build(empty, analysis, [])

    assert result.skills_overview.technical_skills == []
    assert result.job_matching_overview.availability.status == "available"
    assert result.job_matching_overview.best_matching_opportunities == []
    assert "filename" not in result.model_dump(mode="json")


def test_missing_analysis_sections_are_marked_unavailable():
    candidate = profile()
    analysis = ResumeAnalysisPipeline().analyze(candidate)
    analysis.component_scores.pop("content_quality", None)
    analysis.formatting_analysis = None
    result = build_staff_analysis(candidate, analysis)

    assert result.resume_overview.content_quality.availability.status == "unavailable"
    assert result.resume_overview.formatting_quality.availability.status == "unavailable"


def test_unsupported_upstream_schema_versions_are_rejected():
    candidate = profile()
    candidate.pipeline_version = "1.9.0"

    with pytest.raises(UnsupportedSchemaVersionError, match="CandidateProfile"):
        build_staff_analysis(candidate)


def test_builder_does_not_mutate_source_models():
    candidate = profile()
    before = candidate.model_dump(mode="json")
    build_staff_analysis(candidate)
    assert candidate.model_dump(mode="json") == before


def test_staff_projection_excludes_identity_and_contact_details():
    candidate = profile()
    candidate.filename = "Aarav-Sharma-resume.pdf"
    candidate.contact.full_name = "Aarav Sharma"
    candidate.contact.email = "aarav.sharma@example.edu"
    candidate.contact.phone = "+91 9876543210"

    output = build_staff_analysis(candidate).model_dump_json().lower()

    for value in (candidate.filename, candidate.contact.full_name, candidate.contact.email, candidate.contact.phone):
        assert value.lower() not in output
