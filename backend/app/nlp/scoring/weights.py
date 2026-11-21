"""
Scoring weights and configuration for the Sprint 3 Resume Scoring Engine.

Follows the project audit specification:
- Section completeness:      Reference 20
- Content quality:           Reference 25
- Skill visibility:          Reference 20
- Formatting/readability:    Reference 15
- Job-description alignment: Reference 20 (Deferred to Sprint 4)

Active Sprint 3 reference sum is 80 points.
The default redistribution proportionally scales active components to 100.0 points:
- Section completeness:      25.00  (20 * 1.25)
- Content quality:           31.25  (25 * 1.25)
- Skill visibility:          25.00  (20 * 1.25)
- Formatting/readability:    18.75  (15 * 1.25)
Total:                      100.00
"""

from typing import Dict
from pydantic import BaseModel, ConfigDict, Field

SCORING_RULE_VERSION = "3.0.0"

# Component Identifier Constants
COMPONENT_SECTION_COMPLETENESS = "section_completeness"
COMPONENT_CONTENT_QUALITY = "content_quality"
COMPONENT_SKILL_VISIBILITY = "skill_visibility"
COMPONENT_FORMATTING_READABILITY = "formatting_readability"
COMPONENT_JOB_ALIGNMENT = "job_alignment"

# Reference Weights (Audit Baseline)
REFERENCE_WEIGHTS: Dict[str, float] = {
    COMPONENT_SECTION_COMPLETENESS: 20.0,
    COMPONENT_CONTENT_QUALITY: 25.0,
    COMPONENT_SKILL_VISIBILITY: 20.0,
    COMPONENT_FORMATTING_READABILITY: 15.0,
    COMPONENT_JOB_ALIGNMENT: 20.0,
}

# Sprint 3 Proportional Redistribution (scaled to 100 total)
SPRINT3_DEFAULT_WEIGHTS: Dict[str, float] = {
    COMPONENT_SECTION_COMPLETENESS: 25.0,
    COMPONENT_CONTENT_QUALITY: 31.25,
    COMPONENT_SKILL_VISIBILITY: 25.0,
    COMPONENT_FORMATTING_READABILITY: 18.75,
    COMPONENT_JOB_ALIGNMENT: 0.0,
}


class ScoringWeights(BaseModel):
    """
    Configurable weights allocated to each scoring dimension.
    Enables supervisor/product-owner customization while enforcing 0-100 boundaries.
    """
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    section_completeness: float = Field(
        default=SPRINT3_DEFAULT_WEIGHTS[COMPONENT_SECTION_COMPLETENESS],
        ge=0.0,
        le=100.0,
        description="Weight allocated to section presence and completeness",
    )
    content_quality: float = Field(
        default=SPRINT3_DEFAULT_WEIGHTS[COMPONENT_CONTENT_QUALITY],
        ge=0.0,
        le=100.0,
        description="Weight allocated to action verbs, metrics, and bullet quality",
    )
    skill_visibility: float = Field(
        default=SPRINT3_DEFAULT_WEIGHTS[COMPONENT_SKILL_VISIBILITY],
        ge=0.0,
        le=100.0,
        description="Weight allocated to skill volume, diversity, and organization",
    )
    formatting_readability: float = Field(
        default=SPRINT3_DEFAULT_WEIGHTS[COMPONENT_FORMATTING_READABILITY],
        ge=0.0,
        le=100.0,
        description="Weight allocated to structure, layout signals, and extractability",
    )
    job_alignment: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Weight allocated to job description matching (Sprint 4)",
    )

    @property
    def total_weight(self) -> float:
        """Sum of all configured component weights."""
        return round(
            self.section_completeness
            + self.content_quality
            + self.skill_visibility
            + self.formatting_readability
            + self.job_alignment,
            4,
        )

    @classmethod
    def default_sprint3(cls) -> "ScoringWeights":
        """Default proportional weights totaling 100.0 for Sprint 3."""
        return cls()

    @classmethod
    def audit_reference_raw(cls) -> "ScoringWeights":
        """Reference weights matching the unscaled audit baseline (sums to 80.0 active)."""
        return cls(
            section_completeness=REFERENCE_WEIGHTS[COMPONENT_SECTION_COMPLETENESS],
            content_quality=REFERENCE_WEIGHTS[COMPONENT_CONTENT_QUALITY],
            skill_visibility=REFERENCE_WEIGHTS[COMPONENT_SKILL_VISIBILITY],
            formatting_readability=REFERENCE_WEIGHTS[COMPONENT_FORMATTING_READABILITY],
            job_alignment=0.0,
        )


__all__ = [
    "SCORING_RULE_VERSION",
    "COMPONENT_SECTION_COMPLETENESS",
    "COMPONENT_CONTENT_QUALITY",
    "COMPONENT_SKILL_VISIBILITY",
    "COMPONENT_FORMATTING_READABILITY",
    "COMPONENT_JOB_ALIGNMENT",
    "REFERENCE_WEIGHTS",
    "SPRINT3_DEFAULT_WEIGHTS",
    "ScoringWeights",
]
