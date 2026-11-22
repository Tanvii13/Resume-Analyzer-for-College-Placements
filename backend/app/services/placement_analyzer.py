
"""
Placement readiness analysis service.

Evaluates structured resume information against proposed
placement-oriented criteria.

This service does not:
- Extract text from PDF or DOCX files.
- Extract skills from raw resume text.
- Calculate an overall resume score.
- Access the database.
"""

from typing import Any
from numbers import Number
import re

RUBRIC_VERSION = "1.0"

PLACEMENT_CRITERIA = {
    "academic_profile": {
        "name": "Academic Profile",
        "description": "Academic and educational information.",
    },
    "technical_skills": {
        "name": "Technical Skills",
        "description": "Technical skills relevant to placements.",
    },
    "soft_skills": {
        "name": "Non-Technical Skills",
        "description": "Non-technical and interpersonal skills.",
    },
    "projects": {
        "name": "Projects",
        "description": "Academic, personal, or practical projects.",
    },
    "experience": {
        "name": "Experience",
        "description": "Internships, employment, or other relevant experience.",
    },
    "achievements": {
        "name": "Achievements",
        "description": "Relevant accomplishments and recognitions.",
    },
}


# Proposed details used to assess academic profile completeness.
# CGPA/grade is optional and is not used as a pass/fail threshold.
ACADEMIC_DETAIL_FIELDS = {
    "degree": ("degree", "qualification"),
    "field_of_study": ("field_of_study", "major", "specialization"),
    "institution": ("institution", "college", "university"),
    "graduation_year": ("graduation_year", "expected_graduation_year"),
}


# Proposed details used to assess project completeness.
PROJECT_DETAIL_FIELDS = {
    "name": ("name", "title", "project_name"),
    "description": ("description", "summary", "overview"),
    "technologies": ("technologies", "tech_stack", "tools"),
    "role": ("role", "contribution", "responsibilities"),
    "outcome": ("outcome", "result", "impact", "achievements"),
}


# Proposed details used to assess experience completeness.
EXPERIENCE_DETAIL_FIELDS = {
    "organization": ("organization", "company", "employer"),
    "role": ("role", "title", "position"),
    "responsibilities": ("responsibilities", "description", "duties"),
    "duration": ("duration", "dates", "period"),
    "achievements": ("achievements", "results", "impact"),
}


def _extract_evidence(value: Any) -> list[str]:
    """Convert supported structured values into readable evidence."""

    evidence = []

    if isinstance(value, str):
        cleaned_value = value.strip()

        if cleaned_value:
            evidence.append(cleaned_value)

    elif isinstance(value, Number) and not isinstance(value, bool):
        evidence.append(str(value))

    elif isinstance(value, (list, tuple)):
        for item in value:
            evidence.extend(_extract_evidence(item))

    elif isinstance(value, dict):
        for item in value.values():
            evidence.extend(_extract_evidence(item))

    return evidence


def _has_value(value: Any) -> bool:
    """Check whether a field contains meaningful non-empty information."""

    return bool(_extract_evidence(value))


def _assess_detail_item(
    item: Any,
    detail_fields: dict,
) -> dict:
    """Evaluate the completeness of one academic, project, or experience entry."""

    found_details = []
    missing_details = []

    for detail_name, accepted_keys in detail_fields.items():
        found = any(
            key in item and _has_value(item[key])
            for key in accepted_keys
        )

        if found:
            found_details.append(detail_name)
        else:
            missing_details.append(detail_name)

    if not found_details:
        status = "insufficient"
    elif missing_details:
        status = "partial"
    else:
        status = "complete"

    return {
        "status": status,
        "found_details": found_details,
        "missing_details": missing_details,
    }


def _assess_section_details(
    value: Any,
    detail_fields: dict,
) -> dict:
    """Evaluate academic, project, or experience details."""

    if isinstance(value, dict):
        entries = [value]

    elif isinstance(value, (list, tuple)):
        entries = list(value)

    else:
        entries = [value]

    entry_results = []

    for entry in entries:
        if isinstance(entry, dict):
            entry_results.append(
                _assess_detail_item(entry, detail_fields)
            )
        else:
            entry_results.append(
                _assess_detail_item({}, detail_fields)
            )

    if not entry_results:
        overall_status = "insufficient"

    elif all(
        item["status"] == "complete"
        for item in entry_results
    ):
        overall_status = "complete"

    elif any(
        item["status"] in ("complete", "partial")
        for item in entry_results
    ):
        overall_status = "partial"

    else:
        overall_status = "insufficient"

    return {
        "status": overall_status,
        "entries": entry_results,
    }


def _assess_skills(value: Any) -> dict:
    """Assess listed skills and their supplied supporting evidence."""

    if isinstance(value, (str, dict)):
        entries = [value]

    elif isinstance(value, (list, tuple)):
        entries = list(value)

    else:
        entries = []

    assessed_skills = []

    for entry in entries:

        if isinstance(entry, str):
            skill_name = entry.strip()
            supporting_evidence = []

        elif isinstance(entry, dict):
            skill_name = entry.get("name", entry.get("skill", ""))

            if not isinstance(skill_name, str):
                continue

            skill_name = skill_name.strip()

            supporting_evidence = _extract_evidence(
                entry.get(
                    "evidence",
                    entry.get(
                        "supporting_evidence",
                        entry.get("context"),
                    ),
                )
            )

        else:
            continue

        if not skill_name:
            continue

        assessed_skills.append({
            "name": skill_name,
            "mentioned": True,
            "supporting_evidence": supporting_evidence,
            "evidence_status": (
                "available" if supporting_evidence else "not_provided"
            ),
        })

    return {
        "status": "present" if assessed_skills else "missing",
        "total_skills": len(assessed_skills),
        "skills_with_evidence": sum(
            1 for skill in assessed_skills
            if skill["supporting_evidence"]
        ),
        "skills": assessed_skills,
    }


def _analyze_criterion(
    criterion_id: str,
    resume_data: dict,
) -> dict:
    """Analyze one placement criterion."""

    criterion = PLACEMENT_CRITERIA[criterion_id]
    skill_assessment = None

    if criterion_id not in resume_data:
        status = "not_assessable"
        evidence = []

        explanation = (
            "This information was not supplied to the analyzer, "
            "so this criterion could not be evaluated."
        )

    else:

        if criterion_id in ("technical_skills", "soft_skills"):
            skill_assessment = _assess_skills(
                resume_data[criterion_id]
            )

            evidence = []

            for skill in skill_assessment["skills"]:
                evidence.append(skill["name"])
                evidence.extend(skill["supporting_evidence"])

        else:
            evidence = _extract_evidence(
                resume_data[criterion_id]
            )

        if evidence:
            status = "present"

            explanation = (
                f"Information relevant to {criterion['name'].lower()} "
                "was found in the supplied resume data."
            )

        else:
            status = "missing"

            explanation = (
                f"No information relevant to {criterion['name'].lower()} "
                "was found in the supplied resume data."
            )

    result = {
        "criterion_id": criterion_id,
        "criterion_name": criterion["name"],
        "status": status,
        "evidence": evidence,
        "explanation": explanation,
    }

    if skill_assessment is not None:
        result["skill_assessment"] = skill_assessment

    if criterion_id == "academic_profile" and criterion_id in resume_data:
        result["detail_assessment"] = _assess_section_details(
            resume_data[criterion_id],
            ACADEMIC_DETAIL_FIELDS,
        )

    if criterion_id == "projects" and criterion_id in resume_data:
        result["detail_assessment"] = _assess_section_details(
            resume_data[criterion_id],
            PROJECT_DETAIL_FIELDS,
        )

    elif criterion_id == "experience" and criterion_id in resume_data:
        result["detail_assessment"] = _assess_section_details(
            resume_data[criterion_id],
            EXPERIENCE_DETAIL_FIELDS,
        )

    return result


def analyze_placement_readiness(
    resume_data: dict,
    raw_text: str = "",
    page_count: int | None = None,
) -> dict:
    """
    Analyze structured resume information for placement preparation.

    Returns criterion-wise findings and additional detail-completeness
    assessments for academic profile, projects, and experience.
    """

    if not isinstance(resume_data, dict):
        raise TypeError("resume_data must be a dictionary.")

    results = []

    for criterion_id in PLACEMENT_CRITERIA:
        results.append(
            _analyze_criterion(criterion_id, resume_data)
        )

    return {
    "rubric_version": RUBRIC_VERSION,
    "analysis_type": "placement_readiness",
    "results": results,
    "score_explanations": explain_placement_deductions(
        results,
        raw_text=raw_text,
        page_count=page_count,
    ),
}

def explain_placement_deductions(
    criterion_results: list[dict],
    raw_text: str = "",
    page_count: int | None = None,
) -> list[dict]:
    """
    Explain proposed placement-readiness deductions.

    These are project-defined guidance values, not an official
    institutional placement rubric. Missing input is not treated
    as proof that a resume is deficient.
    """

    deductions = []
    criteria_map = {
        result["criterion_id"]: result
        for result in criterion_results
        if isinstance(result, dict) and "criterion_id" in result
    }

    def add_deduction(code, points, category, explanation):
        deductions.append({
            "code": code,
            "points": points,
            "category": category,
            "explanation": explanation,
        })

    # 1. Institutional email: only evaluate when raw text is supplied.
    if raw_text.strip():
        institutional_email = re.search(
            r"\b[A-Za-z0-9._%+-]+@(?:dau\.ac\.in|daiict\.ac\.in)\b",
            raw_text,
            re.IGNORECASE,
        )
        if not institutional_email:
            add_deduction(
                "DEDUCT_NO_INSTITUTIONAL_EMAIL",
                -10,
                "Contact Information",
                "-10 points: No recognized institutional email was detected. "
                "Include one if required by your placement cell.",
            )

    # 2. Page count: only evaluate when supplied.
    if page_count is not None and page_count > 2:
        add_deduction(
            "DEDUCT_EXCEEDS_PAGE_LIMIT",
            -5,
            "Presentation",
            f"-5 points: The resume has {page_count} pages; "
            "a maximum of two pages is recommended by this project rubric.",
        )

    # 3. Academic profile.
    academic = criteria_map.get("academic_profile")
    if academic:
        if academic.get("status") == "missing":
            add_deduction(
                "DEDUCT_MISSING_ACADEMICS",
                -15,
                "Academic Profile",
                "-15 points: No academic profile information was found "
                "in the supplied resume data.",
            )
        elif (
            academic.get("status") == "present"
            and academic.get("detail_assessment", {}).get("status") == "partial"
        ):
            add_deduction(
                "DEDUCT_PARTIAL_ACADEMICS",
                -5,
                "Academic Profile",
                "-5 points: Some academic details are missing. "
                "Review degree, field of study, institution, and graduation year.",
            )

    # 4. Technical skills.
    technical = criteria_map.get("technical_skills")
    if technical:
        if technical.get("status") == "missing":
            add_deduction(
                "DEDUCT_MISSING_TECH_SKILLS",
                -15,
                "Technical Skills",
                "-15 points: No technical skills were found "
                "in the supplied resume data.",
            )
        elif technical.get("status") == "present":
            skill_count = technical.get(
                "skill_assessment", {}
            ).get("total_skills", 0)

            if skill_count < 4:
                add_deduction(
                    "DEDUCT_LIMITED_TECH_SKILLS",
                    -5,
                    "Technical Skills",
                    f"-5 points: Only {skill_count} technical skill(s) "
                    "were found; at least four are recommended by this project rubric.",
                )

    # 5. Projects.
    projects = criteria_map.get("projects")
    if projects:
        if projects.get("status") == "missing":
            add_deduction(
                "DEDUCT_MISSING_PROJECTS",
                -20,
                "Projects",
                "-20 points: No project information was found "
                "in the supplied resume data.",
            )
        elif (
            projects.get("status") == "present"
            and projects.get("detail_assessment", {}).get("status") == "partial"
        ):
            add_deduction(
                "DEDUCT_PARTIAL_PROJECT_DETAILS",
                -10,
                "Projects",
                "-10 points: Project information is incomplete. "
                "Add details about the project name, description, technologies, "
                "your role, and outcomes.",
            )

    # 6. Soft skills.
    soft_skills = criteria_map.get("soft_skills")
    if soft_skills and soft_skills.get("status") == "missing":
        add_deduction(
            "DEDUCT_MISSING_SOFT_SKILLS",
            -5,
            "Non-Technical Skills",
            "-5 points: No non-technical skills were found "
            "in the supplied resume data.",
        )

    # Deliberately no automatic experience deduction:
    # students applying for fresher roles may not have work experience.

    return deductions
