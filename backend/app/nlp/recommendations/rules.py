"""
Recommendation rule registry for Sprint 3 Module E.

Each RecommendationRule says how to turn one kind of Module D issue into student-facing
advice. Rules are plain data so they can be reviewed by the team and changed without
touching the engine.

Rule text guidelines:
- Simple, student-friendly language.
- Never suggest adding skills, certifications, achievements or numbers the student does not
  actually have. Measurable-impact advice always says "only real numbers".
- No job-specific advice (job-description matching is Sprint 4).

`merge_key`: recommendations that would give the same advice share a key and are merged
(for example "missing projects section" from Module A, B and D all become one item).

`actionability`: 0-1, how directly the student can act on the advice in one edit. Used in
priority scoring.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.nlp.recommendations.schemas import RecommendationCategory

RULE_SET_VERSION = "3.0.0"


@dataclass(frozen=True)
class RecommendationRule:
    rule_id: str
    recommendation_id: str
    category: RecommendationCategory
    title: str
    description: str
    why_it_matters: str
    suggested_action: str
    action_steps: List[str] = field(default_factory=list)
    actionability: float = 0.8
    merge_key: Optional[str] = None


# ---------------------------------------------------------------------------
# Section-specific advice for missing sections (used for both IMP_MISSING_* and
# FMT_MISSING_SECTION_HEADING, which reports the section in `affected_section`).
# ---------------------------------------------------------------------------

SECTION_GUIDANCE: Dict[str, Dict[str, object]] = {
    "education": {
        "label": "Education",
        "contents": "your degree and branch, college name, start and graduation year, and CGPA or percentage",
        "steps": [
            "Add a heading named 'Education'.",
            "List your current degree first: degree, branch, college, years, CGPA.",
            "Add Class XII and Class X below it with board, year and percentage.",
        ],
    },
    "projects": {
        "label": "Projects",
        "contents": "2-3 technical projects, each with a title, the technologies used and 2-3 bullet points on what you built",
        "steps": [
            "Add a heading named 'Projects'.",
            "Pick 2-3 projects you actually built (course, hackathon or personal).",
            "For each: title, tech stack, then bullets on the problem, your contribution and the result.",
            "Add the GitHub or live link if the project is public.",
        ],
    },
    "technical_skills": {
        "label": "Technical Skills",
        "contents": "the languages, frameworks, databases and tools you have actually used, grouped by type",
        "steps": [
            "Add a heading named 'Technical Skills'.",
            "Group skills into lines such as Languages, Frameworks, Databases, Tools.",
            "Only list skills you can discuss in an interview.",
        ],
    },
    "experience": {
        "label": "Experience",
        "contents": "your role, organization, dates, and 2-4 bullets on what you did",
        "steps": [
            "Add a heading named 'Experience' or 'Internships'.",
            "For each role: title, organization, location and dates on one line.",
            "Add 2-4 bullets starting with an action verb describing your work.",
        ],
    },
}


def section_label(section: Optional[str]) -> str:
    if not section:
        return "this section"
    guidance = SECTION_GUIDANCE.get(section)
    if guidance:
        return str(guidance["label"])
    return section.replace("_", " ").title()


def missing_section_rule(section: str, rule_id: str) -> RecommendationRule:
    """Build the 'add missing section' rule for a given canonical section name."""
    guidance = SECTION_GUIDANCE.get(section, {})
    label = section_label(section)
    contents = guidance.get("contents", f"the information recruiters expect under {label}")
    steps = list(
        guidance.get("steps", [f"Add a clearly labelled '{label}' heading and fill it in."])
    )
    return RecommendationRule(
        rule_id=rule_id,
        recommendation_id=f"REC_ADD_{section.upper()}_SECTION",
        category=RecommendationCategory.MISSING_SECTION,
        title=f"Add a {label} section",
        description=f"Your resume does not have a {label} section. This section should contain {contents}.",
        why_it_matters=(
            f"Recruiters and resume-screening software look for a {label} section first. "
            "If it is missing, the resume can be filtered out before anyone reads it."
        ),
        suggested_action=f"Add a clearly labelled '{label}' section with {contents}.",
        action_steps=steps,
        actionability=0.95,
        merge_key=f"missing_section:{section}",
    )


_MISSING_SECTION_ISSUES = {
    "IMP_MISSING_EDUCATION": "education",
    "IMP_MISSING_PROJECTS": "projects",
    "IMP_MISSING_SKILLS": "technical_skills",
}

RULES: Dict[str, RecommendationRule] = {
    issue_id: missing_section_rule(section, f"RULE_MISSING_SECTION_{section.upper()}")
    for issue_id, section in _MISSING_SECTION_ISSUES.items()
}

RULES.update(
    {
        # -- practical work -----------------------------------------------------
        "IMP_MISSING_PRACTICAL_WORK": RecommendationRule(
            rule_id="RULE_NO_PRACTICAL_WORK",
            recommendation_id="REC_ADD_PRACTICAL_WORK",
            category=RecommendationCategory.MISSING_SECTION,
            title="Show some hands-on technical work",
            description=(
                "No projects or internships were found. Freshers are not expected to have job experience, "
                "but recruiters do expect to see at least two things you have built."
            ),
            why_it_matters="Projects are the main proof of your technical ability when you have no work experience.",
            suggested_action="Add a Projects section with at least two projects you built yourself or in a team.",
            action_steps=[
                "Course projects, lab mini-projects and hackathon entries all count.",
                "For each project, name the technologies and describe what you personally did.",
            ],
            actionability=0.85,
            merge_key="missing_section:projects",
        ),
        # -- contact ------------------------------------------------------------
        "IMP_CONTACT_MISSING_EMAIL": RecommendationRule(
            rule_id="RULE_CONTACT_EMAIL",
            recommendation_id="REC_ADD_EMAIL",
            category=RecommendationCategory.CONTACT,
            title="Add your email address",
            description="No email address was found in your resume header.",
            why_it_matters="Recruiters send interview invites by email. Without it they cannot contact you.",
            suggested_action="Add a professional email address (your college email or firstname.lastname@...) at the top.",
            action_steps=["Put it in the first two lines, next to your phone number."],
            actionability=1.0,
        ),
        "IMP_CONTACT_MISSING_PHONE": RecommendationRule(
            rule_id="RULE_CONTACT_PHONE",
            recommendation_id="REC_ADD_PHONE",
            category=RecommendationCategory.CONTACT,
            title="Add your phone number",
            description="No phone number was found in your resume header.",
            why_it_matters="Placement cells and recruiters often call to schedule tests and interviews.",
            suggested_action="Add your mobile number with country code (e.g. +91) in the header.",
            actionability=1.0,
        ),
        "IMP_CONTACT_MISSING_DEV_PROFILES": RecommendationRule(
            rule_id="RULE_CONTACT_PROFILES",
            recommendation_id="REC_ADD_PROFILE_LINKS",
            category=RecommendationCategory.CONTACT,
            title="Add your GitHub or LinkedIn link",
            description="No LinkedIn, GitHub, portfolio or coding-profile link was found.",
            why_it_matters="Links let recruiters check your code and background quickly, which builds trust in your resume.",
            suggested_action="Add the links you already have (LinkedIn, GitHub, LeetCode/Codeforces) to the header.",
            action_steps=["Only add profiles that exist and are up to date."],
            actionability=0.9,
        ),
        # -- education ----------------------------------------------------------
        "IMP_EDU_MISSING_CGPA": RecommendationRule(
            rule_id="RULE_EDU_SCORE",
            recommendation_id="REC_ADD_ACADEMIC_SCORE",
            category=RecommendationCategory.EDUCATION,
            title="Add your CGPA or percentage",
            description="Your main degree entry does not show a CGPA or percentage.",
            why_it_matters="Many companies have a CGPA cut-off. A missing score can make your resume fail that check.",
            suggested_action="Write your current CGPA in the format 'CGPA: 8.2/10' next to your degree.",
            actionability=0.95,
        ),
        "IMP_EDU_MISSING_YEAR": RecommendationRule(
            rule_id="RULE_EDU_YEAR",
            recommendation_id="REC_ADD_GRADUATION_YEAR",
            category=RecommendationCategory.EDUCATION,
            title="Add your graduation year",
            description="Your education entry does not show when you started or will graduate.",
            why_it_matters="Companies hire for a specific batch, so recruiters need your graduation year.",
            suggested_action="Add the years as '2022 - 2026' or 'Expected May 2026'.",
            actionability=1.0,
        ),
        "IMP_EDU_MISSING_DEGREE": RecommendationRule(
            rule_id="RULE_EDU_DEGREE",
            recommendation_id="REC_ADD_DEGREE_NAME",
            category=RecommendationCategory.EDUCATION,
            title="Name your degree and branch",
            description="The degree name could not be identified in your education entry.",
            why_it_matters="Job eligibility is usually defined by degree and branch (e.g. B.Tech in CSE/ICT).",
            suggested_action="Write the degree in a standard form such as 'B.Tech in Information and Communication Technology'.",
            actionability=1.0,
        ),
        # -- project content ----------------------------------------------------
        "IMP_WEAK_PROJECT_DESCRIPTION": RecommendationRule(
            rule_id="RULE_WEAK_PROJECTS",
            recommendation_id="REC_IMPROVE_PROJECT_DESCRIPTIONS",
            category=RecommendationCategory.PROJECT_DESCRIPTION,
            title="Explain your projects in more detail",
            description="Some project descriptions are too short to show what you built and how.",
            why_it_matters=(
                "Interviewers pick questions from your projects. A clear description shows real understanding "
                "and gives them something to ask about."
            ),
            suggested_action="Rewrite each listed project as 2-3 bullets: the problem, what you built, and the result.",
            action_steps=[
                "Say what problem the project solves and for whom.",
                "Describe your own contribution (not just the team's).",
                "Name the technologies you actually used and what each was used for.",
                "Mention an implementation detail (e.g. how data is stored, an algorithm, an API design).",
                "Add a real outcome if you have one (users, accuracy, speed) - do not make one up.",
            ],
            actionability=0.8,
        ),
        "IMP_PASSIVE_PHRASING": RecommendationRule(
            rule_id="RULE_PASSIVE_PHRASING",
            recommendation_id="REC_USE_ACTION_VERBS",
            category=RecommendationCategory.CONTENT,
            title="Start bullets with action verbs",
            description="Some bullets start with weak phrases like 'worked on' or 'responsible for'.",
            why_it_matters="Action verbs make it clear what you did yourself, which is what recruiters scan for.",
            suggested_action="Replace the opening phrase with a verb that says what you did (Built, Designed, Implemented, Tested).",
            action_steps=[
                "'Worked on the login module' -> 'Implemented the login module using JWT'.",
                "Keep the facts the same; only change how the sentence starts.",
            ],
            actionability=0.95,
            merge_key="action_verbs",
        ),
        "IMP_LACK_OF_ACTION_VERBS": RecommendationRule(
            rule_id="RULE_FEW_ACTION_VERBS",
            recommendation_id="REC_USE_ACTION_VERBS",
            category=RecommendationCategory.CONTENT,
            title="Start bullets with action verbs",
            description="Few of your bullets start with a clear action verb.",
            why_it_matters="Action verbs make it clear what you did yourself, which is what recruiters scan for.",
            suggested_action="Begin each bullet with a verb that describes your work (Built, Designed, Implemented, Tested).",
            actionability=0.95,
            merge_key="action_verbs",
        ),
        "IMP_LACK_OF_MEASURABLE_IMPACT": RecommendationRule(
            rule_id="RULE_NO_MEASURABLE_IMPACT",
            recommendation_id="REC_ADD_REAL_OUTCOMES",
            category=RecommendationCategory.CONTENT,
            title="Mention real results where you have them",
            description="None of your project or experience bullets mention a measurable result.",
            why_it_matters="Results show the work was finished and useful. Numbers make that easy to see at a glance.",
            suggested_action=(
                "Where you actually measured something, add it (users, accuracy, response time, dataset size, test coverage). "
                "If you did not measure anything, describe the concrete outcome in words instead."
            ),
            action_steps=[
                "Only use numbers you can explain and back up in an interview.",
                "Good sources: your test results, model evaluation, app analytics, load tests, dataset size.",
                "No numbers? 'Deployed for the college fest and used by participants' is still a real outcome.",
            ],
            actionability=0.6,
        ),
        "IMP_DUPLICATE_BULLET_CONTENT": RecommendationRule(
            rule_id="RULE_DUPLICATE_BULLETS",
            recommendation_id="REC_REMOVE_DUPLICATE_BULLETS",
            category=RecommendationCategory.CONTENT,
            title="Remove repeated bullet points",
            description="The same or almost the same bullet appears more than once.",
            why_it_matters="Repetition wastes space and makes the resume look copy-pasted.",
            suggested_action="Keep the bullet where it fits best and rewrite the other one to describe different work.",
            actionability=0.9,
            merge_key="duplicate_bullets",
        ),
        "IMP_GENERIC_RESUME_CLICHES": RecommendationRule(
            rule_id="RULE_GENERIC_CLICHES",
            recommendation_id="REC_REPLACE_GENERIC_PHRASES",
            category=RecommendationCategory.CONTENT,
            title="Replace generic phrases with specifics",
            description="Some lines use generic phrases (like 'using modern technologies') that do not say anything specific.",
            why_it_matters="Specific details are more believable and give interviewers something concrete to discuss.",
            suggested_action="Replace the generic phrase with the actual technology, feature or task.",
            actionability=0.85,
        ),
        # -- skills -------------------------------------------------------------
        "IMP_LOW_SKILL_INVENTORY": RecommendationRule(
            rule_id="RULE_LOW_SKILL_INVENTORY",
            recommendation_id="REC_IMPROVE_SKILL_VISIBILITY",
            category=RecommendationCategory.SKILLS,
            title="Make the skills you already have visible",
            description="Only a few technical skills were found on your resume.",
            why_it_matters="Recruiters and screening software look for skill keywords. Skills you used but did not list are invisible to them.",
            suggested_action="List every technology you have genuinely used in your projects, courses or internships in the Skills section.",
            action_steps=[
                "Do not add skills you have not used - you may be asked about any of them."
            ],
            actionability=0.85,
            merge_key="skill_visibility",
        ),
        "IMP_POOR_SKILL_CATEGORIZATION": RecommendationRule(
            rule_id="RULE_SKILL_ORGANIZATION",
            recommendation_id="REC_ORGANIZE_SKILLS",
            category=RecommendationCategory.SKILLS,
            title="Group your skills by type",
            description="Your skills are not organized into clear groups.",
            why_it_matters="Grouped skills are faster to scan and show the breadth of what you know.",
            suggested_action="Split the Skills section into lines such as Languages, Frameworks, Databases and Tools.",
            actionability=0.9,
        ),
        "IMP_MISSING_SOFT_SKILLS": RecommendationRule(
            rule_id="RULE_SOFT_SKILLS",
            recommendation_id="REC_SHOW_SOFT_SKILLS",
            category=RecommendationCategory.SKILLS,
            title="Show teamwork or communication through examples",
            description="No soft skills (teamwork, communication, leadership) were found.",
            why_it_matters="Companies also assess how you work with others, especially in HR and group rounds.",
            suggested_action=(
                "If you have led or worked in a team (club, hackathon, group project), mention it in a bullet "
                "or list those skills separately from technical skills."
            ),
            action_steps=[
                "Showing a soft skill in a real example is stronger than only listing the word."
            ],
            actionability=0.7,
        ),
        "IMP_UNSUBSTANTIATED_SKILLS": RecommendationRule(
            rule_id="RULE_UNSUBSTANTIATED_SKILLS",
            recommendation_id="REC_BACK_SKILLS_WITH_WORK",
            category=RecommendationCategory.SKILLS,
            title="Back up listed skills with your work",
            description="Some listed skills do not appear in any project or experience entry.",
            why_it_matters="Interviewers trust skills more when they can see where you used them.",
            suggested_action="For key skills, mention where you used them in a project or internship bullet - or remove skills you have not used.",
            actionability=0.7,
        ),
        "IMP_DUPLICATE_SKILLS": RecommendationRule(
            rule_id="RULE_DUPLICATE_SKILLS",
            recommendation_id="REC_REMOVE_DUPLICATE_SKILLS",
            category=RecommendationCategory.SKILLS,
            title="Remove repeated skills",
            description="The same skill is listed more than once (sometimes under different names).",
            why_it_matters="Duplicates take space and can look like padding.",
            suggested_action="Keep each skill once, using its standard name (e.g. 'JavaScript', not both 'JS' and 'JavaScript').",
            actionability=1.0,
        ),
        # -- formatting ---------------------------------------------------------
        "IMP_INCONSISTENT_HEADINGS": RecommendationRule(
            rule_id="RULE_FMT_HEADINGS",
            recommendation_id="REC_CONSISTENT_HEADINGS",
            category=RecommendationCategory.FORMATTING,
            title="Use one heading style",
            description="Section headings use different capitalization or punctuation.",
            why_it_matters="Consistent headings make sections easy to find and easy for software to detect.",
            suggested_action="Write all headings the same way, e.g. all in capitals with no colon: EDUCATION, PROJECTS, SKILLS.",
            actionability=1.0,
        ),
        "IMP_UNSTRUCTURED_WALL_OF_TEXT": RecommendationRule(
            rule_id="RULE_FMT_WALL_OF_TEXT",
            recommendation_id="REC_BREAK_LONG_PARAGRAPHS",
            category=RecommendationCategory.FORMATTING,
            title="Break long paragraphs into bullets",
            description="Some parts of your resume are long paragraphs instead of bullet points.",
            why_it_matters="Recruiters skim a resume in under a minute. Bullets are much faster to read than paragraphs.",
            suggested_action="Split each long paragraph into 2-4 short bullets of one or two lines each.",
            actionability=0.9,
        ),
        "IMP_INCONSISTENT_BULLET_FORMATTING": RecommendationRule(
            rule_id="RULE_FMT_BULLETS",
            recommendation_id="REC_CONSISTENT_BULLETS",
            category=RecommendationCategory.FORMATTING,
            title="Make bullet points consistent",
            description="Bullet markers or bullet lengths are inconsistent, or some bullets are empty.",
            why_it_matters="Uneven bullets make the resume look unfinished.",
            suggested_action="Use one bullet symbol throughout and keep each bullet to one or two lines.",
            actionability=0.95,
        ),
        "IMP_EXCESSIVE_WHITESPACE": RecommendationRule(
            rule_id="RULE_FMT_WHITESPACE",
            recommendation_id="REC_FIX_SPACING",
            category=RecommendationCategory.FORMATTING,
            title="Tidy up spacing",
            description="There are extra blank lines or irregular spaces.",
            why_it_matters="Uneven spacing wastes space and makes the layout look careless.",
            suggested_action="Use a single blank line between sections and remove extra spaces inside lines.",
            actionability=1.0,
        ),
        "IMP_INCONSISTENT_DATE_FORMATS": RecommendationRule(
            rule_id="RULE_FMT_DATES",
            recommendation_id="REC_CONSISTENT_DATES",
            category=RecommendationCategory.FORMATTING,
            title="Write all dates the same way",
            description="Dates are written in different formats (e.g. 'May 2024' and '05/2024').",
            why_it_matters="Consistent dates look professional and are parsed correctly by screening software.",
            suggested_action="Pick one format, such as 'May 2024 - Jul 2024', and use it everywhere.",
            actionability=1.0,
        ),
        "FMT_REPEATED_SECTION_HEADING": RecommendationRule(
            rule_id="RULE_FMT_REPEATED_HEADING",
            recommendation_id="REC_MERGE_REPEATED_SECTIONS",
            category=RecommendationCategory.FORMATTING,
            title="Merge repeated sections",
            description="The same section heading appears more than once.",
            why_it_matters="Split sections confuse readers and screening software.",
            suggested_action="Combine the entries under a single heading.",
            actionability=0.95,
        ),
        "FMT_POOR_SECTION_ORDER": RecommendationRule(
            rule_id="RULE_FMT_SECTION_ORDER",
            recommendation_id="REC_REORDER_SECTIONS",
            category=RecommendationCategory.FORMATTING,
            title="Reorder your sections",
            description="Your sections are in an unusual order.",
            why_it_matters="Recruiters expect the most important information first.",
            suggested_action="For a fresher, a good order is Education, Skills, Projects, Experience, then Achievements.",
            actionability=0.9,
        ),
        "FMT_FRAGMENTED_TEXT_BLOCKS": RecommendationRule(
            rule_id="RULE_FMT_FRAGMENTED",
            recommendation_id="REC_FIX_BROKEN_LINES",
            category=RecommendationCategory.FORMATTING,
            title="Fix broken or split lines",
            description="Some text appears split into many short fragments.",
            why_it_matters="Broken lines are often a sign of a layout (tables, columns) that screening software reads badly.",
            suggested_action="Use a simple single-column layout and keep each entry's text together.",
            actionability=0.8,
        ),
        "FMT_DUPLICATE_BULLET_CONTENT": RecommendationRule(
            rule_id="RULE_FMT_DUPLICATE_BULLETS",
            recommendation_id="REC_REMOVE_DUPLICATE_BULLETS",
            category=RecommendationCategory.CONTENT,
            title="Remove repeated bullet points",
            description="The same or almost the same bullet appears more than once.",
            why_it_matters="Repetition wastes space and makes the resume look copy-pasted.",
            suggested_action="Keep the bullet where it fits best and rewrite the other one to describe different work.",
            actionability=0.9,
            merge_key="duplicate_bullets",
        ),
        "FMT_UNSTRUCTURED_SECTION_DESCRIPTIONS": RecommendationRule(
            rule_id="RULE_FMT_UNSTRUCTURED_SECTION",
            recommendation_id="REC_USE_BULLETS_IN_SECTION",
            category=RecommendationCategory.FORMATTING,
            title="Use bullets inside entries",
            description="Some entries are described in running text instead of bullets.",
            why_it_matters="Bullets make each contribution stand out on its own.",
            suggested_action="Describe each entry with 2-4 bullets, one contribution per bullet.",
            actionability=0.9,
        ),
        "FMT_INCONSISTENT_BULLET_PUNCTUATION": RecommendationRule(
            rule_id="RULE_FMT_BULLET_PUNCTUATION",
            recommendation_id="REC_CONSISTENT_BULLET_PUNCTUATION",
            category=RecommendationCategory.FORMATTING,
            title="End bullets the same way",
            description="Some bullets end with a full stop and others do not.",
            why_it_matters="A small detail, but consistency signals care and attention to detail.",
            suggested_action="Either end every bullet with a full stop or none of them.",
            actionability=1.0,
        ),
        "FMT_INCONSISTENT_INLINE_DELIMITERS": RecommendationRule(
            rule_id="RULE_FMT_DELIMITERS",
            recommendation_id="REC_CONSISTENT_SEPARATORS",
            category=RecommendationCategory.FORMATTING,
            title="Use one separator style",
            description="Lines mix separators such as '|', ',' and '-' between details.",
            why_it_matters="Mixed separators make lines harder to read and to parse.",
            suggested_action="Use one separator (for example ' | ') between details like company, location and dates.",
            actionability=1.0,
        ),
        # -- extraction ---------------------------------------------------------
        "IMP_EXTRACTION_UNCERTAINTY": RecommendationRule(
            rule_id="RULE_EXTRACTION_UNCERTAINTY",
            recommendation_id="REC_CHECK_EXTRACTION",
            category=RecommendationCategory.EXTRACTION,
            title="Check that your resume was read correctly",
            description="The system was not confident it read your resume correctly, so some results may be wrong.",
            why_it_matters=(
                "Many companies use automated screening. If this tool struggled to read your resume, "
                "those systems may struggle too."
            ),
            suggested_action="Review the extracted details for mistakes, and if many are wrong, switch to a simple single-column template.",
            action_steps=[
                "Avoid tables, text boxes, icons and two-column layouts.",
                "Export the PDF from Word/Google Docs/LaTeX rather than from an image or scan.",
            ],
            actionability=0.7,
        ),
    }
)


GENERIC_FALLBACK_RULE_ID = "RULE_GENERIC_FALLBACK"


def get_rule(issue_id: str) -> Optional[RecommendationRule]:
    return RULES.get(issue_id)


__all__ = [
    "GENERIC_FALLBACK_RULE_ID",
    "RULES",
    "RULE_SET_VERSION",
    "RecommendationRule",
    "SECTION_GUIDANCE",
    "get_rule",
    "missing_section_rule",
    "section_label",
]
