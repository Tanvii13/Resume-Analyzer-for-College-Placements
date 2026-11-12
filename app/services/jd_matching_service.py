"""Simple explainable matching between extracted skills and job requirements."""
import re

def _normalize(value) -> str:
    if isinstance(value, dict):
        value = value.get("name") or value.get("skill") or value.get("title") or ""
    return re.sub(r"\s+", " ", str(value)).strip().casefold()

def calculate_jd_match(resume_data: dict, job_data: dict) -> dict:
    if not isinstance(resume_data, dict) or not isinstance(job_data, dict):
        raise ValueError("resume_data and job_data must be objects")

    resume_skills = {_normalize(x) for x in resume_data.get("skills", []) if _normalize(x)}
    required = list(dict.fromkeys(_normalize(x) for x in job_data.get("required_skills", []) if _normalize(x)))
    optional = list(dict.fromkeys(_normalize(x) for x in job_data.get("optional_skills", []) if _normalize(x)))

    matched = [skill for skill in required if skill in resume_skills]
    missing = [skill for skill in required if skill not in resume_skills]
    optional_found = [skill for skill in optional if skill in resume_skills]
    percentage = round((len(matched) / len(required)) * 100, 2) if required else 0.0

    suggestions = [f"Consider adding evidence of {skill} if you have that skill." for skill in missing]
    return {
        "match_percentage": percentage,
        "matched_skills": matched,
        "missing_skills": missing,
        "optional_skills_found": optional_found,
        "suggestions": suggestions,
        "disclaimer": "This percentage compares listed skills only; it is not a hiring prediction.",
    }
