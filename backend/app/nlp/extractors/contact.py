"""
Contact information and online profile extractor.

Module C (NLP-03) of Sprint 2 NLP pipeline.

Extracts candidate identity, email addresses, phone numbers (Indian and international),
and professional web profiles (LinkedIn, GitHub, LeetCode, CodeChef, portfolio) with
high precision and zero fabrication.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.nlp.extractors.base import BaseExtractor
from app.nlp.preprocessing import SegmentedDocument
from app.nlp.sections import SectionMap, SECTION_PERSONAL_INFO

# Optional spaCy NER support
try:
    import spacy
    _SPACY_AVAILABLE = True
except ImportError:
    _SPACY_AVAILABLE = False


@dataclass
class ContactInfo:
    """Structured candidate identity and contact information."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    coding_profiles: Dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0
    all_emails: List[str] = field(default_factory=list)
    all_phones: List[str] = field(default_factory=list)
    all_urls: List[str] = field(default_factory=list)
    source_section: Optional[str] = None
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "linkedin_url": self.linkedin_url,
            "github_url": self.github_url,
            "portfolio_url": self.portfolio_url,
            "coding_profiles": self.coding_profiles,
            "confidence": self.confidence,
            "all_emails": self.all_emails,
            "all_phones": self.all_phones,
            "all_urls": self.all_urls,
            "source_section": self.source_section,
            "provenance": self.provenance,
        }


# Strict email regex conforming to RFC 5322 subset common in resumes
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9](?:[A-Za-z0-9._%+-]*[A-Za-z0-9])?@[A-Za-z0-9.-]+\.[A-Za-z]{2,10}\b"
)

# Indian mobile numbers: 10 digits starting with 6, 7, 8, or 9
_INDIAN_PHONE_RE = re.compile(
    r"(?:\+91[\s.-]?|91[\s.-]?|0)?([6-9]\d{4}[\s.-]?\d{5})\b"
)

# International E.164 phone numbers (with explicit country code, e.g. +1, +44, +61)
_INTL_PHONE_RE = re.compile(
    r"\+(?!91\b)(\d{1,3})[\s.-]?\(?(\d{1,4})\)?[\s.-]?(\d{1,4})[\s.-]?(\d{1,9})\b"
)

# North American / US standard format: (555) 019-2831 or 555-019-2831
_US_PHONE_RE = re.compile(
    r"(?:\+1[\s.-]?)?\(?([2-9]\d{2})\)?[\s.-]?([2-9]\d{2})[\s.-]?(\d{4})\b"
)

# URL detection regex matching standard links and web handles
_URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s,;\"'<>]+|[a-zA-Z0-9.-]+\.(?:com|org|io|dev|in|me|net|tech|app)(?:/[^\s,;\"'<>]*)?",
    re.I,
)

# Words that disqualify a candidate line from being a person's name
_NAME_BLACKLIST_WORDS = {
    # Document labels
    "curriculum", "vitae", "resume", "cv", "biodata", "profile", "portfolio",
    # Section headings
    "education", "academic", "academics", "experience", "employment", "internship",
    "internships", "projects", "skills", "technical", "competencies", "tools",
    "certifications", "certificates", "achievements", "awards", "extracurricular",
    "activities", "summary", "objective", "contact", "details", "information",
    # Job titles and common roles
    "software", "engineer", "developer", "programmer", "architect", "analyst",
    "scientist", "intern", "student", "fresher", "undergraduate", "graduate",
    "full", "stack", "frontend", "backend", "web", "mobile", "ios", "android",
    "data", "machine", "learning", "devops", "cloud", "security", "designer",
    "manager", "lead", "assistant", "consultant", "officer", "administrator",
    # Degree names & Academic terminology
    "bachelor", "master", "doctor", "technology", "engineering", "science",
    "b.tech", "m.tech", "b.e.", "b.sc", "m.sc", "bca", "mca", "ph.d", "hsc", "ssc",
    "university", "institute", "college", "school", "academy", "department",
    "semester", "cgpa", "gpa", "percentage", "marks", "rank", "year",
    # Geography & General terms
    "india", "gujarat", "ahmedabad", "gandhinagar", "mumbai", "delhi", "bangalore",
    "address", "phone", "mobile", "email", "mail", "linkedin", "github", "website",
}


def _clean_url(raw_url: str) -> str:
    """Normalize a raw URL string to a canonical https:// format."""
    url = raw_url.strip().rstrip(".,;:)'\"]}")
    if url.startswith("www."):
        url = "https://" + url
    elif not url.startswith(("http://", "https://")):
        url = "https://" + url
    # Strip trailing slash
    return url.rstrip("/")


class ContactExtractor(BaseExtractor):
    """
    Precision extractor for candidate name, emails, phone numbers, and web profiles.
    """

    def __init__(self, enable_spacy: bool = False):
        self._nlp = None
        if enable_spacy and _SPACY_AVAILABLE:
            try:
                self._nlp = spacy.load("en_core_web_sm", disable=["tagger", "parser", "lemmatizer"])
            except Exception:
                self._nlp = None

    def extract(
        self,
        sections: SectionMap,
        document: Optional[SegmentedDocument] = None,
    ) -> ContactInfo:
        """
        Extract contact details, prioritizing 'personal_info' section and using full text as fallback.
        """
        personal_section = sections.get_section(SECTION_PERSONAL_INFO)

        # 1. Search text prioritization: primary target is personal_info
        if personal_section and personal_section.content.strip():
            primary_text = personal_section.content
            primary_lines = [line.text for line in personal_section.lines if line.text.strip()]
            source_section = SECTION_PERSONAL_INFO
        else:
            # Fallback: first 1000 characters of the whole document
            if document and document.normalized_text:
                primary_text = document.normalized_text[:1200]
                primary_lines = [l.text for l in document.get_non_empty_lines()[:10]]
            else:
                full_content = "\n\n".join(s.content for s in sections.sections)
                primary_text = full_content[:1200]
                primary_lines = [l.strip() for l in primary_text.split("\n") if l.strip()][:10]
            source_section = "document_header_fallback"

        # Also prepare full text for global email/phone/url harvesting
        if document and document.normalized_text:
            full_text = document.normalized_text
        else:
            full_text = "\n\n".join(s.content for s in sections.sections)

        # 2. Extract Candidate Name
        name, name_conf = self._extract_candidate_name(primary_lines, primary_text)

        # 3. Extract Emails
        emails = self._extract_emails(primary_text, full_text)
        primary_email = emails[0] if emails else None

        # 4. Extract Phone Numbers
        phones = self._extract_phones(primary_text, full_text)
        primary_phone = phones[0] if phones else None

        # 5. Extract URLs and Social Profiles
        profiles, urls = self._extract_profiles(primary_text, full_text)

        # Calculate overall confidence
        conf_factors = []
        if name:
            conf_factors.append(name_conf)
        if primary_email:
            conf_factors.append(1.0)
        if primary_phone:
            conf_factors.append(0.95)
        if profiles.get("linkedin") or profiles.get("github"):
            conf_factors.append(1.0)

        overall_conf = round(sum(conf_factors) / len(conf_factors), 2) if conf_factors else 0.50

        return ContactInfo(
            full_name=name,
            email=primary_email,
            phone=primary_phone,
            linkedin_url=profiles.get("linkedin"),
            github_url=profiles.get("github"),
            portfolio_url=profiles.get("portfolio"),
            coding_profiles={k: v for k, v in profiles.items() if k not in ("linkedin", "github", "portfolio")},
            confidence=overall_conf,
            all_emails=emails,
            all_phones=phones,
            all_urls=urls,
            source_section=source_section,
            provenance={
                "name_confidence": name_conf,
                "email_count": len(emails),
                "phone_count": len(phones),
                "profile_count": len(profiles),
            },
        )

    def _extract_candidate_name(
        self,
        lines: List[str],
        section_text: str,
    ) -> Tuple[Optional[str], float]:
        """
        Extract candidate name from header lines using layout heuristics and contextual validation.
        """
        # Step 1: Check lines for explicit labeled name or clean candidates
        for idx, line in enumerate(lines[:8]):
            clean_line = line.strip()
            if not clean_line:
                continue

            # 1a. Explicit "Name:" or "Full Name:" label
            m_label = re.match(r"^(?:Full\s+)?Name\s*:\s*(.+)$", clean_line, flags=re.I)
            if m_label:
                val = m_label.group(1).strip()
                if " | " in val:
                    val = val.split(" | ")[0].strip()
                if self._is_valid_name(val):
                    return self._format_name(val), 1.0

            # 1b. Line containing pipes (e.g., "Aarav Sharma | aarav@example.com | +91...")
            if " | " in clean_line:
                segments = [s.strip() for s in clean_line.split(" | ") if s.strip()]
                for seg in segments:
                    clean_seg = re.sub(r"^(?:Full\s+)?Name\s*:\s*", "", seg, flags=re.I).strip()
                    if self._is_valid_name(clean_seg):
                        return self._format_name(clean_seg), 0.95

            # 1c. Standalone line check
            if self._is_valid_name(clean_line):
                conf = 0.95 if idx == 0 else 0.90
                return self._format_name(clean_line), conf

        # Step 2: Optional spaCy PERSON NER verification on the header block
        if self._nlp is not None:
            doc = self._nlp(section_text[:400])
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    clean_ent = ent.text.strip()
                    if self._is_valid_name(clean_ent):
                        return self._format_name(clean_ent), 0.88

        return None, 0.0

    def _is_valid_name(self, text: str) -> bool:
        """Verify whether a candidate string satisfies the lexical rules for a person name."""
        candidate = text.strip()
        if not (4 <= len(candidate) <= 35):
            return False

        # Reject strings with digits, URLs, emails, or bullet characters
        if re.search(r"[\d@:/\\•*+#=$%&]", candidate):
            return False

        words = candidate.split()
        if not (2 <= len(words) <= 4):
            return False

        # Each token must be alphabetic (allowing optional initial dot like 'H.')
        for w in words:
            clean_w = w.rstrip(".").replace("-", "")
            if not clean_w.isalpha():
                return False

        lower_words = [w.lower().rstrip(".,") for w in words]
        candidate_lower = " ".join(lower_words)

        # Check against blacklist
        for blacklisted in _NAME_BLACKLIST_WORDS:
            if blacklisted in lower_words or blacklisted == candidate_lower:
                return False

        # Must have proper casing (Title Case or ALL UPPERCASE)
        is_title = all(w[0].isupper() for w in words if w)
        is_upper = candidate.isupper()

        return is_title or is_upper

    def _format_name(self, name_str: str) -> str:
        """Standardize candidate name casing to Title Case."""
        words = name_str.strip().split()
        return " ".join(w.capitalize() if w.isupper() else w for w in words)

    def _extract_emails(self, primary_text: str, full_text: str) -> List[str]:
        """Extract and validate distinct email addresses in order of priority."""
        extracted: List[str] = []
        seen: Set[str] = set()

        def scan_text(txt: str):
            for match in _EMAIL_RE.finditer(txt):
                start = match.start()
                end = match.end()

                # Reject if preceded by '.', '@', or alphanumeric (e.g. '.user@domain.com')
                if start > 0 and txt[start - 1] in (".", "@"):
                    continue
                # Reject if immediately followed by '@'
                if end < len(txt) and txt[end] == "@":
                    continue

                raw = match.group(0).strip().rstrip(".,;:")
                # Strip leading mailto: if present
                if raw.lower().startswith("mailto:"):
                    raw = raw[7:]
                clean_email = raw.lower()
                # Basic domain validation
                if "@" in clean_email and "." in clean_email.split("@")[-1]:
                    domain = clean_email.split("@")[-1]
                    # Filter out dummy/image extensions
                    if not domain.endswith((".png", ".jpg", ".pdf", ".gif")):
                        if clean_email not in seen:
                            seen.add(clean_email)
                            extracted.append(clean_email)

        # First scan personal_info section
        scan_text(primary_text)
        # Then scan full document
        scan_text(full_text)

        # Prioritize university or academic emails if multiple found
        extracted.sort(key=lambda e: (0 if any(dom in e for dom in (".edu", ".ac.in")) else 1))
        return extracted

    def _extract_phones(self, primary_text: str, full_text: str) -> List[str]:
        """Extract valid Indian and international phone numbers, filtering out dates and IDs."""
        phones: List[str] = []
        seen_digits: Set[str] = set()

        def extract_from(txt: str):
            # Clean text by removing date ranges like '2021 - 2025' or 'May 2023 - July 2024'
            cleaned = re.sub(
                r"\b(?:19|20)\d{2}\s*[-–]\s*(?:(?:19|20)\d{2}|Present)\b",
                " ",
                txt,
                flags=re.I,
            )
            # Remove URLs and emails so their digits don't interfere
            cleaned = _URL_RE.sub(" ", cleaned)
            cleaned = _EMAIL_RE.sub(" ", cleaned)

            # 1. Search for Indian mobile numbers
            for match in _INDIAN_PHONE_RE.finditer(cleaned):
                digits = re.sub(r"\D", "", match.group(0))
                # Normalized 10 digits
                core_digits = digits[-10:] if len(digits) >= 10 else digits
                if len(core_digits) == 10 and core_digits[0] in "6789":
                    # Reject if it matches a typical year or student ID pattern (e.g. starts with 2024)
                    if core_digits.startswith(("2020", "2021", "2022", "2023", "2024", "2025")):
                        continue
                    if core_digits not in seen_digits:
                        seen_digits.add(core_digits)
                        formatted = f"+91 {core_digits[:5]} {core_digits[5:]}"
                        phones.append(formatted)

            # 2. Search for US / North American numbers
            for match in _US_PHONE_RE.finditer(cleaned):
                digits = re.sub(r"\D", "", match.group(0))
                core_digits = digits[-10:] if len(digits) >= 10 else digits
                if len(core_digits) == 10 and core_digits not in seen_digits:
                    # Guard against Indian numbers starting with 6-9
                    if core_digits[0] not in "6789":
                        seen_digits.add(core_digits)
                        formatted = f"+1 ({core_digits[:3]}) {core_digits[3:6]}-{core_digits[6:]}"
                        phones.append(formatted)

            # 3. Search for international numbers (+XX ...)
            for match in _INTL_PHONE_RE.finditer(cleaned):
                raw = match.group(0).strip()
                digits = re.sub(r"\D", "", raw)
                if 10 <= len(digits) <= 15 and digits not in seen_digits:
                    seen_digits.add(digits)
                    phones.append(raw)

        # Prioritize header/personal section
        extract_from(primary_text)
        if not phones:
            extract_from(full_text)

        return phones

    def _extract_profiles(
        self,
        primary_text: str,
        full_text: str,
    ) -> Tuple[Dict[str, str], List[str]]:
        """Extract social and coding profiles, normalizing URLs and categorizing by platform."""
        profiles: Dict[str, str] = {}
        all_urls: List[str] = []
        seen: Set[str] = set()

        # Remove email addresses first so email domains (e.g. dau.ac.in) are not parsed as URLs
        combined_text = f"{primary_text}\n{full_text}"
        text_without_emails = _EMAIL_RE.sub(" ", combined_text)

        for match in _URL_RE.finditer(text_without_emails):
            raw = match.group(0).strip()
            clean = _clean_url(raw)
            lower = clean.lower()

            if clean in seen:
                continue
            seen.add(clean)
            all_urls.append(clean)

            # Categorize profile
            if "linkedin.com/in/" in lower:
                if "linkedin" not in profiles:
                    profiles["linkedin"] = clean
            elif "github.com/" in lower:
                # Exclude github system URLs
                if not any(sub in lower for sub in ("/topics", "/pricing", "/features", "/trending")):
                    if "github" not in profiles:
                        profiles["github"] = clean
            elif "leetcode.com/" in lower:
                if "leetcode" not in profiles:
                    profiles["leetcode"] = clean
            elif "codechef.com/users/" in lower:
                if "codechef" not in profiles:
                    profiles["codechef"] = clean
            elif "hackerrank.com/" in lower:
                if "hackerrank" not in profiles:
                    profiles["hackerrank"] = clean
            elif "codeforces.com/profile/" in lower:
                if "codeforces" not in profiles:
                    profiles["codeforces"] = clean
            elif "kaggle.com/" in lower:
                if "kaggle" not in profiles:
                    profiles["kaggle"] = clean
            else:
                # Potential personal portfolio website
                if "portfolio" not in profiles:
                    # Ignore common general domains and academic/institutional domains
                    if not any(dom in lower for dom in (
                        "gmail.com", "google.com", "yahoo.com", "outlook.com",
                        "microsoft.com", "adobe.com", "w3schools.com", "stackoverflow.com",
                        ".edu", ".ac.in", ".edu.in", ".gov", ".org",
                    )):
                        # Accept if it looks like a personal root domain or has portfolio keyword
                        if re.search(r"\.(?:dev|me|io|app|in|com)/?$", lower) or "portfolio" in lower:
                            profiles["portfolio"] = clean

        return profiles, all_urls
