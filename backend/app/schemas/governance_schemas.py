from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PlacementState(str, Enum):
    """Allowed human-governed candidate placement states."""

    PENDING_OFFICER_REVIEW = "PENDING_OFFICER_REVIEW"
    SHORTLISTED_BY_OFFICER = "SHORTLISTED_BY_OFFICER"
    REJECTED_BY_OFFICER = "REJECTED_BY_OFFICER"
    REFERRED_FOR_MANUAL_EVALUATION = "REFERRED_FOR_MANUAL_EVALUATION"


class AdvisoryMetadata(BaseModel):
    """Mandatory safeguards accompanying automated recommendations."""

    advisory_only: bool = True
    autonomous_rejection_forbidden: bool = True
    requires_human_signoff: bool = True


class AdvisoryScoreRequest(BaseModel):
    """Request to register an automated score as advisory information."""

    score: float = Field(ge=0.0, le=100.0)


class AdvisoryScoreResponse(BaseModel):
    """Response after registering an advisory score."""

    candidate_id: UUID
    advisory_score: float
    current_state: PlacementState
    advisory_metadata: AdvisoryMetadata
    recorded_at: datetime
    message: str


class CandidateDecisionRequest(BaseModel):
    """A placement decision explicitly submitted by authorized human staff."""

    decision: PlacementState
    rationale: str = Field(min_length=15, max_length=2000)

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, value: str) -> str:
        cleaned = value.strip()

        if len(cleaned) < 15:
            raise ValueError(
                "Officer rationale must contain at least 15 non-whitespace characters."
            )

        return cleaned


class CandidateDecisionResponse(BaseModel):
    """Result of a successfully recorded human placement decision."""

    decision_id: UUID
    candidate_id: UUID
    officer_email: str
    previous_state: PlacementState
    new_state: PlacementState
    rationale: str
    advisory_score: Optional[float] = None
    is_human_override: bool
    recorded_at: datetime
    advisory_metadata: AdvisoryMetadata
    message: str


class DecisionAuditItem(BaseModel):
    """One historical advisory or human-decision event."""

    event_id: UUID
    event_type: str
    actor_email: Optional[str] = None
    previous_state: Optional[PlacementState] = None
    new_state: Optional[PlacementState] = None
    advisory_score: Optional[float] = None
    rationale: Optional[str] = None
    is_human_override: bool
    advisory_metadata: AdvisoryMetadata
    recorded_at: datetime


class DecisionHistoryResponse(BaseModel):
    """Complete governance history for a candidate."""

    candidate_id: UUID
    current_state: PlacementState
    latest_advisory_score: Optional[float] = None
    total_events: int
    history: List[DecisionAuditItem]
