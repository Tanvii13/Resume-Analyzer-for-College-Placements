
"""
Job Description Parser and Ingestion Service for Sprint 3 (US-11).

Responsibilities:
- Sanitize and normalize pasted job-description text.
- Validate that a JD contains at least 50 words.
- Extract job title, experience level, degree requirements,
  and relevant academic disciplines.
"""

import re
import unicodedata
from typing import List, Optional

from pydantic import BaseModel, Field


MIN_JD_WORD_COUNT = 50


COMMON_JOB_ROLES = [
    (
        r"\b(?:software development engineer|sde\s*(?:i{1,3}|[1-3])?)\b",
        "Software Development Engineer (SDE)",
    ),
    (
        r"\b(?:backend engineer|backend developer|server[- ]side developer)\b",
        "Backend Engineer",
    ),
    (
        r"\b(?:frontend engineer|frontend developer|front[- ]end developer|ui developer)\b",
        "Frontend Engineer",
    ),
    (
        r"\b(?:full[- ]?stack engineer|full[- ]?stack developer)\b",
        "Full Stack Developer",
    ),
    (
        r"\b(?:data scientist|data science intern)\b",
        "Data Scientist",
    ),
    (
        r"\b(?:data analyst|business analyst|bi analyst)\b",
        "Data Analyst",
    ),
    (
        r"\b(?:machine learning engineer|ml engineer|ai engineer)\b",
        "Machine Learning Engineer",
    ),
    (
        r"\b(?:devops engineer|cloud engineer|sre|site reliability engineer)\b",
        "DevOps / Cloud Engineer",
    ),
    (
        r"\b(?:qa engineer|quality assurance engineer|software test engineer|automation engineer)\b",
        "QA / Automation Engineer",
    ),
    (
        r"\b(?:mobile developer|android developer|ios developer|flutter developer)\b",
        "Mobile Application Developer",
    ),
    (
        r"\b(?:software engineer intern|sde intern|summer intern|engineering intern)\b",
        "Software Engineering Intern",
    ),
    (
        r"\b(?:software engineer|software developer|graduate engineer trainee)\b",
        "Software Engineer",
    ),
]


EXPERIENCE_PATTERNS = [
    (
        r"\b(?:fresher|freshers|entry[- ]level|college graduate|"
        r"intern|internship|0\s*[-–to]+\s*1\s*(?:years?|yrs?))\b",
        "Fresher / Entry-Level (0-1 years)",
        0.0,
    ),
    (
        r"\b(?:1\s*[-–to]+\s*3\s*(?:years?|yrs?)|"
        r"1\+\s*(?:years?|yrs?)|2\+\s*(?:years?|yrs?))\b",
        "Junior (1-3 years)",
        1.0,
    ),
    (
        r"\b(?:3\s*[-–to]+\s*5\s*(?:years?|yrs?)|"
        r"3\+\s*(?:years?|yrs?)|4\+\s*(?:years?|yrs?))\b",
        "Mid-Level (3-5 years)",
        3.0,
    ),
    (
        r"\b(?:5\+\s*(?:years?|yrs?)|senior|lead|principal)\b",
        "Senior (5+ years)",
        5.0,
    ),
]


DEGREE_PATTERNS = [
    (r"\bB\.?\s?Tech\b|\bB\.?\s?E\.?\b", "B.Tech / B.E."),
    (r"\bM\.?\s?Tech\b|\bM\.?\s?E\.?\b", "M.Tech / M.E."),
    (r"\bM\.?\s?C\.?\s?A\.?\b", "MCA"),
    (r"\bB\.?\s?Sc\.?\b", "B.Sc."),
    (r"\bM\.?\s?Sc\.?\b", "M.Sc."),
    (r"\bbachelor(?:'s)?(?:\s+degree)?\b", "Bachelor's Degree"),
    (r"\bmaster(?:'s)?(?:\s+degree)?\b", "Master's Degree"),
    (r"\bPh\.?\s?D\b|\bdoctorate\b", "Ph.D."),
]


DISCIPLINE_PATTERNS = [
    (r"\bcomputer science\b|\bCSE\b", "Computer Science"),
    (r"\binformation technology\b|\bIT\b", "Information Technology"),
    (
        r"\binformation and communication technology\b|\bICT\b",
        "Information and Communication Technology",
    ),
    (r"\bsoftware engineering\b", "Software Engineering"),
    (
        r"\belectronics(?: and communication)?\b|\bECE\b",
        "Electronics & Communication",
    ),
    (
        r"\bdata science\b|\bartificial intelligence\b|\bAI\b|\bML\b",
        "Data Science / AI",
    ),
    (r"\bmathematics\b|\bstatistics\b", "Mathematics / Statistics"),
]


class ParsedJobDescription(BaseModel):
    """Structured metadata extracted from a job description."""

    title: str = "Not specified"
    experience_level: str = "Not specified"
    minimum_experience_years: Optional[float] = None
    required_degrees: List[str] = Field(default_factory=list)
    required_disciplines: List[str] = Field(default_factory=list)
    word_count: int
    clean_text: str


class JDParser:
    """Sanitizes and extracts useful metadata from job descriptions."""

    @staticmethod
    def sanitize_text(raw_text: str) -> str:
        """
        Normalize Unicode, remove invisible characters, standardize
        line endings, and collapse unnecessary whitespace.
        """

        if not isinstance(raw_text, str):
            raise TypeError("Job description text must be a string.")

        if not raw_text:
            return ""

        normalized = unicodedata.normalize("NFKC", raw_text)

        # Remove zero-width and other invisible formatting characters.
        normalized = re.sub(
            r"[\u200b-\u200d\ufeff\u00ad]",
            "",
            normalized,
        )

        # Standardize line endings.
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

        # Normalize whitespace on each line while preserving paragraphs.
        lines = [
            re.sub(r"[ \t\f\v]+", " ", line).strip()
            for line in normalized.split("\n")
        ]

        cleaned = "\n".join(lines)

        # Limit excessive blank lines.
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        return cleaned.strip()

    @classmethod
    def parse_job_description(
        cls,
        raw_jd_text: str,
    ) -> ParsedJobDescription:
        """
        Sanitize, validate, and extract metadata from a JD.

        Raises:
            TypeError: If input is not a string.
            ValueError: If the sanitized JD has fewer than 50 words.
        """

        clean_text = cls.sanitize_text(raw_jd_text)
        words = clean_text.split()
        word_count = len(words)

        if word_count < MIN_JD_WORD_COUNT:
            raise ValueError(
                f"Job description must contain at least "
                f"{MIN_JD_WORD_COUNT} words to extract meaningful "
                f"requirements (provided: {word_count} words)."
            )

        lower_text = clean_text.lower()

        # 1. Extract the target job title.
        detected_title = "Not specified"

        for pattern, canonical_title in COMMON_JOB_ROLES:
            if re.search(pattern, lower_text, re.IGNORECASE):
                detected_title = canonical_title
                break

        # 2. Extract experience requirements.
        detected_experience = "Not specified"
        minimum_experience: Optional[float] = None

        for pattern, label, years in EXPERIENCE_PATTERNS:
            if re.search(pattern, lower_text, re.IGNORECASE):
                detected_experience = label
                minimum_experience = years
                break

        # 3. Extract degree requirements.
        detected_degrees = []

        for pattern, label in DEGREE_PATTERNS:
            if re.search(pattern, clean_text, re.IGNORECASE):
                if label not in detected_degrees:
                    detected_degrees.append(label)

        # 4. Extract academic disciplines.
        detected_disciplines = []

        for pattern, label in DISCIPLINE_PATTERNS:
            if re.search(pattern, clean_text, re.IGNORECASE):
                if label not in detected_disciplines:
                    detected_disciplines.append(label)

        return ParsedJobDescription(
            title=detected_title,
            experience_level=detected_experience,
            minimum_experience_years=minimum_experience,
            required_degrees=detected_degrees,
            required_disciplines=detected_disciplines,
            word_count=word_count,
            clean_text=clean_text,
        )
