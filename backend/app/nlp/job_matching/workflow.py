"""
Sprint 4 NLP workflow (Module F): one entry point for job matching.

    resume text  --Sprint 2 ResumeNLPPipeline-->  CandidateProfile ─┐
    JD text / opportunity record --Module A + B-->  ParsedJobDescription ─┤
                                                                   ├─ Module C  ResumeJobMatcher   -> JobMatchResult
                                                                   ├─ Module D  SkillGapAnalyzer   -> SkillGapReport
                                                                   └─ Module E  OpportunityRanker  -> OpportunityRankingReport

    JobMatchingWorkflow().compare(resume, job)          -> JobFitReport              (US-11, US-13)
    JobMatchingWorkflow().rank(resume, opportunities)   -> OpportunityRankingReport  (US-12)

Each stage runs in isolation: a failure is returned as a structured error in
`metadata.errors` and the stages that can still run do. Inputs may be raw text or already
structured objects, so the backend can pass whatever it has stored.

`JobFitReport.to_backend_jd_match()` / `.to_backend_jd_compare()` return the field shapes of
the backend's existing JDMatchResponse / JDCompareResponse, so the existing endpoints can
switch to this engine without changing their API contract.

No HTTP, database or LLM dependencies.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.nlp.job_matching.job_description_parser import JobDescriptionParser
from app.nlp.job_matching.matcher_schemas import MATCHER_ENGINE_VERSION, JobMatchResult
from app.nlp.job_matching.opportunity_ranker import OpportunityRanker, fit_tier
from app.nlp.job_matching.ranking_schemas import (
    RANKER_VERSION,
    FitTier,
    JobOpportunity,
    OpportunityRankingReport,
    RankingPreferences,
)
from app.nlp.job_matching.resume_job_matcher import ResumeJobMatcher
from app.nlp.job_matching.schemas import JOB_PARSER_VERSION, ParsedJobDescription
from app.nlp.job_matching.skill_engine import ENGINE_VERSION as SKILL_ENGINE_VERSION
from app.nlp.job_matching.skill_gap_analyzer import SkillGapAnalyzer
from app.nlp.job_matching.skill_gap_schemas import (
    SKILL_GAP_ANALYZER_VERSION,
    EligibilityStatus,
    SkillGapReport,
    SkillGapStatus,
)
from app.nlp.pipeline import ResumeNLPPipeline
from app.nlp.privacy import safe_failure_message
from app.nlp.schemas import CandidateProfile

T = TypeVar("T")
WORKFLOW_VERSION = "4.0.0"


class WorkflowError(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage: str
    error_type: str = Field(..., description="'validation_error' or 'exception'")
    message: str
    details: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    stage_status: dict[str, str] = Field(default_factory=dict, description="stage -> ok / failed / skipped")
    stage_timings_ms: dict[str, float] = Field(default_factory=dict)
    processing_time_ms: float = 0.0
    errors: list[WorkflowError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    versions: dict[str, str] = Field(default_factory=dict)


class JobFitReport(BaseModel):
    """Result of comparing one resume with one job description (US-11, US-13)."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)
    job: ParsedJobDescription | None = None
    match: JobMatchResult | None = None
    skill_gap: SkillGapReport | None = None
    relevance_score: float | None = Field(None, ge=0.0, le=100.0)
    fit_tier: FitTier | None = None
    is_suitable: bool = False
    summary: str = ""
    jd_word_count: int = Field(0, ge=0)
    jd_clean_text: str = ""
    metadata: WorkflowMetadata = Field(default_factory=WorkflowMetadata)
    workflow_version: str = WORKFLOW_VERSION

    # -- adapters for the backend's existing response models --------------

    def _skill_lists(self) -> tuple[list[str], list[str], list[str]]:
        gap = self.skill_gap
        if gap is None:
            return [], [], []
        matched = [i.skill for i in gap.matched_required + gap.matched_preferred if i.status == SkillGapStatus.MATCHED]
        partial = [f"{i.skill} (related: {i.candidate_evidence})" for i in gap.partial_required + gap.partial_preferred]
        missing = [i.skill for i in gap.missing_required + gap.missing_preferred]
        return matched, partial, missing

    def to_backend_jd_match(self) -> dict[str, Any]:
        """Fields of the backend's JDMatchResponse."""
        matched, partial, missing = self._skill_lists()
        gaps = self.skill_gap.priority_gaps if self.skill_gap else []
        return {
            "total_jd_skills_found": len(matched) + len(partial) + len(missing),
            "matched_skills_count": len(matched),
            "missing_skills_count": len(missing),
            "match_percentage": round(self.relevance_score or 0.0, 2),
            "matched_skills": matched + partial,
            "missing_skills": missing,
            "gap_recommendations": [g.how_to_improve for g in gaps if g.how_to_improve][:8],
        }

    def to_backend_jd_compare(self) -> dict[str, Any]:
        """Fields of the backend's JDCompareResponse except `resume_id` / `target_role`."""
        job = self.job
        data = self.to_backend_jd_match()
        data["jd_metadata"] = {
            "title": (job.title if job and job.title else "Not specified"),
            "experience_level": (
                "Fresher" if job and job.experience.is_fresher_eligible
                else f"{job.experience.min_years:g}+ years" if job and job.experience.min_years
                else "Not specified"
            ),
            "minimum_experience_years": job.experience.min_years if job else None,
            "required_degrees": list(job.education.degrees) if job else [],
            "required_disciplines": list(job.education.fields_of_study) if job else [],
            "word_count": self.jd_word_count,
            "clean_text": self.jd_clean_text,
        }
        return data


class JobMatchingWorkflow:
    """End-to-end Sprint 4 NLP workflow with shared, reusable engine instances."""

    def __init__(
        self,
        nlp_pipeline: ResumeNLPPipeline | None = None,
        parser: JobDescriptionParser | None = None,
        matcher: ResumeJobMatcher | None = None,
        gap_analyzer: SkillGapAnalyzer | None = None,
    ) -> None:
        self.nlp_pipeline = nlp_pipeline
        self.parser = parser or JobDescriptionParser()
        self.matcher = matcher or ResumeJobMatcher()
        self.gap_analyzer = gap_analyzer or SkillGapAnalyzer()
        self.ranker = OpportunityRanker(parser=self.parser, matcher=self.matcher, gap_analyzer=self.gap_analyzer)

    # ------------------------------------------------------------------ API

    def compare(
        self,
        resume: CandidateProfile | str,
        job: str | JobOpportunity | ParsedJobDescription | dict[str, Any],
        filename: str = "resume",
        job_id: str | None = None,
    ) -> JobFitReport:
        started = time.perf_counter()
        meta = self._metadata()
        report = JobFitReport(metadata=meta)

        profile = self._run("resume", meta, lambda: self._profile(resume, filename))
        parsed = self._run("job_description", meta, lambda: self._job(job, job_id))
        jd_text = job if isinstance(job, str) else (job.get("description") if isinstance(job, dict)
                                                    else getattr(job, "description", None))
        if jd_text:
            report.jd_clean_text = " ".join(jd_text.split())
            report.jd_word_count = len(report.jd_clean_text.split())
        if parsed is not None:
            report.job = parsed
            if not parsed.required_technical_skills and not parsed.preferred_technical_skills:
                meta.warnings.append("No technical skills could be read from the job description.")

        if profile is not None and parsed is not None:
            match = self._run("matching", meta, lambda: self.matcher.match(profile, parsed))
            if match is not None:
                report.match = match
                gap = self._run("skill_gap", meta, lambda: self.gap_analyzer.analyze(profile, parsed, match))
                if gap is not None:
                    report.skill_gap = gap
                    item = self._run("relevance", meta, lambda: self.ranker._ranked_item(
                        parsed.job_id or job_id or "job", None, parsed, match, gap, include_details=False))
                    if item is not None:
                        report.relevance_score = item.relevance_score
                        report.fit_tier = item.fit_tier
                        report.is_suitable = item.is_suitable
                        report.summary = item.summary
                        meta.warnings.extend(r for r in item.ranking_reasons if "uncertain" in r)
        else:
            for stage in ("matching", "skill_gap", "relevance"):
                meta.stage_status.setdefault(stage, "skipped")

        if not report.summary:
            report.summary = "The comparison could not be completed; see metadata.errors."
        meta.processing_time_ms = round((time.perf_counter() - started) * 1000, 2)
        return report

    def rank(
        self,
        resume: CandidateProfile | str,
        opportunities: Iterable[JobOpportunity | ParsedJobDescription | dict[str, Any] | str],
        preferences: RankingPreferences | None = None,
        include_details: bool = False,
        filename: str = "resume",
    ) -> OpportunityRankingReport:
        profile = resume if isinstance(resume, CandidateProfile) else self._pipeline().process(resume, filename)
        items = [
            JobOpportunity(opportunity_id=f"job-{i + 1}", description=o) if isinstance(o, str) else o
            for i, o in enumerate(opportunities)
        ]
        return self.ranker.rank(profile, items, preferences=preferences, include_details=include_details)

    # ------------------------------------------------------------ helpers

    def _pipeline(self) -> ResumeNLPPipeline:
        if self.nlp_pipeline is None:
            self.nlp_pipeline = ResumeNLPPipeline()
        return self.nlp_pipeline

    def _profile(self, resume: CandidateProfile | str, filename: str) -> CandidateProfile:
        if isinstance(resume, CandidateProfile):
            return resume
        if not isinstance(resume, str):
            raise TypeError(f"resume must be CandidateProfile or str, got {type(resume).__name__}")
        return self._pipeline().process(resume, filename)

    def _job(self, job, job_id: str | None) -> ParsedJobDescription:
        if isinstance(job, ParsedJobDescription):
            return job
        if isinstance(job, str):
            if not job.strip():
                raise ValueError("Job description text is empty.")
            return self.parser.parse(job, job_id=job_id)
        if isinstance(job, dict):
            job = JobOpportunity.from_record(job)
        if isinstance(job, JobOpportunity):
            return self.ranker.to_parsed_job(job)
        raise TypeError(f"Unsupported job input: {type(job).__name__}")

    @staticmethod
    def _metadata() -> WorkflowMetadata:
        return WorkflowMetadata(versions={
            "workflow": WORKFLOW_VERSION,
            "job_parser": JOB_PARSER_VERSION,
            "skill_engine": SKILL_ENGINE_VERSION,
            "matcher": MATCHER_ENGINE_VERSION,
            "skill_gap": SKILL_GAP_ANALYZER_VERSION,
            "ranker": RANKER_VERSION,
        })

    @staticmethod
    def _run(stage: str, meta: WorkflowMetadata, fn: Callable[[], T]) -> T | None:
        start = time.perf_counter()
        try:
            result = fn()
            meta.stage_status[stage] = "ok"
            return result
        except ValidationError as exc:
            meta.stage_status[stage] = "failed"
            meta.errors.append(WorkflowError(
                stage=stage, error_type="validation_error", message=safe_failure_message(stage, exc),
                details=[{k: v for k, v in e.items() if k in ("loc", "type")} for e in exc.errors()],
            ))
            return None
        except Exception as exc:  # noqa: BLE001 - isolate stage failures
            meta.stage_status[stage] = "failed"
            meta.errors.append(WorkflowError(
                stage=stage, error_type="exception", message=safe_failure_message(stage, exc)
            ))
            return None
        finally:
            meta.stage_timings_ms[stage] = round((time.perf_counter() - start) * 1000, 2)


_default: JobMatchingWorkflow | None = None


def get_job_matching_workflow() -> JobMatchingWorkflow:
    """Shared instance (engines are stateless after construction)."""
    global _default
    if _default is None:
        _default = JobMatchingWorkflow()
    return _default


__all__ = [
    "WORKFLOW_VERSION",
    "EligibilityStatus",
    "JobFitReport",
    "JobMatchingWorkflow",
    "WorkflowError",
    "WorkflowMetadata",
    "fit_tier",
    "get_job_matching_workflow",
]
