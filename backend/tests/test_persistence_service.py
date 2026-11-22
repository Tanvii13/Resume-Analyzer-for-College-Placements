import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services import persistence_service as service


@pytest.fixture
def fake_database(monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection

    database = SimpleNamespace(
        connection=connection,
        resume_row=(uuid4(),),
        skill_rows=[],
        section_rows=[],
        skill_id=uuid4(),
    )

    def execute_query(sql, params=None):
        query = " ".join(sql.split())
        result = MagicMock()

        if "SELECT id FROM resumes" in query:
            result.fetchone.return_value = database.resume_row

        elif "SELECT id FROM skills" in query:
            result.fetchone.return_value = (database.skill_id,)

        elif "SELECT s.name" in query:
            result.fetchall.return_value = database.skill_rows

        elif "SELECT section_name, content" in query:
            result.fetchall.return_value = database.section_rows

        return result

    connection.execute.side_effect = execute_query

    monkeypatch.setattr(
        service,
        "get_connection",
        lambda: connection,
    )

    return database


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

    result = service.save_extraction(
        resume_id,
        user_id,
        sample_data,
    )

    assert result["resume_id"] == str(resume_id)
    assert result["message"] == "Extraction saved successfully"

    sql_statements = [
        call.args[0]
        for call in fake_database.connection.execute.call_args_list
    ]

    assert any("INSERT INTO resume_sections" in sql for sql in sql_statements)
    assert any("INSERT INTO skills" in sql for sql in sql_statements)
    assert any("INSERT INTO resume_skills" in sql for sql in sql_statements)
    assert any("UPDATE resumes" in sql for sql in sql_statements)


def test_save_rejects_invalid_data(sample_data):
    sample_data.pop("skills")

    with pytest.raises(ValueError, match="Missing field: skills"):
        service.save_extraction(
            uuid4(),
            uuid4(),
            sample_data,
        )


def test_save_rejects_wrong_owner(fake_database, sample_data):
    fake_database.resume_row = None

    with pytest.raises(service.ResumeNotFoundError):
        service.save_extraction(
            uuid4(),
            uuid4(),
            sample_data,
        )


def test_get_extraction(fake_database, sample_data):
    resume_id = uuid4()
    user_id = uuid4()

    fake_database.skill_rows = [
        ("Python",),
        ("SQL",),
    ]

    fake_database.section_rows = [
        ("education", json.dumps(sample_data["education"])),
        ("projects", json.dumps(sample_data["projects"])),
        ("experience", json.dumps(sample_data["experience"])),
    ]

    result = service.get_extraction(resume_id, user_id)

    assert result["resume_id"] == str(resume_id)
    assert result["skills"] == ["Python", "SQL"]
    assert result["education"] == sample_data["education"]
    assert result["projects"] == sample_data["projects"]
    assert result["experience"] == []


def test_get_extraction_not_found(fake_database):
    # The resume exists and belongs to the user, but no extraction is saved.
    fake_database.skill_rows = []
    fake_database.section_rows = []

    with pytest.raises(service.ExtractionNotFoundError):
        service.get_extraction(uuid4(), uuid4())


def test_reextraction_uses_upsert(fake_database, sample_data):
    service.save_extraction(
        uuid4(),
        uuid4(),
        sample_data,
    )

    sql_statements = [
        call.args[0]
        for call in fake_database.connection.execute.call_args_list
    ]

    section_upsert = next(
        sql for sql in sql_statements
        if "INSERT INTO resume_sections" in sql
    )

    assert "ON CONFLICT (resume_id, section_name)" in section_upsert
    assert "DO UPDATE SET" in section_upsert
