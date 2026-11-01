
import pytest

from app.services.skill_extractor import extract_skills


def get_technical_names(text):
    result = extract_skills(text)
    return {
        skill["name"]
        for skill in result["technical_skills"]
    }


def get_soft_names(text):
    result = extract_skills(text)
    return {
        skill["name"]
        for skill in result["soft_skills"]
    }


def test_skill_aliases():
    names = get_technical_names(
        "I know JS, postgres and k8s."
    )

    assert "JavaScript" in names
    assert "PostgreSQL" in names
    assert "Kubernetes" in names


def test_multi_word_skills():
    names = get_soft_names(
        "I have problem solving and time management skills."
    )

    assert "Problem Solving" in names
    assert "Time Management" in names


def test_cpp_and_csharp():
    names = get_technical_names(
        "I have experience in C++ and C#."
    )

    assert "C++" in names
    assert "C#" in names


def test_c_not_matched_inside_other_skills():
    names = get_technical_names(
        "I know C++, C# and CSS."
    )

    assert "C++" in names
    assert "C#" in names
    assert "C" not in names


def test_empty_text():
    result = extract_skills("")

    assert result["technical_skills"] == []
    assert result["soft_skills"] == []


def test_invalid_input():
    with pytest.raises(ValueError):
        extract_skills(None)


def test_punctuation():
    names = get_technical_names(
        "Skills: Python, JavaScript; PostgreSQL."
    )

    assert "Python" in names
    assert "JavaScript" in names
    assert "PostgreSQL" in names
