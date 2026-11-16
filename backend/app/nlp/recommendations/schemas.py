"""
Pydantic v2 data contracts for Sprint 3 Module E: Rule-Based Recommendation Engine.

Defines schemas for:
- RecommendationCategory: Which part of the resume a recommendation is about.
- RecommendationPriority: Deterministic triage tier (high, medium, low).
- Recommendation: One actionable, evidence-backed suggestion mapped to a detected issue.
- RecommendationReport: The full prioritized recommendation list for a resume.

Every Recommendation is tied to at least one ImprovementIssue from Module D through
`related_issue_id` / `related_issue_ids`. The engine never produces advice that is not
backed by a detected issue.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

RECOMMENDATION_ENGINE_VERSION = "3.0.0"


class RecommendationCategory(str, Enum):
    """Resume area a recommendation targets."""

    MISSING_SECTION = "missing_section"
    CONTACT = "contact"
    EDUCATION = "education"
    PROJECT_DESCRIPTION = "project_description"
    EXPERIENCE = "experience"
    CONTENT = "content"
    SKILLS = "skills"
    FORMATTING = "formatting"
    EXTRACTION = "extraction"


class RecommendationPriority(str, Enum):
    """Triage tier derived from the deterministic priority score."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class _RecommendationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Recommendation(_RecommendationModel):
    """A single actionable improvement suggestion."""

    recommendation_id: str = Field(
        ..., description="Stable identifier, e.g. 'REC_ADD_PROJECTS_SECTION'"
    )
    related_issue_id: str = Field(
        ..., description="Primary Module D issue this recommendation addresses"
    )
    related_issue_ids: List[str] = Field(
        default_factory=list,
        description="All Module D issues addressed (more than one when duplicate advice was merged)",
    )
    title: str = Field(..., description="Short student-facing headline")
    category: RecommendationCategory
    description: str = Field(..., description="What to change, in plain language")
    why_it_matters: str = Field(..., description="Why this change helps in campus placements")
    suggested_action: str = Field(..., description="The single most important next step")
    action_steps: List[str] = Field(
        default_factory=list, description="Concrete checklist for making the change"
    )
    priority: RecommendationPriority
    priority_score: float = Field(
        ..., ge=0.0, le=1.0, description="Deterministic ranking score (higher first)"
    )
    severity: str = Field(
        ..., description="Severity inherited from the related issue (critical/warning/info)"
    )
    affected_section: Optional[str] = Field(
        None, description="Resume section the change applies to"
    )
    related_score_component: Optional[str] = Field(
        None, description="Scoring component this affects"
    )
    potential_score_gain: Optional[float] = Field(
        None,
        ge=0.0,
        description="Upper bound of points deducted by Module A for this issue (None if not linked to a deduction)",
    )
    evidence: List[str] = Field(
        default_factory=list, description="Detected evidence supporting the recommendation"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence inherited from the detected issue"
    )
    low_confidence: bool = Field(
        False, description="True when the underlying detection is uncertain"
    )
    rule_id: str = Field(..., description="Recommendation rule that produced this item")


class RecommendationReport(_RecommendationModel):
    """Prioritized, deduplicated recommendations for one resume."""

    total_recommendations: int = Field(..., ge=0)
    high_priority_count: int = Field(..., ge=0)
    medium_priority_count: int = Field(..., ge=0)
    low_priority_count: int = Field(..., ge=0)
    recommendations: List[Recommendation] = Field(default_factory=list)
    unmapped_issue_ids: List[str] = Field(
        default_factory=list,
        description="Issues with no dedicated rule; they are covered by the generic fallback rule",
    )
    engine_version: str = Field(default=RECOMMENDATION_ENGINE_VERSION)
    metadata: Dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "RECOMMENDATION_ENGINE_VERSION",
    "RecommendationCategory",
    "RecommendationPriority",
    "Recommendation",
    "RecommendationReport",
]
