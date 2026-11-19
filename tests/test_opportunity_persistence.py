
import pytest

from app.services.opportunity_persistence import (
    _validate_skills,
    _validate_uuid,
)


def test_valid_skills():
    assert _validate_skills(
        ["Python", "SQL"], "required_skills"
    ) == ["Python", "SQL"]


def test_empty_skill_is_rejected():
    with pytest.raises(ValueError):
        _validate_skills(["Python", ""], "required_skills")


def test_non_list_skills_are_rejected():
    with pytest.raises(ValueError):
        _validate_skills("Python", "required_skills")


def test_valid_uuid():
    value = "12345678-1234-5678-1234-567812345678"
    assert str(_validate_uuid(value)) == value


def test_invalid_uuid():
    with pytest.raises(ValueError):
        _validate_uuid("not-a-uuid")
