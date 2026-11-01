
import pytest

from app.services.skill_extractor import SkillExtractor


@pytest.fixture
def extractor():
    return SkillExtractor()


def test_technical_skills(extractor):
    result = extractor.extract_skills(
        "I know Python, Java, C++, SQL and React."
    )

    assert "Python" in result["technical_skills"]
    assert "Java" in result["technical_skills"]
    assert "C++" in result["technical_skills"]
    assert "SQL" in result["technical_skills"]
    assert "React" in result["technical_skills"]


def test_soft_skills(extractor):
    result = extractor.extract_skills(
        "I have problem solving and time management skills."
    )

    assert "Problem Solving" in result["soft_skills"]
    assert "Time Management" in result["soft_skills"]


def test_skill_aliases(extractor):
    result = extractor.extract_skills(
        "I know JS, postgres and k8s."
    )

    assert "JavaScript" in result["technical_skills"]
    assert "PostgreSQL" in result["technical_skills"]
    assert "Kubernetes" in result["technical_skills"]


def test_cpp_and_csharp(extractor):
    result = extractor.extract_skills(
        "I have experience in C++ and C#."
    )

    assert "C++" in result["technical_skills"]
    assert "C#" in result["technical_skills"]


def test_c_not_matched_inside_other_skills(extractor):
    result = extractor.extract_skills(
        "I know C++, C# and CSS."
    )

    assert "C++" in result["technical_skills"]
    assert "C#" in result["technical_skills"]
    assert "C" not in result["technical_skills"]


def test_empty_text(extractor):
    result = extractor.extract_skills("")

    assert result["technical_skills"] == []
    assert result["soft_skills"] == []
    assert result["total_count"] == 0


def test_invalid_input(extractor):
    with pytest.raises(TypeError):
        extractor.extract_skills(None)


def test_punctuation(extractor):
    result = extractor.extract_skills(
        "Skills: Python, JavaScript; PostgreSQL."
    )

    assert "Python" in result["technical_skills"]
    assert "JavaScript" in result["technical_skills"]
    assert "PostgreSQL" in result["technical_skills"]


def test_case_insensitive(extractor):
    result = extractor.extract_skills(
        "python, JAVA and communication"
    )

    assert "Python" in result["technical_skills"]
    assert "Java" in result["technical_skills"]
    assert "Communication" in result["soft_skills"]


def test_total_count(extractor):
    result = extractor.extract_skills(
        "Python, Java and Leadership."
    )

    expected = (
        len(result["technical_skills"])
        + len(result["soft_skills"])
    )

    assert result["total_count"] == expected
