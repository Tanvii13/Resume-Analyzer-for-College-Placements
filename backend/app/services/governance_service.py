"""Persistent human-governance service for Sprint 6 (US-18)."""

from uuid import UUID

from fastapi import HTTPException
from psycopg import Error as PsycopgError

from app.database import get_connection
from app.schemas.governance_schemas import PlacementState


ADVISORY_METADATA = {
    "advisory_only": True,
    "autonomous_rejection_forbidden": True,
    "requires_human_signoff": True,
}

# Allowed human decision transitions.
# PENDING_OFFICER_REVIEW is the initial state, not a decision destination.
ALLOWED_TRANSITIONS = {
    PlacementState.PENDING_OFFICER_REVIEW: {
        PlacementState.SHORTLISTED_BY_OFFICER,
        PlacementState.REJECTED_BY_OFFICER,
        PlacementState.REFERRED_FOR_MANUAL_EVALUATION,
    },
    PlacementState.REFERRED_FOR_MANUAL_EVALUATION: {
        PlacementState.SHORTLISTED_BY_OFFICER,
        PlacementState.REJECTED_BY_OFFICER,
    },
    PlacementState.SHORTLISTED_BY_OFFICER: {
        PlacementState.REFERRED_FOR_MANUAL_EVALUATION,
        PlacementState.REJECTED_BY_OFFICER,
    },
    PlacementState.REJECTED_BY_OFFICER: {
        PlacementState.REFERRED_FOR_MANUAL_EVALUATION,
        PlacementState.SHORTLISTED_BY_OFFICER,
    },
}


def _ensure_candidate_exists(conn, candidate_id: UUID) -> None:
    """Verify that the candidate refers to an existing student account."""

    candidate = conn.execute(
        """
        SELECT u.id
        FROM users AS u
        JOIN user_roles AS ur ON ur.user_id = u.id
        JOIN roles AS r ON r.id = ur.role_id
        WHERE u.id = %s
          AND u.is_active = TRUE
          AND r.name = 'student'
        """,
        (candidate_id,),
    ).fetchone()

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail="Active student candidate not found.",
        )


def register_advisory_score(candidate_id: UUID, score: float) -> dict:
    """
    Store an automated score as advisory information only.

    This operation never changes current_state and never creates
    an automated rejection or any other placement decision.
    """

    if not 0.0 <= score <= 100.0:
        raise HTTPException(
            status_code=422,
            detail="Advisory score must be between 0 and 100.",
        )

    try:
        with get_connection() as conn:
            with conn.transaction():
                _ensure_candidate_exists(conn, candidate_id)

                # Create the initial pending state if it does not exist.
                conn.execute(
                    """
                    INSERT INTO candidate_governance_state (candidate_user_id)
                    VALUES (%s)
                    ON CONFLICT (candidate_user_id) DO NOTHING
                    """,
                    (candidate_id,),
                )

                # Update only the score and timestamp.
                # current_state is deliberately not modified.
                state = conn.execute(
                    """
                    UPDATE candidate_governance_state
                    SET latest_advisory_score = %s,
                        updated_at = NOW()
                    WHERE candidate_user_id = %s
                    RETURNING current_state, latest_advisory_score
                    """,
                    (score, candidate_id),
                ).fetchone()

                audit = conn.execute(
                    """
                    INSERT INTO candidate_governance_audit (
                        candidate_user_id,
                        event_type,
                        advisory_score,
                        advisory_metadata
                    )
                    VALUES (%s, 'advisory_score', %s, %s::jsonb)
                    RETURNING recorded_at
                    """,
                    (
                        candidate_id,
                        score,
                        __import__("json").dumps(ADVISORY_METADATA),
                    ),
                ).fetchone()

                return {
                    "candidate_id": candidate_id,
                    "advisory_score": float(state[1]),
                    "current_state": state[0],
                    "advisory_metadata": ADVISORY_METADATA,
                    "recorded_at": audit[0],
                    "message": (
                        "Advisory score recorded. No placement decision "
                        "was made or changed."
                    ),
                }

    except HTTPException:
        raise
    except PsycopgError as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to register the advisory score.",
        ) from exc


def record_officer_decision(
    candidate_id: UUID,
    officer_email: str,
    decision: PlacementState,
    rationale: str,
) -> dict:
    """Record a human placement decision with rationale and audit history."""

    rationale = rationale.strip()

    if len(rationale) < 15:
        raise HTTPException(
            status_code=422,
            detail="Officer rationale must contain at least 15 characters.",
        )

    try:
        with get_connection() as conn:
            with conn.transaction():
                _ensure_candidate_exists(conn, candidate_id)

                officer = conn.execute(
                    """
                    SELECT u.id
                    FROM users AS u
                    JOIN user_roles AS ur ON ur.user_id = u.id
                    JOIN roles AS r ON r.id = ur.role_id
                    WHERE LOWER(u.email) = LOWER(%s)
                      AND u.is_active = TRUE
                      AND r.name IN ('placement_officer', 'career_counselor')
                    """,
                    (officer_email,),
                ).fetchone()

                if officer is None:
                    raise HTTPException(
                        status_code=403,
                        detail="Authorized placement staff account not found.",
                    )

                # Create the initial state if this is the candidate's first review.
                conn.execute(
                    """
                    INSERT INTO candidate_governance_state (candidate_user_id)
                    VALUES (%s)
                    ON CONFLICT (candidate_user_id) DO NOTHING
                    """,
                    (candidate_id,),
                )

                # Lock the candidate state to prevent concurrent decisions
                # from overwriting each other.
                current = conn.execute(
                    """
                    SELECT current_state, latest_advisory_score
                    FROM candidate_governance_state
                    WHERE candidate_user_id = %s
                    FOR UPDATE
                    """,
                    (candidate_id,),
                ).fetchone()

                previous_state = PlacementState(current[0])
                advisory_score = (
                    float(current[1]) if current[1] is not None else None
                )

                allowed = ALLOWED_TRANSITIONS.get(previous_state, set())

                if decision not in allowed:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"Invalid state transition: {previous_state.value} "
                            f"to {decision.value}."
                        ),
                    )

                # A human decision is marked as an override when it conflicts
                # with the advisory recommendation thresholds.
                is_override = (
                    advisory_score is not None
                    and (
                        (
                            advisory_score < 50.0
                            and decision == PlacementState.SHORTLISTED_BY_OFFICER
                        )
                        or (
                            advisory_score >= 80.0
                            and decision == PlacementState.REJECTED_BY_OFFICER
                        )
                    )
                )

                conn.execute(
                    """
                    UPDATE candidate_governance_state
                    SET current_state = %s,
                        updated_at = NOW()
                    WHERE candidate_user_id = %s
                    """,
                    (decision.value, candidate_id),
                )

                audit = conn.execute(
                    """
                    INSERT INTO candidate_governance_audit (
                        candidate_user_id,
                        actor_user_id,
                        event_type,
                        previous_state,
                        new_state,
                        advisory_score,
                        rationale,
                        is_human_override,
                        advisory_metadata
                    )
                    VALUES (
                        %s, %s, 'human_decision', %s, %s, %s, %s, %s, %s::jsonb
                    )
                    RETURNING id, recorded_at
                    """,
                    (
                        candidate_id,
                        officer[0],
                        previous_state.value,
                        decision.value,
                        advisory_score,
                        rationale,
                        is_override,
                        __import__("json").dumps(ADVISORY_METADATA),
                    ),
                ).fetchone()

                return {
                    "decision_id": audit[0],
                    "candidate_id": candidate_id,
                    "officer_email": officer_email,
                    "previous_state": previous_state,
                    "new_state": decision,
                    "rationale": rationale,
                    "advisory_score": advisory_score,
                    "is_human_override": is_override,
                    "recorded_at": audit[1],
                    "advisory_metadata": ADVISORY_METADATA,
                    "message": "Human placement decision recorded successfully.",
                }

    except HTTPException:
        raise
    except PsycopgError as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to record the human placement decision.",
        ) from exc


def get_decision_history(candidate_id: UUID) -> dict:
    """Retrieve the candidate's current state and complete governance history."""

    try:
        with get_connection() as conn:
            _ensure_candidate_exists(conn, candidate_id)

            state = conn.execute(
                """
                SELECT current_state, latest_advisory_score
                FROM candidate_governance_state
                WHERE candidate_user_id = %s
                """,
                (candidate_id,),
            ).fetchone()

            # A candidate without any governance events starts pending.
            current_state = (
                state[0]
                if state is not None
                else PlacementState.PENDING_OFFICER_REVIEW.value
            )

            latest_score = (
                float(state[1])
                if state is not None and state[1] is not None
                else None
            )

            rows = conn.execute(
                """
                SELECT
                    a.id,
                    a.event_type,
                    u.email,
                    a.previous_state,
                    a.new_state,
                    a.advisory_score,
                    a.rationale,
                    a.is_human_override,
                    a.advisory_metadata,
                    a.recorded_at
                FROM candidate_governance_audit AS a
                LEFT JOIN users AS u ON u.id = a.actor_user_id
                WHERE a.candidate_user_id = %s
                ORDER BY a.recorded_at ASC, a.id ASC
                """,
                (candidate_id,),
            ).fetchall()

            history = [
                {
                    "event_id": row[0],
                    "event_type": row[1],
                    "actor_email": row[2],
                    "previous_state": row[3],
                    "new_state": row[4],
                    "advisory_score": (
                        float(row[5]) if row[5] is not None else None
                    ),
                    "rationale": row[6],
                    "is_human_override": row[7],
                    "advisory_metadata": row[8],
                    "recorded_at": row[9],
                }
                for row in rows
            ]

            return {
                "candidate_id": candidate_id,
                "current_state": current_state,
                "latest_advisory_score": latest_score,
                "total_events": len(history),
                "history": history,
            }

    except HTTPException:
        raise
    except PsycopgError as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve candidate decision history.",
        ) from exc
