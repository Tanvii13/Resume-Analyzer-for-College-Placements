"""Tests for Sprint 5 Module D: Placement Reports and Insights (US-15)."""

from functools import lru_cache
from pathlib import Path

import pytest

from app.nlp import ResumeNLPPipeline
from app.nlp.analysis import ResumeAnalysisPipeline
from app.nlp.job_matching import JobMatchingWorkflow
from app.nlp.placement_reports import (
    WEAKNESS_PROGRAMS,
    ConfidenceLevel,
    PlacementReport,
    PlacementReportBuilder,
    Priority,
    PrivacyViolationError,
    StudentRecord,
    build_placement_report,
)
from app.nlp.placement_reports.training_catalog import program_for_skill

FIXTURES = Path(__file__).parent / "fixtures"
SPRINT3 = sorted((FIXTURES / "sprint3").glob("*.txt"))
JOBS = sorted((FIXTURES / "sprint4" / "jobs").glob("*.txt"))


@lru_cache(maxsize=1)
def _pipelines():
    return ResumeNLPPipeline(), ResumeAnalysisPipeline(), JobMatchingWorkflow()


@lru_cache(maxsize=None)
def _analysed(path: Path):
    nlp, s3, _ = _pipelines()
    text = path.read_text(encoding="utf-8")
    profile = nlp.process(text, path.name)
    return profile, s3.analyze(profile, raw_text=text)


@lru_cache(maxsize=None)
def _fit(path: Path, job: Path):
    profile, _ = _analysed(path)
    return _pipelines()[2].compare(profile, job.read_text(encoding="utf-8"))


def _record(i: int, path: Path, department="CSE", with_jobs=True, **kw) -> StudentRecord:
    profile, analysis = _analysed(path)
    fits = [_fit(path, JOBS[0]), _fit(path, JOBS[5])] if with_jobs else []
    return StudentRecord(student_ref=f"stu-{i}", department=department, batch_year=2026, profile=profile,
                         analysis=analysis, job_fits=fits, **kw)


@pytest.fixture(scope="module")
def cohort() -> list[StudentRecord]:
    depts = ["CSE", "ICT"]
    return [_record(i, p, depts[i % 2], with_jobs=i % 4 != 3) for i, p in enumerate(SPRINT3)]


@pytest.fixture(scope="module")
def report(cohort) -> PlacementReport:
    return build_placement_report(cohort, generated_at="2026-11-22")


# ------------------------------------------------------------- statistics

class TestReadiness:
    def test_counts_and_coverage(self, report, cohort):
        c = report.coverage
        assert c.students_in_input == len(cohort) == c.students_analyzed
        assert c.students_with_job_matching == sum(1 for r in cohort if r.job_fits)
        assert report.readiness.score_statistics.count == len(cohort)

    def test_statistics_match_inputs(self, report, cohort):
        scores = [r.analysis.overall_score for r in cohort]
        s = report.readiness.score_statistics
        assert s.minimum == round(min(scores), 2) and s.maximum == round(max(scores), 2)
        assert s.mean == pytest.approx(sum(scores) / len(scores), abs=0.01)

    def test_label_distribution_sums_to_cohort(self, report, cohort):
        dist = report.readiness.label_distribution
        assert sum(x.students for x in dist) == len(cohort)
        assert sum(x.percentage for x in dist) == pytest.approx(100.0, abs=0.5)
        needs = sum(1 for r in cohort if r.analysis.score_label.value == "Needs Improvement")
        assert report.readiness.below_fair_count == needs

    def test_components_sorted_weakest_first(self, report):
        avgs = [c.average_percentage for c in report.readiness.component_averages]
        assert avgs == sorted(avgs) and len(avgs) == 4
        assert all(0 <= a <= 100 for a in avgs)


class TestWeaknessesAndGaps:
    def test_weakness_counts_are_per_student(self, report, cohort):
        for w in report.resume_weaknesses:
            expected = sum(1 for r in cohort if any(i.issue_id == w.issue_id for i in r.analysis.improvement_areas.issues))
            assert w.students_affected == expected
            assert w.percentage == round(100 * expected / len(cohort), 1)

    def test_weaknesses_sorted_by_frequency(self, report):
        counts = [w.students_affected for w in report.resume_weaknesses]
        assert counts == sorted(counts, reverse=True)
        assert report.resume_weaknesses, "fixture cohort has known weaknesses"

    def test_skill_gaps_use_matched_students_as_denominator(self, report, cohort):
        matched = [r for r in cohort if r.job_fits]
        required = [g for g in report.common_skill_gaps if g.level == "required"]
        assert required
        for g in required:
            expected = sum(1 for r in matched if any(
                i.skill == g.skill and not i.from_responsibilities_only
                for f in r.job_fits for i in f.skill_gap.missing_required))
            assert g.students_missing == expected
            assert g.percentage_of_matched_students == round(100 * expected / len(matched), 1)
            assert g.roles_requiring and g.category

    def test_required_before_preferred(self, report):
        levels = [g.level for g in report.common_skill_gaps]
        assert levels == sorted(levels, key=lambda x: x != "required")

    def test_common_skills(self, report):
        assert report.common_skills and report.common_skills[0].students >= report.common_skills[-1].students


class TestTraining:
    def test_recommendations_have_evidence(self, report):
        assert report.training_recommendations
        for t in report.training_recommendations:
            assert t.evidence and t.addresses and t.rationale
            assert t.students_affected >= 2 and t.percentage >= 20.0

    def test_sorted_by_priority(self, report):
        order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
        ranks = [order[t.priority] for t in report.training_recommendations]
        assert ranks == sorted(ranks)

    def test_no_recommendation_for_single_student(self):
        r = build_placement_report([_record(0, SPRINT3[0])], min_group_size=1)
        assert r.training_recommendations == []

    def test_catalog_ids_unique_and_skill_lookup(self):
        ids = [p.program_id for p in WEAKNESS_PROGRAMS]
        assert len(ids) == len(set(ids))
        assert program_for_skill("Git", "DevOps").program_id == "TRN_GIT"
        assert program_for_skill("Docker", "DevOps").program_id == "TRN_DEVOPS_CLOUD"
        assert program_for_skill("Underwater Basket Weaving", None) is None


class TestInsightsAndLimitations:
    def test_insights_have_evidence_and_ids(self, report):
        assert len(report.insights) >= 3
        ids = [i.insight_id for i in report.insights]
        assert len(ids) == len(set(ids))
        assert all(i.evidence and i.statement for i in report.insights)

    def test_small_cohort_confidence_not_high(self, report):
        assert all(i.confidence != ConfidenceLevel.HIGH for i in report.insights if i.type.value != "data_quality")

    def test_limitations_mention_sample_and_job_coverage(self, report):
        text = " ".join(report.limitations)
        assert "students were analysed" in text
        assert "compared with job descriptions" in text
        assert "not an assessment of individual students" in text

    def test_decision_support_note(self, report):
        assert "supporting information only" in report.decision_support_note


# ------------------------------------------------------------- privacy

class TestPrivacy:
    def test_no_personal_data_in_output(self, report, cohort):
        text = report.model_dump_json().lower()
        for r in cohort:
            c = r.profile.contact
            for value in (c.full_name, c.email, c.phone, r.profile.filename, r.student_ref):
                if value and len(value) >= 4:
                    assert value.lower() not in text, value

    def test_small_groups_suppressed(self, cohort):
        records = cohort[:6] + [_record(99, SPRINT3[0], department="ME")]
        r = build_placement_report(records)
        me = next(g for g in r.department_breakdown if g.group == "ME")
        assert me.suppressed and me.students is None and me.average_score is None
        assert r.privacy.suppressed_groups >= 1

    def test_small_cohort_warning(self):
        r = build_placement_report([_record(0, SPRINT3[0]), _record(1, SPRINT3[1])])
        assert r.privacy.small_cohort_warning
        assert all(g.suppressed for g in r.department_breakdown)

    def test_leak_is_refused(self, cohort, monkeypatch):
        record = cohort[0]
        name = record.profile.contact.full_name
        assert name
        monkeypatch.setattr(PlacementReportBuilder, "_limitations", lambda self, r: [f"Leaked {name}"])
        with pytest.raises(PrivacyViolationError):
            build_placement_report([record])

    def test_contains_personal_data_flag(self, report):
        assert report.privacy.contains_personal_data is False


# ------------------------------------------------------------- missing data / robustness

class TestMissingData:
    def test_empty_input(self):
        r = build_placement_report([])
        assert r.coverage.students_in_input == 0
        assert r.readiness.score_statistics.mean is None
        assert r.insights == [] and r.training_recommendations == []
        assert any("No analysed resumes" in x for x in r.limitations)

    def test_records_without_data_are_counted_and_skipped(self, cohort):
        r = build_placement_report(cohort[:5] + [StudentRecord(student_ref="x1"), StudentRecord(student_ref="x2")])
        assert r.coverage.records_without_usable_data == 2
        assert r.coverage.students_analyzed == 5

    def test_duplicates_ignored(self, cohort):
        r = build_placement_report(cohort[:5] + cohort[:2])
        assert r.coverage.duplicate_records_ignored == 2
        assert r.readiness.score_statistics.count == 5

    def test_no_job_data(self, cohort):
        records = [r.model_copy(update={"job_fits": []}) for r in cohort[:6]]
        r = build_placement_report(records)
        assert r.common_skill_gaps == []
        assert not any(t.program_id in {"TRN_GIT", "TRN_DEVOPS_CLOUD", "TRN_BACKEND"} for t in r.training_recommendations)
        assert any("No job-description comparisons" in x for x in r.limitations)

    def test_profile_only_records(self, cohort):
        records = [r.model_copy(update={"analysis": None, "job_fits": []}) for r in cohort[:5]]
        r = build_placement_report(records)
        assert r.coverage.students_analyzed == 0
        assert r.common_skills

    def test_staff_analysis_only_records(self, cohort):
        from app.nlp.staff_insights import build_staff_analysis
        records = [StudentRecord(student_ref=r.student_ref, department="CSE",
                                 staff_analysis=build_staff_analysis(r.profile, r.analysis)) for r in cohort[:5]]
        r = build_placement_report(records)
        assert r.coverage.students_analyzed == 5
        assert r.resume_weaknesses

    def test_invalid_min_group_size(self):
        with pytest.raises(ValueError):
            PlacementReportBuilder(min_group_size=0)


class TestConsistency:
    def test_deterministic(self, cohort):
        a = build_placement_report(cohort, generated_at="t").model_dump_json()
        b = build_placement_report(cohort, generated_at="t").model_dump_json()
        assert a == b

    def test_order_independent(self, cohort):
        a = build_placement_report(cohort).model_dump(exclude={"generated_at"})
        b = build_placement_report(list(reversed(cohort))).model_dump(exclude={"generated_at"})
        assert a == b

    def test_inputs_not_mutated(self, cohort):
        before = [r.model_dump_json() for r in cohort]
        build_placement_report(cohort)
        assert [r.model_dump_json() for r in cohort] == before

    def test_json_round_trip(self, report):
        assert PlacementReport.model_validate_json(report.model_dump_json()) == report

    def test_source_versions_recorded(self, report):
        assert report.source_versions["sprint3_analysis"]
        assert report.source_versions["job_matching"]
