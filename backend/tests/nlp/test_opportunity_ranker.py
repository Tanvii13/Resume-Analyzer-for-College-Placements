"""
Unit tests for Sprint 4 – Module E: Job/Internship Relevance Ranking (US-12).

Covers:
- Openings ordered by relevance (US-12 AC 2), eligible before not-eligible
- Ranking reasons, including why an opening is below the one above it
- Clear message when nothing suitable is found (US-12 AC 3) and when nothing is given
- Raw JD text, structured backend records and ParsedJobDescription inputs
- Employer-listed skills merged with parsed JD text; unknown taxonomy skills still required
- JDs with no readable skills are not reported as good fits
- Experience-gap penalty; "X or Y" requirements don't cost points
- Preferences: job type, location (remote allowed), minimum relevance, top_k, excluding ineligible
- Common gaps across openings
- Bad records reported in `errors` without stopping the ranking
- Output converts to the backend's OpportunityRecommendationsResponse schema
- Deterministic order
"""

from pathlib import Path

import pytest
from app.nlp import ResumeNLPPipeline
from app.nlp.job_matching import parse_job_description
from app.nlp.job_matching.opportunity_ranker import (
    OpportunityRanker,
    fit_tier,
    job_type_from_text,
)
from app.nlp.job_matching.ranking_schemas import (
    FitTier,
    JobOpportunity,
    RankingPreferences,
)
from app.nlp.job_matching.schemas import JobType
from app.nlp.job_matching.skill_gap_schemas import EligibilityStatus

FIX = Path(__file__).parent / "fixtures"
JOBS = sorted((FIX / "sprint4" / "jobs").glob("*.txt"))


def job_list():
    return [JobOpportunity(opportunity_id=p.stem, description=p.read_text(encoding="utf-8")) for p in JOBS]


@pytest.fixture(scope="module")
def nlp():
    return ResumeNLPPipeline()


@pytest.fixture(scope="module")
def ranker():
    return OpportunityRanker()


@pytest.fixture(scope="module")
def strong(nlp):
    return nlp.process((FIX / "sprint3" / "s3_01_strong.txt").read_text(encoding="utf-8"), "strong.txt")


@pytest.fixture(scope="module")
def ece(nlp):
    return nlp.process((FIX / "sprint3" / "s3_08_no_work_experience.txt").read_text(encoding="utf-8"), "ece.txt")


@pytest.fixture(scope="module")
def strong_report(ranker, strong):
    return ranker.rank(strong, job_list())


# ============================================================================
# Ordering
# ============================================================================

def test_ranks_are_contiguous_and_complete(strong_report):
    ranks = [r.rank for r in strong_report.ranked_opportunities]
    assert ranks == list(range(1, len(JOBS) + 1))
    assert strong_report.total_evaluated == len(JOBS)
    assert strong_report.errors == []


def test_eligible_before_not_eligible_then_by_relevance(strong_report):
    items = strong_report.ranked_opportunities
    eligible = [r for r in items if r.eligibility_status != EligibilityStatus.NOT_MET]
    blocked = [r for r in items if r.eligibility_status == EligibilityStatus.NOT_MET]
    assert items == eligible + blocked
    for group in (eligible, blocked):
        scores = [r.relevance_score for r in group]
        assert scores == sorted(scores, reverse=True)


def test_best_match_for_cs_backend_student(strong_report):
    top = strong_report.ranked_opportunities[0]
    assert top.opportunity_id == "j01_backend_intern"
    assert top.fit_tier == FitTier.HIGH and top.is_suitable


def test_best_match_for_ece_student(ranker, ece):
    rep = ranker.rank(ece, job_list())
    assert rep.ranked_opportunities[0].opportunity_id == "j05_embedded_intern"
    # CS-only openings are marked not eligible for an ECE student
    blocked = {r.opportunity_id for r in rep.ranked_opportunities if r.eligibility_status == EligibilityStatus.NOT_MET}
    assert {"j04_ml_intern", "j06_devops_intern"} <= blocked


def test_branch_restricted_job_is_not_eligible_for_other_branch(strong_report):
    by = {r.opportunity_id: r for r in strong_report.ranked_opportunities}
    assert by["j05_embedded_intern"].eligibility_status == EligibilityStatus.NOT_MET
    assert not by["j05_embedded_intern"].is_suitable
    assert any("branch" in i.lower() for i in by["j05_embedded_intern"].eligibility_issues)


def test_every_item_explains_its_position(strong_report):
    items = strong_report.ranked_opportunities
    for r in items:
        assert r.ranking_reasons and r.summary
    for r in items[1:]:
        assert any(reason.startswith(("Ranked below", "Same relevance")) for reason in r.ranking_reasons)


def test_jd_without_readable_skills_is_not_a_good_fit(strong_report):
    mech = next(r for r in strong_report.ranked_opportunities if r.opportunity_id == "j08_mechanical_design")
    assert mech.fit_tier == FitTier.DEVELOPING and not mech.is_suitable
    assert any("No technical skills could be read" in x for x in mech.ranking_reasons)


def test_experience_requirement_lowers_relevance(strong_report):
    sde = next(r for r in strong_report.ranked_opportunities if r.opportunity_id == "j07_fullstack_sde")
    assert not sde.is_suitable
    assert any("2 years" in x for x in sde.ranking_reasons)


def test_either_or_requirement_does_not_cost_points(ranker, nlp):
    text = "Kiran\nkiran@gmail.com\n\nEDUCATION\nB.Tech in CSE, Nirma University, 2022 - 2026, CGPA 8.0/10\n\nSKILLS\nJava, Git\n"
    p = nlp.process(text, "k.txt")
    either = JobOpportunity(opportunity_id="either", title="Either",
                            description="Role\n\nRequired Skills\n- Strong programming skills in Python or Java\n- Git\n")
    rep = ranker.rank(p, [either])
    assert rep.ranked_opportunities[0].required_coverage == 1.0
    assert rep.ranked_opportunities[0].missing_required == []


# ============================================================================
# "No suitable opportunity" messaging (US-12 AC 3)
# ============================================================================

def test_no_suitable_match_message(ranker, nlp):
    weak = nlp.process((FIX / "sprint3" / "s3_02_weak.txt").read_text(encoding="utf-8"), "weak.txt")
    rep = ranker.rank(weak, job_list())
    assert not rep.has_suitable_matches and rep.suitable_count == 0
    assert rep.guidance_message.startswith("No opportunity is a strong match")
    assert rep.ranked_opportunities[0].title in rep.guidance_message


def test_empty_input(ranker, strong):
    rep = ranker.rank(strong, [])
    assert rep.total_evaluated == 0 and rep.ranked_opportunities == []
    assert "No opportunities are available" in rep.guidance_message


def test_good_match_message(strong_report):
    assert strong_report.has_suitable_matches
    assert strong_report.guidance_message.startswith(f"{strong_report.suitable_count} of {len(JOBS)}")


# ============================================================================
# Inputs
# ============================================================================

SEED = [
    {"id": "seed-1", "title": "Python Backend Developer", "company": "Example Technologies", "location": "Ahmedabad",
     "opportunity_type": "Internship", "description": "Entry-level backend development opportunity.",
     "required_skills": ["Python", "SQL", "REST API"], "preferred_skills": ["FastAPI", "PostgreSQL", "Git"], "min_cgpa": 6.0},
    {"id": "seed-2", "title": "Frontend Developer Intern", "company": "Example Software", "location": "Pune",
     "opportunity_type": "Internship", "description": "Frontend internship for college students.",
     "required_skills": ["HTML", "CSS", "JavaScript"], "preferred_skills": ["React", "Git"], "min_cgpa": 6.5},
    {"id": "seed-3", "title": "Data Analyst", "company": "Example Analytics", "location": "Remote",
     "opportunity_type": "Full-time", "description": "Entry-level data analysis opportunity.",
     "required_skills": ["Python", "SQL", "Excel"], "preferred_skills": ["Power BI", "Pandas"], "min_cgpa": 9.5},
]


def test_backend_records(ranker, strong):
    rep = ranker.rank(strong, SEED)
    by = {r.opportunity_id: r for r in rep.ranked_opportunities}
    assert by["seed-1"].rank == 1
    assert "RESTful APIs" in by["seed-1"].matched_required  # "REST API" normalized
    assert by["seed-3"].eligibility_status == EligibilityStatus.NOT_MET  # min_cgpa 9.5 > 9.12
    assert "Excel" in by["seed-3"].missing_required  # unknown to the taxonomy but still required


def test_persisted_opportunity_row_shape(ranker, strong):
    """Exact dict shape returned by services/opportunity_persistence.get_opportunities()."""
    import datetime

    row = {"id": "11111111-1111-1111-1111-111111111111", "title": "Python Backend Developer",
           "company": "Example Technologies", "description": "Entry-level backend development opportunity.",
           "required_skills": ["Python", "SQL", "REST API"], "preferred_skills": ["FastAPI", "PostgreSQL", "Git"],
           "min_cgpa": 6.0, "deadline": datetime.date(2026, 12, 15), "is_active": True,
           "created_at": datetime.datetime(2026, 11, 17, 10, 0, tzinfo=datetime.UTC)}
    rep = ranker.rank(strong, [row])
    assert rep.errors == []
    assert rep.ranked_opportunities[0].opportunity_id == row["id"]
    assert JobOpportunity.from_record(row).deadline == "2026-12-15"


def test_backend_response_shape(ranker, strong):
    schemas = pytest.importorskip("app.schemas.opportunity_schemas", reason="backend schemas not on this branch")
    OpportunityRecommendationsResponse = schemas.OpportunityRecommendationsResponse

    rep = ranker.rank(strong, SEED)
    response = OpportunityRecommendationsResponse(**rep.to_backend_response())
    assert response.total_opportunities_evaluated == 3
    card = response.recommended_opportunities[0]
    assert card.relevance_tier in {"High Fit", "Moderate Fit", "Developing Fit"}
    assert card.skills_breakdown.matched_required


def test_structured_skills_merge_with_description(ranker):
    opp = JobOpportunity(opportunity_id="m", title="Backend", required_skills=["Docker"], preferred_skills=["Python"],
                         description=(JOBS[0]).read_text(encoding="utf-8"), min_cgpa=8.0)
    parsed = ranker.to_parsed_job(opp)
    req = {s.canonical_name for s in parsed.required_technical_skills}
    pref = {s.canonical_name for s in parsed.preferred_technical_skills}
    assert "Docker" in req and "Docker" not in pref  # listed as required wins over parser's preferred
    assert "Python" in req  # already required in the text; not downgraded
    assert parsed.eligibility.min_cgpa == 8.0
    assert parsed.title == "Backend"


def test_parsed_job_input(ranker, strong):
    parsed = parse_job_description(JOBS[1].read_text(encoding="utf-8"), job_id="frontend")
    rep = ranker.rank(strong, [parsed])
    assert rep.ranked_opportunities[0].opportunity_id == "frontend"


def test_bad_record_is_reported_not_fatal(ranker, strong):
    rep = ranker.rank(strong, [SEED[0], {"id": "broken", "min_cgpa": "not-a-number"}])
    assert len(rep.ranked_opportunities) == 1
    assert rep.errors and rep.errors[0]["opportunity_id"] == "broken"


# ============================================================================
# Preferences
# ============================================================================

def test_job_type_filter(ranker, strong):
    rep = ranker.rank(strong, job_list(), RankingPreferences(job_types=["internship"]))
    assert all(r.opportunity_type == "internship" for r in rep.ranked_opportunities)
    assert {f.opportunity_id for f in rep.filtered_out} >= {"j03_data_analyst", "j07_fullstack_sde"}


def test_location_filter_keeps_remote(ranker, strong):
    rep = ranker.rank(strong, job_list(), RankingPreferences(locations=["Pune"]))
    kept = {r.opportunity_id for r in rep.ranked_opportunities}
    assert "j07_fullstack_sde" in kept and "j04_ml_intern" in kept  # Pune + Remote
    assert "j01_backend_intern" not in kept


def test_min_relevance_top_k_and_exclude_ineligible(ranker, strong):
    rep = ranker.rank(strong, job_list(), RankingPreferences(min_relevance=50, include_ineligible=False, top_k=2))
    assert len(rep.ranked_opportunities) == 2
    assert all(r.relevance_score >= 50 and r.eligibility_status != EligibilityStatus.NOT_MET
               for r in rep.ranked_opportunities)
    assert any("Not eligible" in f.reason for f in rep.filtered_out)


def test_filtered_everything_message(ranker, strong):
    rep = ranker.rank(strong, job_list(), RankingPreferences(locations=["Chennai"], job_types=["full-time"]))
    assert rep.ranked_opportunities == []
    assert len(rep.filtered_out) == len(JOBS)
    assert not rep.has_suitable_matches
    assert "filtered out" in rep.guidance_message


# ============================================================================
# Misc
# ============================================================================

def test_common_gaps(ranker, nlp):
    p = nlp.process("Neel\nneel@gmail.com\n\nEDUCATION\nB.Tech in CSE, Nirma University, 2022 - 2026, CGPA 8/10\n\nSKILLS\nPython\n", "n.txt")
    jobs = [JobOpportunity(opportunity_id=f"o{i}", title=f"Role {i}", required_skills=["Python", "Docker", "SQL"]) for i in range(3)]
    rep = ranker.rank(p, jobs)
    gaps = {g.skill: g.missing_in for g in rep.common_gaps}
    assert gaps.get("Docker") == 3 and gaps.get("SQL") == 3
    assert "Python" not in gaps


def test_include_details(ranker, strong):
    rep = ranker.rank(strong, job_list()[:1], include_details=True)
    item = rep.ranked_opportunities[0]
    assert item.match_result is not None and item.skill_gap is not None
    assert ranker.rank(strong, job_list()[:1]).ranked_opportunities[0].match_result is None


def test_deterministic(ranker, strong):
    a = ranker.rank(strong, job_list()).model_dump(exclude={"processing_time_ms"})
    b = ranker.rank(strong, list(reversed(job_list()))).model_dump(exclude={"processing_time_ms"})
    assert a == b


@pytest.mark.parametrize("score, tier", [(85, FitTier.HIGH), (70, FitTier.HIGH), (69.9, FitTier.MODERATE),
                                          (50, FitTier.MODERATE), (49.9, FitTier.DEVELOPING)])
def test_fit_tiers(score, tier):
    assert fit_tier(score) == tier


@pytest.mark.parametrize("text, jt", [("Internship", JobType.INTERNSHIP), ("Full-time", JobType.FULL_TIME),
                                      ("full time", JobType.FULL_TIME), ("Contract", JobType.CONTRACT), (None, JobType.UNKNOWN)])
def test_job_type_text(text, jt):
    assert job_type_from_text(text) == jt
