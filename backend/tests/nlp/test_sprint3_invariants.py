"""
Sprint 3 – Module G: scoring invariants, robustness and performance.

Invariants (Prompt G §5):
- Scores stay within 0-100 for every fixture and for damaged / shuffled input
- Same input + same rule version -> identical result
- Personal attributes (name, email, phone, city, college name, gender) do not change the score
- Every deduction has a reason and evidence
- Missing sections and unreadable resumes are reported differently
- No contradictory explanations (cross-module consistency checks)
- No duplicate deductions (one known Module A exception is tracked as xfail)

Performance (Prompt G §7):
- Per-module and end-to-end time limits
- Peak memory for one analysis
- No repeated processing: formatting analysis runs once per resume
"""

import random
import time
import tracemalloc
from pathlib import Path

import pytest

from app.nlp import ResumeNLPPipeline
from app.nlp.analysis import ResumeAnalysisPipeline

ROOT = Path(__file__).parent / "fixtures"
ALL_RESUMES = sorted((ROOT / "sprint3").glob("*.txt")) + sorted((ROOT / "resumes").glob("*.txt"))
IDS = [p.stem for p in ALL_RESUMES]


@pytest.fixture(scope="module")
def pipeline():
    return ResumeAnalysisPipeline()


@pytest.fixture(scope="module")
def results(pipeline):
    return {
        p.stem: pipeline.analyze_text(p.read_text(encoding="utf-8"), p.name) for p in ALL_RESUMES
    }


def strip_timing(result):
    data = result.model_dump(mode="json")
    data["analysis_metadata"].pop("processing_time_ms")
    data["analysis_metadata"].pop("module_timings_ms")
    return data


# ============================================================================
# Score bounds
# ============================================================================


@pytest.mark.parametrize("case", IDS)
def test_scores_within_bounds(results, case):
    r = results[case]
    assert 0.0 <= r.overall_score <= 100.0
    for comp in r.component_scores.values():
        assert 0.0 <= comp.score <= comp.max_score
    assert abs(sum(c.score for c in r.component_scores.values()) - r.overall_score) <= 0.05


def test_scores_bounded_on_damaged_input(pipeline):
    rng = random.Random(42)
    base = (ROOT / "sprint3" / "s3_01_strong.txt").read_text(encoding="utf-8")
    lines = base.splitlines()
    variants = [
        "\n".join(rng.sample(lines, len(lines))),  # shuffled lines
        base[: len(base) // 3],  # truncated
        base.upper(),  # all caps
        base.replace("\n", " "),  # one long line
        "\n\n\n".join(lines),  # excessive blank lines
        base * 4,  # repeated content
        "".join(c for c in base if not c.isalpha()),  # letters stripped
    ]
    for text in variants:
        r = pipeline.analyze_text(text, "variant.txt")
        assert r.analysis_metadata.errors == []
        assert 0.0 <= r.overall_score <= 100.0


# ============================================================================
# Determinism
# ============================================================================


@pytest.mark.parametrize("case", IDS[:6])
def test_deterministic(pipeline, results, case):
    path = next(p for p in ALL_RESUMES if p.stem == case)
    again = pipeline.analyze_text(path.read_text(encoding="utf-8"), path.name)
    assert strip_timing(again) == strip_timing(results[case])


def test_deterministic_across_fresh_instances():
    text = (ROOT / "sprint3" / "s3_09_inconsistent_formatting.txt").read_text(encoding="utf-8")
    a = ResumeAnalysisPipeline().analyze_text(text, "x")
    b = ResumeAnalysisPipeline().analyze_text(text, "x")
    assert strip_timing(a) == strip_timing(b)
    assert a.rule_version == b.rule_version


# ============================================================================
# Personal attributes do not influence the score
# ============================================================================

PERSONAL_SWAPS = [
    ("Meera Krishnan", "Arjun Malhotra"),
    ("meera.krishnan@gmail.com", "a.malhotra99@yahoo.co.in"),
    ("+91 98250 44110", "+91 70450 12345"),
]


def test_personal_attributes_do_not_change_score(pipeline):
    base = (ROOT / "sprint3" / "s3_01_strong.txt").read_text(encoding="utf-8")
    swapped = base
    for old, new in PERSONAL_SWAPS:
        swapped = swapped.replace(old, new)
    college_swapped = swapped.replace("Nirma University", "Ahmedabad University").replace(
        "Delhi Public School", "Kendriya Vidyalaya"
    )
    with_gender = base.replace(
        "+91 98250 44110 |", "+91 98250 44110 | Gender: Female | Ahmedabad, India |"
    )

    base_r = pipeline.analyze_text(base, "a.txt")
    for variant in (swapped, college_swapped, with_gender):
        r = pipeline.analyze_text(variant, "b.txt")
        assert r.overall_score == base_r.overall_score
        assert {k: v.score for k, v in r.component_scores.items()} == {
            k: v.score for k, v in base_r.component_scores.items()
        }
        assert [x.recommendation_id for x in r.recommendations.recommendations] == [
            x.recommendation_id for x in base_r.recommendations.recommendations
        ]


# ============================================================================
# Evidence and explanations
# ============================================================================


@pytest.mark.parametrize("case", IDS)
def test_every_deduction_has_reason_and_evidence(results, case):
    for comp in results[case].explanations.score_breakdown:
        for d in comp.deductions:
            assert d.reason.strip(), (case, d.rule_id)
            assert d.evidence and d.evidence.strip(), (case, d.rule_id)
            assert d.points_deducted > 0, (case, d.rule_id)


@pytest.mark.parametrize("case", IDS)
def test_no_contradictory_explanations(results, case):
    checks = results[case].analysis_metadata.consistency_checks
    for name in (
        "recommendations_map_to_detected_issues",
        "no_duplicate_recommendations",
        "no_missing_section_contradictions",
        "component_scores_sum_to_overall",
        "every_deduction_explained",
        "every_deduction_has_reason",
        "every_issue_explained",
    ):
        assert checks[name], (case, name)


KNOWN_UNCOVERED_DEDUCTIONS = {
    # Module D does not emit an action-verb issue (only passive phrasing) - see verification report.
    "CONTENT_FEW_ACTION_VERBS",
    # Module D does not emit IMP_UNSUBSTANTIATED_SKILLS although Module A deducts for it.
    "SKILL_UNSUBSTANTIATED",
    # Consequence of the Module D missing-skills check (GitHub link counted as a skill).
    "SEC_MISSING_TECHNICAL_SKILLS",
}


@pytest.mark.parametrize("case", IDS)
def test_only_known_deductions_lack_an_improvement_area(results, case):
    warnings = [
        w
        for w in results[case].analysis_metadata.warnings
        if w.startswith("Score deductions with no matching")
    ]
    uncovered = set()
    for w in warnings:
        uncovered |= set(w.split(": ", 1)[1].strip("[]").replace("'", "").split(", "))
    assert uncovered <= KNOWN_UNCOVERED_DEDUCTIONS, (case, uncovered - KNOWN_UNCOVERED_DEDUCTIONS)


def test_no_contradiction_between_strengths_and_issues(results):
    for case, r in results.items():
        issue_ids = {i.issue_id for i in r.improvement_areas.issues}
        if "IMP_LACK_OF_MEASURABLE_IMPACT" in issue_ids:
            assert not any("Quantifiable impact demonstrated" in s for s in r.strengths), case
        if "IMP_MISSING_PROJECTS" in issue_ids:
            assert not any("project portfolio" in s.lower() for s in r.strengths), case


# ============================================================================
# Missing vs unreadable
# ============================================================================


def test_missing_and_unreadable_are_distinguished(results):
    missing = results["s3_03_missing_sections"]
    unreadable = results["s3_13_low_confidence"]
    missing_ids = {i.issue_id for i in missing.improvement_areas.issues}
    unreadable_ids = {i.issue_id for i in unreadable.improvement_areas.issues}
    assert "IMP_MISSING_PROJECTS" in missing_ids
    assert "IMP_EXTRACTION_UNCERTAINTY" not in missing_ids
    assert "IMP_EXTRACTION_UNCERTAINTY" in unreadable_ids
    assert "REC_CHECK_EXTRACTION" in {
        r.recommendation_id for r in unreadable.recommendations.recommendations
    }
    assert (
        unreadable.analysis_metadata.extraction_confidence
        < missing.analysis_metadata.extraction_confidence
    )


def test_empty_text_is_not_a_crash(pipeline):
    r = pipeline.analyze_text("", "empty.pdf")
    assert r.analysis_metadata.errors == []
    assert r.analysis_metadata.module_status["formatting"] == "skipped"


# ============================================================================
# Duplicate deductions
# ============================================================================


def _duplicate_rule_ids(result):
    ids = [d.rule_id for c in result.explanations.score_breakdown for d in c.deductions]
    return sorted({i for i in ids if ids.count(i) > 1})


@pytest.mark.parametrize("case", IDS)
def test_no_duplicate_deductions(results, case):
    assert _duplicate_rule_ids(results[case]) == [], case


def test_no_duplicate_deductions_experience_without_projects(results):
    assert _duplicate_rule_ids(results["04_diploma_fulltime"]) == []


# ============================================================================
# Performance and repeated processing
# ============================================================================


def test_module_and_end_to_end_latency(pipeline):
    texts = [p.read_text(encoding="utf-8") for p in ALL_RESUMES]
    pipeline.analyze_text(texts[0], "warmup")
    for text in texts:
        start = time.perf_counter()
        r = pipeline.analyze_text(text, "timing")
        total_ms = (time.perf_counter() - start) * 1000
        assert total_ms < 300, f"end-to-end {total_ms:.1f} ms"
        for module, ms in r.analysis_metadata.module_timings_ms.items():
            assert ms < 100, f"{module} took {ms} ms"


def test_peak_memory(pipeline):
    text = (ROOT / "sprint3" / "s3_01_strong.txt").read_text(encoding="utf-8")
    pipeline.analyze_text(text, "warmup")
    tracemalloc.start()
    pipeline.analyze_text(text, "mem")
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < 20 * 1024 * 1024, f"peak {peak / 1e6:.1f} MB"


def test_formatting_and_scoring_run_once_per_analysis():
    pipe = ResumeAnalysisPipeline()
    calls = {"formatting": 0, "scoring": 0}
    fmt_analyze, score_eval = pipe.formatting_analyzer.analyze, pipe.scoring_engine.evaluate

    def count_fmt(*a, **k):
        calls["formatting"] += 1
        return fmt_analyze(*a, **k)

    def count_score(*a, **k):
        calls["scoring"] += 1
        return score_eval(*a, **k)

    pipe.formatting_analyzer.analyze = count_fmt
    pipe.scoring_engine.evaluate = count_score

    import app.nlp.improvement.detector as detector_module

    original_fmt, original_score = detector_module.analyze_formatting, detector_module.score_resume
    hidden = {"formatting": 0, "scoring": 0}

    def hidden_fmt(*a, **k):
        hidden["formatting"] += 1
        return original_fmt(*a, **k)

    def hidden_score(*a, **k):
        hidden["scoring"] += 1
        return original_score(*a, **k)

    detector_module.analyze_formatting, detector_module.score_resume = hidden_fmt, hidden_score
    try:
        pipe.analyze_text(
            (ROOT / "sprint3" / "s3_09_inconsistent_formatting.txt").read_text(encoding="utf-8"),
            "x",
        )
    finally:
        detector_module.analyze_formatting, detector_module.score_resume = (
            original_fmt,
            original_score,
        )
    assert calls == {"formatting": 1, "scoring": 1}
    assert hidden == {"formatting": 0, "scoring": 0}, (
        "Module D re-ran an analysis the pipeline already did"
    )


def test_sprint2_pipeline_untouched_by_sprint3(sample_resume_text):
    nlp = ResumeNLPPipeline()
    profile = nlp.process(sample_resume_text, "x.pdf")
    snapshot = profile.model_dump(mode="json", exclude={"metadata"})
    ResumeAnalysisPipeline(nlp_pipeline=nlp).analyze(profile, raw_text=sample_resume_text)
    assert profile.model_dump(mode="json", exclude={"metadata"}) == snapshot
