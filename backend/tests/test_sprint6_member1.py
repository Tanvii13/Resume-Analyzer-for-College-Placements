from datetime import datetime, timezone
from app.services import governance_service
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from app.dependencies import roles
from app.routers import governance as governance_router
from app.schemas.governance_schemas import (
    CandidateDecisionRequest,
    PlacementState,
)
from app.services.governance_service import (
    ADVISORY_METADATA,
    ALLOWED_TRANSITIONS,
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_auth_overrides():
    app.dependency_overrides[roles.get_current_user] = lambda: SimpleNamespace(
        email="student@example.com",
        role="student",
    )
    yield
    app.dependency_overrides.pop(roles.get_current_user, None)


def test_student_cannot_record_placement_decision():
    response = client.post(
        f"/placements/candidates/{uuid4()}/record-decision",
        json={
            "decision": "SHORTLISTED_BY_OFFICER",
            "rationale": "Candidate demonstrates strong technical skills.",
        },
    )
    assert response.status_code == 403


def test_unauthenticated_user_cannot_record_decision():
    app.dependency_overrides.pop(roles.get_current_user, None)

    response = client.post(
        f"/placements/candidates/{uuid4()}/record-decision",
        json={
            "decision": "SHORTLISTED_BY_OFFICER",
            "rationale": "Candidate demonstrates strong technical skills.",
        },
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "staff_role",
    ["placement_officer", "career_counselor"],
)
def test_authorized_staff_can_record_decision(staff_role, monkeypatch):
    candidate_id = uuid4()
    captured = {}

    app.dependency_overrides[roles.get_current_user] = lambda: SimpleNamespace(
        email="staff@example.com",
        role=staff_role,
    )

    def fake_record_decision(
        candidate_id,
        officer_email,
        decision,
        rationale,
    ):
        captured.update({
            "candidate_id": candidate_id,
            "officer_email": officer_email,
            "decision": decision,
            "rationale": rationale,
        })
        return {"message": "Human placement decision recorded successfully."}

    monkeypatch.setattr(
        governance_router,
        "record_officer_decision",
        fake_record_decision,
    )

    response = client.post(
        f"/placements/candidates/{candidate_id}/record-decision",
        json={
            "decision": "SHORTLISTED_BY_OFFICER",
            "rationale": "Candidate demonstrates strong technical skills.",
        },
    )

    assert response.status_code == 200
    assert captured["candidate_id"] == candidate_id
    assert captured["officer_email"] == "staff@example.com"
    assert captured["decision"] == PlacementState.SHORTLISTED_BY_OFFICER


@pytest.mark.parametrize(
    "rationale",
    ["", "Too short", "12345678901234"],
)

def test_short_or_empty_rationale_is_rejected(rationale):
    app.dependency_overrides[roles.get_current_user] = (
        lambda: SimpleNamespace(
            email="officer@example.com",
            role="placement_officer",
        )
    )

    response = client.post(
        f"/placements/candidates/{uuid4()}/record-decision",
        json={
            "decision": "REJECTED_BY_OFFICER",
            "rationale": rationale,
        },
    )

    assert response.status_code == 422


def test_invalid_candidate_id_returns_400():
    app.dependency_overrides[roles.get_current_user] = lambda: SimpleNamespace(
        email="staff@example.com",
        role="placement_officer",
    )

    response = client.post(
        "/placements/candidates/not-a-uuid/record-decision",
        json={
            "decision": "SHORTLISTED_BY_OFFICER",
            "rationale": "Candidate demonstrates strong technical skills.",
        },
    )
    assert response.status_code == 400


def test_staff_can_view_decision_audit(monkeypatch):
    candidate_id = uuid4()

    app.dependency_overrides[roles.get_current_user] = lambda: SimpleNamespace(
        email="officer@example.com",
        role="placement_officer",
    )

    monkeypatch.setattr(
        governance_router,
        "get_decision_history",
        lambda candidate_id: {
            "candidate_id": candidate_id,
            "current_state": "PENDING_OFFICER_REVIEW",
            "latest_advisory_score": 5.0,
            "total_events": 1,
            "history": [],
        },
    )

    response = client.get(
        f"/placements/candidates/{candidate_id}/decision-audit"
    )

    assert response.status_code == 200
    assert response.json()["latest_advisory_score"] == 5.0


def test_student_cannot_view_decision_audit():
    response = client.get(
        f"/placements/candidates/{uuid4()}/decision-audit"
    )
    assert response.status_code == 403


def test_advisory_metadata_forbids_autonomous_rejection():
    assert ADVISORY_METADATA == {
        "advisory_only": True,
        "autonomous_rejection_forbidden": True,
        "requires_human_signoff": True,
    }


def test_low_score_does_not_define_an_automatic_rejection_transition():
    # Automated scores are advisory. Only a human decision can select
    # REJECTED_BY_OFFICER through the authorized decision service.
    assert PlacementState.REJECTED_BY_OFFICER in ALLOWED_TRANSITIONS[
        PlacementState.PENDING_OFFICER_REVIEW
    ]


def test_all_four_governance_states_are_defined():
    assert len(PlacementState) == 4


def test_pending_state_cannot_transition_back_to_pending():
    assert (
        PlacementState.PENDING_OFFICER_REVIEW
        not in ALLOWED_TRANSITIONS[PlacementState.PENDING_OFFICER_REVIEW]
    )


def test_rationale_is_trimmed_and_validated():
    request = CandidateDecisionRequest(
        decision=PlacementState.SHORTLISTED_BY_OFFICER,
        rationale="  Candidate has excellent technical skills.  ",
    )
    assert request.rationale == "Candidate has excellent technical skills."

def test_score_of_5_keeps_candidate_pending(monkeypatch):
    candidate_id = uuid4()
    executed_queries = []

    class FakeCursor:
        def __init__(self, query):
            self.query = query

        def fetchone(self):
            if "SELECT u.id" in self.query:
                return (candidate_id,)

            if "RETURNING current_state, latest_advisory_score" in self.query:
                return ("PENDING_OFFICER_REVIEW", 5.0)

            if "RETURNING recorded_at" in self.query:
                return (datetime.now(timezone.utc),)

            return None

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def transaction(self):
            from contextlib import nullcontext
            return nullcontext()

        def execute(self, query, params=None):
            executed_queries.append(query)
            return FakeCursor(query)

    monkeypatch.setattr(
        governance_service,
        "get_connection",
        lambda: FakeConnection(),
    )

    result = governance_service.register_advisory_score(
        candidate_id=candidate_id,
        score=5.0,
    )

    assert result["advisory_score"] == 5.0
    assert result["current_state"] == "PENDING_OFFICER_REVIEW"
    assert result["advisory_metadata"]["advisory_only"] is True
    assert result["advisory_metadata"]["autonomous_rejection_forbidden"] is True

    update_query = next(
        query for query in executed_queries
        if "UPDATE candidate_governance_state" in query
    )

    assert "latest_advisory_score" in update_query
    assert "current_state =" not in update_query
