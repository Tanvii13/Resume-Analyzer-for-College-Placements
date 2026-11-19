import re
import hashlib
from typing import Dict, List, Optional, Tuple


class PrivacyMaskingService:
    """
    US-17: Service for detecting and masking Personally Identifiable Information (PII)
    in student resumes according to NFR-03, NFR-09, and DR-08.

    Conceals candidate names, emails, phone numbers, and pincodes while guaranteeing
    zero corruption to technical skills (C++, Node.js), metrics (CGPA, 99.9%),
    and project achievements.
    """

    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )
    PHONE_PATTERN = re.compile(
        r"(?:(?:\+|00)?91[\s.-]?)?[6-9]\d{4}[\s.-]?\d{5}\b"
    )
    PINCODE_PATTERN = re.compile(
        r"\b[1-9][0-9]{2}\s?[0-9]{3}\b"
    )

    # Verification regex patterns to ensure no raw unmasked PII remains
    UNMASKED_EMAIL_PATTERN = re.compile(
        r"(?<![*a-zA-Z0-9])[A-Za-z0-9._%+-]{2,}@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )
    UNMASKED_PHONE_PATTERN = re.compile(
        r"(?:(?:\+|00)?91[\s.-]?)?[6-9]\d{4}[\s.-]?\d{5}\b"
    )

    @classmethod
    def mask_email(cls, email: str, style: str = "tag") -> str:
        """
        Masks an email address.
        - style='tag' -> '[REDACTED_EMAIL]'
        - style='partial' -> 't****h@dau.ac.in'
        """
        if style == "partial" and "@" in email:
            user, domain = email.split("@", 1)
            if len(user) <= 2:
                masked_user = user[0] + "*"
            else:
                masked_user = user[0] + ("*" * (len(user) - 2)) + user[-1]
            return f"{masked_user}@{domain}"
        return "[REDACTED_EMAIL]"

    @classmethod
    def mask_phone(cls, phone: str, style: str = "tag") -> str:
        """
        Masks an Indian/international phone number.
        - style='tag' -> '[REDACTED_PHONE]'
        - style='partial' -> '+91 98******10'
        """
        if style == "partial":
            digits = re.sub(r"\D", "", phone)
            if len(digits) >= 10:
                last10 = digits[-10:]
                return f"+91 {last10[:2]}******{last10[-2:]}"
        return "[REDACTED_PHONE]"

    @classmethod
    def generate_candidate_hash(cls, identifier: str) -> str:
        """
        Generates a deterministic pseudonymous candidate ID (e.g. 'CAND-A89F12').
        """
        digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:8].upper()
        return f"CAND-{digest}"

    @classmethod
    def anonymize_text(
        cls, 
        text: str, 
        candidate_name: Optional[str] = None, 
        style: str = "tag"
    ) -> Tuple[str, Dict[str, int], List[str]]:
        """
        Scans and redacts contact PII from raw resume text while preserving
        technical skills, academic credentials, and bullet point metrics.

        Returns:
            Tuple of (masked_text, detected_pii_counts, list_of_masked_fields)
        """
        if not text:
            return "", {}, []

        masked_text = text
        stats = {
            "emails_masked": 0,
            "phones_masked": 0,
            "pincodes_masked": 0,
            "names_masked": 0
        }
        masked_fields: List[str] = []

        # 1. Mask Candidate Name (if provided)
        if candidate_name and candidate_name.strip():
            clean_name = candidate_name.strip()
            name_pattern = re.compile(
                r"\b" + re.escape(clean_name) + r"\b", 
                re.IGNORECASE
            )
            matches = name_pattern.findall(masked_text)
            if matches:
                stats["names_masked"] = len(matches)
                masked_text = name_pattern.sub("[CANDIDATE NAME REDACTED]", masked_text)
                masked_fields.append("candidate_name")

        # 2. Mask Email Addresses
        emails = cls.EMAIL_PATTERN.findall(masked_text)
        if emails:
            for em in set(emails):
                count = len(re.findall(re.escape(em), masked_text))
                stats["emails_masked"] += count
                replacement = cls.mask_email(em, style=style)
                masked_text = masked_text.replace(em, replacement)
            masked_fields.append("email")

        # 3. Mask Phone Numbers
        phones = cls.PHONE_PATTERN.findall(masked_text)
        if phones:
            for ph in set(phones):
                count = len(re.findall(re.escape(ph), masked_text))
                stats["phones_masked"] += count
                replacement = cls.mask_phone(ph, style=style)
                masked_text = masked_text.replace(ph, replacement)
            masked_fields.append("phone")

        # 4. Mask Pincodes / Postal Codes
        pincodes = cls.PINCODE_PATTERN.findall(masked_text)
        if pincodes:
            for pin in set(pincodes):
                count = len(re.findall(re.escape(pin), masked_text))
                stats["pincodes_masked"] += count
                masked_text = masked_text.replace(pin, "[POSTAL_CODE]")
            masked_fields.append("pincode")

        return masked_text, stats, masked_fields

    @classmethod
    def is_properly_anonymized(cls, text: str) -> bool:
        """
        Audits whether raw, unmasked email addresses or phone numbers remain.
        """
        if not text:
            return True
        has_raw_email = bool(cls.UNMASKED_EMAIL_PATTERN.search(text))
        has_raw_phone = bool(cls.UNMASKED_PHONE_PATTERN.search(text))
        return not (has_raw_email or has_raw_phone)
