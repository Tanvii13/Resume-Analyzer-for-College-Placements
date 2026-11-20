"""
Job Description Processing and Structured Extraction Engine.

Sprint 4 Module A (Job Matching).

Parses raw, unstructured, noisy, or semi-formatted job descriptions into a
validated `ParsedJobDescription` schema containing:
1. Job title
2. Company name
3. Job type (full_time, internship, part_time, contract, unknown)
4. Experience requirements (min, max, fresher eligible)
5. Required technical skills (symbol-safe, taxonomy-validated, deduplicated)
6. Preferred technical skills (distinguished from required skills)
7. Soft skills
8. Educational qualifications (degrees, levels, fields of study, batches)
9. Responsibilities
10. Placement eligibility requirements (CGPA/CPI, percentage, batches, branches, backlogs)
11. Location and workplace type (remote, hybrid, on-site)
12. Other relevant job requirements (stipend/salary, bond, selection process)

Deterministic, local NLP techniques only. No external LLMs or network APIs.
"""

import re
import time
from typing import Dict, List, Optional, Set, Tuple

from app.nlp.extractors.education import _degree_patterns
from app.nlp.extractors.skills import SkillExtractor
from app.nlp.job_matching.schemas import (
    JOB_PARSER_VERSION,
    EducationRequirement,
    EligibilityCriteria,
    ExperienceRequirement,
    JobParsingMetadata,
    JobSkillRequirement,
    JobType,
    LocationRequirement,
    OtherJobRequirements,
    ParsedJobDescription,
    WorkplaceType,
)
from app.nlp.preprocessing import is_bullet, normalize_text, split_bullet
from app.nlp.schemas import ConfidenceLevel
from app.nlp.taxonomy import load_degrees

# ---------------------------------------------------------------------------
# Section Heading Recognition Patterns
# ---------------------------------------------------------------------------

SEC_ABOUT_COMPANY = "ABOUT_COMPANY"
SEC_ROLE_OVERVIEW = "ROLE_OVERVIEW"
SEC_RESPONSIBILITIES = "RESPONSIBILITIES"
SEC_REQUIRED_QUALIFICATIONS = "REQUIRED_QUALIFICATIONS"
SEC_PREFERRED_QUALIFICATIONS = "PREFERRED_QUALIFICATIONS"
SEC_ELIGIBILITY = "ELIGIBILITY"
SEC_EDUCATION = "EDUCATION"
SEC_EXPERIENCE = "EXPERIENCE"
SEC_LOCATION = "LOCATION"
SEC_COMPENSATION = "COMPENSATION"
SEC_SELECTION_PROCESS = "SELECTION_PROCESS"
SEC_OTHER = "OTHER"
SEC_HEADER = "HEADER"
SEC_GENERAL = "GENERAL"

_HEADING_KEYWORDS: List[Tuple[str, str]] = [
    # Preferred qualifications (check before general requirements)
    (r"\b(?:preferred\s+(?:technical\s+)?(?:qualifications?|skills?|requirements?)|nice\s+to\s+have|good\s+to\s+have|desired\s+(?:technical\s+)?(?:qualifications?|skills?|requirements?)|bonus\s+(?:points?|skills?)|plus\s+points?|what\s+would\s+be\s+great|optional\s+skills?)\b", SEC_PREFERRED_QUALIFICATIONS),
    # Required qualifications
    (r"\b(?:required\s+(?:technical\s+)?(?:skills?|qualifications?|requirements?)|basic\s+qualifications?|minimum\s+qualifications?|must\s+have|mandatory\s+(?:skills?|requirements?)|what\s+you\s+need|what\s+we(?:'re|\s+are)\s+looking\s+for|technical\s+(?:requirements?|skills?|competencies)|core\s+skills?|key\s+requirements?|requirements?)\b", SEC_REQUIRED_QUALIFICATIONS),
    # Soft Skills
    (r"\b(?:soft\s+skills?|behavioral\s+skills?|interpersonal\s+skills?|people\s+skills?)\b", SEC_OTHER),
    # Responsibilities
    (r"\b(?:responsibilit(?:ies|y)|what\s+you(?:'ll|\s+will)\s+do|key\s+deliverables|duties|tasks|day\s+to\s+day|what\s+you'll\s+be\s+doing|roles?\s+and\s+responsibilities?|role\s+summary|job\s+duties)\b", SEC_RESPONSIBILITIES),
    # Eligibility (college placement specific)
    (r"\b(?:eligibility(?:\s+criteria)?|academic\s+criteria|who\s+can\s+apply|campus\s+criteria|placement\s+criteria|candidate\s+criteria)\b", SEC_ELIGIBILITY),
    # Education
    (r"\b(?:education(?:al)?(?:\s+qualifications?|\s+requirements?)?|academic\s+qualifications?|educational\s+background)\b", SEC_EDUCATION),
    # Experience
    (r"\b(?:experience(?:\s+required|\s+level)?|work\s+experience|years\s+of\s+experience)\b", SEC_EXPERIENCE),
    # About Company
    (r"\b(?:about\s+(?:the\s+)?company|about\s+us|company\s+overview|who\s+we\s+are|our\s+story|company\s+profile)\b", SEC_ABOUT_COMPANY),
    # Overview
    (r"\b(?:job\s+summary|about\s+the\s+role|position\s+overview|role\s+overview|overview)\b", SEC_ROLE_OVERVIEW),
    # Location
    (r"\b(?:work\s+location|job\s+location|work\s+mode|location\s+and\s+work\s+model|location)\b", SEC_LOCATION),
    # Compensation
    (r"\b(?:compensation|salary|stipend|package|ctc|perks\s+and\s+benefits|remuneration)\b", SEC_COMPENSATION),
    # Selection process
    (r"\b(?:selection\s+process|hiring\s+process|interview\s+rounds?|interview\s+process|recruitment\s+process)\b", SEC_SELECTION_PROCESS),
    # Other
    (r"\b(?:other\s+details?|additional\s+info(?:rmation)?|terms\s+(?:and|&)\s+conditions|bond(?:\s+details)?)\b", SEC_OTHER),
]

_COMPILED_HEADING_PATTERNS = [(re.compile(pat, re.I), sec) for pat, sec in _HEADING_KEYWORDS]

# ---------------------------------------------------------------------------
# Preference Markers within Lines
# ---------------------------------------------------------------------------

_PREFERRED_LINE_CUES = re.compile(
    r"\b(?:nice\s+to\s+have|good\s+to\s+have|preferred|preference|desirable|bonus|plus|optional|advantageous|would\s+be\s+(?:great|a\s+plus)|is\s+a\s+plus|added\s+advantage|helpful)\b",
    re.IGNORECASE,
)

_REQUIRED_LINE_CUES = re.compile(
    r"\b(?:must\s+have|required|mandatory|essential|necessary|proficiency\s+in|strong\s+knowledge\s+of|hands-on\s+experience\s+with|must\s+be\s+proficient|expertise\s+in|should\s+have)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Known Title / Company / Location Tokens
# ---------------------------------------------------------------------------

_TITLE_WORDS = {
    "intern", "internship", "engineer", "developer", "analyst", "assistant", "associate",
    "manager", "lead", "researcher", "consultant", "designer", "scientist", "trainee",
    "fellow", "architect", "specialist", "officer", "executive", "tester", "administrator",
    "sde", "swe", "mts", "programmer", "qa", "devops", "full stack", "full-stack",
    "backend", "back-end", "frontend", "front-end", "cloud architect", "data engineer",
    "get", "graduate engineer trainee", "systems engineer",
}

_COMPANY_SUFFIX_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9\s&.,'-]+?\s+(?:Pvt\.?\s*Ltd\.?|Private\s+Limited|Ltd\.?|Limited|Inc\.?|LLC|Corporation|Corp\.?|Technologies|Solutions|Systems|Labs|Infotech))\b"
)

_LOCATION_INDIAN_CITIES = [
    "Bengaluru", "Bangalore", "Hyderabad", "Pune", "Mumbai", "Delhi", "New Delhi",
    "Noida", "Gurugram", "Gurgaon", "Ahmedabad", "Gandhinagar", "Chennai", "Kolkata",
    "Kochi", "Indore", "Jaipur", "Chandigarh", "Vadodara", "Surat", "Coimbatore",
]

_LOCATION_GLOBAL_CITIES = [
    "San Francisco", "New York", "Seattle", "Austin", "Boston", "Chicago", "London",
    "Singapore", "Dublin", "Toronto", "Berlin", "Tokyo", "Sydney",
]

_LOCATION_CITIES = sorted(_LOCATION_INDIAN_CITIES + _LOCATION_GLOBAL_CITIES, key=len, reverse=True)
_LOCATION_CITIES_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in _LOCATION_CITIES) + r")\b", re.I)

# ---------------------------------------------------------------------------
# Experience, Eligibility, Compensation Regexes
# ---------------------------------------------------------------------------

_EXP_RANGE_RE = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)(?:\s+(?:of\s+)?(?:relevant\s+)?experience)?",
    re.IGNORECASE,
)
_EXP_MIN_RE = re.compile(
    r"(?:(?:minimum|min\.?|at\s+least)\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)|(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?))(?:\s+(?:of\s+)?(?:relevant\s+)?experience)?",
    re.IGNORECASE,
)
_EXP_MAX_RE = re.compile(
    r"(?:maximum|max\.?|up\s+to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)(?:\s+(?:of\s+)?(?:relevant\s+)?experience)?",
    re.IGNORECASE,
)
_EXP_SINGLE_RE = re.compile(
    r"(?<![\d.])(\d+(?:\.\d+)?)\s*(?:years?|yrs?)(?:\s+(?:of\s+)?(?:relevant\s+)?experience)",
    re.IGNORECASE,
)
_FRESHER_RE = re.compile(
    r"\b(?:fresher(?:s)?|fresh\s+graduates?|entry\s+level|0\s*years?|no\s+(?:prior\s+)?experience(?:\s+required|\s+needed)?|open\s+to\s+freshers|campus\s+(?:placement|hiring|recruitment))\b",
    re.IGNORECASE,
)

_CGPA_RE = re.compile(
    r"(?:(?:minimum|min\.?|at\s+least|aggregate)?\s*"
    r"(?:c\.?g\.?p\.?a|c\.?p\.?i|g\.?p\.?a)"
    r"(?:\s+(?:criteria|cutoff|cut-off|score|requirement|threshold|aggregate))?\s*"
    r"(?:of|is|was|[:\-–>=≥])*\s*"
    r"(\d{1,2}(?:\.\d{1,2})?)"
    r"(?:\s*(?:/|out\s+of)\s*(\d{1,2}(?:\.\d+)?))?|"
    r"(?<![\d.])(\d{1,2}(?:\.\d{1,2})?)(?:\s*(?:/|out\s+of)\s*(\d{1,2}(?:\.\d+)?))?\s*(?:c\.?g\.?p\.?a|c\.?p\.?i|g\.?p\.?a)\b)",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(
    r"(?<![\d.])(\d{2,3}(?:\.\d{1,2})?)\s*(?:%|percent(?:age)?\b)|percent(?:age)?\s*[:=\-–]?\s*(\d{2,3}(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
_BATCH_RE = re.compile(r"\b(202[0-9])\b")
_BACKLOG_RE = re.compile(
    r"(no\s+(?:active|current|standing|dead|live)?\s*backlogs?|maximum\s+\d+\s+(?:active\s+|standing\s+)?backlogs?(?:\s+permitted|\s+allowed)?|up\s+to\s+\d+\s+backlogs?|0\s+active\s+backlogs?)",
    re.IGNORECASE,
)
_BRANCH_RE = re.compile(
    r"\b(all\s+branches|all\s+engineering\s+branches|circuit\s+branches|cse|it|ict|ece|ee|me|civil|ai&ds|aiml|computer\s+science|information\s+technology|electronics)\b",
    re.IGNORECASE,
)

_SALARY_RE = re.compile(
    r"(\b\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?\s*(?:lpa|ctc|lac|lakhs?)\b|"
    r"\b(?:₹|rs\.?)\s*[\d,]+(?:\s*-\s*[\d,]+)?\s*(?:/|-)?\s*(?:month|pm|per\s+month)?|"
    r"\b\d{1,2}[kK]\s*(?:/|-)?\s*(?:month|pm)?|"
    r"\b(?:stipend|salary|ctc|package)\s*[:\-–]\s*[^\n;]+)",
    re.IGNORECASE,
)
_BOND_RE = re.compile(
    r"(\d+(?:\.\d+)?\s*(?:years?|yrs?|months?)\s*(?:service\s+agreement|bond)|service\s+agreement\s*(?:of\s*)?\d+\s*(?:years?|months?)|no\s+bond|no\s+service\s+agreement)",
    re.IGNORECASE,
)

_FIELDS_OF_STUDY = [
    "Computer Science and Engineering", "Computer Science & Engineering",
    "Information and Communication Technology", "Information & Communication Technology",
    "Electronics and Communication Engineering", "Electronics & Communication Engineering",
    "Electrical and Electronics Engineering", "Artificial Intelligence and Machine Learning",
    "Artificial Intelligence and Data Science", "Mathematics and Computing",
    "Computer Science", "Computer Engineering", "Information Technology",
    "Electrical Engineering", "Electronics Engineering", "Mechanical Engineering",
    "Civil Engineering", "Data Science", "Artificial Intelligence",
    "Mathematics", "Physics", "Statistics", "Software Engineering",
    "ICT", "CSE", "CS", "IT", "ECE", "EE", "ME", "EEE", "AIML", "AI&DS",
]

_UPPER_ONLY_FIELDS = {"ICT", "CSE", "CS", "IT", "ECE", "EE", "ME", "EEE", "AIML", "AI&DS"}


# ---------------------------------------------------------------------------
# Main Job Description Parser
# ---------------------------------------------------------------------------

class JobDescriptionParser:
    """
    Deterministic NLP parser for campus placement and industry Job Descriptions.

    Converts raw JD text into a validated `ParsedJobDescription`.
    """

    def __init__(self, skill_extractor: Optional[SkillExtractor] = None):
        """
        Initialize the parser.

        Reuses the precompiled `SkillExtractor` patterns for high performance.
        """
        self.skill_extractor = skill_extractor or SkillExtractor()
        self.degrees_data = load_degrees()

    def parse(self, text: str, job_id: Optional[str] = None) -> ParsedJobDescription:
        """
        Parse raw job description text into a structured, validated ParsedJobDescription.

        Args:
            text: Raw job description text.
            job_id: Optional identifier for the job posting.

        Returns:
            Validated ParsedJobDescription instance.
        """
        start_time = time.perf_counter()

        if not text or not text.strip():
            return ParsedJobDescription(
                job_id=job_id,
                title=None,
                company_name=None,
                job_type=JobType.UNKNOWN,
                metadata=JobParsingMetadata(
                    processing_time_ms=0.0,
                    raw_text_length=0,
                    identified_sections=[],
                    missing_critical_sections=["job_title", "required_technical_skills", "responsibilities"],
                    warnings=["Empty job description provided."],
                    overall_confidence=0.0,
                    confidence_level=ConfidenceLevel.LOW,
                ),
                parser_version=JOB_PARSER_VERSION,
            )

        normalized_text = normalize_text(text)
        sections = self._segment_into_sections(normalized_text)
        identified_section_names = [s for s in sections.keys() if s not in (SEC_HEADER, SEC_GENERAL)]

        warnings: List[str] = []

        # 1. Job Title
        title = self._extract_job_title(sections, normalized_text)

        # 2. Company Name
        company_name = self._extract_company_name(sections, normalized_text)

        # 3. Job Type
        job_type = self._extract_job_type(sections, title, normalized_text)

        # 4. Experience Requirement
        experience = self._extract_experience(sections, job_type, normalized_text)

        # 5, 6, 7. Skills (Required, Preferred, Soft)
        required_tech, preferred_tech, soft_skills = self._extract_skills(sections, company_name)

        # 8. Education Requirement
        education = self._extract_education(sections, normalized_text)

        # 9. Responsibilities
        responsibilities = self._extract_responsibilities(sections)

        # 10. Placement Eligibility Criteria
        eligibility = self._extract_eligibility(sections, normalized_text)

        # 11. Location Requirement
        location = self._extract_location(sections, normalized_text)

        # 12. Other Requirements
        other_requirements = self._extract_other_requirements(sections, normalized_text)

        # Check missing critical sections
        missing_critical: List[str] = []
        if not title:
            missing_critical.append("job_title")
        if not required_tech:
            missing_critical.append("required_technical_skills")
        if not responsibilities:
            missing_critical.append("responsibilities")

        # Confidence calculation
        confidence = 1.0
        if not title:
            confidence -= 0.20
        if not required_tech and not preferred_tech:
            confidence -= 0.35
        if not responsibilities:
            confidence -= 0.15
        if not education.degrees and not education.fields_of_study:
            confidence -= 0.10
        confidence = max(0.20, min(1.0, round(confidence, 2)))

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        metadata = JobParsingMetadata(
            processing_time_ms=round(elapsed_ms, 2),
            raw_text_length=len(normalized_text),
            identified_sections=identified_section_names,
            missing_critical_sections=missing_critical,
            warnings=warnings,
            overall_confidence=confidence,
            confidence_level=ConfidenceLevel.from_score(confidence),
        )

        return ParsedJobDescription(
            job_id=job_id,
            title=title,
            company_name=company_name,
            job_type=job_type,
            location=location,
            experience=experience,
            required_technical_skills=required_tech,
            preferred_technical_skills=preferred_tech,
            soft_skills=soft_skills,
            education=education,
            eligibility=eligibility,
            responsibilities=responsibilities,
            other_requirements=other_requirements,
            metadata=metadata,
            parser_version=JOB_PARSER_VERSION,
        )

    def parse_multiple(self, texts: List[str]) -> List[ParsedJobDescription]:
        """
        Parse multiple job descriptions independently without state leakage.
        """
        return [self.parse(t) for t in texts]

    _ATTRIBUTE_PREFIXES = {
        "job title", "title", "role", "position", "designation",
        "company", "company name", "organization", "employer",
        "location", "job location", "work location", "work mode",
        "job type", "work type", "employment type",
        "ctc", "salary", "stipend", "package", "remuneration",
        "bond", "service agreement", "batch", "batches",
        "cpi", "cgpa", "gpa", "percentage", "backlogs",
    }

    # -----------------------------------------------------------------------
    # Section Segmentation
    # -----------------------------------------------------------------------

    def _segment_into_sections(self, text: str) -> Dict[str, List[str]]:
        """
        Segment text into logical sections based on headings and layout.
        """
        lines = [line.strip() for line in text.split("\n")]
        sections: Dict[str, List[str]] = {}
        current_sec = SEC_HEADER

        for line in lines:
            if not line:
                continue

            # Check if line is a single-line key-value attribute
            if ":" in line:
                head_part, _, val_part = line.partition(":")
                if head_part.strip().lower() in self._ATTRIBUTE_PREFIXES and val_part.strip():
                    sections.setdefault(current_sec, []).append(line)
                    continue

            heading_match, inline_content = self._classify_heading(line)
            if heading_match:
                current_sec = heading_match
                sections.setdefault(current_sec, [])
                if inline_content:
                    sections[current_sec].append(inline_content)
            else:
                sections.setdefault(current_sec, []).append(line)

        return sections

    def _classify_heading(self, line: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Determine if a line is a section heading, returning (section_name, inline_content).
        """
        stripped = line.strip()
        head_part = stripped
        inline_content = None

        if ":" in stripped:
            h, _, c = stripped.partition(":")
            if c.strip():
                head_part = h.strip()
                inline_content = c.strip()
            else:
                head_part = h.strip()

        clean = head_part.rstrip(":#=-–_")
        lower = clean.lower()

        words = clean.split()
        is_short = len(words) <= 5 and len(clean) <= 45

        is_explicit_heading = (
            stripped.endswith(":") or
            stripped.startswith(("#", "###", "##", "==")) or
            (clean.isupper() and len(words) <= 4)
        )

        if not (is_short or is_explicit_heading):
            return None, None

        for pattern, sec in _COMPILED_HEADING_PATTERNS:
            if pattern.search(lower):
                return sec, inline_content

        return None, None

    # -----------------------------------------------------------------------
    # 1. Job Title Extraction
    # -----------------------------------------------------------------------

    def _extract_job_title(self, sections: Dict[str, List[str]], raw_text: str) -> Optional[str]:
        """
        Extract job title from labeled line, header lines, or role overview.
        """
        title_label_re = re.compile(
            r"^\s*(?:job\s+title|role|position|designation|profile)\s*[:\-–]\s*(.+)$",
            re.IGNORECASE,
        )

        # Check explicit label first
        for lines in sections.values():
            for line in lines:
                m = title_label_re.match(line)
                if m:
                    cand = self._clean_title(m.group(1))
                    if cand:
                        return cand

        # Check header section (first few lines)
        header_lines = sections.get(SEC_HEADER, [])[:5]
        for line in header_lines:
            clean = line.strip().rstrip(":")
            if not clean:
                continue
            # Avoid picking up company or location lines
            if re.match(r"^(?:company|location|experience|salary|batch|eligibility)\s*[:\-–]", clean, re.I):
                continue
            lower = clean.lower()
            if any(tw in lower for tw in _TITLE_WORDS) and len(clean) <= 75 and len(clean.split()) <= 8:
                return self._clean_title(clean)

        # Check prose intro (e.g. "Looking for a Backend Developer to join...")
        intro_re = re.compile(
            r"(?:looking\s+for|seeking|hiring|opening\s+for)\s+(?:an?|experienced)?\s+([A-Za-z0-9\s/&.-]+?)(?:\s+(?:to\s+join|who|with|for\s+our|\.|$))",
            re.IGNORECASE,
        )
        for line in header_lines + sections.get(SEC_ROLE_OVERVIEW, []):
            m = intro_re.search(line)
            if m:
                cand = self._clean_title(m.group(1))
                if cand and any(tw in cand.lower() for tw in _TITLE_WORDS):
                    return cand

        # Fallback: scan lines or first chunk for role phrase (e.g. "developer needed", "python developer")
        role_search_re = re.compile(
            r"\b([A-Za-z/&-]+(?:\s+[A-Za-z/&-]+){0,2}\s+(?:developer|engineer|intern(?:ship)?|analyst|architect|scientist|specialist|trainee))\b",
            re.IGNORECASE,
        )
        for chunk in header_lines + [raw_text[:250]]:
            for sub in re.split(r"[.!?…\n]+", chunk):
                m = role_search_re.search(sub)
                if m:
                    cand = self._clean_title(m.group(1))
                    if cand and len(cand.split()) <= 4:
                        return cand.title()

        return None

    def _clean_title(self, raw: str) -> Optional[str]:
        """Clean and sanitize extracted title string."""
        cleaned = re.sub(r"[\t\r\n]+", " ", raw).strip()
        # Remove trailing parentheses with location or job type
        cleaned = re.sub(r"\s*\((?:remote|hybrid|full[\s-]?time|internship|bangalore|pune|mumbai|delhi|india)[^)]*\)", "", cleaned, flags=re.I).strip()
        cleaned = re.sub(r"^[–\-\*•\s]+|[–\-\*•\s:]+$", "", cleaned).strip()
        return cleaned if (cleaned and len(cleaned) <= 80) else None

    # -----------------------------------------------------------------------
    # 2. Company Name Extraction
    # -----------------------------------------------------------------------

    def _extract_company_name(self, sections: Dict[str, List[str]], raw_text: str) -> Optional[str]:
        """
        Extract company name from label, About section, or intro phrases.
        """
        company_label_re = re.compile(
            r"^\s*(?:company(?:\s+name)?|organization|employer|client)\s*[:\-–]\s*(.+)$",
            re.IGNORECASE,
        )

        for lines in sections.values():
            for line in lines:
                m = company_label_re.match(line)
                if m:
                    cand = self._clean_company(m.group(1))
                    if cand:
                        return cand

        # Check About Company heading / text
        about_lines = sections.get(SEC_ABOUT_COMPANY, [])
        for line in about_lines[:3]:
            m = re.search(r"^\s*([A-Z0-9][A-Za-z0-9&.,'-]+(?:\s+[A-Z0-9][A-Za-z0-9&.,'-]+)*?)\s+(?:is|was|has\s+been)\s+(?:a|an|the)\b", line)
            if m:
                cand = self._clean_company(m.group(1))
                if cand:
                    return cand

        # Check for Company Suffixes (Pvt Ltd, LLC, Inc) in header / about lines
        for line in sections.get(SEC_HEADER, []) + about_lines:
            m = _COMPANY_SUFFIX_RE.search(line)
            if m:
                cand = self._clean_company(m.group(1))
                if cand:
                    return cand

        # Check "At <Company>, we..." or "Join <Company>"
        join_re = re.compile(
            r"\b(?:welcome\s+to|at|join)\s+([A-Z][A-Za-z0-9&.,'-]+(?:\s+[A-Z][A-Za-z0-9&.,'-]+)*?)(?:,\s*we\b|\s+we\s+are\b|\s+team\b)",
            re.IGNORECASE,
        )
        for line in sections.get(SEC_HEADER, []) + sections.get(SEC_ROLE_OVERVIEW, []) + about_lines:
            m = join_re.search(line)
            if m:
                cand = self._clean_company(m.group(1))
                if cand:
                    return cand

        # Fallback: company domain from careers email
        email_re = re.compile(r"[\w.-]+@([a-zA-Z0-9-]+)\.(?:com|org|net|co|in|io)")
        for line in raw_text.splitlines():
            m = email_re.search(line)
            if m:
                domain = m.group(1).lower()
                if domain not in {"gmail", "yahoo", "outlook", "hotmail", "icloud"}:
                    return domain.capitalize()

        return None

    def _clean_company(self, raw: str) -> Optional[str]:
        cleaned = re.sub(r"[\t\r\n]+", " ", raw).strip()
        cleaned = re.sub(r"^[–\-\*•\s]+|[–\-\*•\s:]+$", "", cleaned).strip()
        return cleaned if (cleaned and len(cleaned) <= 60) else None

    # -----------------------------------------------------------------------
    # 3. Job Type Extraction
    # -----------------------------------------------------------------------

    def _extract_job_type(
        self,
        sections: Dict[str, List[str]],
        title: Optional[str],
        raw_text: str,
    ) -> JobType:
        """Extract employment type: internship, full-time, part-time, or contract."""
        job_type_label_re = re.compile(
            r"^\s*(?:job\s+type|employment\s+type|nature\s+of\s+job|work\s+type)\s*[:\-–]\s*(.+)$",
            re.IGNORECASE,
        )

        for lines in sections.values():
            for line in lines:
                m = job_type_label_re.match(line)
                if m:
                    cand = m.group(1).lower()
                    if "intern" in cand:
                        return JobType.INTERNSHIP
                    if "full" in cand or "fte" in cand:
                        return JobType.FULL_TIME
                    if "part" in cand:
                        return JobType.PART_TIME
                    if "contract" in cand or "freelance" in cand:
                        return JobType.CONTRACT

        # Check title
        if title:
            title_lower = title.lower()
            if "intern" in title_lower or "trainee" in title_lower:
                return JobType.INTERNSHIP

        # Scan text for prominent keywords
        text_lower = raw_text.lower()
        if re.search(r"\b(?:internship|intern|summer\s+intern|winter\s+intern|industrial\s+training)\b", text_lower):
            return JobType.INTERNSHIP
        if re.search(r"\b(?:full[\s-]?time|fte|permanent\s+role)\b", text_lower):
            return JobType.FULL_TIME
        if re.search(r"\b(?:part[\s-]?time)\b", text_lower):
            return JobType.PART_TIME
        if re.search(r"\b(?:contract(?:ual)?|freelance|temporary\s+position)\b", text_lower):
            return JobType.CONTRACT

        return JobType.UNKNOWN

    # -----------------------------------------------------------------------
    # 4. Experience Requirement Extraction
    # -----------------------------------------------------------------------

    def _extract_experience(
        self,
        sections: Dict[str, List[str]],
        job_type: JobType,
        raw_text: str,
    ) -> ExperienceRequirement:
        """Extract minimum, maximum years of experience and fresher eligibility."""
        min_years: Optional[float] = None
        max_years: Optional[float] = None
        evidence: Optional[str] = None
        raw_exp_text: Optional[str] = None

        fresher_found = bool(_FRESHER_RE.search(raw_text)) or (job_type == JobType.INTERNSHIP)

        # Prioritize EXPERIENCE and REQUIRED_QUALIFICATIONS sections
        target_lines = (
            sections.get(SEC_EXPERIENCE, []) +
            sections.get(SEC_REQUIRED_QUALIFICATIONS, []) +
            sections.get(SEC_ELIGIBILITY, []) +
            sections.get(SEC_HEADER, []) +
            sections.get(SEC_ROLE_OVERVIEW, [])
        )

        # Check for bounded ranges first across target lines
        for line in target_lines:
            m_range = _EXP_RANGE_RE.search(line)
            if m_range:
                min_years = float(m_range.group(1))
                max_years = float(m_range.group(2))
                evidence = line.strip()
                raw_exp_text = m_range.group(0)
                break

        # If no bounded range, check single/min/max patterns
        if min_years is None and max_years is None:
            for line in target_lines:
                m_max = _EXP_MAX_RE.search(line)
                if m_max:
                    min_years = 0.0
                    max_years = float(m_max.group(1))
                    evidence = line.strip()
                    raw_exp_text = m_max.group(0)
                    break

                m_min = _EXP_MIN_RE.search(line)
                if m_min:
                    min_years = float(m_min.group(1) or m_min.group(2))
                    max_years = None
                    evidence = line.strip()
                    raw_exp_text = m_min.group(0)
                    break

                m_single = _EXP_SINGLE_RE.search(line)
                if m_single:
                    min_years = float(m_single.group(1))
                    max_years = None
                    evidence = line.strip()
                    raw_exp_text = m_single.group(0)
                    break

        # Fallback to scanning whole text if not found in target sections
        if min_years is None and max_years is None:
            m_range = _EXP_RANGE_RE.search(raw_text)
            if m_range:
                min_years = float(m_range.group(1))
                max_years = float(m_range.group(2))
                raw_exp_text = m_range.group(0)
                evidence = raw_exp_text

        # Determine fresher eligibility
        is_fresher = fresher_found or (min_years is not None and min_years == 0.0)

        # If fresher is eligible and no min experience was explicitly given, default min=0.0
        if is_fresher and min_years is None:
            min_years = 0.0
            if max_years is None:
                max_years = 0.0
            if not evidence:
                evidence = "Freshers eligible / Internship"

        confidence = 1.0 if (min_years is not None or is_fresher) else 0.50

        return ExperienceRequirement(
            min_years=min_years,
            max_years=max_years,
            is_fresher_eligible=is_fresher,
            raw_text=raw_exp_text,
            evidence=evidence,
            confidence=confidence,
        )

    # -----------------------------------------------------------------------
    # 5, 6, 7. Skills Extraction (Required vs Preferred vs Soft Skills)
    # -----------------------------------------------------------------------

    def _extract_skills(
        self,
        sections: Dict[str, List[str]],
        company_name: Optional[str],
    ) -> Tuple[List[JobSkillRequirement], List[JobSkillRequirement], List[JobSkillRequirement]]:
        """
        Extract required technical skills, preferred technical skills, and soft skills.

        Distinguishes required vs preferred using both section context and clause markers.
        """
        required_tech_map: Dict[str, JobSkillRequirement] = {}
        preferred_tech_map: Dict[str, JobSkillRequirement] = {}
        soft_skills_map: Dict[str, JobSkillRequirement] = {}

        company_clean = company_name.lower() if company_name else None

        # Sections to inspect for skills (skip ABOUT_COMPANY and SELECTION_PROCESS)
        skill_sections = [
            (SEC_REQUIRED_QUALIFICATIONS, True),
            (SEC_PREFERRED_QUALIFICATIONS, False),
            (SEC_RESPONSIBILITIES, True),
            (SEC_ELIGIBILITY, True),
            (SEC_EDUCATION, True),
            (SEC_HEADER, True),
            (SEC_OTHER, True),
            (SEC_GENERAL, True),
            (SEC_ROLE_OVERVIEW, True),
        ]

        for sec_name, default_required in skill_sections:
            lines = sections.get(sec_name, [])
            for line in lines:
                # If header section, skip pure attribute lines
                if sec_name == SEC_HEADER and re.match(
                    r"^\s*(?:job\s+title|role|position|company|location|work\s+mode|salary|ctc|stipend)\s*[:\-–]",
                    line,
                    re.I,
                ):
                    continue

                # Mask URLs and emails to avoid false positives
                sanitized_line = re.sub(r"https?://\S+|www\.\S+|[\w.-]+@[\w.-]+", " ", line)

                # Split into clauses/sentences to allow inline preference switching
                clauses = self._split_clauses(sanitized_line)
                for clause in clauses:
                    is_req = self._determine_clause_requirement(clause, sec_name, default_required)
                    raw_skills = self.skill_extractor.extract_from_text(clause)

                    for skill in raw_skills:
                        c_name = skill.canonical_name

                        # Guard: filter out false positives
                        if not self._is_valid_jd_skill_match(c_name, skill.matched_text, clause, company_clean):
                            continue

                        evidence_text = clause.strip()

                        if skill.category == "Soft Skills":
                            if c_name not in soft_skills_map:
                                soft_skills_map[c_name] = JobSkillRequirement(
                                    canonical_name=c_name,
                                    matched_alias=skill.matched_text,
                                    category=skill.category,
                                    is_required=is_req,
                                    confidence=round(skill.confidence, 2),
                                    occurrences=1,
                                    evidence=evidence_text,
                                )
                            else:
                                soft_skills_map[c_name].occurrences += 1
                        else:
                            # Technical skill
                            if is_req:
                                if c_name in required_tech_map:
                                    required_tech_map[c_name].occurrences += 1
                                else:
                                    # If it was previously marked preferred, promote to required
                                    prev_occ = 0
                                    if c_name in preferred_tech_map:
                                        prev_occ = preferred_tech_map.pop(c_name).occurrences
                                    required_tech_map[c_name] = JobSkillRequirement(
                                        canonical_name=c_name,
                                        matched_alias=skill.matched_text,
                                        category=skill.category,
                                        is_required=True,
                                        confidence=round(skill.confidence, 2),
                                        occurrences=prev_occ + 1,
                                        evidence=evidence_text,
                                    )
                            else:
                                # Preferred skill
                                # If already in required, keep required
                                if c_name in required_tech_map:
                                    required_tech_map[c_name].occurrences += 1
                                elif c_name in preferred_tech_map:
                                    preferred_tech_map[c_name].occurrences += 1
                                else:
                                    preferred_tech_map[c_name] = JobSkillRequirement(
                                        canonical_name=c_name,
                                        matched_alias=skill.matched_text,
                                        category=skill.category,
                                        is_required=False,
                                        confidence=round(skill.confidence, 2),
                                        occurrences=1,
                                        evidence=evidence_text,
                                    )

        req_list = sorted(list(required_tech_map.values()), key=lambda s: (s.category, s.canonical_name))
        pref_list = sorted(list(preferred_tech_map.values()), key=lambda s: (s.category, s.canonical_name))
        soft_list = sorted(list(soft_skills_map.values()), key=lambda s: s.canonical_name)

        return req_list, pref_list, soft_list

    def _split_clauses(self, text: str) -> List[str]:
        """
        Split a line into clauses without breaking technical tokens (.NET, Node.js).
        """
        # Split on semicolon, newline, or period followed by whitespace and capital/bullet
        parts = re.split(r"(?:;\s*|\n+|\.\s+(?=[A-Z•\-\d]))", text)
        return [p.strip() for p in parts if p.strip()]

    def _determine_clause_requirement(self, clause: str, section_name: str, default_required: bool) -> bool:
        """
        Determine if skills in this clause are required or preferred.
        """
        if section_name == SEC_PREFERRED_QUALIFICATIONS:
            return False

        has_pref = bool(_PREFERRED_LINE_CUES.search(clause))
        has_req = bool(_REQUIRED_LINE_CUES.search(clause))

        if has_pref and not has_req:
            return False
        if has_req:
            return True

        return default_required

    def _is_valid_jd_skill_match(
        self,
        canonical_name: str,
        matched_text: str,
        clause: str,
        company_clean: Optional[str],
    ) -> bool:
        """
        Validate extracted skill to prevent English false positives or company names.
        """
        m_lower = matched_text.lower()

        # Check if matched token is company name (unless canonical tech skill)
        if company_clean and m_lower == company_clean:
            if canonical_name not in {"Oracle Database", "Microsoft Azure", "Amazon Web Services (AWS)"}:
                return False

        m = re.search(r"\b" + re.escape(matched_text) + r"\b", clause, re.I)
        if not m:
            return True

        start, end = m.span()
        after_text = clause[end:].lstrip()
        before_text = clause[:start].rstrip()

        first_after = re.sub(r'[^a-zA-Z0-9]', '', after_text.split()[0].lower()) if after_text.split() else ""
        last_before = re.sub(r'[^a-zA-Z0-9]', '', before_text.split()[-1].lower()) if before_text.split() else ""

        # 1. Next.js vs 'next'
        if canonical_name == "Next.js" and m_lower == "next":
            if clause[end:end+1] == "-":
                return False
            if first_after in {"generation", "gen", "step", "steps", "round", "rounds", "level", "year", "semester", "phase", "week", "month", "time"}:
                return False
            window = clause[max(0, start - 40):min(len(clause), end + 40)].lower()
            if not any(k in window for k in ["react", "vue", "frontend", "front-end", "node", "typescript", "javascript", "web", "tailwind"]):
                return False

        # 2. React vs 'react'
        if canonical_name == "React" and m_lower == "react":
            if first_after in {"to", "quickly", "under", "with", "appropriately", "effectively"}:
                return False
            if last_before in {"to", "can", "able", "ability"}:
                return False

        # 3. Spring Framework vs 'spring'
        if canonical_name == "Spring Framework" and m_lower == "spring":
            if first_after in {"2024", "2025", "2026", "2027", "break", "semester", "internship", "season", "session"}:
                return False
            window = clause[max(0, start - 40):min(len(clause), end + 40)].lower()
            if not any(k in window for k in ["boot", "framework", "java", "backend", "microservices", "mvc"]):
                return False

        # 4. Computer Vision vs 'cv' (Curriculum Vitae / Resume)
        if canonical_name == "Computer Vision" and m_lower == "cv":
            window = clause[max(0, start - 35):min(len(clause), end + 35)].lower()
            if any(k in window for k in ["send", "submit", "share", "email", "attach", "resume", "to hr", "your", "mail"]):
                return False
            if not any(k in window for k in ["vision", "image", "nlp", "ml", "dl", "deep learning", "machine learning", "opencv", "pytorch", "tensorflow", "ai"]):
                return False

        # 5. Bootstrap vs 'bs' (Bachelor of Science / Degree)
        if canonical_name == "Bootstrap" and m_lower == "bs":
            window = clause[max(0, start - 35):min(len(clause), end + 35)].lower()
            if any(k in window for k in ["degree", "in computer science", "ms", "bachelor", "master", "stem", "equivalent"]):
                return False
            if not any(k in window for k in ["css", "html", "frontend", "ui", "web", "tailwind"]):
                return False

        return True

    # -----------------------------------------------------------------------
    # 8. Education Requirement Extraction
    # -----------------------------------------------------------------------

    def _extract_education(
        self,
        sections: Dict[str, List[str]],
        raw_text: str,
    ) -> EducationRequirement:
        """Extract degrees, degree levels, fields of study, and graduation years."""
        degrees: Set[str] = set()
        degree_levels: Set[str] = set()
        fields_of_study: Set[str] = set()
        min_grad_year: Optional[int] = None
        max_grad_year: Optional[int] = None
        evidence_lines: List[str] = []

        target_lines = (
            sections.get(SEC_EDUCATION, []) +
            sections.get(SEC_ELIGIBILITY, []) +
            sections.get(SEC_REQUIRED_QUALIFICATIONS, []) +
            sections.get(SEC_ROLE_OVERVIEW, []) +
            sections.get(SEC_HEADER, []) +
            sections.get(SEC_GENERAL, [])
        )

        for line in target_lines:
            matched_in_line = False
            for pat, deg_record in _degree_patterns():
                if pat.search(line):
                    deg_level = deg_record.get("level")
                    if deg_level != "secondary":
                        deg_name = deg_record.get("name")
                        if deg_name:
                            degrees.add(deg_name)
                        if deg_level:
                            degree_levels.add(deg_level)
                        matched_in_line = True
            if matched_in_line:
                evidence_lines.append(line.strip())

            # Fields of study
            for field in _FIELDS_OF_STUDY:
                if field in _UPPER_ONLY_FIELDS:
                    pat = rf"(?<![A-Za-z0-9]){re.escape(field)}(?![A-Za-z0-9])"
                    if re.search(pat, line):
                        fields_of_study.add(field)
                else:
                    pat = rf"(?<![A-Za-z0-9]){re.escape(field)}(?![A-Za-z0-9])"
                    if re.search(pat, line, re.I):
                        fields_of_study.add(field)

        # Grad years from batch mentions
        batches = [int(b) for b in _BATCH_RE.findall(raw_text)]
        if batches:
            min_grad_year = min(batches)
            max_grad_year = max(batches)

        evidence = "; ".join(evidence_lines[:3]) if evidence_lines else None
        confidence = 1.0 if degrees or fields_of_study else 0.50

        return EducationRequirement(
            degrees=sorted(list(degrees)),
            degree_levels=sorted(list(degree_levels)),
            fields_of_study=sorted(list(fields_of_study)),
            min_graduation_year=min_grad_year,
            max_graduation_year=max_grad_year,
            raw_text=evidence,
            evidence=evidence,
            confidence=confidence,
        )

    # -----------------------------------------------------------------------
    # 9. Responsibilities Extraction
    # -----------------------------------------------------------------------

    def _extract_responsibilities(self, sections: Dict[str, List[str]]) -> List[str]:
        """Extract cleaned and deduplicated responsibilities."""
        lines = sections.get(SEC_RESPONSIBILITIES, [])
        responsibilities: List[str] = []
        seen: Set[str] = set()

        for line in lines:
            clean = line.strip()
            if not clean:
                continue

            # Strip bullet marker
            if is_bullet(clean):
                _, bullet_text = split_bullet(clean)
                clean = bullet_text.strip()
            else:
                clean = re.sub(r"^[–\-\*•\d\.\)]+\s*", "", clean).strip()

            # Filter short fragments or headings
            if len(clean) < 12 or clean.endswith(":"):
                continue

            clean_lower = clean.lower()
            if clean_lower not in seen:
                seen.add(clean_lower)
                responsibilities.append(clean)

        return responsibilities

    # -----------------------------------------------------------------------
    # 10. Placement Eligibility Criteria Extraction
    # -----------------------------------------------------------------------

    def _extract_eligibility(
        self,
        sections: Dict[str, List[str]],
        raw_text: str,
    ) -> EligibilityCriteria:
        """Extract CGPA/CPI, percentage, batches, branches, and backlog policy."""
        min_cgpa: Optional[float] = None
        cgpa_scale: Optional[float] = None
        min_percentage: Optional[float] = None
        allowed_branches: Set[str] = set()
        allowed_batches: Set[int] = set()
        backlog_policy: Optional[str] = None
        raw_criteria: List[str] = []
        evidence_list: List[str] = []

        target_lines = (
            sections.get(SEC_ELIGIBILITY, []) +
            sections.get(SEC_EDUCATION, []) +
            sections.get(SEC_REQUIRED_QUALIFICATIONS, []) +
            sections.get(SEC_ROLE_OVERVIEW, []) +
            sections.get(SEC_OTHER, []) +
            sections.get(SEC_HEADER, []) +
            sections.get(SEC_GENERAL, [])
        )

        for line in target_lines:
            clean_line = line.strip()
            # CGPA / CPI
            m_cgpa = _CGPA_RE.search(clean_line)
            if m_cgpa and min_cgpa is None:
                val_str = m_cgpa.group(1) or m_cgpa.group(3) or m_cgpa.group(5)
                scale_str = m_cgpa.group(2) or m_cgpa.group(4)
                if val_str:
                    val = float(val_str)
                    sc = float(scale_str) if scale_str else (
                        4.0 if val <= 4.0 and "gpa" in m_cgpa.group(0).lower() and "cgpa" not in m_cgpa.group(0).lower() else 10.0
                    )
                    if 0 < val <= sc:
                        min_cgpa = val
                        cgpa_scale = sc
                        evidence_list.append(clean_line)

            # Percentage
            m_pct = _PERCENT_RE.search(clean_line)
            if m_pct and min_percentage is None:
                pct_val = float(m_pct.group(1) or m_pct.group(2))
                if 40.0 <= pct_val <= 100.0:
                    min_percentage = pct_val
                    evidence_list.append(clean_line)

            # Batches (if line mentions batch / graduating / passout / students)
            if re.search(r"\b(?:batch|pass[\s-]?outs?|graduating|class|students?)\b", clean_line, re.I):
                for b_match in _BATCH_RE.finditer(clean_line):
                    allowed_batches.add(int(b_match.group(1)))
                    evidence_list.append(clean_line)

            # Backlogs
            m_back = _BACKLOG_RE.search(clean_line)
            if m_back and backlog_policy is None:
                backlog_policy = m_back.group(0).strip()
                evidence_list.append(clean_line)

            # Branches
            for br_match in _BRANCH_RE.finditer(clean_line):
                br_str = br_match.group(1).strip()
                allowed_branches.add(br_str.upper() if len(br_str) <= 5 else br_str.title())
                evidence_list.append(clean_line)

        if not allowed_batches:
            for m in re.finditer(r"\b(202[0-9])\b", raw_text):
                span_text = raw_text[max(0, m.start() - 25):min(len(raw_text), m.end() + 25)].lower()
                if any(k in span_text for k in ("batch", "passout", "graduat", "placement", "intern", "students")):
                    allowed_batches.add(int(m.group(1)))

        if min_cgpa is None:
            m_cgpa = _CGPA_RE.search(raw_text)
            if m_cgpa:
                val_str = m_cgpa.group(1) or m_cgpa.group(3)
                scale_str = m_cgpa.group(2) or m_cgpa.group(4)
                if val_str:
                    val = float(val_str)
                    sc = float(scale_str) if scale_str else (
                        4.0 if val <= 4.0 and "gpa" in m_cgpa.group(0).lower() and "cgpa" not in m_cgpa.group(0).lower() else 10.0
                    )
                    if 0 < val <= sc:
                        min_cgpa = val
                        cgpa_scale = sc
                        evidence_list.append(m_cgpa.group(0).strip())

        if min_percentage is None:
            m_pct = _PERCENT_RE.search(raw_text)
            if m_pct:
                pct_val = float(m_pct.group(1) or m_pct.group(2))
                if 40.0 <= pct_val <= 100.0:
                    min_percentage = pct_val
                    evidence_list.append(m_pct.group(0).strip())

        if SEC_ELIGIBILITY in sections:
            raw_criteria = [line.strip() for line in sections[SEC_ELIGIBILITY] if line.strip()]
        else:
            raw_criteria = [
                line.strip() for line in target_lines
                if "eligib" in line.lower() or _CGPA_RE.search(line) or _BACKLOG_RE.search(line)
            ]

        return EligibilityCriteria(
            min_cgpa=min_cgpa,
            cgpa_scale=cgpa_scale,
            min_percentage=min_percentage,
            allowed_branches=sorted(list(allowed_branches)),
            allowed_batches=sorted(list(allowed_batches)),
            backlog_policy=backlog_policy,
            raw_criteria=raw_criteria,
            evidence=list(dict.fromkeys(evidence_list)),
        )

    # -----------------------------------------------------------------------
    # 11. Location Extraction
    # -----------------------------------------------------------------------

    def _extract_location(
        self,
        sections: Dict[str, List[str]],
        raw_text: str,
    ) -> LocationRequirement:
        """Extract city, state, country, workplace type, and remote status."""
        raw_loc: Optional[str] = None
        city: Optional[str] = None
        state: Optional[str] = None
        country: Optional[str] = None
        workplace_type = WorkplaceType.UNKNOWN
        is_remote = False
        evidence: Optional[str] = None

        loc_label_re = re.compile(
            r"^\s*(?:job\s+)?location\s*[:\-–]\s*(.+)$",
            re.IGNORECASE,
        )

        for lines in sections.values():
            for line in lines:
                m = loc_label_re.match(line)
                if m:
                    raw_loc = m.group(1).strip()
                    evidence = line.strip()
                    break
            if raw_loc:
                break

        scan_target = raw_loc or raw_text

        # Detect Workplace Type
        lower_target = scan_target.lower()
        if re.search(r"\b(?:remote|work\s+from\s+home|wfh|telecommute|virtual)\b", lower_target):
            workplace_type = WorkplaceType.REMOTE
            is_remote = True
        elif re.search(r"\b(?:hybrid|partial\s+remote)\b", lower_target):
            workplace_type = WorkplaceType.HYBRID
            is_remote = False
        elif re.search(r"\b(?:on[\s-]?site|in[\s-]?office|work\s+from\s+office|wfo)\b", lower_target):
            workplace_type = WorkplaceType.ON_SITE
            is_remote = False

        # City detection
        city_m = _LOCATION_CITIES_RE.search(scan_target)
        if city_m:
            matched_city = city_m.group(1)
            # Normalize Bangalore -> Bengaluru
            city = "Bengaluru" if matched_city.lower() in ("bangalore", "bengaluru") else matched_city.title()
            if workplace_type == WorkplaceType.UNKNOWN:
                workplace_type = WorkplaceType.ON_SITE

        # State detection for Indian tech hubs
        if city in ("Bengaluru", "Bangalore"):
            state = "Karnataka"
            country = "India"
        elif city in ("Hyderabad",):
            state = "Telangana"
            country = "India"
        elif city in ("Pune", "Mumbai"):
            state = "Maharashtra"
            country = "India"
        elif city in ("Ahmedabad", "Gandhinagar", "Vadodara", "Surat"):
            state = "Gujarat"
            country = "India"
        elif city in ("Noida",):
            state = "Uttar Pradesh"
            country = "India"
        elif city in ("Gurugram", "Gurgaon"):
            state = "Haryana"
            country = "India"
        elif city in ("Chennai", "Coimbatore"):
            state = "Tamil Nadu"
            country = "India"
        elif city in ("Kolkata",):
            state = "West Bengal"
            country = "India"
        elif city in ("San Francisco",):
            state = "California"
            country = "USA"

        return LocationRequirement(
            raw_location=raw_loc,
            city=city,
            state=state,
            country=country,
            workplace_type=workplace_type,
            is_remote=is_remote,
            evidence=evidence or raw_loc,
        )

    # -----------------------------------------------------------------------
    # 12. Other Relevant Job Requirements Extraction
    # -----------------------------------------------------------------------

    def _extract_other_requirements(
        self,
        sections: Dict[str, List[str]],
        raw_text: str,
    ) -> OtherJobRequirements:
        """Extract CTC/stipend, bond/service agreement, and selection process."""
        salary: Optional[str] = None
        bond: Optional[str] = None
        selection_process: List[str] = []
        additional_notes: List[str] = []
        evidence_list: List[str] = []

        target_lines = (
            sections.get(SEC_COMPENSATION, []) +
            sections.get(SEC_SELECTION_PROCESS, []) +
            sections.get(SEC_OTHER, []) +
            sections.get(SEC_HEADER, [])
        )

        for line in target_lines:
            clean = line.strip()
            # Salary / Stipend
            m_sal = _SALARY_RE.search(clean)
            if m_sal and salary is None:
                salary = m_sal.group(0).strip()
                evidence_list.append(clean)

            # Bond
            m_bond = _BOND_RE.search(clean)
            if m_bond and bond is None:
                bond = m_bond.group(0).strip()
                evidence_list.append(clean)

            # Selection rounds
            if any(term in clean.lower() for term in ("round", "interview", "assessment", "online test")):
                # Check if it lists numbered or comma-separated steps
                if re.search(r"\d+\.|\bround\b", clean, re.I):
                    steps = [s.strip() for s in re.split(r",|\d+\.", clean) if s.strip() and len(s.strip()) > 3]
                    for step in steps:
                        if step not in selection_process and len(step) < 50:
                            selection_process.append(step)
                            evidence_list.append(clean)

        # Fallback to scan raw text if salary/bond not in target sections
        if salary is None:
            m_sal = _SALARY_RE.search(raw_text)
            if m_sal:
                salary = m_sal.group(0).strip()
                evidence_list.append(salary)

        if bond is None:
            m_bond = _BOND_RE.search(raw_text)
            if m_bond:
                bond = m_bond.group(0).strip()
                evidence_list.append(bond)

        return OtherJobRequirements(
            salary_or_stipend=salary,
            bond_or_service_agreement=bond,
            selection_process=selection_process,
            additional_notes=additional_notes,
            evidence=list(dict.fromkeys(evidence_list)),
        )


__all__ = [
    "JobDescriptionParser",
]
