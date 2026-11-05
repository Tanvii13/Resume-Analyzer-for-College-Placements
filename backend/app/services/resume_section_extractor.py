
import re


SECTION_ALIASES = {
    "education": [
        "education",
        "academic background",
        "educational qualification",
        "academic qualification",
    ],
    "projects": [
        "projects",
        "academic projects",
        "personal projects",
        "project experience",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "internship",
        "internships",
    ],
}

OTHER_HEADINGS = [
    "skills",
    "technical skills",
    "soft skills",
    "certifications",
    "certificates",
    "achievements",
    "awards",
    "languages",
    "interests",
    "hobbies",
    "summary",
    "profile",
    "objective",
    "contact",
    "references",
]


def normalize_heading(line):
    """Normalize a possible resume section heading."""

    line = line.strip().lower()
    line = re.sub(r"^\d+[\.\)]\s*", "", line)
    line = re.sub(r"[:\-]+$", "", line)
    line = re.sub(r"\s+", " ", line)

    return line.strip()


def identify_heading(line):
    """Identify supported section headings."""

    heading = normalize_heading(line)

    for section, aliases in SECTION_ALIASES.items():
        if heading in aliases:
            return section

    if heading in OTHER_HEADINGS:
        return "other"

    return None


def extract_resume_sections(resume_text):
    """
    Extract education, projects and experience
    using resume section headings.
    """

    if not isinstance(resume_text, str):
        raise TypeError("Resume text must be a string.")

    result = {
        "education": [],
        "projects": [],
        "experience": [],
    }

    current_section = None
    section_lines = []

    def save_current_section():
        if current_section in result and section_lines:
            content = "\n".join(section_lines).strip()

            if content:
                result[current_section].append(content)

    for line in resume_text.splitlines():
        heading = identify_heading(line)

        if heading is not None:
            save_current_section()
            current_section = heading if heading != "other" else None
            section_lines = []
            continue

        if current_section is not None and line.strip():
            section_lines.append(line.strip())

    save_current_section()

    return result
