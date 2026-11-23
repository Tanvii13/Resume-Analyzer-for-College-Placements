"""
Sprint 4 – Module F: labelled evaluation of job matching and ranking.

Runs the whole Sprint 4 workflow on 8 synthetic job descriptions x 7 synthetic student
resumes (tests/nlp/fixtures/sprint4/) and checks the measured metrics against thresholds.

Thresholds sit just below the measured values, so a regression fails the build. Each known
miss is listed in KNOWN_* with the module that causes it; when that module is fixed the
"known misses" test fails, so the list and thresholds get updated.

Labels were written from the documents before running the system (see labels.json). The set
is small and synthetic - these numbers describe these cases only, not real-world accuracy.
"""

import json
from pathlib import Path

import pytest
from app.nlp.job_matching.evaluation import JobMatchingEvaluator, ndcg_at_k

FIXTURES = Path(__file__).parent / "fixtures"

KNOWN_JD_SKILL_MISSES = {
    # Module A: "- Experience with React" / "- Familiarity with Git" are read as an EXPERIENCE heading.
    "j02_frontend_intern:react", "j02_frontend_intern:git",
    # Module B taxonomy has no Excel / embedded / mechanical skills.
    "j03_data_analyst:excel",
    "j05_embedded_intern:arduino", "j05_embedded_intern:digital electronics", "j05_embedded_intern:embedded c",
    "j05_embedded_intern:microcontrollers", "j05_embedded_intern:pcb design",
    "j08_mechanical_design:autocad", "j08_mechanical_design:engineering drawing",
    "j08_mechanical_design:solidworks", "j08_mechanical_design:strength of materials",
}
# Module A: "Work with product and QA teams" (responsibilities) becomes required skill "Quality Assurance".
KNOWN_JD_EXTRA_SKILLS = {"j01_backend_intern:quality assurance"}


@pytest.fixture(scope="module")
def evaluation():
    return JobMatchingEvaluator(FIXTURES).run(timing_repeats=1)


def test_label_file_is_complete():
    labels = json.loads((FIXTURES / "sprint4" / "labels.json").read_text(encoding="utf-8"))
    jobs = {p.stem for p in (FIXTURES / "sprint4" / "jobs").glob("*.txt")}
    assert set(labels["jobs"]) == jobs and len(jobs) == 8
    for cid, rel in labels["candidates"].items():
        assert (FIXTURES / rel).exists(), cid
        assert set(labels["relevance"][cid]) == jobs
        assert all(g in (0, 1, 2, 3) for g in labels["relevance"][cid].values())
    # at least one student has no strong fit, so the "no suitable match" path is exercised
    assert any(max(g.values()) < 3 for g in labels["relevance"].values())
    assert len(labels["skill_pairs"]) >= 20
    assert sum(1 for *_, eq in labels["skill_pairs"] if not eq) >= 10


def test_ndcg_math():
    assert ndcg_at_k([3, 2, 1], [1, 2, 3], 3) == pytest.approx(1.0)
    assert ndcg_at_k([0, 0, 3], [3, 0, 0], 3) < 0.6
    assert ndcg_at_k([0, 0], [0, 0], 2) is None


def test_jd_parsing(evaluation):
    m = evaluation["jd_parsing"]
    assert m["skill_precision"] >= 0.95, m["extra_skills"]
    assert m["skill_recall"] >= 0.80, m["missed_skills"]
    assert m["level_accuracy"] >= 0.95, m["level_errors"]
    for field in ("title", "company", "job_type", "min_cgpa", "batches"):
        assert m["field_accuracy"][field] == 1.0, field
    assert m["field_accuracy"]["experience"] >= 0.85


def test_skill_equivalence(evaluation):
    m = evaluation["skill_equivalence"]
    assert m["accuracy"] == 1.0, m["errors"]
    assert m["false_equivalence_rate"] == 0.0  # related-but-different skills never treated as the same


def test_skill_gaps(evaluation):
    m = evaluation["skill_gaps"]
    assert m["have_reported_as_missing"] == 0, m["errors"]
    assert m["missing_recall"] == 1.0, m["errors"]
    assert m["have_recall"] >= 0.70, m["errors"]


def test_ranking(evaluation):
    m = evaluation["ranking"]
    assert m["mrr"] == 1.0  # the first opening shown is always at least a reasonable fit
    assert m["ndcg_at_3"] >= 0.90
    assert m["precision_at_1"] >= 0.85
    assert m["pairwise_order_accuracy"] >= 0.93, m["order_errors"]
    assert m["suitability_precision"] >= 0.75
    assert m["suitability_recall"] >= 0.90


def test_each_specialist_gets_their_job_first(evaluation):
    tops = {c: v["top"] for c, v in evaluation["ranking"]["per_candidate"].items()}
    assert tops["s3_08_no_work_experience"] == "j05_embedded_intern"
    assert tops["s3_11_measurable_achievements"] == "j06_devops_intern"
    assert tops["r_frontend"] == "j02_frontend_intern"
    assert tops["r_data"] == "j03_data_analyst"
    assert tops["s3_01_strong"] == "j01_backend_intern"


def test_performance(evaluation):
    perf = evaluation["performance"]
    assert perf["compare_ms"]["median"] < 100
    assert perf["rank_8_jobs_ms"]["median"] < 500


def test_known_misses_are_still_present(evaluation):
    """Fails once a known miss is fixed - then shrink the KNOWN_* sets and raise the thresholds."""
    m = evaluation["jd_parsing"]
    assert set(m["missed_skills"]) == KNOWN_JD_SKILL_MISSES
    assert set(m["extra_skills"]) == KNOWN_JD_EXTRA_SKILLS


def test_implied_broad_skill_is_partial_not_matched():
    from app.nlp import ResumeNLPPipeline
    from app.nlp.job_matching.workflow import JobMatchingWorkflow

    resume = (FIXTURES / "sprint3" / "s3_06_detailed_projects.txt").read_text(encoding="utf-8")
    jd = (FIXTURES / "sprint4" / "jobs" / "j04_ml_intern.txt").read_text(encoding="utf-8")
    gap = JobMatchingWorkflow(nlp_pipeline=ResumeNLPPipeline()).compare(resume, jd).skill_gap
    ml = next(i for i in gap.partial_required + gap.missing_required if i.skill == "Machine Learning")
    assert ml.status.value == "partial" and ml.candidate_evidence == "PyTorch"
    assert "Name Machine Learning explicitly" in ml.how_to_improve
    numpy = next(i for i in gap.missing_required if i.skill == "NumPy")  # narrow skills are never inferred
    assert numpy.status.value == "missing"
