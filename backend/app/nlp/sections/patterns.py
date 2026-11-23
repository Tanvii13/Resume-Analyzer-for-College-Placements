"""
Canonical section patterns, aliases, and heading detection utilities.

Module B (NLP-02) of Sprint 2 NLP pipeline.

Supports 10 canonical resume sections:
- personal_info
- education
- experience
- internships
- projects
- technical_skills
- soft_skills
- certifications
- achievements
- extracurricular
"""

import re
from typing import Dict, List, Optional, Pattern, Set, Tuple

# Attempt to use rapidfuzz if installed; fallback seamlessly to pure-Python implementation
try:
    from rapidfuzz.distance import Levenshtein as rf_levenshtein
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False


# 10 Canonical Section Keys
SECTION_PERSONAL_INFO = "personal_info"
SECTION_EDUCATION = "education"
SECTION_EXPERIENCE = "experience"
SECTION_INTERNSHIPS = "internships"
SECTION_PROJECTS = "projects"
SECTION_TECHNICAL_SKILLS = "technical_skills"
SECTION_SOFT_SKILLS = "soft_skills"
SECTION_CERTIFICATIONS = "certifications"
SECTION_ACHIEVEMENTS = "achievements"
SECTION_EXTRACURRICULAR = "extracurricular"
SECTION_GENERAL_BODY = "general_body"

CANONICAL_SECTIONS = [
    SECTION_PERSONAL_INFO,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_INTERNSHIPS,
    SECTION_PROJECTS,
    SECTION_TECHNICAL_SKILLS,
    SECTION_SOFT_SKILLS,
    SECTION_CERTIFICATIONS,
    SECTION_ACHIEVEMENTS,
    SECTION_EXTRACURRICULAR,
]


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute standard Levenshtein edit distance between two strings."""
    if _HAS_RAPIDFUZZ:
        return int(rf_levenshtein.distance(s1, s2))

    if s1 == s2:
        return 0
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def string_similarity(s1: str, s2: str) -> float:
    """Compute normalized similarity ratio between 0.0 and 1.0."""
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(s1, s2)
    return round(1.0 - (dist / max_len), 4)


# Primary aliases dictionary: normalized lowercase string -> canonical section
HEADING_ALIASES: Dict[str, str] = {
    # personal_info
    "personal information": SECTION_PERSONAL_INFO,
    "personal info": SECTION_PERSONAL_INFO,
    "personal details": SECTION_PERSONAL_INFO,
    "contact": SECTION_PERSONAL_INFO,
    "contact info": SECTION_PERSONAL_INFO,
    "contact information": SECTION_PERSONAL_INFO,
    "contact details": SECTION_PERSONAL_INFO,
    "profile": SECTION_PERSONAL_INFO,
    "personal profile": SECTION_PERSONAL_INFO,
    "profile summary": SECTION_PERSONAL_INFO,
    "about me": SECTION_PERSONAL_INFO,
    "bio": SECTION_PERSONAL_INFO,
    "biography": SECTION_PERSONAL_INFO,
    "summary": SECTION_PERSONAL_INFO,
    "professional summary": SECTION_PERSONAL_INFO,
    "career objective": SECTION_PERSONAL_INFO,
    "objective": SECTION_PERSONAL_INFO,

    # education
    "education": SECTION_EDUCATION,
    "educational background": SECTION_EDUCATION,
    "educational qualifications": SECTION_EDUCATION,
    "educational details": SECTION_EDUCATION,
    "academic background": SECTION_EDUCATION,
    "academic details": SECTION_EDUCATION,
    "academic qualifications": SECTION_EDUCATION,
    "academic credentials": SECTION_EDUCATION,
    "academic record": SECTION_EDUCATION,
    "academics": SECTION_EDUCATION,
    "qualifications": SECTION_EDUCATION,
    "degrees": SECTION_EDUCATION,
    "formal education": SECTION_EDUCATION,
    "education details": SECTION_EDUCATION,
    "education and training": SECTION_EDUCATION,
    "studies": SECTION_EDUCATION,

    # experience
    "experience": SECTION_EXPERIENCE,
    "work experience": SECTION_EXPERIENCE,
    "professional experience": SECTION_EXPERIENCE,
    "employment": SECTION_EXPERIENCE,
    "employment history": SECTION_EXPERIENCE,
    "work history": SECTION_EXPERIENCE,
    "career history": SECTION_EXPERIENCE,
    "professional background": SECTION_EXPERIENCE,
    "relevant experience": SECTION_EXPERIENCE,
    "industry experience": SECTION_EXPERIENCE,
    "prior experience": SECTION_EXPERIENCE,
    "work background": SECTION_EXPERIENCE,

    # internships
    "internship": SECTION_INTERNSHIPS,
    "internships": SECTION_INTERNSHIPS,
    "summer internship": SECTION_INTERNSHIPS,
    "summer internships": SECTION_INTERNSHIPS,
    "internship experience": SECTION_INTERNSHIPS,
    "industrial training": SECTION_INTERNSHIPS,
    "research internship": SECTION_INTERNSHIPS,
    "virtual internship": SECTION_INTERNSHIPS,
    "internship details": SECTION_INTERNSHIPS,
    "training and internships": SECTION_INTERNSHIPS,

    # projects
    "projects": SECTION_PROJECTS,
    "project": SECTION_PROJECTS,
    "academic projects": SECTION_PROJECTS,
    "personal projects": SECTION_PROJECTS,
    "key projects": SECTION_PROJECTS,
    "technical projects": SECTION_PROJECTS,
    "major projects": SECTION_PROJECTS,
    "minor projects": SECTION_PROJECTS,
    "course projects": SECTION_PROJECTS,
    "selected projects": SECTION_PROJECTS,
    "notable projects": SECTION_PROJECTS,
    "software projects": SECTION_PROJECTS,
    "capstone project": SECTION_PROJECTS,
    "open source projects": SECTION_PROJECTS,
    "development projects": SECTION_PROJECTS,

    # technical_skills
    "technical skills": SECTION_TECHNICAL_SKILLS,
    "technical skill": SECTION_TECHNICAL_SKILLS,
    "skills": SECTION_TECHNICAL_SKILLS,
    "programming skills": SECTION_TECHNICAL_SKILLS,
    "skills and tools": SECTION_TECHNICAL_SKILLS,
    "skills & tools": SECTION_TECHNICAL_SKILLS,
    "technical competencies": SECTION_TECHNICAL_SKILLS,
    "technical proficiencies": SECTION_TECHNICAL_SKILLS,
    "technologies": SECTION_TECHNICAL_SKILLS,
    "technologies and tools": SECTION_TECHNICAL_SKILLS,
    "tech stack": SECTION_TECHNICAL_SKILLS,
    "core skills": SECTION_TECHNICAL_SKILLS,
    "key skills": SECTION_TECHNICAL_SKILLS,
    "it skills": SECTION_TECHNICAL_SKILLS,
    "computer skills": SECTION_TECHNICAL_SKILLS,
    "languages and technologies": SECTION_TECHNICAL_SKILLS,
    "tools and technologies": SECTION_TECHNICAL_SKILLS,
    "tools & technologies": SECTION_TECHNICAL_SKILLS,
    "areas of expertise": SECTION_TECHNICAL_SKILLS,
    "technical strengths": SECTION_TECHNICAL_SKILLS,
    "competencies": SECTION_TECHNICAL_SKILLS,

    # soft_skills
    "soft skills": SECTION_SOFT_SKILLS,
    "soft skill": SECTION_SOFT_SKILLS,
    "interpersonal skills": SECTION_SOFT_SKILLS,
    "non technical skills": SECTION_SOFT_SKILLS,
    "non-technical skills": SECTION_SOFT_SKILLS,
    "behavioral skills": SECTION_SOFT_SKILLS,
    "personal skills": SECTION_SOFT_SKILLS,
    "leadership skills": SECTION_SOFT_SKILLS,
    "communication skills": SECTION_SOFT_SKILLS,
    "professional skills": SECTION_SOFT_SKILLS,

    # certifications
    "certifications": SECTION_CERTIFICATIONS,
    "certification": SECTION_CERTIFICATIONS,
    "certificates": SECTION_CERTIFICATIONS,
    "certificate": SECTION_CERTIFICATIONS,
    "licenses": SECTION_CERTIFICATIONS,
    "licenses & certifications": SECTION_CERTIFICATIONS,
    "licenses and certifications": SECTION_CERTIFICATIONS,
    "courses & certifications": SECTION_CERTIFICATIONS,
    "courses and certifications": SECTION_CERTIFICATIONS,
    "certified courses": SECTION_CERTIFICATIONS,
    "professional certifications": SECTION_CERTIFICATIONS,
    "credentials": SECTION_CERTIFICATIONS,
    "online certifications": SECTION_CERTIFICATIONS,

    # achievements
    "achievements": SECTION_ACHIEVEMENTS,
    "achievement": SECTION_ACHIEVEMENTS,
    "awards": SECTION_ACHIEVEMENTS,
    "honors": SECTION_ACHIEVEMENTS,
    "honours": SECTION_ACHIEVEMENTS,
    "awards and honors": SECTION_ACHIEVEMENTS,
    "awards & honors": SECTION_ACHIEVEMENTS,
    "honors and awards": SECTION_ACHIEVEMENTS,
    "honors & awards": SECTION_ACHIEVEMENTS,
    "accomplishments": SECTION_ACHIEVEMENTS,
    "accolades": SECTION_ACHIEVEMENTS,
    "key achievements": SECTION_ACHIEVEMENTS,
    "academic achievements": SECTION_ACHIEVEMENTS,
    "competitive programming achievements": SECTION_ACHIEVEMENTS,
    "recognitions": SECTION_ACHIEVEMENTS,
    "distinctions": SECTION_ACHIEVEMENTS,

    # extracurricular
    "extracurricular activities": SECTION_EXTRACURRICULAR,
    "extracurricular activity": SECTION_EXTRACURRICULAR,
    "extracurricular": SECTION_EXTRACURRICULAR,
    "extra-curricular": SECTION_EXTRACURRICULAR,
    "extra curricular": SECTION_EXTRACURRICULAR,
    "extra curricular activities": SECTION_EXTRACURRICULAR,
    "activities": SECTION_EXTRACURRICULAR,
    "positions of responsibility": SECTION_EXTRACURRICULAR,
    "position of responsibility": SECTION_EXTRACURRICULAR,
    "co-curricular activities": SECTION_EXTRACURRICULAR,
    "co curricular activities": SECTION_EXTRACURRICULAR,
    "volunteering": SECTION_EXTRACURRICULAR,
    "volunteer work": SECTION_EXTRACURRICULAR,
    "leadership and activities": SECTION_EXTRACURRICULAR,
    "leadership & activities": SECTION_EXTRACURRICULAR,
    "clubs and committees": SECTION_EXTRACURRICULAR,
    "clubs & committees": SECTION_EXTRACURRICULAR,
    "social work": SECTION_EXTRACURRICULAR,
}

# Regex patterns for matching section headers with optional numbering and punctuation
SECTION_REGEXES: Dict[str, List[Pattern]] = {
    SECTION_PERSONAL_INFO: [
        re.compile(r"^(\d+[\.\)]\s*)?(personal\s+(information|details|info|data)|contact(\s+(information|details|info))?|profile(\s+summary)?|about\s+me|career\s+objective|objective|professional\s+summary)\s*:?$", re.I),
    ],
    SECTION_EDUCATION: [
        re.compile(r"^(\d+[\.\)]\s*)?(education(al)?(\s+(background|qualifications?|details?|credentials?))?|academic(s|\s+(background|qualifications?|details?|record|credentials?))|qualifications?|degrees?)\s*:?$", re.I),
    ],
    SECTION_INTERNSHIPS: [
        re.compile(r"^(\d+[\.\)]\s*)?(internships?(\s+(experience|details?|history))?|summer\s+internships?|industrial\s+training|research\s+internships?)\s*:?$", re.I),
    ],
    SECTION_EXPERIENCE: [
        re.compile(r"^(\d+[\.\)]\s*)?(work\s+experience|professional\s+experience|employment(\s+history)?|work\s+history|experience|career\s+history|industry\s+experience)\s*:?$", re.I),
    ],
    SECTION_PROJECTS: [
        re.compile(r"^(\d+[\.\)]\s*)?((academic|personal|key|technical|major|minor|course|selected|notable|software)?\s*projects?|capstone\s+projects?)\s*:?$", re.I),
    ],
    SECTION_TECHNICAL_SKILLS: [
        re.compile(r"^(\d+[\.\)]\s*)?(technical\s+skills?|programming\s+skills?|skills(\s*(&|and)\s*tools?)?|technologies(\s*(&|and)\s*tools?)?|tech\s+stack|core\s+skills?|key\s+skills?|it\s+skills?|computer\s+skills?|areas\s+of\s+expertise|tools\s*(&|and)\s*technologies)\s*:?$", re.I),
    ],
    SECTION_SOFT_SKILLS: [
        re.compile(r"^(\d+[\.\)]\s*)?(soft\s+skills?|interpersonal\s+skills?|non[- ]technical\s+skills?|behavioral\s+skills?|personal\s+skills?|leadership\s+skills?)\s*:?$", re.I),
    ],
    SECTION_CERTIFICATIONS: [
        re.compile(r"^(\d+[\.\)]\s*)?(certifications?|certificates?|licenses?(\s*(&|and)\s*certifications?)?|courses\s*(&|and)\s*certifications?|certified\s+courses?|credentials?)\s*:?$", re.I),
    ],
    SECTION_ACHIEVEMENTS: [
        re.compile(r"^(\d+[\.\)]\s*)?(achievements?|awards?(\s*(&|and)\s*honou?rs?)?|honou?rs?(\s*(&|and)\s*awards?)?|accomplishments?|accolades?|key\s+achievements?|distinctions?)\s*:?$", re.I),
    ],
    SECTION_EXTRACURRICULAR: [
        re.compile(r"^(\d+[\.\)]\s*)?(extracurricular(\s+activities)?|extra[- ]curricular(\s+activities)?|activities|positions?\s+of\s+responsibility|co[- ]curricular(\s+activities)?|volunteer(ing|\s+work)?|clubs\s*(&|and)\s*committees)\s*:?$", re.I),
    ],
}
