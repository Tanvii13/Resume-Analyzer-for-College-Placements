import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app

client = TestClient(app)


def register_test_user():
    email = f"student-{uuid4().hex}@example.com"
    password = "TestPass123!"

    response = client.post(
        "/auth/register",
        json={
            "full_name": "Test Student",
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 201, response.text
    return email, password


def get_access_token():
    email, password = register_test_user()

    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )

    assert response.status_code == 200, response.text
    return email, response.json()["access_token"]


def test_register_success():
    email, _ = register_test_user()

    response = client.post(
        "/auth/login",
        data={"username": email, "password": "TestPass123!"},
    )

    assert response.status_code == 200


def test_register_duplicate_email():
    email, _ = register_test_user()

    response = client.post(
        "/auth/register",
        json={
            "full_name": "Another Student",
            "email": email,
            "password": "AnotherPass123!",
        },
    )

    assert response.status_code == 409


def test_login_success():
    email, password = register_test_user()

    response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password():
    email, _ = register_test_user()

    response = client.post(
        "/auth/login",
        data={"username": email, "password": "WrongPassword123!"},
    )

    assert response.status_code == 401


def test_login_unknown_user():
    response = client.post(
        "/auth/login",
        data={
            "username": f"unknown-{uuid4().hex}@example.com",
            "password": "TestPass123!",
        },
    )

    assert response.status_code == 401


def test_profile_without_token():
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_profile_with_valid_token():
    email, token = get_access_token()

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == email
    assert response.json()["role"] == "student"


def test_profile_with_invalid_token():
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401

def test_register_rejects_short_password():
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Test Student",
            "email": f"short-{uuid4().hex}@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_profile_with_expired_token():
    from datetime import datetime, timedelta, timezone
    import jwt

    from app.services.auth_service import ALGORITHM, SECRET_KEY

    expired_token = jwt.encode(
        {
            "sub": f"expired-{uuid4().hex}@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
