
import pytest

from app.services.jd_matching_service import calculate_jd_match


def test_all_required_skills_match():
    result = calculate_jd_match(
        {"skills": ["Python", "SQL"]},
        {"required_skills": ["Python", "SQL"]}
    )

    assert result["match_percentage"] == 100
    assert result["missing_skills"] == []


def test_partial_match():
    result = calculate_jd_match(
        {"skills": ["Python", "Git"]},
        {"required_skills": ["Python", "SQL", "Java", "Git"]}
    )

    assert result["match_percentage"] == 50
    assert len(result["missing_skills"]) == 2


def test_no_match():
    result = calculate_jd_match(
        {"skills": ["C++"]},
        {"required_skills": ["Python", "SQL"]}
    )

    assert result["match_percentage"] == 0


def test_empty_required_skills():
    result = calculate_jd_match(
        {"skills": ["Python"]},
        {"required_skills": []}
    )

    assert result["match_percentage"] == 0


def test_invalid_input():
    with pytest.raises(ValueError):
        calculate_jd_match([], {})
