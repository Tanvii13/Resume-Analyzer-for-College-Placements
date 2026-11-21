from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WeakArea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str = "General"
    priority: str = "Medium"
    issue: str
    remediation: Optional[str] = None


# US-09: BULLET POINT ANALYSIS

class BulletAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bullet: str = Field(..., min_length=1)


class BulletAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_text: str
    is_weak: bool
    weak_verbs_found: List[str]
    has_action_verb: bool
    action_verb_used: Optional[str]
    has_quantified_metric: bool
    detected_metric: Optional[str]
    suggestion: str
    star_template_example: str


class BulletAuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bullet_text: str = Field(..., min_length=1)


class BulletAuditResponse(BulletAnalysisResponse):
    pass


# US-09: RESUME SUGGESTIONS

class ResumeSuggestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extracted_skills: Dict[str, List[str]]
    raw_text: str
    weak_areas: Optional[List[WeakArea]] = None


class ResumeSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str
    priority: str
    issue: str
    recommendation: str


class SectionSuggestion(ResumeSuggestion):
    pass


class ResumeSuggestionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_id: Optional[UUID] = None
    suggestions_count: int = 0
    priority_breakdown: Dict[str, int] = Field(
        default_factory=lambda: {
            "High": 0,
            "Medium": 0,
            "Low": 0,
        }
    )
    suggestions: List[ResumeSuggestion]


# US-11: JOB DESCRIPTION MATCHING

class JDMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_skills: List[str]
    jd_text: str = Field(..., min_length=1)


class JDMatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_jd_skills_found: int
    matched_skills_count: int
    missing_skills_count: int
    match_percentage: float = Field(ge=0, le=100)
    matched_skills: List[str]
    missing_skills: List[str]
    gap_recommendations: List[str]


class JDCompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jd_text: str = Field(..., min_length=1)
    target_role: Optional[str] = None


class JDMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = "Not specified"
    experience_level: str = "Not specified"
    minimum_experience_years: Optional[float] = None
    required_degrees: List[str] = Field(default_factory=list)
    required_disciplines: List[str] = Field(default_factory=list)
    word_count: int
    clean_text: str


class JDCompareResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_id: UUID
    target_role: Optional[str] = None
    jd_metadata: JDMetadata
    total_jd_skills_found: int
    matched_skills_count: int
    missing_skills_count: int
    match_percentage: float = Field(ge=0, le=100)
    matched_skills: List[str]
    missing_skills: List[str]
    gap_recommendations: List[str]


# US-08: IMPROVEMENT AREA DETECTION

class ImprovementAreaItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    section: str
    priority: str
    issue: str
    reason: str
    remediation: str


class ImprovementAreasResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resume_id: UUID
    total_issues_count: int
    priority_breakdown: Dict[str, int]
    improvement_areas: List[ImprovementAreaItem]
