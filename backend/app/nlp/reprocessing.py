"""Pure-Python regeneration of Sprint 3 and Sprint 4 results from a profile."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.nlp.analysis import ResumeAnalysisPipeline, Sprint3AnalysisResult
from app.nlp.job_matching import JobFitReport, JobMatchingWorkflow
from app.nlp.job_matching.schemas import ParsedJobDescription
from app.nlp.schemas import CandidateProfile
from app.nlp.scoring import ScoringWeights

SUPPORTED_RESUME_CONFIGURATIONS = ("sprint3-default-v3", "sprint3-audit-reference-v3")
SUPPORTED_JOB_CONFIGURATIONS = ("sprint4-default-v4",)


class UnsupportedHistoricalVersionError(ValueError):
    """The stored result cannot safely be represented by this implementation."""


class ReprocessedResumeAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    generation_kind: Literal["reprocessed"] = "reprocessed"
    configuration_id: str
    source_profile_version: str
    historical_result_supplied: bool
    result: Sprint3AnalysisResult


class ReprocessedJobMatching(BaseModel):
    model_config = ConfigDict(extra="forbid")
    generation_kind: Literal["reprocessed"] = "reprocessed"
    configuration_id: str
    source_profile_version: str
    historical_result_supplied: bool
    result: JobFitReport


def _require_profile(profile: CandidateProfile) -> None:
    if not isinstance(profile, CandidateProfile):
        raise TypeError("profile must be an existing CandidateProfile")
    if profile.pipeline_version.split(".", 1)[0] != "2":
        raise UnsupportedHistoricalVersionError(
            f"CandidateProfile version {profile.pipeline_version!r} is unsupported for reprocessing."
        )


def _require_major(version: str, expected: str, name: str) -> None:
    if version.split(".", 1)[0] != expected:
        raise UnsupportedHistoricalVersionError(f"{name} version {version!r} is unsupported for reprocessing.")


def _resume_weights(configuration: str) -> ScoringWeights:
    if configuration == "sprint3-default-v3":
        return ScoringWeights.default_sprint3()
    if configuration == "sprint3-audit-reference-v3":
        return ScoringWeights.audit_reference_raw()
    raise ValueError(f"Unsupported resume reprocessing configuration: {configuration!r}")


def reprocess_resume_analysis(
    profile: CandidateProfile,
    *,
    configuration: str = "sprint3-default-v3",
    historical_result: Optional[Sprint3AnalysisResult] = None,
    raw_text: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> ReprocessedResumeAnalysis:
    """Generate a new Sprint 3 result without mutating the profile or old result.

    `historical_result` is validation/provenance input only; it is never edited
    and no attempt is made to emulate an unavailable old implementation.
    """
    _require_profile(profile)
    if historical_result is not None:
        _require_major(historical_result.analyzer_version, "3", "Historical Sprint3AnalysisResult")
    weights = _resume_weights(configuration)
    result = ResumeAnalysisPipeline(weights=weights).analyze(profile, raw_text=raw_text, created_at=created_at)
    return ReprocessedResumeAnalysis(configuration_id=configuration,
        source_profile_version=profile.pipeline_version,
        historical_result_supplied=historical_result is not None, result=result)


def reprocess_job_matching(
    profile: CandidateProfile,
    job: ParsedJobDescription,
    *,
    configuration: str = "sprint4-default-v4",
    historical_result: Optional[JobFitReport] = None,
) -> ReprocessedJobMatching:
    """Re-run deterministic Sprint 4 matching and skill-gap analysis from structures."""
    _require_profile(profile)
    if configuration not in SUPPORTED_JOB_CONFIGURATIONS:
        raise ValueError(f"Unsupported job reprocessing configuration: {configuration!r}")
    if not isinstance(job, ParsedJobDescription):
        raise TypeError("job must be a structured ParsedJobDescription")
    if historical_result is not None:
        _require_major(historical_result.workflow_version, "4", "Historical JobFitReport")
    result = JobMatchingWorkflow().compare(profile, job)
    return ReprocessedJobMatching(configuration_id=configuration,
        source_profile_version=profile.pipeline_version,
        historical_result_supplied=historical_result is not None, result=result)


__all__ = ["SUPPORTED_JOB_CONFIGURATIONS", "SUPPORTED_RESUME_CONFIGURATIONS", "ReprocessedJobMatching", "ReprocessedResumeAnalysis", "UnsupportedHistoricalVersionError", "reprocess_job_matching", "reprocess_resume_analysis"]
