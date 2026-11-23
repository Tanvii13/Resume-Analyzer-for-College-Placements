"""
Sprint 5 integrated NLP workflow (Module E: integration of Modules A-D).

One entry point for the backend / frontend:

    wf = Sprint5Workflow()
    student = wf.analyze_student(raw_text, "resume.txt", job_descriptions=[jd1, jd2], student_ref="42",
                                 department="CSE", batch_year=2026)
    # student.record.staff_analysis   -> Module A staff view for one student
    # student.version_metadata        -> Module B version snapshot to store with the result
    stored = wf.from_stored(profile, analysis=old_result, reprocess=True)   # Module C
    report = wf.build_report([student.record, stored.record, ...])        # Module D

Every stage reuses the Sprint 2-4 implementations unchanged. A failing stage is recorded in
`StudentAnalysis.errors` and the remaining stages still run, so one bad resume never stops a
batch. No I/O, no database, deterministic for the same input and `created_at`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.nlp.analysis import ResumeAnalysisPipeline, Sprint3AnalysisResult
from app.nlp.job_matching import JobFitReport, JobMatchingWorkflow
from app.nlp.job_matching.schemas import ParsedJobDescription
from app.nlp.pipeline import ResumeNLPPipeline
from app.nlp.placement_reports.builder import PlacementReportBuilder
from app.nlp.placement_reports.schemas import DEFAULT_MIN_GROUP_SIZE, PlacementReport, StudentRecord
from app.nlp.reprocessing import (
    UnsupportedHistoricalVersionError,
    reprocess_job_matching,
    reprocess_resume_analysis,
)
from app.nlp.schemas import CandidateProfile
from app.nlp.staff_insights import StaffAnalysisBuilder
from app.nlp.versioning import NLPVersionMetadata, build_version_metadata

SPRINT5_WORKFLOW_VERSION = "5.0.0"
VERSION_COMPONENTS = (
    "resume_parser", "profile_extraction", "scoring", "formatting", "content", "improvement",
    "recommendations", "analysis", "job_parser", "skill_matching", "job_matching",
)

T = TypeVar("T")


class StudentAnalysis(BaseModel):
    """Everything produced for one student. `record` is what Module D aggregates."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    record: StudentRecord
    version_metadata: NLPVersionMetadata
    reprocessed: bool = False
    stage_status: dict[str, str] = Field(default_factory=dict, description="stage -> ok / skipped / failed")
    errors: list[str] = Field(default_factory=list)
    workflow_version: str = SPRINT5_WORKFLOW_VERSION


class Sprint5Workflow:
    """Joins Sprint 2-4 analysis with Sprint 5 Modules A (staff view), B (versions), C (reprocessing), D (reports)."""

    def __init__(
        self,
        nlp_pipeline: ResumeNLPPipeline | None = None,
        analysis_pipeline: ResumeAnalysisPipeline | None = None,
        job_workflow: JobMatchingWorkflow | None = None,
        min_group_size: int = DEFAULT_MIN_GROUP_SIZE,
    ) -> None:
        self.nlp_pipeline = nlp_pipeline or ResumeNLPPipeline()
        self.analysis_pipeline = analysis_pipeline or ResumeAnalysisPipeline()
        self.job_workflow = job_workflow or JobMatchingWorkflow()
        self.staff_builder = StaffAnalysisBuilder()
        self.report_builder = PlacementReportBuilder(min_group_size=min_group_size)

    # ------------------------------------------------------- one student

    def analyze_student(
        self,
        raw_text: str,
        filename: str = "resume",
        job_descriptions: Iterable[str | ParsedJobDescription | dict[str, Any]] = (),
        student_ref: str | None = None,
        department: str | None = None,
        batch_year: int | None = None,
        created_at: datetime | None = None,
    ) -> StudentAnalysis:
        """Full fresh analysis of one resume: profile -> analysis -> job fits -> staff view."""
        status: dict[str, str] = {}
        errors: list[str] = []
        profile = self._stage("profile", status, errors, lambda: self.nlp_pipeline.process(raw_text, filename))
        analysis = None
        if profile is not None:
            analysis = self._stage("analysis", status, errors, lambda: self.analysis_pipeline.analyze(
                profile, raw_text=raw_text, created_at=created_at))
        else:
            status["analysis"] = "skipped"
        fits = self._job_fits(profile, job_descriptions, status, errors)
        return self._finish(student_ref or filename, department, batch_year, profile, analysis, fits,
                            status, errors, created_at, reprocessed=False)

    def from_stored(
        self,
        profile: CandidateProfile,
        analysis: Sprint3AnalysisResult | None = None,
        job_fits: Iterable[JobFitReport] = (),
        student_ref: str | None = None,
        department: str | None = None,
        batch_year: int | None = None,
        reprocess: bool = False,
        jobs: Iterable[ParsedJobDescription] = (),
        configuration: str = "sprint3-default-v3",
        created_at: datetime | None = None,
    ) -> StudentAnalysis:
        """Wrap results already stored in the database.

        With `reprocess=True` (or when no analysis is stored), the Sprint 3 analysis is regenerated
        from the stored profile with Module C; stored results are passed only as provenance and are
        never modified. `jobs` (structured job descriptions) are re-matched the same way.
        An unsupported historical version is reported as an error and the stored result is kept.
        """
        status: dict[str, str] = {"profile": "ok"}
        errors: list[str] = []
        fits = list(job_fits)
        did_reprocess = False
        if reprocess or analysis is None:
            new = self._stage("reprocess_analysis", status, errors, lambda: reprocess_resume_analysis(
                profile, configuration=configuration, historical_result=analysis, created_at=created_at))
            if new is not None:
                analysis, did_reprocess = new.result, True
        status.setdefault("analysis", "ok" if analysis is not None else "skipped")
        jobs = list(jobs)
        if jobs:
            old = {(f.job.job_id if f.job else None): f for f in fits}
            refreshed = []
            for job in jobs:
                r = self._stage("reprocess_job_matching", status, errors, lambda job=job: reprocess_job_matching(
                    profile, job, historical_result=old.get(job.job_id)))
                if r is not None:
                    refreshed.append(r.result)
                    did_reprocess = True
            kept = [f for f in fits if not f.job or f.job.job_id not in {j.job_id for j in jobs}]
            fits = kept + refreshed
        status.setdefault("job_matching", "ok" if fits else "skipped")
        return self._finish(student_ref or profile.filename, department, batch_year, profile, analysis, fits,
                            status, errors, created_at, reprocessed=did_reprocess)

    # ------------------------------------------------------- many students

    def analyze_batch(
        self,
        resumes: Iterable[dict[str, Any]],
        job_descriptions: Iterable[str | ParsedJobDescription | dict[str, Any]] = (),
        created_at: datetime | None = None,
    ) -> list[StudentAnalysis]:
        """`resumes`: dicts with raw_text and optional filename, student_ref, department, batch_year."""
        parsed_jobs = [self._parse_job(j) for j in job_descriptions]
        return [self.analyze_student(r["raw_text"], r.get("filename", "resume"), parsed_jobs,
                                     student_ref=r.get("student_ref"), department=r.get("department"),
                                     batch_year=r.get("batch_year"), created_at=created_at)
                for r in resumes]

    def build_report(
        self,
        students: Iterable[StudentAnalysis | StudentRecord],
        title: str = "Placement preparation report",
        generated_at: str | None = None,
    ) -> PlacementReport:
        records = [s.record if isinstance(s, StudentAnalysis) else s for s in students]
        return self.report_builder.build(records, title=title, generated_at=generated_at)

    # ------------------------------------------------------------ helpers

    @staticmethod
    def _stage(name: str, status: dict[str, str], errors: list[str], fn: Callable[[], T]) -> T | None:
        try:
            out = fn()
        except UnsupportedHistoricalVersionError as exc:
            status[name] = "failed"
            errors.append(f"{name}: unsupported historical version ({exc})")
            return None
        except Exception as exc:  # noqa: BLE001 - one failing stage must not stop the batch
            status[name] = "failed"
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            return None
        status[name] = "ok"
        return out

    def _parse_job(self, job):
        if isinstance(job, ParsedJobDescription):
            return job
        try:
            return self.job_workflow._job(job, None)
        except Exception:  # noqa: BLE001 - fall back to parsing per comparison
            return job

    def _job_fits(self, profile, jobs, status, errors) -> list[JobFitReport]:
        jobs = list(jobs)
        if profile is None or not jobs:
            status["job_matching"] = "skipped"
            return []
        fits = []
        for i, job in enumerate(jobs):
            fit = self._stage("job_matching", status, errors, lambda job=job, i=i: self.job_workflow.compare(
                profile, job, job_id=f"job-{i + 1}"))
            if fit is not None:
                fits.append(fit)
                if fit.metadata.errors:
                    errors.extend(f"job_matching: {e}" for e in fit.metadata.errors)
        status["job_matching"] = "ok" if fits and len(fits) == len(jobs) else ("failed" if not fits else "partial")
        return fits

    def _finish(self, ref, department, batch_year, profile, analysis, fits, status, errors, created_at,
                reprocessed: bool) -> StudentAnalysis:
        staff = None
        if profile is not None:
            matches = [f.match for f in fits if f.match is not None]
            staff = self._stage("staff_analysis", status, errors,
                                lambda: self.staff_builder.build(profile, analysis, matches or None))
        else:
            status["staff_analysis"] = "skipped"
        engine = getattr(self.analysis_pipeline, "scoring_engine", None)
        weights = getattr(engine, "weights", None)
        versions = build_version_metadata(VERSION_COMPONENTS, created_at=created_at, scoring_weights=weights)
        record = StudentRecord(student_ref=str(ref or "unknown"), department=department, batch_year=batch_year,
                               profile=profile, analysis=analysis, job_fits=fits, staff_analysis=staff)
        return StudentAnalysis(record=record, version_metadata=versions, reprocessed=reprocessed,
                               stage_status=status, errors=errors)


__all__ = ["SPRINT5_WORKFLOW_VERSION", "StudentAnalysis", "Sprint5Workflow"]
