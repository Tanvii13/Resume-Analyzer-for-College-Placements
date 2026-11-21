"""
Comprehensive automated tests for Sprint 2 – Module B: Section Classification Engine.

Covers:
- Recognition of all 10 canonical sections
- Alias and synonym matching
- Regex-based heading patterns with numbering and punctuation
- Typo-tolerant Levenshtein fuzzy matching
- Preservation of section ordering and line provenance
- Content before first heading assigned to 'personal_info'
- Resumes without headings handled safely
- Empty sections handled cleanly
- Unknown headings mapped to 'general_body' without crashing
- False-positive prevention on ordinary sentences
- Full end-to-end classification on realistic resume text
"""

import pytest

from app.nlp.preprocessing import segment_text
from app.nlp.sections import (
    CANONICAL_SECTIONS,
    ClassifiedSection,
    SectionMap,
    SECTION_ACHIEVEMENTS,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_EXTRACURRICULAR,
    SECTION_GENERAL_BODY,
    SECTION_INTERNSHIPS,
    SECTION_PERSONAL_INFO,
    SECTION_PROJECTS,
    SECTION_SOFT_SKILLS,
    SECTION_TECHNICAL_SKILLS,
    classify_heading,
    classify_sections,
)


# ============================================================================
# Heading Classification Unit Tests
# ============================================================================

def test_all_10_canonical_sections_exact_match():
    """Verify that all 10 canonical section names are recognized with confidence 1.0."""
    for section_name in CANONICAL_SECTIONS:
        # Title case, uppercase, lowercase
        for variation in [section_name, section_name.upper(), section_name.title(), section_name.replace("_", " ")]:
            result = classify_heading(variation)
            assert result is not None, f"Failed to match canonical section: {variation}"
            canonical, confidence = result
            assert canonical == section_name
            assert confidence >= 0.95


def test_alias_and_synonym_matching():
    """Verify alias and synonym mappings for all major section types."""
    aliases = [
        # education
        ("Academic Background", SECTION_EDUCATION),
        ("Academic Qualifications", SECTION_EDUCATION),
        ("Educational Details", SECTION_EDUCATION),
        ("Academics", SECTION_EDUCATION),
        ("Qualifications", SECTION_EDUCATION),

        # experience
        ("Work Experience", SECTION_EXPERIENCE),
        ("Professional Experience", SECTION_EXPERIENCE),
        ("Employment History", SECTION_EXPERIENCE),
        ("Work History", SECTION_EXPERIENCE),
        ("Career History", SECTION_EXPERIENCE),

        # internships
        ("Internship", SECTION_INTERNSHIPS),
        ("Internships", SECTION_INTERNSHIPS),
        ("Summer Internship", SECTION_INTERNSHIPS),
        ("Industrial Training", SECTION_INTERNSHIPS),

        # projects
        ("Academic Projects", SECTION_PROJECTS),
        ("Personal Projects", SECTION_PROJECTS),
        ("Key Projects", SECTION_PROJECTS),
        ("Technical Projects", SECTION_PROJECTS),

        # technical_skills
        ("Technical Skills", SECTION_TECHNICAL_SKILLS),
        ("Programming Skills", SECTION_TECHNICAL_SKILLS),
        ("Technologies and Tools", SECTION_TECHNICAL_SKILLS),
        ("Tech Stack", SECTION_TECHNICAL_SKILLS),
        ("Skills & Tools", SECTION_TECHNICAL_SKILLS),

        # soft_skills
        ("Soft Skills", SECTION_SOFT_SKILLS),
        ("Interpersonal Skills", SECTION_SOFT_SKILLS),
        ("Non-Technical Skills", SECTION_SOFT_SKILLS),
        ("Behavioral Skills", SECTION_SOFT_SKILLS),

        # certifications
        ("Certifications", SECTION_CERTIFICATIONS),
        ("Certificates", SECTION_CERTIFICATIONS),
        ("Licenses & Certifications", SECTION_CERTIFICATIONS),
        ("Courses & Certifications", SECTION_CERTIFICATIONS),

        # achievements
        ("Achievements", SECTION_ACHIEVEMENTS),
        ("Awards and Honors", SECTION_ACHIEVEMENTS),
        ("Accomplishments", SECTION_ACHIEVEMENTS),
        ("Honors & Awards", SECTION_ACHIEVEMENTS),

        # extracurricular
        ("Extracurricular Activities", SECTION_EXTRACURRICULAR),
        ("Positions of Responsibility", SECTION_EXTRACURRICULAR),
        ("Co-Curricular Activities", SECTION_EXTRACURRICULAR),
        ("Volunteer Work", SECTION_EXTRACURRICULAR),
    ]

    for alias, expected_canonical in aliases:
        result = classify_heading(alias)
        assert result is not None, f"Failed to match alias: {alias}"
        canonical, confidence = result
        assert canonical == expected_canonical, f"Alias '{alias}' mapped to '{canonical}', expected '{expected_canonical}'"
        assert confidence >= 0.95


def test_numbered_and_punctuated_headings():
    """Verify regex matching on headings with numeric prefixes and colons."""
    headings = [
        ("1. Education", SECTION_EDUCATION),
        ("2) Work Experience:", SECTION_EXPERIENCE),
        ("3. TECHNICAL SKILLS:", SECTION_TECHNICAL_SKILLS),
        ("[4] Academic Projects", SECTION_PROJECTS),
        ("I. Certifications:", SECTION_CERTIFICATIONS),
        ("II. Achievements", SECTION_ACHIEVEMENTS),
    ]

    for heading, expected_canonical in headings:
        result = classify_heading(heading)
        assert result is not None, f"Failed on numbered heading: {heading}"
        canonical, _ = result
        assert canonical == expected_canonical


def test_typo_tolerant_levenshtein_matching():
    """Verify that common typographical errors in headings are accurately classified."""
    misspellings = [
        ("Experiance", SECTION_EXPERIENCE),
        ("Certifactions", SECTION_CERTIFICATIONS),
        ("Educaton", SECTION_EDUCATION),
        ("Achivements", SECTION_ACHIEVEMENTS),
        ("Projcts", SECTION_PROJECTS),
        ("Techincal Skills", SECTION_TECHNICAL_SKILLS),
        ("Exracurricular", SECTION_EXTRACURRICULAR),
    ]

    for typo, expected_canonical in misspellings:
        result = classify_heading(typo)
        assert result is not None, f"Failed to classify typo heading: {typo}"
        canonical, confidence = result
        assert canonical == expected_canonical, f"Typo '{typo}' mapped to '{canonical}', expected '{expected_canonical}'"
        assert 0.80 <= confidence < 1.0


def test_false_positive_sentence_protection():
    """Verify that regular descriptive sentences are not mistakenly classified as headings."""
    sentences = [
        "I have experience with Python, C++, and Docker.",
        "Education is the foundation of computer science.",
        "Developed projects using React and Node.js.",
        "Projects include building distributed key-value stores.",
        "Demonstrated strong communication skills in team meetings.",
        "Received awards for high academic performance.",
        "These skills are necessary for full stack engineering.",
    ]

    for sent in sentences:
        assert classify_heading(sent) is None, f"Sentence was incorrectly classified as a heading: {sent}"


# ============================================================================
# Section Classification Engine Integration Tests
# ============================================================================

def test_preamble_assigned_to_personal_info():
    """Verify that all text prior to the first recognized heading is assigned to 'personal_info'."""
    text = (
        "Jane Doe\n"
        "jane.doe@example.com | +91 9876543210\n"
        "linkedin.com/in/janedoe | github.com/janedoe\n\n"
        "EDUCATION\n"
        "B.Tech in Computer Science, ABC University, 2024"
    )
    section_map = classify_sections(text)

    personal_info = section_map.get_section(SECTION_PERSONAL_INFO)
    assert personal_info is not None
    assert personal_info.canonical_name == SECTION_PERSONAL_INFO
    assert personal_info.original_heading is None
    assert "Jane Doe" in personal_info.content
    assert "jane.doe@example.com" in personal_info.content
    assert personal_info.start_line == 1
    assert personal_info.end_line <= 3

    education = section_map.get_section(SECTION_EDUCATION)
    assert education is not None
    assert "B.Tech in Computer Science" in education.content


def test_resume_without_headings():
    """Verify that a resume with zero headings is cleanly assigned to 'personal_info' without crashing."""
    text = (
        "Alex Rivera\n"
        "alex.rivera@dau.ac.in\n"
        "Software developer with 3 years of experience in Python and FastAPI.\n"
        "Built distributed databases and microservices."
    )
    section_map = classify_sections(text)

    assert len(section_map.sections) == 1
    sec = section_map.sections[0]
    assert sec.canonical_name == SECTION_PERSONAL_INFO
    assert sec.original_heading is None
    assert "Alex Rivera" in sec.content
    assert sec.confidence == 0.50


def test_empty_section_handling():
    """Verify that an empty section (heading with no body) is captured without crashing."""
    text = (
        "EDUCATION\n\n"
        "TECHNICAL SKILLS\n"
        "• Python, C++, Docker"
    )
    section_map = classify_sections(text)

    edu = section_map.get_section(SECTION_EDUCATION)
    assert edu is not None
    assert edu.content == ""
    assert edu.original_heading == "EDUCATION"
    assert not section_map.has_section(SECTION_EDUCATION)

    skills = section_map.get_section(SECTION_TECHNICAL_SKILLS)
    assert skills is not None
    assert section_map.has_section(SECTION_TECHNICAL_SKILLS)
    assert "Python, C++, Docker" in skills.content


def test_internships_vs_experience_distinction():
    """Verify that internships and general experience are routed to distinct canonical sections."""
    text = (
        "WORK EXPERIENCE\n"
        "Software Engineer at Acme Corp | 2023 - Present\n"
        "• Built backend APIs.\n\n"
        "INTERNSHIPS\n"
        "Frontend Intern at Startup Inc | May 2022 - July 2022\n"
        "• Built React components."
    )
    section_map = classify_sections(text)

    assert section_map.has_section(SECTION_EXPERIENCE)
    assert section_map.has_section(SECTION_INTERNSHIPS)

    exp = section_map.get_section(SECTION_EXPERIENCE)
    assert "Acme Corp" in exp.content
    assert "Startup Inc" not in exp.content

    intern = section_map.get_section(SECTION_INTERNSHIPS)
    assert "Startup Inc" in intern.content
    assert "Acme Corp" not in intern.content


def test_technical_vs_soft_skills_distinction():
    """Verify that technical skills and soft skills are routed to distinct canonical sections."""
    text = (
        "TECHNICAL SKILLS\n"
        "• Python, FastAPI, Docker, PostgreSQL\n\n"
        "SOFT SKILLS\n"
        "• Leadership, Communication, Problem Solving"
    )
    section_map = classify_sections(text)

    tech = section_map.get_section(SECTION_TECHNICAL_SKILLS)
    assert tech is not None
    assert "Python" in tech.content
    assert "Leadership" not in tech.content

    soft = section_map.get_section(SECTION_SOFT_SKILLS)
    assert soft is not None
    assert "Leadership" in soft.content
    assert "Python" not in soft.content


def test_section_ordering_preservation():
    """Verify that section_order preserves exact document order."""
    text = (
        "Name Header\n\n"
        "PROJECTS\n"
        "Project 1 description\n\n"
        "EDUCATION\n"
        "B.Tech 2025\n\n"
        "TECHNICAL SKILLS\n"
        "Python, C++\n\n"
        "ACHIEVEMENTS\n"
        "CodeVita Rank 45"
    )
    section_map = classify_sections(text)

    expected_order = [
        SECTION_PERSONAL_INFO,
        SECTION_PROJECTS,
        SECTION_EDUCATION,
        SECTION_TECHNICAL_SKILLS,
        SECTION_ACHIEVEMENTS,
    ]
    assert section_map.section_names == expected_order


def test_section_map_to_dict():
    """Verify dictionary serialization for SectionMap."""
    text = (
        "EDUCATION\n"
        "DA-IICT 2025\n\n"
        "SKILLS\n"
        "Python, React"
    )
    section_map = classify_sections(text)
    data = section_map.to_dict()

    assert "sections" in data
    assert "section_order" in data
    assert "identified_count" in data
    assert data["identified_count"] == 2
    assert data["section_order"] == [SECTION_EDUCATION, SECTION_TECHNICAL_SKILLS]


def test_end_to_end_classification_on_sample_resume(sample_resume_text):
    """Verify classification across all sections of the realistic sample resume fixture."""
    section_map = classify_sections(sample_resume_text)

    # Verify expected canonical sections are present
    assert section_map.has_section(SECTION_PERSONAL_INFO)
    assert section_map.has_section(SECTION_EDUCATION)
    assert section_map.has_section(SECTION_TECHNICAL_SKILLS)
    assert section_map.has_section(SECTION_EXPERIENCE)
    assert section_map.has_section(SECTION_PROJECTS)

    # Verify content routing
    p_info = section_map.get_section(SECTION_PERSONAL_INFO)
    assert "Aarav Sharma" in p_info.content
    assert "aarav.sharma@dau.ac.in" in p_info.content

    edu = section_map.get_section(SECTION_EDUCATION)
    assert "B.Tech in ICT" in edu.content
    assert "DA-IICT" in edu.content

    skills = section_map.get_section(SECTION_TECHNICAL_SKILLS)
    assert "FastAPI" in skills.content
    assert "C++" in skills.content

    exp = section_map.get_section(SECTION_EXPERIENCE)
    assert "Credence Analytics" in exp.content

    proj = section_map.get_section(SECTION_PROJECTS)
    assert "College Placement Portal" in proj.content
