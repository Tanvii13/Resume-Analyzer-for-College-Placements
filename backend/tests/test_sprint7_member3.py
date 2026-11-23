
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import health


test_app = FastAPI()
test_app.include_router(health.router)
client = TestClient(test_app)


def test_health_live_returns_alive():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@patch("app.routers.health.get_connection")
@patch("app.routers.health.STORAGE_DIR")
def test_health_ready_when_dependencies_are_available(
    mock_storage,
    mock_connection,
):
    mock_connection.return_value.__enter__.return_value = MagicMock()
    mock_storage.is_dir.return_value = True

    with patch("app.routers.health.os.access", return_value=True):
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@patch("app.routers.health.get_connection")
@patch("app.routers.health.STORAGE_DIR")
def test_health_ready_returns_503_when_database_is_down(
    mock_storage,
    mock_connection,
):
    mock_connection.side_effect = RuntimeError("Database unavailable")
    mock_storage.is_dir.return_value = True

    with patch("app.routers.health.os.access", return_value=True):
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["database"] == "unavailable"


@patch("app.routers.health.ResumeRepository")
@patch("app.routers.health.shutil.disk_usage")
@patch("app.routers.health.STORAGE_DIR")
def test_telemetry_returns_counts_and_storage(
    mock_storage,
    mock_disk_usage,
    mock_repository,
):
    mock_storage.exists.return_value = True

    mock_repository.get_telemetry_counts.return_value = {
        "total_resumes": 20,
        "processed_resumes": 15,
    }
    mock_repository.get_active_user_count.return_value = 8
    mock_repository.get_storage_bytes.return_value = 5000

    mock_disk_usage.return_value = MagicMock(
        total=10000,
        used=6000,
        free=4000,
    )

    response = client.get("/health/telemetry")

    assert response.status_code == 200

    data = response.json()

    assert data["total_resumes"] == 20
    assert data["processed_resumes"] == 15
    assert data["active_users"] == 8
    assert data["resume_file_bytes"] == 5000
    assert data["storage"]["used_percent"] == 60.0


@patch("app.routers.health.ResumeRepository")
@patch("app.routers.health.STORAGE_DIR")
def test_telemetry_returns_503_when_storage_is_missing(
    mock_storage,
    mock_repository,
):
    mock_storage.exists.return_value = False

    response = client.get("/health/telemetry")

    assert response.status_code == 503


def test_repository_exposes_expected_operations():
    from app.repositories.resume_repository import ResumeRepository
    from app.repositories.opportunity_repository import OpportunityRepository

    assert callable(ResumeRepository.get_active_user_id)
    assert callable(ResumeRepository.create_resume)
    assert callable(ResumeRepository.get_resume_file)
    assert callable(ResumeRepository.update_status)
    assert callable(ResumeRepository.delete_resume_records)
    assert callable(ResumeRepository.get_telemetry_counts)

    assert callable(
        OpportunityRepository.get_student_latest_resume
    )
