"""Pydantic contracts for the Sprint 5 staff-facing analysis adapter.

The models deliberately retain source evidence instead of re-scoring a resume.
``unavailable`` means a preceding analysis module was not supplied; it does not
mean the student failed that check.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


STAFF_INSIGHTS_VERSION = "5.0.0"


class _StaffModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Availability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class AvailabilityNote(_StaffModel):
    status: Availability
    reason: Optional[str] = None


class ScoreOverview(_StaffModel):
    overall_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    max_score: Optional[float] = Field(None, gt=0.0)
    score_label: Optional[str] = None
    availability: AvailabilityNote


class QualityDimension(_StaffModel):
    name: str
    score: Optional[float] = Field(None, ge=0.0)
    max_score: Optional[float] = Field(None, gt=0.0)
    percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    explanation: Optional[str] = None
    evidence: list[str] = Field(default_factory=list)
    availability: AvailabilityNote


class ResumeOverview(_StaffModel):
    overall_score: ScoreOverview
    section_completeness: QualityDimension
    content_quality: QualityDimension
    skill_visibility: QualityDimension
    formatting_quality: QualityDimension
    strengths: list[str] = Field(default_factory=list)


class EvidenceItem(_StaffModel):
    item_id: str
    title: str
    description: str
    affected_section: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    evidence: list[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class MeasurableAchievements(_StaffModel):
    detected: Optional[bool] = None
    count: Optional[int] = Field(None, ge=0)
    availability: AvailabilityNote


class ImprovementOverview(_StaffModel):
    critical_missing_sections: list[EvidenceItem] = Field(default_factory=list)
    weak_resume_sections: list[EvidenceItem] = Field(default_factory=list)
    content_issues: list[EvidenceItem] = Field(default_factory=list)
    formatting_issues: list[EvidenceItem] = Field(default_factory=list)
    missing_measurable_achievements: MeasurableAchievements
    actionable_recommendations: list[EvidenceItem] = Field(default_factory=list)


class SkillEvidence(_StaffModel):
    name: str
    category: str
    extraction_confidence: float = Field(..., ge=0.0, le=1.0)
    source_section: Optional[str] = None
    supported: bool
    evidence: list[str] = Field(default_factory=list)


class SkillsOverview(_StaffModel):
    technical_skills: list[SkillEvidence] = Field(default_factory=list)
    soft_skills: list[SkillEvidence] = Field(default_factory=list)
    supported_skills: list[SkillEvidence] = Field(default_factory=list)
    insufficiently_supported_skills: list[SkillEvidence] = Field(default_factory=list)


class JobOpportunity(_StaffModel):
    job_id: Optional[str] = None
    job_title: Optional[str] = None
    matching_score: float = Field(..., ge=0.0, le=100.0)
    matching_skills: list[EvidenceItem] = Field(default_factory=list)
    missing_required_skills: list[EvidenceItem] = Field(default_factory=list)
    qualification_gaps: list[EvidenceItem] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)


class JobMatchingOverview(_StaffModel):
    availability: AvailabilityNote
    best_matching_opportunities: list[JobOpportunity] = Field(default_factory=list)


class StaffFriendlySummary(_StaffModel):
    doing_well: list[str] = Field(default_factory=list)
    needs_improvement: list[str] = Field(default_factory=list)
    demonstrated_skills: list[str] = Field(default_factory=list)
    skills_requiring_evidence: list[str] = Field(default_factory=list)
    next_priorities: list[str] = Field(default_factory=list)
    narrative: str


class StaffAnalysisResult(_StaffModel):
    """Privacy-minimised staff analysis built from existing NLP results.

    Identity, contact details, filenames and raw resume text are deliberately
    absent.  The backend associates this analysis with an authorised record.
    """

    resume_overview: ResumeOverview
    improvement_overview: ImprovementOverview
    skills_overview: SkillsOverview
    job_matching_overview: JobMatchingOverview
    summary: StaffFriendlySummary
    source_versions: dict[str, Optional[str]] = Field(default_factory=dict)
    adapter_version: str = STAFF_INSIGHTS_VERSION

