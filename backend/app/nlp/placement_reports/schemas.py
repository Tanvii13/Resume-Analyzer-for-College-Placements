"""
Pydantic v2 contracts for Sprint 5 Module D: Placement Reports and Insights (US-15).

Input:  StudentRecord - one student's existing NLP results (Sprint 2-4 outputs and/or the
        Module A staff analysis). Nothing is re-analysed.
Output: PlacementReport - batch-level statistics, common skill gaps, frequent resume
        weaknesses, training / workshop recommendations, evidence-backed insights and
        explicit limitations.

Privacy (US-15 AC 2-3, US-17): the report contains only aggregated counts. No names,
emails, phone numbers, student ids, filenames or resume text are ever copied into it, and
any group smaller than `min_group_size` is suppressed.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.nlp.analysis import Sprint3AnalysisResult
from app.nlp.job_matching import JobFitReport, OpportunityRankingReport
from app.nlp.schemas import CandidateProfile
from app.nlp.staff_insights import StaffAnalysisResult

PLACEMENT_REPORT_VERSION = "5.0.0"
DEFAULT_MIN_GROUP_SIZE = 5

SUPPORTING_INFORMATION_NOTE = (
    "Automated analysis is supporting information only. It must not be used on its own to "
    "reject or rank individual students; decisions remain with placement staff."
)


class _ReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class StudentRecord(BaseModel):
    """One student's existing analysis results. `student_ref` is never copied into the report."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    student_ref: str = Field(..., min_length=1, description="Any internal id; used only for de-duplication")
    department: str | None = None
    batch_year: int | None = None
    profile: CandidateProfile | None = None
    analysis: Sprint3AnalysisResult | None = None
    job_fits: list[JobFitReport] = Field(default_factory=list)
    ranking: OpportunityRankingReport | None = None
    staff_analysis: StaffAnalysisResult | None = None


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InsightType(str, Enum):
    STRENGTH = "strength"
    CONCERN = "concern"
    DATA_QUALITY = "data_quality"
    COMPARISON = "comparison"


class DataCoverage(_ReportModel):
    students_in_input: int = Field(..., ge=0)
    students_analyzed: int = Field(..., ge=0, description="Students with a resume score")
    students_with_job_matching: int = Field(..., ge=0)
    students_with_low_extraction_confidence: int = Field(..., ge=0)
    students_with_module_errors: int = Field(..., ge=0)
    duplicate_records_ignored: int = Field(0, ge=0)
    records_without_usable_data: int = Field(0, ge=0)


class ScoreStatistics(_ReportModel):
    count: int = Field(..., ge=0)
    mean: float | None = None
    median: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    std_dev: float | None = None


class LabelShare(_ReportModel):
    label: str
    students: int = Field(..., ge=0)
    percentage: float = Field(..., ge=0.0, le=100.0)


class ComponentAverage(_ReportModel):
    component: str
    label: str
    average_percentage: float = Field(..., ge=0.0, le=100.0, description="Average score as % of the component maximum")
    students: int = Field(..., ge=0)


class ReadinessSummary(_ReportModel):
    score_statistics: ScoreStatistics
    label_distribution: list[LabelShare] = Field(default_factory=list)
    component_averages: list[ComponentAverage] = Field(default_factory=list, description="Weakest first")
    below_fair_count: int = Field(0, ge=0, description="Students scoring 'Needs Improvement'")


class GroupSummary(_ReportModel):
    group: str
    students: int | None = Field(None, ge=0, description="None when suppressed")
    average_score: float | None = None
    most_common_weakness: str | None = None
    suppressed: bool = False
    suppression_reason: str | None = None


class SkillGapStat(_ReportModel):
    skill: str
    category: str
    level: str = Field(..., description="required / preferred")
    students_missing: int = Field(..., ge=1)
    students_partial: int = Field(0, ge=0)
    percentage_of_matched_students: float = Field(..., ge=0.0, le=100.0)
    roles_requiring: list[str] = Field(default_factory=list, description="Job titles (not student data)")


class WeaknessStat(_ReportModel):
    issue_id: str
    title: str
    category: str
    severity: str
    students_affected: int = Field(..., ge=1)
    percentage: float = Field(..., ge=0.0, le=100.0)
    related_score_component: str | None = None


class SkillPresence(_ReportModel):
    skill: str
    category: str
    students: int = Field(..., ge=1)
    percentage: float = Field(..., ge=0.0, le=100.0)


class TrainingRecommendation(_ReportModel):
    program_id: str
    title: str
    format: str = Field(..., description="workshop / bootcamp / hands-on lab / session / mentoring")
    description: str
    addresses: list[str] = Field(default_factory=list, description="Issue ids or skills this targets")
    students_affected: int = Field(..., ge=1)
    percentage: float = Field(..., ge=0.0, le=100.0)
    priority: Priority
    evidence: list[str] = Field(default_factory=list)
    rationale: str


class Insight(_ReportModel):
    insight_id: str
    type: InsightType
    statement: str
    evidence: list[str] = Field(default_factory=list)
    metrics: dict[str, float | int] = Field(default_factory=dict)
    confidence: ConfidenceLevel


class PrivacySummary(_ReportModel):
    contains_personal_data: bool = False
    min_group_size: int = Field(..., ge=1)
    suppressed_groups: int = Field(0, ge=0)
    small_cohort_warning: bool = False
    notes: list[str] = Field(default_factory=list)


class PlacementReport(_ReportModel):
    title: str
    batch_years: list[int] = Field(default_factory=list)
    departments_included: int = Field(0, ge=0)
    generated_at: str | None = None
    coverage: DataCoverage
    readiness: ReadinessSummary
    department_breakdown: list[GroupSummary] = Field(default_factory=list)
    common_skill_gaps: list[SkillGapStat] = Field(default_factory=list)
    resume_weaknesses: list[WeaknessStat] = Field(default_factory=list)
    common_skills: list[SkillPresence] = Field(default_factory=list)
    training_recommendations: list[TrainingRecommendation] = Field(default_factory=list)
    insights: list[Insight] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    privacy: PrivacySummary
    decision_support_note: str = SUPPORTING_INFORMATION_NOTE
    source_versions: dict[str, list[str]] = Field(default_factory=dict)
    configuration: dict[str, Any] = Field(default_factory=dict)
    report_version: str = PLACEMENT_REPORT_VERSION


__all__ = [
    "DEFAULT_MIN_GROUP_SIZE",
    "PLACEMENT_REPORT_VERSION",
    "SUPPORTING_INFORMATION_NOTE",
    "ComponentAverage",
    "ConfidenceLevel",
    "DataCoverage",
    "GroupSummary",
    "Insight",
    "InsightType",
    "LabelShare",
    "PlacementReport",
    "Priority",
    "PrivacySummary",
    "ReadinessSummary",
    "ScoreStatistics",
    "SkillGapStat",
    "SkillPresence",
    "StudentRecord",
    "TrainingRecommendation",
    "WeaknessStat",
]
