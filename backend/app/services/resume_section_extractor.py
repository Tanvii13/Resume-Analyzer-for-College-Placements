
import re


SECTION_ALIASES = {
    "education": [
        "education",
        "academic background",
        "educational qualification",
        "academic qualification",
        "academic details",
        "education details",
        "educational background",
    ],
    "projects": [
        "projects",
        "academic projects",
        "personal projects",
        "project experience",
        "project work",
        "key projects",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history",
        "internship",
        "internships",
        "professional background",
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
    "career objective",
    "contact",
    "references",
]


def normalize_heading(line):
    """Normalize a possible resume section heading."""

    line = line.strip().lower()
    line = re.sub(r"^\d+[\.\)]\s*", "", line)
    line = re.sub(r"[:\-–—.]+$", "", line)
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

            if content and content not in result[current_section]:
                result[current_section].append(content)

    for line in resume_text.splitlines():
        heading = identify_heading(line)

        inline_content = None

        if heading is None and ":" in line:
            possible_heading, remaining_text = line.split(":", 1)
            heading = identify_heading(possible_heading)

            if heading is not None:
                inline_content = remaining_text.strip()

        if heading is not None:
            save_current_section()
            current_section = heading if heading != "other" else None
            section_lines = []

            if current_section is not None and inline_content:
                section_lines.append(inline_content)

            continue

        if current_section is not None and line.strip():
            section_lines.append(line.strip())

    save_current_section()

    return result
