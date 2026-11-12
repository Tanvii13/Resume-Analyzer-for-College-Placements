
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WeakArea(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str = "General"
    priority: str = "Medium"
    issue: str
    remediation: Optional[str] = None


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


class ResumeSuggestionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggestions: List[ResumeSuggestion]


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
