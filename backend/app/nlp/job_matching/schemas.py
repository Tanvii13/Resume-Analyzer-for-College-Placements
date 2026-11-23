"""
Pydantic v2 data contracts for Sprint 4 Module A: Job Description Processing.

Defines validated representations for parsed job descriptions:
- JobType, WorkplaceType enums
- JobSkillRequirement (required vs preferred, category, evidence)
- ExperienceRequirement (min, max, fresher eligible, evidence)
- EducationRequirement (degrees, degree levels, fields, batches)
- EligibilityCriteria (CGPA/CPI, percentage, batches, branches, backlogs)
- LocationRequirement (city, state, country, workplace type, remote)
- OtherJobRequirements (salary/stipend, bond, selection rounds)
- JobParsingMetadata
- ParsedJobDescription (unified contract)
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.nlp.schemas import ConfidenceLevel

JOB_PARSER_VERSION = "4.0.0"


class JobType(str, Enum):
    """Employment type extracted from job description."""
    FULL_TIME = "full_time"
    INTERNSHIP = "internship"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    UNKNOWN = "unknown"


class WorkplaceType(str, Enum):
    """Work model/location type."""
    ON_SITE = "on_site"
    REMOTE = "remote"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class _JobModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class JobSkillRequirement(_JobModel):
    """One technical or soft skill requirement extracted from the job description."""
    canonical_name: str
    matched_alias: str
    category: str
    is_required: bool = True
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    occurrences: int = Field(1, ge=1)
    evidence: Optional[str] = Field(None, description="Line or clause where skill was mentioned")


class ExperienceRequirement(_JobModel):
    """Experience requirements extracted from job description."""
    min_years: Optional[float] = Field(None, ge=0.0)
    max_years: Optional[float] = Field(None, ge=0.0)
    is_fresher_eligible: bool = False
    raw_text: Optional[str] = None
    evidence: Optional[str] = None
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class EducationRequirement(_JobModel):
    """Academic qualification requirements extracted from job description."""
    degrees: List[str] = Field(default_factory=list)
    degree_levels: List[str] = Field(default_factory=list)
    fields_of_study: List[str] = Field(default_factory=list)
    min_graduation_year: Optional[int] = None
    max_graduation_year: Optional[int] = None
    raw_text: Optional[str] = None
    evidence: Optional[str] = None
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class EligibilityCriteria(_JobModel):
    """College placement specific eligibility requirements."""
    min_cgpa: Optional[float] = Field(None, ge=0.0)
    cgpa_scale: Optional[float] = Field(None, gt=0.0)
    min_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    allowed_branches: List[str] = Field(default_factory=list)
    allowed_batches: List[int] = Field(default_factory=list)
    backlog_policy: Optional[str] = None
    raw_criteria: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)


class LocationRequirement(_JobModel):
    """Location and workplace arrangement requirements."""
    raw_location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    workplace_type: WorkplaceType = WorkplaceType.UNKNOWN
    is_remote: bool = False
    evidence: Optional[str] = None


class OtherJobRequirements(_JobModel):
    """Compensation, service agreement/bond, and selection process."""
    salary_or_stipend: Optional[str] = None
    bond_or_service_agreement: Optional[str] = None
    selection_process: List[str] = Field(default_factory=list)
    additional_notes: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)


class JobParsingMetadata(_JobModel):
    """Diagnostics and processing metadata."""
    processing_time_ms: float = 0.0
    raw_text_length: int = 0
    identified_sections: List[str] = Field(default_factory=list)
    missing_critical_sections: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    overall_confidence: float = Field(1.0, ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel = ConfidenceLevel.HIGH


class ParsedJobDescription(_JobModel):
    """Structured, validated representation of a job description."""
    job_id: Optional[str] = None
    title: Optional[str] = None
    company_name: Optional[str] = None
    job_type: JobType = JobType.UNKNOWN
    location: LocationRequirement = Field(default_factory=LocationRequirement)
    experience: ExperienceRequirement = Field(default_factory=ExperienceRequirement)
    required_technical_skills: List[JobSkillRequirement] = Field(default_factory=list)
    preferred_technical_skills: List[JobSkillRequirement] = Field(default_factory=list)
    soft_skills: List[JobSkillRequirement] = Field(default_factory=list)
    education: EducationRequirement = Field(default_factory=EducationRequirement)
    eligibility: EligibilityCriteria = Field(default_factory=EligibilityCriteria)
    responsibilities: List[str] = Field(default_factory=list)
    other_requirements: OtherJobRequirements = Field(default_factory=OtherJobRequirements)
    metadata: JobParsingMetadata = Field(default_factory=JobParsingMetadata)
    parser_version: str = JOB_PARSER_VERSION


__all__ = [
    "JOB_PARSER_VERSION",
    "JobType",
    "WorkplaceType",
    "JobSkillRequirement",
    "ExperienceRequirement",
    "EducationRequirement",
    "EligibilityCriteria",
    "LocationRequirement",
    "OtherJobRequirements",
    "JobParsingMetadata",
    "ParsedJobDescription",
]
