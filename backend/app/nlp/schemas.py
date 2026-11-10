"""
Pydantic v2 data contracts for the Sprint 2 NLP pipeline.

Module F (NLP-10) output contract, matching Section 9 of
Documents/NLP_SPRINT_2_PLAN.md.

Naming note: Module C's internal dataclass is `app.nlp.extractors.ContactInfo`.
To avoid two different classes sharing that name, the Pydantic contract model
is called `ContactSchema`. The pipeline converts one into the other.

Missing information is always represented as None or an empty list; nothing is
ever invented to fill a gap.
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

PIPELINE_VERSION = "2.0.0"


class ConfidenceLevel(str, Enum):
    """Bucketed confidence used for explainability in the UI."""
    HIGH = "high"        # >= 0.85
    MEDIUM = "medium"    # 0.60 - 0.84
    LOW = "low"          # < 0.60

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score >= 0.85:
            return cls.HIGH
        if score >= 0.60:
            return cls.MEDIUM
        return cls.LOW


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class NLPProcessingRequest(_Model):
    """Input payload to the NLP pipeline."""
    resume_id: Optional[str] = None
    filename: str
    text: str  # Extracted text from Sprint 1 ResumeParseResult


class ContactSchema(_Model):
    """Candidate identity and contact details (Module C output, validated)."""
    full_name: Optional[str] = Field(None, description="Extracted candidate name")
    email: Optional[str] = Field(None, description="Primary email address")
    phone: Optional[str] = Field(None, description="Formatted phone number")
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    coding_profiles: Dict[str, str] = Field(default_factory=dict)
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class EducationEntry(_Model):
    """One academic qualification (Module D1)."""
    institution: Optional[str] = None
    degree: Optional[str] = None
    degree_level: Optional[str] = None  # bachelors / masters / doctorate / secondary / diploma
    field_of_study: Optional[str] = None
    board: Optional[str] = None  # CBSE / ICSE / GSEB etc. for school entries
    start_year: Optional[int] = None
    graduation_year: Optional[int] = None
    is_expected: bool = False
    cgpa: Optional[float] = Field(None, ge=0.0)
    cgpa_scale: Optional[float] = Field(None, gt=0.0)
    percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    raw_text: Optional[str] = None
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class ExperienceEntry(_Model):
    """
    One job or internship (Module D2).

    `company_name` and `job_title` are Optional (the plan sketch had them as
    required `str`) so that a partially parsed entry is returned with None
    rather than an invented value.
    """
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    is_internship: bool = False
    location: Optional[str] = None
    start_date: Optional[str] = None  # 'YYYY-MM' or 'YYYY'
    end_date: Optional[str] = None
    is_current: bool = False
    duration_months: Optional[int] = Field(None, ge=0)
    responsibilities: List[str] = Field(default_factory=list)
    technologies_used: List[str] = Field(default_factory=list)
    source_section: Optional[str] = None
    raw_text: Optional[str] = None
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class ProjectEntry(_Model):
    """One personal / academic project (Module D3)."""
    title: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    project_url: Optional[str] = None
    github_url: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class SkillItem(_Model):
    """One normalized skill (Module E output, validated)."""
    canonical_name: str
    matched_alias: str
    category: str
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    source_section: Optional[str] = None
    occurrences: int = Field(1, ge=1)


class SectionSummary(_Model):
    identified_sections: List[str] = Field(default_factory=list)
    missing_critical_sections: List[str] = Field(default_factory=list)


class PipelineMetadata(_Model):
    """Run diagnostics. Module failures land in `warnings` instead of raising."""
    resume_id: Optional[str] = None
    processing_time_ms: float = 0.0
    module_status: Dict[str, str] = Field(default_factory=dict)  # module -> 'ok' | 'failed' | 'skipped'
    warnings: List[str] = Field(default_factory=list)
    overall_confidence: float = Field(0.0, ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel = ConfidenceLevel.LOW


class CandidateProfile(_Model):
    """Unified structured output for the Sprint 2 NLP pipeline."""
    filename: str
    contact: ContactSchema = Field(default_factory=ContactSchema)
    education: List[EducationEntry] = Field(default_factory=list)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    internships: List[ExperienceEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    technical_skills: List[SkillItem] = Field(default_factory=list)
    soft_skills: List[SkillItem] = Field(default_factory=list)
    skills_by_category: Dict[str, List[str]] = Field(default_factory=dict)
    certifications: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    extracurricular: List[str] = Field(default_factory=list)
    section_summary: SectionSummary = Field(default_factory=SectionSummary)
    metadata: PipelineMetadata = Field(default_factory=PipelineMetadata)
    pipeline_version: str = PIPELINE_VERSION


__all__ = [
    "PIPELINE_VERSION",
    "ConfidenceLevel",
    "NLPProcessingRequest",
    "ContactSchema",
    "EducationEntry",
    "ExperienceEntry",
    "ProjectEntry",
    "SkillItem",
    "SectionSummary",
    "PipelineMetadata",
    "CandidateProfile",
]
