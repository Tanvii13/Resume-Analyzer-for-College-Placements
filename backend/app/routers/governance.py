"""
Human governance and placement decision endpoints for Sprint 6 (US-18).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.roles import require_staff_or_counselor
from app.routers.auth import UserResponse
from app.schemas.governance_schemas import CandidateDecisionRequest
from app.services.governance_service import (
    record_officer_decision,
    get_decision_history,
)


router = APIRouter(
    prefix="/placements",
    tags=["Placement Governance"],
)


def parse_candidate_id(candidate_id: str) -> UUID:
    """
    Convert the candidate ID from the URL into a UUID.
    Return HTTP 400 when the supplied ID is invalid.
    """

    try:
        return UUID(candidate_id)
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid candidate ID. A valid UUID is required.",
        )


@router.post("/candidates/{candidate_id}/record-decision")
def submit_candidate_decision(
    candidate_id: str,
    request: CandidateDecisionRequest,
    current_user: UserResponse = Depends(require_staff_or_counselor),
):
    """
    Allow authorized placement staff to record a human placement decision.
    Every decision must contain a rationale of at least 15 characters.
    """

    candidate_uuid = parse_candidate_id(candidate_id)

    return record_officer_decision(
        candidate_id=candidate_uuid,
        officer_email=current_user.email,
        decision=request.decision,
        rationale=request.rationale,
    )


@router.get("/candidates/{candidate_id}/decision-audit")
def get_candidate_decision_audit(
    candidate_id: str,
    current_user: UserResponse = Depends(require_staff_or_counselor),
):
    """
    Retrieve the audit history of human decisions and automated advisory scores.
    """

    candidate_uuid = parse_candidate_id(candidate_id)

    return get_decision_history(
        candidate_id=candidate_uuid,
    )
