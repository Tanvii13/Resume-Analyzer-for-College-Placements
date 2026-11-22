from uuid import UUID
from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field


class FactorContribution(BaseModel):
    """
    US-19: Identifiable breakdown of a single scoring factor.
    """
    factor_name: str = Field(..., description="Name of the scoring dimension (e.g. Technical Skills)")
    weight_percentage: float = Field(..., description="Weight of this factor in overall score (e.g. 40.0)")
    points_awarded: float = Field(..., description="Points earned in this dimension")
    max_points: float = Field(..., description="Maximum possible points for this dimension")
    description: str = Field(..., description="Explanation of what this factor evaluates")
    positive_drivers: List[str] = Field(default_factory=list, description="Specific elements that boosted score")
    negative_penalties: List[str] = Field(default_factory=list, description="Areas of deduction or missing gap")


class ScoreFactorBreakdown(BaseModel):
    """
    US-19 / DR-09: Complete transparent explainability breakdown for a resume score.
    """
    resume_id: Union[UUID, str]
    total_composite_score: float
    factors: List[FactorContribution] = Field(default_factory=list)
    advisory_notice: str = Field(
        default="This automated score is for guidance and supporting information only. Final placement decisions rest strictly with human decision makers.",
        description="Mandatory advisory notice per US-18 / US-19"
    )
    explainability_summary: str = Field(..., description="Human-readable synthesis of scoring rationale")
    is_fairness_certified: bool = Field(default=True, description="Indicates that demographic neutrality check passed")


class FairnessAuditRequest(BaseModel):
    """
    Payload for running a demographic neutrality and fairness audit on resume text.
    """
    raw_text: str = Field(..., min_length=1, description="Raw resume text to evaluate")
    extracted_skills: Optional[List[str]] = Field(default_factory=list, description="List of recognized skills")
    target_role: Optional[str] = Field(None, description="Optional target job profile")


class FairnessAuditReport(BaseModel):
    """
    US-19: Audit report certifying demographic neutrality and recording disparities.
    """
    is_demographically_neutral: bool = Field(..., description="True if non-job demographic tokens produce zero score disparity")
    detected_non_job_tokens: Dict[str, List[str]] = Field(default_factory=dict, description="Detected demographic, gender, or non-job tokens")
    score_disparity_detected: bool = Field(default=False, description="True if swapping demographic attributes causes score divergence")
    disparity_delta: float = Field(default=0.0, description="Measured score divergence across variants")
    fairness_audit_passed: bool = Field(default=True, description="Overall compliance with US-19 fairness standards")
    flags: List[str] = Field(default_factory=list, description="Recorded potential fairness warnings or issues for review")
    advisory_status: str = Field(default="SUPPORTING_INFORMATION_ONLY", description="Enforces non-autonomous status per US-18")
