"""
Pydantic v2 data contracts for Sprint 3 Module F: Explainability & NLP Pipeline Integration.

`Sprint3AnalysisResult` is the single structured output of the Sprint 3 NLP layer. It wraps
the outputs of Modules A-E unchanged and adds `explanations` (US-10):

- ComponentExplanation:      what a score component measures, points, deductions, how to improve
- IssueExplanation:          what was detected, where, evidence, confidence, why it matters
- RecommendationExplanation: which issue it addresses, why, what to do, supporting evidence

`overall_score` / `score_label` are None (not 0) when the scoring module itself failed, so a
failure is never mistaken for a very weak resume.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.nlp.content import ContentQualityReport
from app.nlp.formatting import FormattingAnalysisResult
from app.nlp.improvement import ImprovementAreasReport
from app.nlp.recommendations import RecommendationReport
from app.nlp.scoring import ComponentScore, ScoreLabel

SPRINT3_ANALYZER_VERSION = "3.0.0"


class _AnalysisModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class DeductionExplanation(_AnalysisModel):
    rule_id: str
    points_deducted: float = Field(..., ge=0.0)
    reason: str
    evidence: Optional[str] = None
    related_issue_id: Optional[str] = Field(
        None, description="Module D issue this deduction corresponds to, if any"
    )


class ComponentExplanation(_AnalysisModel):
    component: str
    label: str
    what_is_measured: str
    score: float = Field(..., ge=0.0)
    max_score: float = Field(..., gt=0.0)
    weight: float = Field(..., ge=0.0)
    percentage: float = Field(
        ..., ge=0.0, le=100.0, description="score / max_score as a percentage"
    )
    points_lost: float = Field(..., ge=0.0)
    reason: str
    evidence: List[str] = Field(default_factory=list)
    deductions: List[DeductionExplanation] = Field(default_factory=list)
    how_to_improve: List[str] = Field(default_factory=list)
    related_recommendation_ids: List[str] = Field(default_factory=list)


class IssueExplanation(_AnalysisModel):
    issue_id: str
    title: str
    what_was_detected: str
    where: str = Field(..., description="Resume section, or 'whole resume'")
    evidence: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_label: str = Field(..., description="high / medium / low")
    why_it_matters: str
    severity: str
    priority: str
    related_score_component: Optional[str] = None
    recommendation_ids: List[str] = Field(default_factory=list)


class RecommendationExplanation(_AnalysisModel):
    recommendation_id: str
    title: str
    related_issue_ids: List[str] = Field(default_factory=list)
    reason: str = Field(
        ..., description="Why this suggestion was made, in terms of the detected issue"
    )
    suggested_action: str
    supporting_evidence: List[str] = Field(default_factory=list)
    priority: str
    why_this_priority: str


class AnalysisExplanations(_AnalysisModel):
    score_summary: str
    score_breakdown: List[ComponentExplanation] = Field(default_factory=list)
    improvement_areas: List[IssueExplanation] = Field(default_factory=list)
    recommendations: List[RecommendationExplanation] = Field(default_factory=list)
    job_alignment_note: str = Field(
        default="Job-description alignment is not scored in Sprint 3; it is planned for Sprint 4.",
    )


class ModuleError(_AnalysisModel):
    """Structured error from one module; the rest of the analysis still runs."""

    module: str
    error_type: str = Field(..., description="'validation_error' or 'exception'")
    message: str
    details: List[Dict[str, Any]] = Field(
        default_factory=list, description="Pydantic error details for validation errors"
    )


class AnalysisMetadata(_AnalysisModel):
    module_status: Dict[str, str] = Field(
        default_factory=dict, description="module -> ok / failed / skipped"
    )
    module_timings_ms: Dict[str, float] = Field(default_factory=dict)
    processing_time_ms: float = Field(0.0, ge=0.0)
    errors: List[ModuleError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    consistency_checks: Dict[str, bool] = Field(default_factory=dict)
    module_versions: Dict[str, str] = Field(default_factory=dict)
    extraction_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    raw_text_available: bool = False


class Sprint3AnalysisResult(_AnalysisModel):
    """Complete explainable Sprint 3 resume analysis."""

    filename: str
    overall_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    max_score: float = 100.0
    score_label: Optional[ScoreLabel] = None
    component_scores: Dict[str, ComponentScore] = Field(default_factory=dict)
    formatting_analysis: Optional[FormattingAnalysisResult] = None
    content_quality_analysis: Optional[ContentQualityReport] = None
    improvement_areas: Optional[ImprovementAreasReport] = None
    recommendations: Optional[RecommendationReport] = None
    explanations: AnalysisExplanations
    strengths: List[str] = Field(default_factory=list)
    rule_version: Optional[str] = None
    analyzer_version: str = SPRINT3_ANALYZER_VERSION
    analysis_metadata: AnalysisMetadata = Field(default_factory=AnalysisMetadata)


__all__ = [
    "SPRINT3_ANALYZER_VERSION",
    "AnalysisExplanations",
    "AnalysisMetadata",
    "ComponentExplanation",
    "DeductionExplanation",
    "IssueExplanation",
    "ModuleError",
    "RecommendationExplanation",
    "Sprint3AnalysisResult",
]
