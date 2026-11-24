"""
Integration tests for Sprint 4 – Module F: the end-to-end job matching workflow.

Covers:
- compare(): resume text / CandidateProfile x JD text / backend record / ParsedJobDescription
- Every stage reported in metadata; failures isolated with structured errors
- Adapters validate against the backend's real response schemas
  (JDMatchResponse, JDCompareResponse, OpportunityRecommendationsResponse)
- rank(): raw texts and records together
- Matching and missing skills shown separately; required vs preferred kept apart (US-13)
- Consistency between Modules C, D and E for the same pair
- Serialization round trip, determinism, latency
- Sprint 2 CandidateProfile not mutated
"""

import time
from pathlib import Path
from uuid import uuid4

import pytest
from app.nlp import ResumeNLPPipeline
from app.nlp.job_matching import parse_job_description
from app.nlp.job_matching.ranking_schemas import JobOpportunity
from app.nlp.job_matching.workflow import (
    JobFitReport,
    JobMatchingWorkflow,
    get_job_matching_workflow,
)

FIX = Path(__file__).parent / "fixtures"
JOBS = sorted((FIX / "sprint4" / "jobs").glob("*.txt"))
RESUME = (FIX / "sprint3" / "s3_11_measurable_achievements.txt").read_text(encoding="utf-8")
JD = JOBS[0].read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def wf():
    return JobMatchingWorkflow()


@pytest.fixture(scope="module")
def report(wf):
    return wf.compare(RESUME, JD, "nikhil.txt", job_id="j01")


def test_compare_runs_every_stage(report):
    assert report.metadata.stage_status == {
        "resume": "ok", "job_description": "ok", "matching": "ok", "skill_gap": "ok", "relevance": "ok"}
    assert report.metadata.errors == []
    for key in ("workflow", "job_parser", "skill_engine", "matcher", "skill_gap", "ranker"):
        assert key in report.metadata.versions


def test_compare_output(report):
    assert "candidate_name" not in report.model_dump(mode="json")
    assert report.job.title.startswith("Software Development Engineer Intern")
    assert report.match is not None and report.skill_gap is not None
    assert 0 <= report.relevance_score <= 100 and report.fit_tier is not None
    assert report.summary.startswith(report.fit_tier.value)
    assert report.jd_word_count > 50


def test_matching_and_missing_separate(report):
    gap = report.skill_gap
    matched = {i.skill for i in gap.matched_required + gap.matched_preferred}
    missing = {i.skill for i in gap.missing_required + gap.missing_preferred}
    assert matched and missing and not (matched & missing)
    assert {i.skill for i in gap.matched_required}.isdisjoint({i.skill for i in gap.matched_preferred})


def test_modules_agree(wf, report):
    """C, D and E describe the same pair consistently."""
    gap, match = report.skill_gap, report.match
    c_missing = {m.requirement_name for m in match.missing_requirements if m.requirement_type.value.endswith("technical_skill")}
    d_missing = {i.skill for i in gap.missing_required + gap.missing_preferred}
    d_alt = {i.skill for i in gap.matched_required + gap.matched_preferred if i.status.value == "satisfied_by_alternative"}
    assert d_missing <= c_missing  # D never invents a missing skill
    assert c_missing <= d_missing | d_alt  # every C miss is still missing or covered by an "X or Y" alternative
    profile = ResumeNLPPipeline().process(RESUME, "nikhil.txt")
    ranked = wf.rank(profile, [JobOpportunity(opportunity_id="j01", description=JD)]).ranked_opportunities[0]
    assert ranked.relevance_score == report.relevance_score
    assert set(ranked.missing_required) == {i.skill for i in gap.missing_required}


@pytest.mark.parametrize("kind", ["profile", "record", "parsed", "opportunity"])
def test_compare_input_types(wf, report, kind):
    profile = ResumeNLPPipeline().process(RESUME, "nikhil.txt")
    job = {
        "profile": JD,
        "record": {"id": "j01", "description": JD},
        "parsed": parse_job_description(JD, job_id="j01"),
        "opportunity": JobOpportunity(opportunity_id="j01", description=JD),
    }[kind]
    r = wf.compare(profile if kind == "profile" else RESUME, job, "nikhil.txt", job_id="j01")
    assert r.metadata.errors == []
    assert r.relevance_score == report.relevance_score


def test_backend_adapters_validate(report):
    schemas = pytest.importorskip("app.schemas.sprint3_schemas", reason="backend schemas not on this branch")
    JDCompareResponse, JDMatchResponse = schemas.JDCompareResponse, schemas.JDMatchResponse

    JDMatchResponse(**report.to_backend_jd_match())
    data = report.to_backend_jd_compare()
    resp = JDCompareResponse(resume_id=uuid4(), target_role=None, **data)
    assert resp.jd_metadata.title == report.job.title
    assert resp.jd_metadata.experience_level == "Fresher"
    assert resp.missing_skills_count == len(resp.missing_skills)


def test_empty_jd_is_a_structured_error(wf):
    r = wf.compare(RESUME, "   ", "x.txt")
    assert r.metadata.stage_status["job_description"] == "failed"
    assert r.metadata.stage_status["matching"] == "skipped"
    assert r.metadata.errors[0].error_type == "exception"
    assert r.relevance_score is None and "could not be completed" in r.summary


def test_bad_resume_type_is_a_structured_error(wf):
    r = wf.compare(12345, JD)
    assert r.metadata.stage_status["resume"] == "failed"
    assert "TypeError" in r.metadata.errors[0].message


def test_matcher_failure_isolated():
    wf = JobMatchingWorkflow()

    def boom(*a, **k):
        raise RuntimeError("matcher exploded")

    wf.matcher.match = boom
    r = wf.compare(RESUME, JD)
    assert r.metadata.stage_status["matching"] == "failed"
    assert r.job is not None  # earlier stage output kept
    assert "RuntimeError" in r.metadata.errors[0].message
    assert "exploded" not in r.metadata.errors[0].message


def test_jd_without_skills_warns(wf):
    r = wf.compare(RESUME, JOBS[-1].read_text(encoding="utf-8"))  # mechanical design
    assert any("No technical skills" in w for w in r.metadata.warnings)
    assert not r.is_suitable


def test_rank_mixed_inputs(wf):
    report = wf.rank(RESUME, [JD, {"id": "rec", "title": "Go Dev", "required_skills": ["Go", "Kubernetes"]}])
    assert report.total_evaluated == 2
    assert {r.opportunity_id for r in report.ranked_opportunities} == {"job-1", "rec"}


def test_round_trip_and_determinism(wf, report):
    again = JobFitReport.model_validate_json(report.model_dump_json())
    assert again == report
    other = wf.compare(RESUME, JD, "nikhil.txt", job_id="j01")
    drop = {"metadata": {"processing_time_ms", "stage_timings_ms"}, "job": {"metadata": {"processing_time_ms"}}}
    assert other.model_dump(exclude=drop) == report.model_dump(exclude=drop)


def test_profile_not_mutated(wf):
    profile = ResumeNLPPipeline().process(RESUME, "nikhil.txt")
    before = profile.model_dump()
    wf.compare(profile, JD)
    wf.rank(profile, [JD])
    assert profile.model_dump() == before


def test_latency(wf):
    profile = ResumeNLPPipeline().process(RESUME, "nikhil.txt")
    wf.compare(profile, JD)
    start = time.perf_counter()
    wf.compare(profile, JD)
    assert (time.perf_counter() - start) * 1000 < 150
    start = time.perf_counter()
    wf.rank(profile, [p.read_text(encoding="utf-8") for p in JOBS])
    assert (time.perf_counter() - start) * 1000 < 1000


def test_shared_instance():
    assert get_job_matching_workflow() is get_job_matching_workflow()
