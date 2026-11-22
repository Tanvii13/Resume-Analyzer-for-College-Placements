from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from app.dependencies import roles
from app.routers import officer as officer_router


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_auth_overrides():
    app.dependency_overrides[roles.get_current_user] = (
        lambda: SimpleNamespace(
            email="student@example.com",
            role="student",
        )
    )

    yield

    app.dependency_overrides.pop(roles.get_current_user, None)


def test_student_cannot_access_officer_endpoint():
    student_id = str(uuid4())

    response = client.get(
        f"/officer/students/{student_id}/resume-analysis"
    )

    assert response.status_code == 403


@pytest.mark.parametrize(
    "staff_role",
    ["placement_officer", "career_counselor"],
)
def test_authorized_staff_can_access_endpoint(
    staff_role,
    monkeypatch,
):
    student_id = str(uuid4())
    service_calls = {}

    app.dependency_overrides[roles.get_current_user] = (
        lambda: SimpleNamespace(
            email="staff@example.com",
            role=staff_role,
        )
    )

    def fake_inspect_student_resume(student_id, staff_email):
        service_calls["student_id"] = student_id
        service_calls["staff_email"] = staff_email

        return {
            "student": {"id": student_id},
            "analysis": {"analysis_type": "placement_readiness"},
        }

    monkeypatch.setattr(
        officer_router,
        "inspect_student_resume",
        fake_inspect_student_resume,
    )

    response = client.get(
        f"/officer/students/{student_id}/resume-analysis"
    )

    assert response.status_code == 200
    assert response.json()["analysis"]["analysis_type"] == (
        "placement_readiness"
    )
    assert service_calls["student_id"] == student_id
    assert service_calls["staff_email"] == "staff@example.com"


def test_unauthorized_access_does_not_call_service(monkeypatch):
    service_called = False

    def fake_inspect_student_resume(student_id, staff_email):
        nonlocal service_called
        service_called = True
        return {}

    monkeypatch.setattr(
        officer_router,
        "inspect_student_resume",
        fake_inspect_student_resume,
    )

    response = client.get(
        f"/officer/students/{uuid4()}/resume-analysis"
    )

    assert response.status_code == 403
    assert service_called is False


def test_invalid_student_id_is_rejected():
    app.dependency_overrides[roles.get_current_user] = (
        lambda: SimpleNamespace(
            email="staff@example.com",
            role="placement_officer",
        )
    )

    response = client.get(
        "/officer/students/not-a-valid-uuid/resume-analysis"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid student ID format."


def test_career_counselor_can_submit_review(monkeypatch):
    student_id = str(uuid4())
    resume_id = str(uuid4())
    saved_review = {}

    app.dependency_overrides[roles.get_current_user] = (
        lambda: SimpleNamespace(
            email="counselor@example.com",
            role="career_counselor",
        )
    )

    def fake_create_review(
        student_id,
        resume_id,
        reviewer_email,
        review_status,
        notes,
    ):
        saved_review.update({
            "student_id": student_id,
            "resume_id": resume_id,
            "reviewer_email": reviewer_email,
            "status": review_status,
            "notes": notes,
        })
        return {
            "id": str(uuid4()),
            "status": review_status,
            "notes": notes,
        }

    monkeypatch.setattr(
        officer_router,
        "create_counselor_review",
        fake_create_review,
    )

    response = client.post(
        f"/officer/students/{student_id}/resumes/{resume_id}/reviews",
        json={
            "status": "Approved for Placement",
            "notes": "Resume reviewed successfully.",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Approved for Placement"
    assert saved_review["reviewer_email"] == "counselor@example.com"
    assert saved_review["student_id"] == student_id
    assert saved_review["resume_id"] == resume_id


def test_placement_officer_cannot_submit_counselor_review(
    monkeypatch,
):
    app.dependency_overrides[roles.get_current_user] = (
        lambda: SimpleNamespace(
            email="officer@example.com",
            role="placement_officer",
        )
    )

    service_called = False

    def fake_create_review(**kwargs):
        nonlocal service_called
        service_called = True
        return {}

    monkeypatch.setattr(
        officer_router,
        "create_counselor_review",
        fake_create_review,
    )

    response = client.post(
        f"/officer/students/{uuid4()}/resumes/{uuid4()}/reviews",
        json={
            "status": "Revision Needed",
            "notes": "Please improve project descriptions.",
        },
    )

    assert response.status_code == 403
    assert service_called is False


def test_authorized_staff_can_view_review_history(monkeypatch):
    student_id = str(uuid4())
    resume_id = str(uuid4())

    app.dependency_overrides[roles.get_current_user] = (
        lambda: SimpleNamespace(
            email="officer@example.com",
            role="placement_officer",
        )
    )

    monkeypatch.setattr(
        officer_router,
        "get_counselor_review_history",
        lambda student_id, resume_id: [
            {
                "id": str(uuid4()),
                "reviewer_name": "Career Counselor",
                "status": "Revision Needed",
                "notes": "Add more project details.",
                "reviewed_at": "2026-11-17T10:00:00",
            }
        ],
    )

    response = client.get(
        f"/officer/students/{student_id}/resumes/{resume_id}/reviews"
    )

    assert response.status_code == 200
    assert response.json()["student_id"] == student_id
    assert response.json()["resume_id"] == resume_id
    assert len(response.json()["reviews"]) == 1
    assert response.json()["reviews"][0]["status"] == "Revision Needed"
