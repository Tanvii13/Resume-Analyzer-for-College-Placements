
import pytest

from app.services.jd_parser import JDParser


VALID_JD = """
We are looking for a Backend Engineer to join our technology team.
The candidate will design, develop, and maintain scalable backend
applications and services. The candidate should have strong knowledge
of Python, Java, SQL, REST APIs, and database management systems.
Applicants should have a B.Tech or B.E. degree in Computer Science,
Information Technology, or Information and Communication Technology.
Candidates should understand data structures, algorithms, operating
systems, computer networks, and software engineering principles.
The candidate will collaborate with frontend developers and product
teams to build reliable applications. Good communication, analytical
thinking, teamwork, and problem-solving skills are required.
Freshers and recent graduates are welcome to apply for this role.
Candidates should demonstrate their knowledge through academic,
personal, or internship projects. Familiarity with Git and version
control is preferred. The selected candidate will participate in
code reviews, testing, debugging, and application development.
"""


def test_sanitize_text_normalizes_whitespace():
    raw_text = "  Backend Engineer  \r\n\r\n\r\nPython   Developer  "

    result = JDParser.sanitize_text(raw_text)

    assert result == "Backend Engineer\n\nPython Developer"


def test_sanitize_text_removes_invisible_characters():
    raw_text = "Backend\u200b Engineer\u200b"

    result = JDParser.sanitize_text(raw_text)

    assert result == "Backend Engineer"


def test_short_job_description_is_rejected():
    short_jd = "We need a Python developer with database skills."

    with pytest.raises(ValueError, match="at least 50 words"):
        JDParser.parse_job_description(short_jd)


def test_job_title_and_experience_are_extracted():
    result = JDParser.parse_job_description(VALID_JD)

    assert result.title == "Backend Engineer"
    assert result.experience_level == "Fresher / Entry-Level (0-1 years)"
    assert result.minimum_experience_years == 0.0
    assert result.word_count >= 50


def test_degrees_and_disciplines_are_extracted():
    result = JDParser.parse_job_description(VALID_JD)

    assert "B.Tech / B.E." in result.required_degrees
    assert "Computer Science" in result.required_disciplines
    assert (
        "Information and Communication Technology"
        in result.required_disciplines
    )
