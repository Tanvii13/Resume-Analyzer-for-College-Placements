"""
Automated unit and integration tests for Sprint 2 – Module C: Contact & Online Profile Extractor.

Covers:
- Candidate name extraction (standalone line, single-line with pipes, labeled, preceded by job title/CV)
- Email extraction and RFC-compliance validation
- Indian mobile phone formats (+91, 0, 10-digit without prefix, hyphens, spaces)
- International phone numbers (US E.164, UK format)
- False-positive number rejection (dates 2021-2025, 6-digit pin codes, metrics)
- Online profiles extraction (LinkedIn, GitHub, LeetCode, CodeChef, personal portfolio)
- Normalization of URLs without invention
- Missing contact details handling (returns None gracefully)
- Integration with Module B SectionMap and sample_resume_text
"""

import pytest

from app.nlp.extractors.contact import ContactExtractor, ContactInfo
from app.nlp.sections import classify_sections


@pytest.fixture
def extractor():
    return ContactExtractor(enable_spacy=False)


# ============================================================================
# Candidate Name Extraction Tests
# ============================================================================

def test_name_standalone_first_line(extractor):
    """Verify name extraction when candidate name is on the first line."""
    text = (
        "Aarav Sharma\n"
        "aarav.sharma@dau.ac.in | +91 98250 12345\n\n"
        "EDUCATION\n"
        "B.Tech in ICT, DA-IICT"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)

    assert contact.full_name == "Aarav Sharma"
    assert contact.confidence >= 0.90


def test_name_and_contact_in_single_line(extractor):
    """Verify name extraction when name and contact info are separated by pipes on line 1."""
    text = (
        "Tanvi Dhiren Nakum | tanvi@dau.ac.in | +91 98765 43210 | Ahmedabad, India\n\n"
        "EDUCATION\n"
        "DA-IICT 2025"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)

    assert contact.full_name == "Tanvi Dhiren Nakum"
    assert contact.email == "tanvi@dau.ac.in"
    assert contact.phone == "+91 98765 43210"


def test_name_preceded_by_cv_label(extractor):
    """Verify that document labels like 'Curriculum Vitae' or 'Resume' are not treated as names."""
    text = (
        "CURRICULUM VITAE\n"
        "Harshil Rajendrabhai Tejot\n"
        "harshil@example.com | +91 98111 22233\n\n"
        "SKILLS\n"
        "Python, React"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)

    assert contact.full_name == "Harshil Rajendrabhai Tejot"
    assert "Curriculum" not in contact.full_name


def test_name_preceded_by_job_title(extractor):
    """Verify that leading job titles like 'Software Engineer' are not extracted as candidate name."""
    text = (
        "FULL STACK SOFTWARE ENGINEER\n"
        "Shlok Ashokbhai Topaliya\n"
        "shlok@dau.ac.in | +91 98980 11223\n\n"
        "EDUCATION\n"
        "B.Tech"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)

    assert contact.full_name == "Shlok Ashokbhai Topaliya"
    assert "Engineer" not in contact.full_name


def test_name_with_explicit_label(extractor):
    """Verify extraction when name is explicitly labeled 'Name: John Doe'."""
    text = (
        "Name: John Michael Doe\n"
        "Email: john.doe@example.com\n"
        "Phone: +1 (555) 019-2831\n\n"
        "EDUCATION\n"
        "BS in Computer Science"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)

    assert contact.full_name == "John Michael Doe"


def test_name_all_uppercase_normalized_to_title_case(extractor):
    """Verify that all-uppercase names are properly normalized to Title Case."""
    text = (
        "DHRUVIL MEHTA\n"
        "dhruvil@example.com | +91 98222 33445\n\n"
        "PROJECTS\n"
        "Resume Analyzer"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)

    assert contact.full_name == "Dhruvil Mehta"


# ============================================================================
# Email Extraction Tests
# ============================================================================

def test_extract_valid_email_and_prioritize_academic(extractor):
    """Verify extraction of standard emails and prioritization of academic domains."""
    text = (
        "Aarav Sharma\n"
        "Personal: aarav.personal@gmail.com | College: aarav.sharma@dau.ac.in\n\n"
        "EDUCATION\n"
        "DA-IICT"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)

    assert contact.email == "aarav.sharma@dau.ac.in"  # .ac.in prioritized over gmail
    assert len(contact.all_emails) == 2
    assert "aarav.personal@gmail.com" in contact.all_emails


def test_invalid_email_rejection(extractor):
    """Verify that malformed email-like tokens are ignored."""
    text = (
        "Jane Doe\n"
        "Invalid emails: user@, user@@domain.com, .user@example.com, no-tld@domain\n"
        "Valid email: jane.doe@example.org\n\n"
        "SKILLS\n"
        "Python"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)

    assert contact.email == "jane.doe@example.org"
    assert len(contact.all_emails) == 1


def test_missing_email_gracefully_returns_none(extractor):
    """Verify that a resume without an email returns email=None without crashing."""
    text = (
        "Jane Doe\n"
        "+91 98765 43210 | linkedin.com/in/janedoe\n\n"
        "EDUCATION\n"
        "B.Tech 2025"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)

    assert contact.email is None
    assert contact.all_emails == []
    assert contact.full_name == "Jane Doe"


# ============================================================================
# Phone Number Extraction Tests
# ============================================================================

def test_indian_mobile_phone_formats(extractor):
    """Verify extraction across varied Indian phone number notations."""
    test_cases = [
        ("+91 98250 12345", "+91 98250 12345"),
        ("+91-98250-12345", "+91 98250 12345"),
        ("09825012345", "+91 98250 12345"),
        ("9825012345", "+91 98250 12345"),
        ("98250 12345", "+91 98250 12345"),
    ]

    for raw_phone, expected_canonical in test_cases:
        text = f"Candidate Name\n{raw_phone} | test@dau.ac.in\n\nEDUCATION\nDA-IICT"
        sections = classify_sections(text)
        contact = extractor.extract(sections)
        assert contact.phone == expected_canonical, f"Failed on raw format: {raw_phone}"


def test_international_phone_number_formats(extractor):
    """Verify extraction of US and international E.164 phone numbers."""
    text = (
        "John Smith\n"
        "Phone: +1 (555) 019-2831\n"
        "Email: john@example.com\n\n"
        "EXPERIENCE\n"
        "Developer"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)

    assert contact.phone is not None
    assert "555" in contact.phone and "019" in contact.phone


def test_reject_dates_and_metrics_as_phone_numbers(extractor):
    """Verify that date ranges (2021-2025), pincodes (382007), and metrics are not parsed as phone numbers."""
    text = (
        "Aarav Sharma\n"
        "aarav@example.com | Ahmedabad, Gujarat - 382007\n\n"
        "EDUCATION\n"
        "B.Tech in ICT (2021 - 2025) | CGPA: 8.74 / 10\n"
        "Class XII (2019 - 2021) | 94.6%\n\n"
        "EXPERIENCE\n"
        "Handled 50,000 API requests per day.\n"
        "Roll No: 202401230"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)

    # There is no real phone number in this resume
    assert contact.phone is None
    assert contact.all_phones == []


# ============================================================================
# Online Profiles and URLs Extraction Tests
# ============================================================================

def test_online_profiles_extraction_and_categorization(extractor):
    """Verify extraction of LinkedIn, GitHub, LeetCode, CodeChef, and portfolio URLs."""
    text = (
        "Aarav Sharma\n"
        "aarav@dau.ac.in | +91 98250 12345\n"
        "LinkedIn: https://linkedin.com/in/aarav-sharma-cs/\n"
        "GitHub: github.com/aaravsharma\n"
        "LeetCode: https://leetcode.com/aarav_s\n"
        "CodeChef: codechef.com/users/aarav_s\n"
        "Portfolio: https://aaravsharma.dev\n\n"
        "SKILLS\n"
        "Python, C++"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)

    assert contact.linkedin_url == "https://linkedin.com/in/aarav-sharma-cs"
    assert contact.github_url == "https://github.com/aaravsharma"
    assert contact.portfolio_url == "https://aaravsharma.dev"
    assert "leetcode" in contact.coding_profiles
    assert contact.coding_profiles["leetcode"] == "https://leetcode.com/aarav_s"
    assert "codechef" in contact.coding_profiles
    assert contact.coding_profiles["codechef"] == "https://codechef.com/users/aarav_s"


def test_url_normalization_without_invention(extractor):
    """Verify that bare domains like 'github.com/user' are normalized to 'https://github.com/user'."""
    text = (
        "John Doe\n"
        "linkedin.com/in/johndoe, github.com/johndoe\n\n"
        "PROJECTS\n"
        "Web App"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)

    assert contact.linkedin_url == "https://linkedin.com/in/johndoe"
    assert contact.github_url == "https://github.com/johndoe"
    assert contact.portfolio_url is None


def test_contact_info_serialization_to_dict(extractor):
    """Verify that ContactInfo serializes to a dictionary compatible with CandidateProfile schema."""
    text = (
        "Aarav Sharma\n"
        "aarav@example.com | +91 98250 12345\n"
        "github.com/aarav"
    )
    sections = classify_sections(text)
    contact = extractor.extract(sections)
    data = contact.to_dict()

    assert data["full_name"] == "Aarav Sharma"
    assert data["email"] == "aarav@example.com"
    assert data["phone"] == "+91 98250 12345"
    assert data["github_url"] == "https://github.com/aarav"
    assert "provenance" in data
    assert "confidence" in data


# ============================================================================
# End-to-End Extraction on Synthetic Benchmark Fixture
# ============================================================================

def test_sample_resume_fixture_contact_extraction(sample_resume_text, extractor):
    """Verify contact extraction on the comprehensive synthetic placement resume fixture."""
    sections = classify_sections(sample_resume_text)
    contact = extractor.extract(sections)

    assert contact.full_name == "Aarav Sharma"
    assert contact.email == "aarav.sharma@dau.ac.in"
    assert contact.phone == "+91 98250 12345"
    assert contact.linkedin_url == "https://linkedin.com/in/aarav-sharma-cs"
    assert contact.github_url == "https://github.com/aaravsharma"
    assert contact.confidence >= 0.95
    assert contact.source_section == "personal_info"
