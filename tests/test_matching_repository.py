
from unittest.mock import MagicMock, patch

import pytest

from app.services import matching_repository as repo


def fake_db(row=None, rows=None):
    cursor = MagicMock()
    cursor.fetchone.return_value = row
    cursor.fetchall.return_value = rows or []

    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    return connection, cursor


@patch("app.services.matching_repository.get_connection")
def test_save_job_description(mock_connection):
    row = (
        "job-id",
        "Backend Developer",
        "Example Company",
        "Build APIs",
        ["Python"],
        [],
        None
    )

    connection, cursor = fake_db(row=row)
    mock_connection.return_value = connection

    result = repo.save_job_description(
        "11111111-1111-1111-1111-111111111111",
        {
            "title": "Backend Developer",
            "description": "Build APIs",
            "required_skills": ["Python"]
        }
    )

    assert result["title"] == "Backend Developer"
    cursor.execute.assert_called_once()


@patch("app.services.matching_repository.get_connection")
def test_get_missing_job_raises_not_found(mock_connection):
    connection, cursor = fake_db(row=None)
    mock_connection.return_value = connection

    with pytest.raises(repo.ResourceNotFoundError):
        repo.get_job_description(
            "22222222-2222-2222-2222-222222222222",
            "11111111-1111-1111-1111-111111111111"
        )


def test_invalid_uuid_is_rejected():
    with pytest.raises(ValueError):
        repo.get_all_job_descriptions("not-a-uuid")
