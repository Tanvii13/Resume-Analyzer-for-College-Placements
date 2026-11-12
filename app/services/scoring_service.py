"""Deterministic, explainable resume scoring; no external AI dependency."""
from typing import Any

WEIGHTS = {
    "skills": 30,
    "education": 20,
    "projects": 20,
    "experience": 20,
    "completeness": 10,
}

def _list(data: dict, key: str) -> list:
    value = data.get(key, [])
    return value if isinstance(value, list) else []

def _text(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return " ".join(str(v) for v in item.values() if v is not None).strip()
    return str(item).strip()

def score_resume(extracted_data: dict) -> dict:
    """Score extracted resume fields and explain every awarded point."""
    if not isinstance(extracted_data, dict):
        raise ValueError("extracted_data must be an object")

    skills = [x for x in _list(extracted_data, "skills") if _text(x)]
    education = [x for x in _list(extracted_data, "education") if _text(x)]
    projects = [x for x in _list(extracted_data, "projects") if _text(x)]
    experience = [x for x in _list(extracted_data, "experience") if _text(x)]

    # Category scoring is intentionally transparent and deterministic.
    # It measures presence/completeness, not a hiring decision or candidate quality.
    def category(count: int, maximum: int, threshold: int, reason: str) -> dict:
        points = round(maximum * min(count / threshold, 1), 2)
        return {
            "score": points,
            "maximum": maximum,
            "reason": reason if count else f"No {reason.lower()} were extracted.",
            "evidence_count": count,
        }

    scores = {
        "skills": category(len(skills), WEIGHTS["skills"], 8,
                           "Technical or professional skills were extracted."),
        "education": category(len(education), WEIGHTS["education"], 1,
                              "At least one education entry was extracted."),
        "projects": category(len(projects), WEIGHTS["projects"], 2,
                             "Project entries were extracted."),
        "experience": category(len(experience), WEIGHTS["experience"], 2,
                               "Experience entries were extracted."),
    }

    contact_present = bool(extracted_data.get("email") or extracted_data.get("phone"))
    summary_present = bool(extracted_data.get("summary"))
    completeness_points = (5 if contact_present else 0) + (5 if summary_present else 0)
    scores["completeness"] = {
        "score": completeness_points,
        "maximum": WEIGHTS["completeness"],
        "reason": "Contact details and summary are present." if completeness_points == 10
                  else "Add or verify contact details and a short professional summary.",
        "evidence_count": int(contact_present) + int(summary_present),
    }

    total = round(sum(item["score"] for item in scores.values()), 2)
    warnings = []
    if not skills: warnings.append("No skills were extracted; verify the resume parsing result.")
    if not education: warnings.append("No education details were extracted.")
    if not projects: warnings.append("No projects were extracted.")
    if not experience: warnings.append("No experience details were extracted.")
    if extracted_data.get("extraction_complete") is False:
        warnings.append("Text extraction was marked incomplete; score may be unreliable.")

    return {
        "overall_score": total,
        "maximum_score": 100,
        "category_scores": scores,
        "warnings": warnings,
        "disclaimer": (
            "This is a rule-based completeness and relevance aid, not a hiring decision. "
            "Scores depend on the quality of extracted resume data."
        ),
    }
