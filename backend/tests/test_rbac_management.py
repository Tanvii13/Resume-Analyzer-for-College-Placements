
from uuid import uuid4, UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app
from app.routers.auth import UserResponse, get_current_user
from app.routers import admin as admin_router
from app.dependencies.roles import require_admin, require_role
from app.services.rbac_service import (
    validate_role,
    InvalidRoleError,
    UserNotFoundError,
    UnauthorizedActorError,
)
from app.services.audit_logger import log_role_change


client = TestClient(app)


# --------------------------------------------------
# TEST FIXTURE
# --------------------------------------------------

@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    original_overrides = app.dependency_overrides.copy()

    yield

    app.dependency_overrides.clear()
    app.dependency_overrides.update(original_overrides)


def set_current_user(role, email="rbac.test@example.com"):
    app.dependency_overrides[get_current_user] = (
        lambda: UserResponse(email=email, role=role)
    )


# --------------------------------------------------
# 1. ROLE VALIDATION TESTS
# --------------------------------------------------

@pytest.mark.parametrize(
    "role",
    ["student", "placement_officer", "career_counselor", "admin"],
)
def test_validate_supported_roles(role):
    assert validate_role(role) == role


def test_validate_role_normalizes_input():
    assert validate_role(" ADMIN ") == "admin"


def test_validate_invalid_role():
    with pytest.raises(InvalidRoleError):
        validate_role("unknown_role")


# --------------------------------------------------
# 2. ADMIN PERMISSION TESTS
# --------------------------------------------------

def test_admin_dependency_allows_admin():
    user = UserResponse(
        email="admin@example.com",
        role="admin",
    )

    result = require_admin(user)

    assert result.role == "admin"


@pytest.mark.parametrize(
    "role",
    ["student", "placement_officer", "career_counselor"],
)
def test_admin_dependency_rejects_non_admin(role):
    user = UserResponse(
        email="user@example.com",
        role=role,
    )

    with pytest.raises(HTTPException) as exc:
        require_admin(user)

    assert exc.value.status_code == 403


# --------------------------------------------------
# 3. DYNAMIC ROLE GUARD TESTS
# --------------------------------------------------

def test_require_role_allows_authorized_role():
    checker = require_role("admin", "placement_officer")

    user = UserResponse(
        email="officer@example.com",
        role="placement_officer",
    )

    assert checker(user).role == "placement_officer"


def test_require_role_rejects_unauthorized_role():
    checker = require_role("admin", "placement_officer")

    user = UserResponse(
        email="student@example.com",
        role="student",
    )

    with pytest.raises(HTTPException) as exc:
        checker(user)

    assert exc.value.status_code == 403


def test_require_role_rejects_empty_allowlist():
    with pytest.raises(ValueError):
        require_role()


# --------------------------------------------------
# 4. ADMIN ROLE UPDATE API TESTS
# --------------------------------------------------

def test_admin_can_update_user_role(monkeypatch):
    set_current_user(
        "admin",
        "admin@example.com",
    )

    target_user_id = str(uuid4())
    service_calls = {}

    def fake_update_user_role(user_id, new_role, actor_email):
        service_calls["user_id"] = user_id
        service_calls["new_role"] = new_role
        service_calls["actor_email"] = actor_email

        return {
            "user_id": user_id,
            "email": "student@example.com",
            "old_role": "student",
            "role": new_role,
            "message": "User role updated successfully.",
        }

    monkeypatch.setattr(
        admin_router,
        "update_user_role",
        fake_update_user_role,
    )

    response = client.put(
        f"/admin/users/{target_user_id}/role",
        json={"role": "career_counselor"},
    )

    assert response.status_code == 200
    assert response.json()["old_role"] == "student"
    assert response.json()["role"] == "career_counselor"

    assert service_calls["user_id"] == target_user_id
    assert service_calls["new_role"] == "career_counselor"
    assert service_calls["actor_email"] == "admin@example.com"


@pytest.mark.parametrize(
    "role",
    ["student", "placement_officer", "career_counselor"],
)
def test_non_admin_cannot_update_user_role(role, monkeypatch):
    set_current_user(role)

    service_called = False

    def fake_update_user_role(*args):
        nonlocal service_called
        service_called = True
        return {}

    monkeypatch.setattr(
        admin_router,
        "update_user_role",
        fake_update_user_role,
    )

    response = client.put(
        f"/admin/users/{uuid4()}/role",
        json={"role": "career_counselor"},
    )

    assert response.status_code == 403
    assert service_called is False


def test_admin_api_rejects_invalid_role(monkeypatch):
    set_current_user("admin")

    def fake_update_user_role(*args):
        raise InvalidRoleError("Unsupported role.")

    monkeypatch.setattr(
        admin_router,
        "update_user_role",
        fake_update_user_role,
    )

    response = client.put(
        f"/admin/users/{uuid4()}/role",
        json={"role": "unknown_role"},
    )

    assert response.status_code == 400


def test_admin_api_handles_missing_user(monkeypatch):
    set_current_user("admin")

    def fake_update_user_role(*args):
        raise UserNotFoundError("User not found or inactive.")

    monkeypatch.setattr(
        admin_router,
        "update_user_role",
        fake_update_user_role,
    )

    response = client.put(
        f"/admin/users/{uuid4()}/role",
        json={"role": "student"},
    )

    assert response.status_code == 404


def test_admin_api_handles_unauthorized_actor(monkeypatch):
    set_current_user("admin")

    def fake_update_user_role(*args):
        raise UnauthorizedActorError("Only active administrators can change user roles.")

    monkeypatch.setattr(
        admin_router,
        "update_user_role",
        fake_update_user_role,
    )

    response = client.put(
        f"/admin/users/{uuid4()}/role",
        json={"role": "student"},
    )

    assert response.status_code == 403


# --------------------------------------------------
# 5. AUDIT LOGGER TEST
# --------------------------------------------------

def test_audit_logger_records_role_change():
    class FakeConnection:
        def __init__(self):
            self.query = None
            self.parameters = None

        def execute(self, query, parameters):
            self.query = query
            self.parameters = parameters

    connection = FakeConnection()

    actor_id = uuid4()
    target_id = uuid4()

    log_role_change(
        conn=connection,
        actor_user_id=actor_id,
        target_user_id=target_id,
        old_role="student",
        new_role="career_counselor",
    )

    assert "INSERT INTO role_change_audit_log" in connection.query
    assert connection.parameters == (
        actor_id,
        target_id,
        "student",
        "career_counselor",
        "role_updated",
    )
