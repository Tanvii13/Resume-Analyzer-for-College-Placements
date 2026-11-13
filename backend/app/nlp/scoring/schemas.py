"""
Pydantic v2 data contracts for the Sprint 3 Resume Scoring Engine.

Defines schemas for:
- ComponentScore: Explainable score breakdown for an individual scoring dimension.
- ScoreDeduction: Identifiable deduction itemizing why points were lost.
- ScoreLabel: Categorical readiness tier (Excellent, Good, Fair, Needs Improvement).
- ScoringResult: Complete explainable score evaluation matching Prompt A specifications.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class _ScoringModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ScoreLabel(str, Enum):
    """Categorical placement readiness classification."""
    EXCELLENT = "Excellent"                  # >= 85.0
    GOOD = "Good"                            # 70.0 - 84.99
    FAIR = "Fair"                            # 50.0 - 69.99
    NEEDS_IMPROVEMENT = "Needs Improvement"  # < 50.0

    @classmethod
    def from_score(cls, score: float) -> "ScoreLabel":
        if score >= 85.0:
            return cls.EXCELLENT
        if score >= 70.0:
            return cls.GOOD
        if score >= 50.0:
            return cls.FAIR
        return cls.NEEDS_IMPROVEMENT


class ScoreDeduction(_ScoringModel):
    """An explainable deduction recording why points were lost."""
    component: str = Field(..., description="Scoring component where deduction occurred")
    rule_id: str = Field(..., description="Machine-readable rule identifier (e.g. SEC_MISSING_PROJECTS)")
    points_deducted: float = Field(..., ge=0.0, description="Points subtracted from max component score")
    reason: str = Field(..., description="Human-readable explanation of why points were lost")
    evidence: Optional[str] = Field(None, description="Extracted profile evidence or lack thereof")


class ComponentScore(_ScoringModel):
    """Detailed score evaluation for one scoring dimension."""
    component: str = Field(..., description="Name of the scoring component")
    score: float = Field(..., ge=0.0, description="Earned points for this component")
    max_score: float = Field(..., gt=0.0, description="Maximum possible points for this component")
    weight: float = Field(..., ge=0.0, description="Configured weight allocated to this component")
    evidence: List[str] = Field(default_factory=list, description="Positive signals detected in candidate profile")
    reason: str = Field(..., description="Summary explanation of the component score")
    how_to_improve: List[str] = Field(default_factory=list, description="Actionable improvement suggestions")


class ScoringResult(_ScoringModel):
    """Overall explainable placement readiness score report."""
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Placement readiness score clamped to 0-100")
    max_score: float = Field(default=100.0, description="Maximum possible overall score")
    score_label: ScoreLabel = Field(..., description="Categorical readiness classification")
    component_scores: Dict[str, ComponentScore] = Field(
        ...,
        description="Keyed dictionary of component scores (e.g. section_completeness, content_quality)",
    )
    strengths: List[str] = Field(default_factory=list, description="Top positive placement-ready attributes found")
    deductions: List[ScoreDeduction] = Field(default_factory=list, description="Itemized point deductions")
    rule_version: str = Field(..., description="Scoring rule set version")
    scoring_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metadata including weight configuration and diagnostics",
    )


__all__ = [
    "ScoreLabel",
    "ScoreDeduction",
    "ComponentScore",
    "ScoringResult",
]
