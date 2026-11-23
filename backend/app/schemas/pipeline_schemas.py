from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PipelineStageEnum(str, Enum):
    EXTRACTION = "extraction"
    SCORING = "scoring"
    MATCHING = "matching"
    FAIRNESS = "fairness"
    PRIVACY = "privacy"


class StageExecutionMetric(BaseModel):
    stage_name: str
    duration_ms: float
    success: bool
    error_message: Optional[str] = None


class ExtractedProfileDTO(BaseModel):
    skills: List[str] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    sections: Dict[str, str] = Field(default_factory=dict)


class ScoringResultDTO(BaseModel):
    composite_score: float
    bullet_feedback_count: int
    section_grades: Dict[str, str] = Field(default_factory=dict)
    is_advisory: bool = True


class MatchingResultDTO(BaseModel):
    target_role: Optional[str] = None
    match_percentage: float = 0.0
    matched_skills: List[str] = Field(default_factory=list)
    missing_required_skills: List[str] = Field(default_factory=list)
    missing_preferred_skills: List[str] = Field(default_factory=list)


class FairnessAuditDTO(BaseModel):
    is_fair: bool = True
    disparity_ratio: float = 1.0
    flagged_factors: List[str] = Field(default_factory=list)
    audit_notes: str = "Automated fairness verification passed"


class FullPipelineResult(BaseModel):
    profile: ExtractedProfileDTO
    scoring: ScoringResultDTO
    matching: Optional[MatchingResultDTO] = None
    fairness: Optional[FairnessAuditDTO] = None
    total_duration_ms: float = 0.0
    execution_metrics: List[StageExecutionMetric] = Field(default_factory=list)
    is_advisory: bool = True


class PilotBenchmarkSummaryDTO(BaseModel):
    total_resumes_tested: int
    average_duration_ms: float
    average_composite_score: float
    fairness_parity_maintained: bool
    stage_latency_breakdown: Dict[str, float]
