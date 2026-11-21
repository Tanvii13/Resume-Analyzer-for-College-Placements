import pytest
from uuid import uuid4
from app.services.privacy_masking_service import PrivacyMaskingService
from app.schemas.privacy_schemas import (
    AnonymizedResumeResponse,
    DirectMaskRequest,
    DirectMaskResponse,
)


def test_email_masking_tag_and_partial():
    raw_email = "tanish.solanki@dau.ac.in"
    tag_result = PrivacyMaskingService.mask_email(raw_email, style="tag")
    assert tag_result == "[REDACTED_EMAIL]"

    partial_result = PrivacyMaskingService.mask_email(raw_email, style="partial")
    assert partial_result.startswith("t")
    assert partial_result.endswith("@dau.ac.in")
    assert "*" in partial_result


def test_phone_masking_formats():
    phones = ["+91 9876543210", "+91-98765-43210", "9876543210"]
    for ph in phones:
        tag_result = PrivacyMaskingService.mask_phone(ph, style="tag")
        assert tag_result == "[REDACTED_PHONE]"

        partial_result = PrivacyMaskingService.mask_phone(ph, style="partial")
        assert "+91 98******10" == partial_result


def test_pincode_masking():
    text = "Student resident of Gandhinagar 382007, Gujarat."
    masked, stats, fields = PrivacyMaskingService.anonymize_text(text)
    assert "382007" not in masked
    assert "[POSTAL_CODE]" in masked
    assert stats["pincodes_masked"] == 1
    assert "pincode" in fields


def test_candidate_name_redaction():
    text = "Resume of Tanish Solanki, software developer."
    masked, stats, fields = PrivacyMaskingService.anonymize_text(
        text, 
        candidate_name="Tanish Solanki"
    )
    assert "Tanish Solanki" not in masked
    assert "[CANDIDATE NAME REDACTED]" in masked
    assert stats["names_masked"] == 1
    assert "candidate_name" in fields


def test_technical_skills_preservation():
    tech_text = "Proficient in C++, C#, Node.js, Python, React.js, CI/CD, and Docker."
    masked, _, _ = PrivacyMaskingService.anonymize_text(tech_text)
    # Skills must not be corrupted
    assert "C++" in masked
    assert "C#" in masked
    assert "Node.js" in masked
    assert "CI/CD" in masked
    assert "React.js" in masked


def test_academic_metrics_and_percentages_preservation():
    metrics_text = "CGPA: 8.85/10.0, achieved 99.9% uptime and reduced latency by 45.5% across 10,000 requests."
    masked, _, _ = PrivacyMaskingService.anonymize_text(metrics_text)
    assert "8.85/10.0" in masked
    assert "99.9%" in masked
    assert "45.5%" in masked
    assert "10,000" in masked


def test_properly_anonymized_audit():
    unmasked = "Contact: john@gmail.com, phone 9876543210"
    assert PrivacyMaskingService.is_properly_anonymized(unmasked) is False

    masked, _, _ = PrivacyMaskingService.anonymize_text(unmasked)
    assert PrivacyMaskingService.is_properly_anonymized(masked) is True


def test_candidate_hash_determinism():
    email = "tanish.solanki@dau.ac.in"
    h1 = PrivacyMaskingService.generate_candidate_hash(email)
    h2 = PrivacyMaskingService.generate_candidate_hash(email)
    assert h1 == h2
    assert h1.startswith("CAND-")


def test_privacy_schemas_validation():
    response = AnonymizedResumeResponse(
        resume_id=str(uuid4()),
        candidate_id_hash="CAND-TEST01",
        anonymized_text="Safe redacted text",
        skills=["Python", "FastAPI"],
        masked_fields=["email", "phone"]
    )
    assert response.status == "success"
    assert response.is_anonymized is True
    assert len(response.skills) == 2

    direct_req = DirectMaskRequest(raw_text="Call 9876543210")
    assert direct_req.mask_style == "tag"

    direct_res = DirectMaskResponse(
        original_length=15,
        masked_length=20,
        masked_text="Call [REDACTED_PHONE]",
        is_safe=True
    )
    assert direct_res.is_safe is True
