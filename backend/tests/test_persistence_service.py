
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services import persistence_service as service


@pytest.fixture
def fake_database(monkeypatch):
    connection = MagicMock()
    cursor = MagicMock()

    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    monkeypatch.setattr(
        service,
        "get_connection",
        lambda: connection,
    )

    return cursor


@pytest.fixture
def sample_data():
    return {
        "skills": ["Python", "SQL"],
        "education": [
            {
                "degree": "B.Tech",
                "institution": "Example College",
            }
        ],
        "projects": [
            {
                "name": "Resume Analyzer",
                "technologies": ["Python"],
            }
        ],
        "experience": [],
    }


def test_save_extraction(fake_database, sample_data):
    resume_id = uuid4()
    user_id = uuid4()

    fake_database.fetchone.return_value = (resume_id,)

    result = service.save_extraction(
        resume_id,
        user_id,
        sample_data,
    )

    assert result["resume_id"] == str(resume_id)
    assert result["message"] == "Extraction saved successfully"

    fake_database.execute.assert_called_once()


def test_save_rejects_invalid_data(sample_data):
    resume_id = uuid4()
    user_id = uuid4()

    sample_data.pop("skills")

    with pytest.raises(ValueError, match="Missing field: skills"):
        service.save_extraction(
            resume_id,
            user_id,
            sample_data,
        )


def test_save_rejects_wrong_owner(fake_database, sample_data):
    fake_database.fetchone.return_value = None

    with pytest.raises(service.ResumeNotFoundError):
        service.save_extraction(
            uuid4(),
            uuid4(),
            sample_data,
        )


def test_get_extraction(fake_database, sample_data):
    resume_id = uuid4()
    user_id = uuid4()

    fake_database.fetchone.return_value = (
        resume_id,
        sample_data["skills"],
        sample_data["education"],
        sample_data["projects"],
        sample_data["experience"],
    )

    result = service.get_extraction(resume_id, user_id)

    assert result["resume_id"] == str(resume_id)
    assert result["skills"] == ["Python", "SQL"]
    assert result["education"] == sample_data["education"]
    assert result["projects"] == sample_data["projects"]
    assert result["experience"] == []


def test_get_extraction_not_found(fake_database):
    fake_database.fetchone.return_value = None

    with pytest.raises(service.ExtractionNotFoundError):
        service.get_extraction(uuid4(), uuid4())


def test_reextraction_uses_upsert(fake_database, sample_data):
    resume_id = uuid4()
    user_id = uuid4()

    fake_database.fetchone.return_value = (resume_id,)

    service.save_extraction(resume_id, user_id, sample_data)

    sql = fake_database.execute.call_args.args[0]

    assert "ON CONFLICT (resume_id)" in sql
    assert "DO UPDATE SET" in sql
