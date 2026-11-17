
import pytest

from app.services.improvement_detector import ImprovementDetector


@pytest.fixture
def detector():
    return ImprovementDetector()


@pytest.fixture
def complete_resume():
    return """
    EDUCATION
    B.Tech in Information and Communication Technology
    DA-IICT
    CGPA: 8.4/10
    Expected Graduation: 2027

    SKILLS
    Python, C, C++, Java, SQL, HTML, CSS

    PROJECTS
    Resume Analyzer
    Developed a resume analysis application.
    Designed the backend architecture.
    Implemented authentication.
    Optimized API response time by 30%.
    Deployed the application for 100 users.
    Tested application functionality.

    EXPERIENCE
    Software Engineering Intern
    Built and maintained backend services.

    CONTACT
    shlok@dau.ac.in
    +91 9876543210
    https://linkedin.com/in/shlok
    https://github.com/SHLOK-TOPALIYA
    """


def test_empty_resume_returns_critical_issue(detector):
    report = detector.detect_improvements("")

    assert report.total_issues == 1
    assert report.improvement_areas[0].id == "CRIT_EMPTY_RESUME"
    assert report.improvement_areas[0].priority == "High"
    assert report.priority_breakdown == {
        "High": 1,
        "Medium": 0,
        "Low": 0,
    }


def test_complete_resume_has_no_missing_core_sections(
    detector, complete_resume
):
    report = detector.detect_improvements(complete_resume)

    issue_ids = {issue.id for issue in report.improvement_areas}

    assert "HIGH_MISSING_SECTION_EDUCATION" not in issue_ids
    assert "HIGH_MISSING_SECTION_SKILLS" not in issue_ids
    assert "HIGH_MISSING_SECTION_PROJECTS" not in issue_ids


def test_structured_data_prevents_false_missing_section_flags(detector):
    structured_data = {
        "education": ["B.Tech in ICT"],
        "skills": ["Python", "Java"],
        "projects": ["Resume Analyzer project"],
        "experience": [],
    }

    report = detector.detect_improvements(
        raw_text="",
        structured_data=structured_data,
    )

    issue_ids = {issue.id for issue in report.improvement_areas}

    assert "HIGH_MISSING_SECTION_EDUCATION" not in issue_ids
    assert "HIGH_MISSING_SECTION_SKILLS" not in issue_ids
    assert "HIGH_MISSING_SECTION_PROJECTS" not in issue_ids


def test_missing_experience_is_not_flagged_for_freshers(detector):
    resume = """
    EDUCATION
    B.Tech in ICT
    CGPA: 8.5/10
    Graduation Year: 2027

    SKILLS
    Python, Java, SQL

    PROJECTS
    Developed a web application.
    """

    report = detector.detect_improvements(resume)

    assert not any(
        issue.id == "HIGH_MISSING_SECTION_EXPERIENCE"
        for issue in report.improvement_areas
    )


def test_missing_contact_details_are_detected(detector):
    report = detector.detect_improvements(
        "EDUCATION\nB.Tech\nSKILLS\nPython\nPROJECTS\nBuilt an app."
    )

    issue_ids = {issue.id for issue in report.improvement_areas}

    assert "HIGH_MISSING_EMAIL" in issue_ids
    assert "HIGH_MISSING_PHONE" in issue_ids


def test_missing_academic_details_are_detected(detector):
    report = detector.detect_improvements(
        "EDUCATION\nBachelor of Technology\nExpected Graduation"
    )

    issue_ids = {issue.id for issue in report.improvement_areas}

    assert "HIGH_MISSING_CGPA" in issue_ids
    assert "HIGH_MISSING_GRAD_YEAR" in issue_ids


def test_weak_verbs_are_detected(detector):
    resume = """
    PROJECTS
    Worked on a web application.
    Helped with backend development.
    """

    report = detector.detect_improvements(resume)

    issue_ids = {issue.id for issue in report.improvement_areas}

    assert "LOW_WEAK_VERBS_USED" in issue_ids


def test_missing_quantifiable_metrics_are_detected(detector):
    resume = """
    PROJECTS
    Developed a web application.
    Designed the database.
    Implemented authentication.
    """

    report = detector.detect_improvements(resume)

    issue_ids = {issue.id for issue in report.improvement_areas}

    assert "MED_NO_QUANTIFIABLE_METRICS" in issue_ids


def test_page_limit_issue_is_detected(detector):
    report = detector.detect_improvements(
        "EDUCATION\nB.Tech",
        page_count=3,
    )

    issue_ids = {issue.id for issue in report.improvement_areas}

    assert "MED_EXCEEDS_PAGE_LIMIT" in issue_ids


def test_short_resume_is_flagged(detector):
    report = detector.detect_improvements(
        "EDUCATION\nB.Tech in ICT\nSKILLS\nPython"
    )

    issue_ids = {issue.id for issue in report.improvement_areas}

    assert "MED_RESUME_TOO_BRIEF" in issue_ids


def test_issues_are_sorted_by_priority(detector):
    resume = """
    PROJECTS
    Worked on a small application.
    """

    report = detector.detect_improvements(resume)

    priorities = [
        issue.priority for issue in report.improvement_areas
    ]

    priority_values = {
        "High": 1,
        "Medium": 2,
        "Low": 3,
    }

    assert priorities == sorted(
        priorities,
        key=lambda priority: priority_values[priority],
    )


def test_invalid_input_is_rejected(detector):
    with pytest.raises(TypeError):
        detector.detect_improvements(None)

    with pytest.raises(ValueError):
        detector.detect_improvements("Some resume text", page_count=0)
