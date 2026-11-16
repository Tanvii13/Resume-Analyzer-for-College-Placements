"""
Sprint 3 – Module G: labelled evaluation of the Sprint 3 NLP layer.

Runs the full Sprint 3 analysis on 13 labelled synthetic resumes
(tests/nlp/fixtures/sprint3/) and 36 labelled bullets, and checks the measured metrics
against minimum thresholds.

Thresholds sit just below the measured values so a regression fails the build. Each known
miss is listed in KNOWN_MISSES with the module that causes it; when that module is fixed the
"known misses are still present" test fails, so the list and thresholds get updated.

Methodology (also in labels.json): labels were written from the resume text before running
the system; unlabelled detections are excluded from precision/recall and reported for review.
Metrics describe this small synthetic set only - they are not real-world accuracy figures.
"""

import json
import re
from pathlib import Path

import pytest

from app.nlp.evaluation import ConfusionCounts, Sprint3Evaluator
from app.nlp.recommendations import RULES

FIXTURES = Path(__file__).parent / "fixtures" / "sprint3"

KNOWN_MISSES = {
    # Module D: checks profile.technical_skills instead of section_summary.missing_critical_sections,
    # and a GitHub URL in the header is extracted as a "skill", so the missing section is not flagged.
    "improvement_fn": {
        "s3_03_missing_sections:IMP_MISSING_SKILLS",
        # Sprint 2 skill extractor reads "Communication" from the branch name
        # "Electronics and Communication Engineering" as a soft skill.
        "s3_08_no_work_experience:IMP_MISSING_SOFT_SKILLS",
    },
    # Module B: year-only education ranges vs month-year job ranges counted as inconsistent dates.
    "formatting_fp": {
        "s3_01_strong:FMT_INCONSISTENT_DATE_FORMATS",
        "s3_11_measurable_achievements:FMT_INCONSISTENT_DATE_FORMATS",
    },
}


@pytest.fixture(scope="module")
def evaluation():
    return Sprint3Evaluator(FIXTURES).run(timing_repeats=1)


# ============================================================================
# Label set sanity
# ============================================================================


def test_label_set_covers_required_cases():
    labels = json.loads((FIXTURES / "labels.json").read_text(encoding="utf-8"))
    cases = {k: v for k, v in labels.items() if not k.startswith("_")}
    assert len(cases) == 13
    for case in cases:
        assert (FIXTURES / f"{case}.txt").exists()
    required = [
        "Strong",
        "Weak",
        "Missing critical",
        "Incomplete education",
        "Limited project",
        "Detailed project",
        "No internships",
        "No work experience",
        "Inconsistent formatting",
        "Repeated bullet",
        "Measurable achievements",
        "No measurable",
        "Low-confidence",
    ]
    descriptions = " | ".join(v["case"] for v in cases.values())
    for name in required:
        assert name.lower() in descriptions.lower(), name


def test_labels_only_use_real_ids():
    import inspect
    from app.nlp.formatting import rules as fmt_rules
    from app.nlp.improvement import detector
    from app.nlp.improvement.deduplicator import CANONICAL_ISSUE_CLUSTERS

    issue_ids = set(re.findall(r'"(IMP_[A-Z_]+)"', inspect.getsource(detector))) | set(
        CANONICAL_ISSUE_CLUSTERS.values()
    )
    fmt_ids = set(re.findall(r'issue_id="(FMT_[A-Z_]+)"', inspect.getsource(fmt_rules)))
    rec_ids = {r.recommendation_id for r in RULES.values()} | {
        "REC_ADD_PROJECTS_SECTION",
        "REC_ADD_TECHNICAL_SKILLS_SECTION",
        "REC_ADD_EDUCATION_SECTION",
        "REC_EXPERIENCE_OUTCOMES",
    }
    labels = json.loads((FIXTURES / "labels.json").read_text(encoding="utf-8"))
    for case, label in labels.items():
        if case.startswith("_"):
            continue
        for i in label["expected_issues"] + label["forbidden_issues"]:
            assert i in issue_ids | fmt_ids, f"{case}: unknown issue id {i}"
        for f in label["expected_formatting"] + label["forbidden_formatting"]:
            assert f in fmt_ids, f"{case}: unknown formatting id {f}"
        for r in label["expected_recommendations"]:
            assert r in rec_ids, f"{case}: unknown recommendation id {r}"


def test_confusion_counts_math():
    c = ConfusionCounts()
    c.add("a", detected={"X", "Y", "Z"}, expected={"X", "W"}, forbidden={"Y", "V"})
    assert (c.tp, c.fn, c.fp, c.tn) == (1, 1, 1, 1)
    assert c.precision == 0.5 and c.recall == 0.5 and c.f1 == 0.5 and c.false_positive_rate == 0.5
    assert c.unlabelled_detections == ["a:Z"]
    with pytest.raises(ValueError):
        c.add("b", detected=set(), expected={"X"}, forbidden={"X"})


# ============================================================================
# Metric thresholds
# ============================================================================


def test_improvement_detection_quality(evaluation):
    m = evaluation["improvement_detection"]
    assert m["support"] >= 20
    assert m["precision"] >= 0.95, m["false_positives"]
    assert m["recall"] >= 0.90, m["false_negatives"]
    assert m["f1"] >= 0.92


def test_formatting_detection_quality(evaluation):
    m = evaluation["formatting_detection"]
    assert m["recall"] >= 0.95, m["false_negatives"]
    assert m["precision"] >= 0.75, m["false_positives"]
    assert m["false_positive_rate"] <= 0.10


def test_content_quality_metrics(evaluation):
    c = evaluation["content_quality"]
    assert c["labelled_bullets"] >= 30
    assert c["action_verb_detection_accuracy"] >= 0.90
    assert c["impact_metric_detection_accuracy"] >= 0.85
    assert c["weak_opening_detection_accuracy"] >= 0.95
    assert c["band_agreement"] >= 0.70


def test_recommendation_metrics(evaluation):
    r = evaluation["recommendations"]
    assert r["issue_to_recommendation_mapping_accuracy"] == 1.0
    assert r["duplicate_recommendation_rate"] == 0.0
    assert r["expected_recommendation_recall"] >= 0.85, r["missing_expected_recommendations"]


def test_scores_order_strong_above_weak(evaluation):
    s = evaluation["scoring"]
    assert s["ordering_pairs"] >= 40
    assert s["pairwise_ordering_accuracy"] == 1.0, s["ordering_violations"]


def test_no_module_errors_on_label_set(evaluation):
    for case, data in evaluation["per_case"].items():
        assert data["module_errors"] == [], case


def test_known_misses_are_still_present(evaluation):
    """Fails once a known miss is fixed - then remove it from KNOWN_MISSES and raise the thresholds."""
    fn = set(evaluation["improvement_detection"]["false_negatives"])
    fp = set(evaluation["formatting_detection"]["false_positives"])
    assert fn == KNOWN_MISSES["improvement_fn"], f"improvement misses changed: {fn}"
    assert fp == KNOWN_MISSES["formatting_fp"], f"formatting false positives changed: {fp}"
