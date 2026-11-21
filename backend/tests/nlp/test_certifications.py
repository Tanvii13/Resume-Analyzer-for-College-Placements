"""
Unit tests for Sprint 2 – Module D4: Certifications & Achievements Extractor (NLP-09).
"""

from app.nlp.extractors.certifications import CertificationsExtractor
from app.nlp.sections import SectionMap, classify_sections

TEXT = """Test Student

CERTIFICATIONS
- AWS Certified Cloud Practitioner (2024)
- Google Data Analytics Professional Certificate
https://coursera.org/verify/ABC123

ACHIEVEMENTS
- Finalist, Smart India Hackathon 2024
- Rank 312 in CodeChef Starters 120

EXTRACURRICULAR ACTIVITIES
- Core member, Google Developer Student Club
"""


def test_lists_extracted_per_section():
    result = CertificationsExtractor().extract(classify_sections(TEXT))
    assert result.certifications == [
        "AWS Certified Cloud Practitioner (2024)",
        "Google Data Analytics Professional Certificate (https://coursera.org/verify/ABC123)",
    ]
    assert result.achievements == ["Finalist, Smart India Hackathon 2024", "Rank 312 in CodeChef Starters 120"]
    assert result.extracurricular == ["Core member, Google Developer Student Club"]


def test_missing_sections_give_empty_lists():
    result = CertificationsExtractor().extract(SectionMap())
    assert result.to_dict() == {"certifications": [], "achievements": [], "extracurricular": []}
