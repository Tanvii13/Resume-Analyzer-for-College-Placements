"""
Sprint 5 Module E: integration, evaluation and regression tests.

Covers the integrated workflow joining Module A (staff insights), B (versioning),
C (historical reprocessing) and D (placement reports) with the Sprint 2-4 pipeline.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

import app.nlp as nlp
from app.nlp import (
    CandidateProfile,
    NLPVersionMetadata,
    PlacementReport,
    Sprint5Workflow,
    StudentAnalysis,
    StudentRecord,
)
from app.nlp.analysis import ResumeAnalysisPipeline, Sprint3AnalysisResult
from app.nlp.job_matching import JobFitReport, JobMatchingWorkflow
from app.nlp.staff_insights import StaffAnalysisResult

FIXTURES = Path(__file__).parent / "fixtures"
SPRINT3 = sorted((FIXTURES / "sprint3").glob("*.txt"))
JOBS = [p.read_text(encoding="utf-8") for p in sorted((FIXTURES / "sprint4" / "jobs").glob("*.txt"))]
CREATED = datetime(2026, 11, 22, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def wf() -> Sprint5Workflow:
    return Sprint5Workflow()


@pytest.fixture(scope="module")
def students(wf) -> list[StudentAnalysis]:
    resumes = [{"raw_text": p.read_text(encoding="utf-8"), "filename": p.name, "student_ref": f"r{i}",
                "department": "CSE" if i % 2 else "ICT", "batch_year": 2026} for i, p in enumerate(SPRINT3)]
    return wf.analyze_batch(resumes, JOBS[:3], created_at=CREATED)


# ------------------------------------------------------------- individual student workflow

class TestIndividualWorkflow:
    def test_all_stages_run(self, students):
        for s in students:
            assert s.errors == []
            assert all(v == "ok" for v in s.stage_status.values()), s.stage_status
            assert set(s.stage_status) >= {"profile", "analysis", "job_matching", "staff_analysis"}

    def test_outputs_are_existing_sprint_types(self, students):
        r = students[0].record
        assert isinstance(r.profile, CandidateProfile)
        assert isinstance(r.analysis, Sprint3AnalysisResult)
        assert all(isinstance(f, JobFitReport) for f in r.job_fits) and len(r.job_fits) == 3
        assert isinstance(r.staff_analysis, StaffAnalysisResult)

    def test_matches_standalone_sprint3_and_4(self, wf, students):
        """Integration must not change Sprint 3/4 results."""
        p = SPRINT3[0]
        text = p.read_text(encoding="utf-8")
        profile = nlp.ResumeNLPPipeline().process(text, p.name)
        standalone = ResumeAnalysisPipeline().analyze(profile, raw_text=text, created_at=CREATED)
        r = students[0].record
        assert r.analysis.overall_score == standalone.overall_score
        assert r.analysis.score_label == standalone.score_label
        fit = JobMatchingWorkflow().compare(profile, JOBS[0])
        assert r.job_fits[0].relevance_score == fit.relevance_score

    def test_staff_view_consistent_with_analysis(self, students):
        for s in students:
            r = s.record
            assert r.staff_analysis.resume_overview.overall_score.overall_score == pytest.approx(r.analysis.overall_score)

    def test_version_metadata(self, students):
        v = students[0].version_metadata
        assert isinstance(v, NLPVersionMetadata)
        assert v.component_versions["analysis"].startswith("3.")
        assert v.component_versions["job_matching"].startswith("4.")
        assert v.taxonomy_fingerprint and v.scoring_configuration_fingerprint
        assert v.created_at == CREATED
        assert len({s.version_metadata.model_dump_json() for s in students}) == 1

    def test_without_jobs(self, wf):
        s = wf.analyze_student(SPRINT3[0].read_text(encoding="utf-8"), SPRINT3[0].name)
        assert s.stage_status["job_matching"] == "skipped"
        assert s.record.job_fits == [] and s.record.staff_analysis is not None


# ------------------------------------------------------------- reprocessing (Module C)

class TestStoredAndReprocessed:
    def test_from_stored_without_reprocess_keeps_results(self, wf, students):
        r = students[1].record
        s = wf.from_stored(r.profile, analysis=r.analysis, job_fits=r.job_fits, student_ref="x")
        assert s.reprocessed is False
        assert s.record.analysis is r.analysis

    def test_reprocess_regenerates_same_result(self, wf, students):
        r = students[1].record
        before = r.analysis.model_dump_json()
        s = wf.from_stored(r.profile, analysis=r.analysis, reprocess=True, jobs=[f.job for f in r.job_fits],
                           created_at=CREATED)
        assert s.reprocessed and s.errors == []
        assert s.record.analysis.overall_score == r.analysis.overall_score
        assert len(s.record.job_fits) == len(r.job_fits)
        assert r.analysis.model_dump_json() == before, "stored result must not be modified"

    def test_missing_analysis_is_regenerated(self, wf, students):
        s = wf.from_stored(students[2].record.profile)
        assert s.reprocessed and s.record.analysis is not None

    def test_unsupported_historical_version_reported(self, wf, students):
        r = students[3].record
        old = r.analysis.model_copy(update={"analyzer_version": "1.0.0"})
        s = wf.from_stored(r.profile, analysis=old, reprocess=True)
        assert s.stage_status["reprocess_analysis"] == "failed"
        assert any("unsupported historical version" in e for e in s.errors)
        assert s.record.analysis is old, "stored result is kept when it cannot be reprocessed"

    def test_unsupported_configuration_reported(self, wf, students):
        s = wf.from_stored(students[0].record.profile, reprocess=True, configuration="sprint9-future")
        assert s.stage_status["reprocess_analysis"] == "failed"


# ------------------------------------------------------------- aggregate report (Module D)

class TestAggregateReport:
    def test_report_from_workflow(self, wf, students):
        report = wf.build_report(students, generated_at="2026-11-22")
        assert isinstance(report, PlacementReport)
        assert report.coverage.students_analyzed == len(students)
        assert report.coverage.students_with_job_matching == len(students)
        assert report.resume_weaknesses and report.common_skill_gaps and report.training_recommendations
        assert report.insights and report.limitations

    def test_accepts_records_and_analyses(self, wf, students):
        a = wf.build_report(students).model_dump(exclude={"generated_at"})
        b = wf.build_report([s.record for s in students]).model_dump(exclude={"generated_at"})
        assert a == b

    def test_json_serialisable_for_api(self, wf, students):
        payload = json.loads(wf.build_report(students).model_dump_json())
        assert {"coverage", "readiness", "insights", "limitations", "privacy"} <= set(payload)

    def test_labelled_evaluation(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
        from evaluate_nlp_sprint5 import evaluate
        result = evaluate()
        assert result["weakness_prevalence"]["accuracy"] >= 0.9
        assert result["skill_gap_prevalence"]["accuracy"] >= 0.9
        assert result["privacy"]["leaks"] == 0
        assert result["deterministic"] and result["stage_failures"] == 0


# ------------------------------------------------------------- missing data / privacy

class TestMissingDataAndPrivacy:
    @pytest.mark.parametrize("text", ["", "   \n  ", "Lorem ipsum dolor sit amet."])
    def test_empty_or_unreadable_resume(self, wf, text):
        s = wf.analyze_student(text, "bad.txt", JOBS[:1])
        assert s.record.profile is not None
        report = wf.build_report([s])
        assert report.coverage.students_in_input == 1
        assert report.privacy.small_cohort_warning

    def test_bad_job_description_does_not_stop_student(self, wf):
        s = wf.analyze_student(SPRINT3[0].read_text(encoding="utf-8"), "a.txt", ["", JOBS[0]])
        assert s.record.analysis is not None
        assert s.stage_status["job_matching"] in {"partial", "ok"}

    def test_failing_stage_is_isolated(self, students, monkeypatch):
        wf = Sprint5Workflow()

        def boom(*a, **k):
            raise RuntimeError("scoring unavailable")
        monkeypatch.setattr(wf.analysis_pipeline, "analyze", boom)
        s = wf.analyze_student(SPRINT3[0].read_text(encoding="utf-8"), "a.txt", JOBS[:1])
        assert s.stage_status["analysis"] == "failed"
        assert s.stage_status["staff_analysis"] == "ok" and s.record.job_fits
        assert any("scoring unavailable" in e for e in s.errors)
        report = wf.build_report([s] + students[:4])
        assert report.coverage.students_analyzed == 4

    def test_no_personal_data_in_report(self, wf, students):
        text = wf.build_report(students).model_dump_json().lower()
        for s in students:
            c = s.record.profile.contact
            for v in (c.full_name, c.email, c.phone, s.record.profile.filename):
                if v and len(v) >= 4:
                    assert v.lower() not in text

    def test_student_record_rejects_unknown_fields(self):
        with pytest.raises(ValueError):
            StudentRecord(student_ref="a", name="Someone")


# ------------------------------------------------------------- regression

class TestRegression:
    def test_package_exports_still_present(self):
        for name in ("ResumeNLPPipeline", "build_staff_analysis",
                     "build_version_metadata", "reprocess_resume_analysis", "reprocess_job_matching",
                     "build_placement_report", "Sprint5Workflow"):
            assert hasattr(nlp, name), name
        missing = [n for n in nlp.__all__ if not hasattr(nlp, n)]
        assert missing == []

    def test_deterministic_batch(self, wf, students):
        again = wf.analyze_batch([{"raw_text": SPRINT3[0].read_text(encoding="utf-8"), "filename": SPRINT3[0].name,
                                   "student_ref": "r0", "department": "ICT", "batch_year": 2026}],
                                 JOBS[:3], created_at=CREATED)[0]
        a, b = again.record.analysis, students[0].record.analysis
        assert a.overall_score == b.overall_score
        assert [i.issue_id for i in a.improvement_areas.issues] == [i.issue_id for i in b.improvement_areas.issues]
