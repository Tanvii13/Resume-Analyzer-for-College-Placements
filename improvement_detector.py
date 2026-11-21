
"""
Resume Improvement Area Detector Service for Sprint 3 (US-08).

Responsibilities:
- Detect missing or weak areas in a resume.
- Rank detected issues as High, Medium, or Low priority.
- Consider both raw resume text and extracted structured data.
- Avoid flagging a section as missing when its content is present.
"""

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ImprovementIssue(BaseModel):
    """One actionable improvement identified in a resume."""

    id: str
    section: str
    priority: str
    issue: str
    reason: str
    remediation: str


class ImprovementReport(BaseModel):
    """Complete improvement report with priority counts."""

    total_issues: int
    priority_breakdown: Dict[str, int]
    improvement_areas: List[ImprovementIssue]


class ImprovementDetector:
    """Detect weak and missing resume areas and rank their importance."""

    PRIORITY_ORDER = {"High": 1, "Medium": 2, "Low": 3}

    # Common resume section heading alternatives.
    SECTION_HEADINGS = {
        "education": {
            "education", "academic", "academics", "academic background",
            "educational background", "qualifications",
            "educational qualifications",
        },
        "skills": {
            "skills", "technical skills", "technical expertise",
            "technologies", "technical competencies",
        },
        "projects": {
            "projects", "academic projects", "personal projects",
            "project experience", "project work", "key projects",
        },
        "experience": {
            "experience", "work experience", "professional experience",
            "employment history", "internship", "internships",
        },
    }

    def __init__(self) -> None:
        # Contact information.
        self.email_pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
            re.IGNORECASE,
        )
        self.institutional_email_pattern = re.compile(
            r"\b[A-Za-z0-9._%+-]+@(?:dau\.ac\.in|daiict\.ac\.in)\b",
            re.IGNORECASE,
        )
        self.phone_pattern = re.compile(
            r"(?<!\d)(?:\+91[\s.-]?)?[6-9]\d{9}(?!\d)"
        )
        self.linkedin_pattern = re.compile(
            r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?",
            re.IGNORECASE,
        )
        self.github_pattern = re.compile(
            r"(?:https?://)?(?:www\.)?github\.com/[\w-]+/?",
            re.IGNORECASE,
        )

        # Academic information.
        self.cgpa_pattern = re.compile(
            r"\b(?:cgpa|gpa|c\.g\.p\.a\.?|pointer)\s*[:=-]?\s*"
            r"\d+(?:\.\d+)?(?:\s*/\s*(?:10|4))?\b"
            r"|\b\d\.\d{1,2}\s*/\s*(?:10|4)\b",
            re.IGNORECASE,
        )
        self.percentage_pattern = re.compile(
            r"\b\d{2,3}(?:\.\d{1,2})?\s*(?:%|percent)\b",
            re.IGNORECASE,
        )
        self.degree_pattern = re.compile(
            r"\b(?:B\.?\s?Tech|B\.?\s?E\.?|M\.?\s?Tech|M\.?\s?E\.?|"
            r"M\.?\s?C\.?\s?A\.?|B\.?\s?Sc\.?|M\.?\s?Sc\.?|"
            r"bachelor(?:'s)?|master(?:'s)?|Ph\.?\s?D\.?)\b",
            re.IGNORECASE,
        )
        self.graduation_year_pattern = re.compile(
            r"\b(?:20\d{2}|203[0-5])\b"
        )

        # Evidence of measurable results.
        self.metric_pattern = re.compile(
            r"\b\d+(?:\.\d+)?\s*%|\b\d+\+|\b\d+\s*"
            r"(?:users|clients|requests|ms|milliseconds|seconds|"
            r"minutes|hours|projects|records|downloads|members|"
            r"transactions|days|weeks)\b",
            re.IGNORECASE,
        )

        self.weak_verbs = (
            "worked on",
            "helped",
            "assisted",
            "responsible for",
            "participated",
            "involved in",
            "handled",
            "did",
            "made",
            "used",
        )

        self.strong_verbs = {
            "architected", "automated", "built", "configured",
            "created", "debugged", "deployed", "designed",
            "developed", "engineered", "enhanced", "executed",
            "implemented", "improved", "increased", "integrated",
            "launched", "led", "managed", "monitored", "optimized",
            "programmed", "refactored", "resolved", "scaled",
            "standardized", "streamlined", "tested", "trained",
            "analyzed", "analyser", "coordinated", "delivered",
            "established", "formulated", "maintained", "reduced",
        }

    @staticmethod
    def _has_section_data(
        structured_data: Optional[Dict[str, Any]],
        section: str,
    ) -> bool:
        """Check whether extracted structured data contains a section."""

        if not isinstance(structured_data, dict):
            return False

        aliases = {
            "education": ("education", "academic_profile"),
            "skills": ("skills", "technical_skills", "soft_skills"),
            "projects": ("projects",),
            "experience": ("experience", "work_experience"),
        }

        for key in aliases.get(section, (section,)):
            value = structured_data.get(key)

            if isinstance(value, str) and value.strip():
                return True

            if isinstance(value, (list, tuple, set)) and len(value) > 0:
                if any(
                    (isinstance(item, str) and item.strip())
                    or (isinstance(item, dict) and bool(item))
                    for item in value
                ):
                    return True

            if isinstance(value, dict) and bool(value):
                return True

        return False

    def _has_section_heading(self, text: str, section: str) -> bool:
        """Check for a recognizable standalone section heading."""

        headings = self.SECTION_HEADINGS[section]

        for line in text.splitlines():
            cleaned = re.sub(r"^[\s\d.#*_\-]+|[:\s]+$", "", line)
            cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()

            if cleaned in headings:
                return True

        return False

    @staticmethod
    def _make_issue(
        issue_id: str,
        section: str,
        priority: str,
        issue: str,
        reason: str,
        remediation: str,
    ) -> ImprovementIssue:
        return ImprovementIssue(
            id=issue_id,
            section=section,
            priority=priority,
            issue=issue,
            reason=reason,
            remediation=remediation,
        )

    def detect_improvements(
        self,
        raw_text: str,
        structured_data: Optional[Dict[str, Any]] = None,
        page_count: Optional[int] = None,
    ) -> ImprovementReport:
        """
        Analyze resume text and optional extracted data.

        Returns issues sorted from High to Low priority.
        """

        if not isinstance(raw_text, str):
            raise TypeError("raw_text must be a string.")

        if structured_data is not None and not isinstance(
            structured_data, dict
        ):
            raise TypeError("structured_data must be a dictionary or None.")

        if page_count is not None and (
            not isinstance(page_count, int)
            or isinstance(page_count, bool)
            or page_count < 1
        ):
            raise ValueError("page_count must be a positive integer or None.")

        text = raw_text.strip()
        issues: List[ImprovementIssue] = []

        if not text and not structured_data:
            issues.append(
                self._make_issue(
                    "CRIT_EMPTY_RESUME",
                    "General",
                    "High",
                    "Resume text is empty or unreadable.",
                    "No resume content is available for analysis.",
                    "Upload a valid text-based PDF or DOCX resume.",
                )
            )
            return self._build_report(issues)

        lower_text = text.lower()
        word_count = len(text.split())

        # ---------------------------------------------------------
        # 1. ACADEMIC INFORMATION
        # ---------------------------------------------------------

        has_cgpa = bool(
            self.cgpa_pattern.search(text)
            or self.percentage_pattern.search(text)
        )
        has_degree = bool(self.degree_pattern.search(text))
        has_graduation_year = bool(
            self.graduation_year_pattern.search(text)
        )

        has_education = (
            self._has_section_heading(text, "education")
            or self._has_section_data(structured_data, "education")
        )

        if has_education and not has_cgpa:
            issues.append(
                self._make_issue(
                    "HIGH_MISSING_CGPA",
                    "Academics",
                    "High",
                    "Academic score (CGPA or percentage) was not detected.",
                    "Academic scores are commonly used for placement eligibility cut-offs.",
                    "Add your current CGPA or aggregate percentage in the Education section.",
                )
            )

        if has_education and not has_degree:
            issues.append(
                self._make_issue(
                    "HIGH_MISSING_DEGREE",
                    "Academics",
                    "High",
                    "Degree program or qualification was not clearly detected.",
                    "Recruiters need to identify the candidate's academic qualification.",
                    "Mention your degree, such as B.Tech, B.E., MCA, or M.Tech.",
                )
            )

        if has_education and not has_graduation_year:
            issues.append(
                self._make_issue(
                    "HIGH_MISSING_GRAD_YEAR",
                    "Academics",
                    "High",
                    "Expected graduation or batch year was not detected.",
                    "Placement opportunities may be restricted to specific graduating batches.",
                    "Add your expected graduation year or study duration in the Education section.",
                )
            )

        # ---------------------------------------------------------
        # 2. CONTACT INFORMATION
        # ---------------------------------------------------------

        has_email = bool(self.email_pattern.search(text))
        has_institutional_email = bool(
            self.institutional_email_pattern.search(text)
        )
        has_phone = bool(self.phone_pattern.search(text))
        has_linkedin = bool(self.linkedin_pattern.search(text))
        has_github = bool(self.github_pattern.search(text))

        if text and not has_email:
            issues.append(
                self._make_issue(
                    "HIGH_MISSING_EMAIL",
                    "Contact Information",
                    "High",
                    "No email address was detected.",
                    "Recruiters need an email address to contact candidates.",
                    "Add a professional email address in the resume header.",
                )
            )
        elif has_email and not has_institutional_email:
            issues.append(
                self._make_issue(
                    "HIGH_MISSING_INSTITUTIONAL_EMAIL",
                    "Contact Information",
                    "High",
                    "Institutional email address was not detected.",
                    "An institutional address can help verify student enrollment during campus placements.",
                    "Consider including your official college email address if required by your placement cell.",
                )
            )

        if text and not has_phone:
            issues.append(
                self._make_issue(
                    "HIGH_MISSING_PHONE",
                    "Contact Information",
                    "High",
                    "Contact phone number was not detected.",
                    "Recruiters may need a phone number for interview coordination.",
                    "Add a reachable mobile number with the appropriate country code.",
                )
            )

        if text and not has_linkedin:
            issues.append(
                self._make_issue(
                    "MED_MISSING_LINKEDIN",
                    "Contact Information",
                    "Medium",
                    "LinkedIn profile URL was not detected.",
                    "A professional profile can help recruiters review your background.",
                    "Add your LinkedIn profile URL if you maintain a professional profile.",
                )
            )

        if text and not has_github:
            issues.append(
                self._make_issue(
                    "MED_MISSING_GITHUB",
                    "Projects",
                    "Medium",
                    "GitHub profile or repository link was not detected.",
                    "A repository link can help technical recruiters inspect project work.",
                    "Add relevant GitHub profile or project repository links.",
                )
            )

        # ---------------------------------------------------------
        # 3. CORE RESUME SECTIONS
        # ---------------------------------------------------------

        for section in ("education", "skills", "projects", "experience"):
            section_exists = (
                self._has_section_heading(text, section)
                or self._has_section_data(structured_data, section)
            )

            # Experience is not compulsory for every fresher.
            if section == "experience":
                continue

            if text and not section_exists:
                issues.append(
                    self._make_issue(
                        f"HIGH_MISSING_SECTION_{section.upper()}",
                        section.capitalize(),
                        "High",
                        f"The {section.capitalize()} section was not detected.",
                        f"A clearly labeled {section} section helps recruiters and resume parsers locate relevant information.",
                        f"Add a clearly labeled '{section.capitalize()}' section containing relevant information.",
                    )
                )

        # ---------------------------------------------------------
        # 4. ACTION VERBS AND MEASURABLE ACHIEVEMENTS
        # ---------------------------------------------------------

        tokens = re.findall(r"\b[a-zA-Z]{3,}\b", lower_text)
        found_strong_verbs = {
            token for token in tokens if token in self.strong_verbs
        }

        weak_verbs_found = [
            verb
            for verb in self.weak_verbs
            if re.search(r"\b" + re.escape(verb) + r"\b", lower_text)
        ]

        metrics_found = self.metric_pattern.findall(text)

        has_project_or_experience = (
            self._has_section_heading(text, "projects")
            or self._has_section_heading(text, "experience")
            or self._has_section_data(structured_data, "projects")
            or self._has_section_data(structured_data, "experience")
        )

        if has_project_or_experience and len(found_strong_verbs) < 5:
            issues.append(
                self._make_issue(
                    "MED_LOW_ACTION_VERBS",
                    "Projects & Experience",
                    "Medium",
                    f"Limited strong action verbs detected ({len(found_strong_verbs)} unique verbs found).",
                    "Action verbs help communicate ownership and describe contributions clearly.",
                    "Begin project and experience bullet points with specific verbs such as Developed, Designed, Implemented, or Optimized.",
                )
            )

        if has_project_or_experience and weak_verbs_found:
            issues.append(
                self._make_issue(
                    "LOW_WEAK_VERBS_USED",
                    "Projects & Experience",
                    "Low",
                    f"Weak or passive phrases detected: {', '.join(weak_verbs_found[:3])}.",
                    "Vague phrases can make individual contributions difficult to understand.",
                    "Replace vague phrases with precise descriptions of what you personally built, improved, tested, or delivered.",
                )
            )

        if has_project_or_experience and not metrics_found:
            issues.append(
                self._make_issue(
                    "MED_NO_QUANTIFIABLE_METRICS",
                    "Projects & Experience",
                    "Medium",
                    "No measurable results or quantifiable metrics were detected.",
                    "Numbers and measurable outcomes can make project achievements more concrete.",
                    "Where accurate, include results such as response-time improvements, number of users, records processed, or test coverage.",
                )
            )

        # ---------------------------------------------------------
        # 5. RESUME LENGTH AND PRESENTATION
        # ---------------------------------------------------------

        if text and word_count < 350:
            issues.append(
                self._make_issue(
                    "MED_RESUME_TOO_BRIEF",
                    "Formatting",
                    "Medium",
                    f"Resume content is brief ({word_count} words).",
                    "A very short resume may not provide enough detail about academic work, skills, and projects.",
                    "Consider adding relevant project descriptions, technical skills, coursework, and achievements without adding filler.",
                )
            )
        elif word_count > 800:
            issues.append(
                self._make_issue(
                    "LOW_RESUME_TOO_VERBOSE",
                    "Formatting",
                    "Low",
                    f"Resume contains a large amount of text ({word_count} words).",
                    "Excessive content can make important information harder to scan.",
                    "Remove repetition and keep descriptions concise and relevant.",
                )
            )

        if page_count is not None and page_count > 2:
            issues.append(
                self._make_issue(
                    "MED_EXCEEDS_PAGE_LIMIT",
                    "Formatting",
                    "Medium",
                    f"Resume exceeds two pages ({page_count} pages detected).",
                    "A concise resume can make important qualifications easier to review.",
                    "Review repeated content and shorten descriptions where appropriate.",
                )
            )

        return self._build_report(issues)

    def _build_report(
        self,
        issues: List[ImprovementIssue],
    ) -> ImprovementReport:
        """Sort issues and calculate the priority breakdown."""

        issues.sort(
            key=lambda item: self.PRIORITY_ORDER.get(item.priority, 4)
        )

        breakdown = {
            "High": sum(1 for item in issues if item.priority == "High"),
            "Medium": sum(1 for item in issues if item.priority == "Medium"),
            "Low": sum(1 for item in issues if item.priority == "Low"),
        }

        return ImprovementReport(
            total_issues=len(issues),
            priority_breakdown=breakdown,
            improvement_areas=issues,
        )
