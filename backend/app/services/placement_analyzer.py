
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


def analyze_placement_readiness(resume_data: dict) -> dict:
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
    }
