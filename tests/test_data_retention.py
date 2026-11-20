from unittest.mock import MagicMock

import pytest

from app.services import retention_service


def mock_connection(monkeypatch, fetchone=None, fetchall=None):
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = fetchone
    conn.execute.return_value.fetchall.return_value = fetchall or []

    connection_context = MagicMock()
    connection_context.__enter__.return_value = conn
    connection_context.__exit__.return_value = False

    monkeypatch.setattr(
        retention_service,
        "get_connection",
        lambda: connection_context,
    )

    return conn


def test_set_resume_retention(monkeypatch):
    expected_id = "11111111-1111-1111-1111-111111111111"
    expected_date = "2027-11-20"

    mock_connection(
        monkeypatch,
        fetchone=(expected_id, expected_date),
    )

    result = retention_service.set_resume_retention(
        expected_id,
        retention_days=365,
    )

    assert result["resume_id"] == expected_id
    assert result["retention_expires_at"] == expected_date


def test_set_resume_retention_rejects_invalid_days():
    with pytest.raises(ValueError):
        retention_service.set_resume_retention(
            "11111111-1111-1111-1111-111111111111",
            retention_days=0,
        )


def test_retention_summary(monkeypatch):
    mock_connection(
        monkeypatch,
        fetchone=(10, 8, 2, 6),
    )

    result = retention_service.get_retention_summary()

    assert result["total_resumes"] == 10
    assert result["resumes_with_policy"] == 8
    assert result["expired_resumes"] == 2
    assert result["active_retention"] == 6
    assert "checked_at" in result


def test_get_expired_resume_ids(monkeypatch):
    mock_connection(
        monkeypatch,
        fetchall=[
            ("11111111-1111-1111-1111-111111111111",),
            ("22222222-2222-2222-2222-222222222222",),
        ],
    )

    result = retention_service.get_expired_resume_ids(limit=50)

    assert len(result) == 2
    assert result[0] == "11111111-1111-1111-1111-111111111111"


def test_get_expired_resume_ids_rejects_invalid_limit():
    with pytest.raises(ValueError):
        retention_service.get_expired_resume_ids(limit=0)