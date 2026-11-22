"""
Training / workshop catalog for Sprint 5 Module D.

Rules are plain data so the placement cell can review and edit them. A program is
recommended only when enough students show the weaknesses or skill gaps it addresses
(see `builder.TRIGGER_*`). Programs describe generic training formats; the report never
names a vendor, course link or individual student.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TrainingProgram:
    program_id: str
    title: str
    format: str
    description: str
    issue_ids: tuple[str, ...] = ()
    skill_categories: tuple[str, ...] = ()
    skills: tuple[str, ...] = field(default_factory=tuple)


# Resume-weakness programs (driven by Sprint 3 Module D improvement areas)
WEAKNESS_PROGRAMS: tuple[TrainingProgram, ...] = (
    TrainingProgram(
        "TRN_RESUME_IMPACT", "Resume writing workshop: action verbs and real outcomes", "workshop",
        "Hands-on session where students rewrite their own project and internship bullets to start with an "
        "action verb and state real, verifiable outcomes.",
        issue_ids=("IMP_LACK_OF_ACTION_VERBS", "IMP_PASSIVE_PHRASING", "IMP_LACK_OF_MEASURABLE_IMPACT",
                   "IMP_GENERIC_RESUME_CLICHES", "IMP_DUPLICATE_BULLET_CONTENT"),
    ),
    TrainingProgram(
        "TRN_PROJECT_PORTFOLIO", "Project portfolio clinic", "mentoring",
        "Small-group review of student projects: describing the problem, own contribution, tech stack and result; "
        "guidance for students who have no projects yet on course and hackathon projects.",
        issue_ids=("IMP_WEAK_PROJECT_DESCRIPTION", "IMP_MISSING_PROJECTS", "IMP_MISSING_PRACTICAL_WORK"),
    ),
    TrainingProgram(
        "TRN_RESUME_ESSENTIALS", "Resume essentials and template session", "session",
        "Walk-through of the sections, contact details and academic information recruiters expect, using the "
        "placement cell's standard resume template.",
        issue_ids=("IMP_MISSING_EDUCATION", "IMP_MISSING_SKILLS", "IMP_CONTACT_MISSING_EMAIL", "IMP_CONTACT_MISSING_PHONE",
                   "IMP_EDU_MISSING_CGPA", "IMP_EDU_MISSING_YEAR", "IMP_EDU_MISSING_DEGREE", "FMT_MISSING_SECTION_HEADING"),
    ),
    TrainingProgram(
        "TRN_ONLINE_PROFILES", "GitHub and LinkedIn profile building", "session",
        "Setting up and maintaining GitHub and LinkedIn profiles and linking them from the resume.",
        issue_ids=("IMP_CONTACT_MISSING_DEV_PROFILES",),
    ),
    TrainingProgram(
        "TRN_ATS_FORMATTING", "ATS-friendly resume formatting", "session",
        "Consistent headings, bullets, dates and single-column layouts that screening software can read.",
        issue_ids=("IMP_INCONSISTENT_HEADINGS", "IMP_UNSTRUCTURED_WALL_OF_TEXT", "IMP_INCONSISTENT_BULLET_FORMATTING",
                   "IMP_EXCESSIVE_WHITESPACE", "IMP_INCONSISTENT_DATE_FORMATS", "IMP_EXTRACTION_UNCERTAINTY",
                   "FMT_REPEATED_SECTION_HEADING", "FMT_POOR_SECTION_ORDER", "FMT_FRAGMENTED_TEXT_BLOCKS",
                   "FMT_UNSTRUCTURED_SECTION_DESCRIPTIONS", "FMT_INCONSISTENT_BULLET_PUNCTUATION",
                   "FMT_INCONSISTENT_INLINE_DELIMITERS"),
    ),
    TrainingProgram(
        "TRN_SKILLS_SECTION", "Presenting technical skills", "session",
        "Organising the skills section by category, removing duplicates and backing each listed skill with a "
        "project or internship.",
        issue_ids=("IMP_POOR_SKILL_CATEGORIZATION", "IMP_DUPLICATE_SKILLS", "IMP_UNSUBSTANTIATED_SKILLS",
                   "IMP_LOW_SKILL_INVENTORY"),
    ),
    TrainingProgram(
        "TRN_SOFT_SKILLS", "Communication and teamwork sessions", "workshop",
        "Group discussions, presentations and mock HR interviews, and how to show teamwork through concrete examples.",
        issue_ids=("IMP_MISSING_SOFT_SKILLS",),
        skill_categories=("Soft Skills",),
    ),
)

# Skill-gap programs (driven by Sprint 4 job-matching gaps). Specific skills win over categories.
SKILL_PROGRAMS: tuple[TrainingProgram, ...] = (
    TrainingProgram(
        "TRN_GIT", "Git and GitHub hands-on workshop", "hands-on lab",
        "Version control basics, branching, pull requests and collaborating on a shared repository.",
        skills=("Git", "GitHub", "GitLab"),
    ),
    TrainingProgram(
        "TRN_DATABASES", "Databases and SQL bootcamp", "bootcamp",
        "Relational modelling, SQL queries and working with PostgreSQL / MySQL and a NoSQL store.",
        skill_categories=("Databases",), skills=("SQL",),
    ),
    TrainingProgram(
        "TRN_BACKEND", "Backend and REST API development workshop", "workshop",
        "Building and testing a REST API with a common backend framework.",
        skill_categories=("Backend Development",),
    ),
    TrainingProgram(
        "TRN_FRONTEND", "Web frontend development bootcamp", "bootcamp",
        "HTML, CSS, JavaScript and a component framework through a guided project.",
        skill_categories=("Frontend Development",),
    ),
    TrainingProgram(
        "TRN_DEVOPS_CLOUD", "Docker, cloud and DevOps hands-on lab", "hands-on lab",
        "Containers, CI/CD pipelines, Linux basics and deploying to a cloud provider.",
        skill_categories=("DevOps", "Cloud Computing", "Operating Systems"),
    ),
    TrainingProgram(
        "TRN_DATA_ML", "Data analysis and machine learning foundations", "bootcamp",
        "Python data tools, statistics, visualisation and introductory machine learning.",
        skill_categories=("Data Science", "Machine Learning", "Artificial Intelligence"),
    ),
    TrainingProgram(
        "TRN_PROGRAMMING", "Programming and problem-solving practice", "workshop",
        "Regular coding practice in the languages employers asked for, plus data structures and algorithms.",
        skill_categories=("Programming Languages", "Software Engineering"),
    ),
    TrainingProgram(
        "TRN_TESTING", "Software testing workshop", "workshop",
        "Unit, integration and automated UI testing in practice.",
        skill_categories=("Testing & QA",),
    ),
)


def program_for_skill(skill: str, category: str | None) -> TrainingProgram | None:
    for p in SKILL_PROGRAMS:
        if skill in p.skills:
            return p
    for p in SKILL_PROGRAMS:
        if category and category in p.skill_categories:
            return p
    return None


__all__ = ["SKILL_PROGRAMS", "WEAKNESS_PROGRAMS", "TrainingProgram", "program_for_skill"]
