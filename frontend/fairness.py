"""
Sprint 6 · US-19 Check Scoring and Matching for Fairness (DR-09)

Question: could a personal detail that has nothing to do with the job change a student's
score or job match?

How we check: take a resume, make copies where ONLY a personal detail is different
(another name, a stated gender, date of birth and religion, a home address, another college,
another email and phone), run every copy through the same scoring and matching code, and
compare. Every result must be exactly the same. Any difference is recorded as a fairness
issue for the admin to review (acceptance criterion 3).

This is a "counterfactual" test. It shows the rules ignore these details. It can't prove
statistical fairness across groups of real students, because that needs outcome data the
system doesn't collect, so the app never claims that.
"""

import re

from resume_parser import parse_text

# Acceptance criterion 1: the main factors are identifiable.
# These describe analyze_resume() and compare_skills() in app.py. A test checks the titles
# still match the code, so this list can't silently drift.
SCORING_FACTORS = [
    ("Core resume sections", 20, "Education and Skills sections are both present."),
    ("Projects", 20, "A Projects section is present."),
    ("Experience", 20, "An Experience or internship section is present."),
    ("Contact details", 20, "An email address and a phone number can be found (only whether they exist)."),
    ("Relevant skills", 20, "At least 3 skills from the skills list are found in the resume text."),
]
MATCHING_FACTORS = [
    ("Required skills", "Skills from the skills list that appear in the job description."),
    ("Skills you have", "Required skills that also appear in your resume text."),
    ("Match %", "Skills you have ÷ required skills × 100. Nothing else is counted."),
]

# Acceptance criterion 2: characteristics that are not relevant to the job.
NOT_USED = [
    "Name",
    "Gender",
    "Photo (only the text of a resume is read)",
    "Date of birth and age",
    "Religion, caste and category",
    "Marital status",
    "Nationality",
    "Home address and home town",
    "College name",
    "The actual email address and phone number (only whether they exist)",
]

PERSONAL_DETAILS = {
    "Gender stated: female": "Gender: Female",
    "Gender stated: male": "Gender: Male",
    "Date of birth, religion, category, marital status, nationality":
        "Date of Birth: 14 March 2004\nReligion: Hindu\nCategory: OBC\nMarital Status: Single\nNationality: Indian",
    "Home address": "Address: 12 Station Road, Gorakhpur, Uttar Pradesh 273001",
}
COLLEGE_RE = re.compile(r"[A-Z][A-Za-z.&' ]*?(?:University|College|Institute(?: of Technology)?)")


def results(parsed, analyze, match, jobs):
    """Everything automated that a person could act on, in a form that can be compared."""
    analysis = analyze(parsed)
    record = {"parsed": parsed}
    return {
        "Score": analysis["score"],
        "Checklist": [(c["title"], c["passed"]) for c in analysis["criteria"]],
        "Skills found": [s for g in analysis["skills"] for s in g["skills"]],
        "Job match": [(job["id"], match(record, job["description"])["match_percent"],
                       match(record, job["description"])["matched_skills"]) for job in jobs],
    }


def variants(text, parsed):
    """(label, changed text) pairs. Each one changes a single kind of personal detail."""
    out = []
    name = parsed["contact"].get("name")
    if name:
        for new_name in ("Fatima Shaikh", "Joseph D'Souza"):
            out.append((f"Different name ({new_name})", text.replace(name, new_name)))
    for label, block in PERSONAL_DETAILS.items():
        out.append((label, f"{text.rstrip()}\nPERSONAL DETAILS\n{block}\n"))
    college = COLLEGE_RE.search(text)
    if college:
        out.append(("Different college", text.replace(college.group(), "Government Engineering College, Bhuj")))
    changed = text
    for old, new in ((parsed["contact"].get("email"), "student.one@example.edu"),
                     (parsed["contact"].get("phone"), "+91 90000 11111")):
        if old:
            changed = changed.replace(old, new)
    if changed != text:
        out.append(("Different email and phone", changed))
    return out


def check_text(text, analyze, match, jobs):
    """Run every variant of one resume. Returns checks, passed and the differences found."""
    base_parsed = parse_text(text)
    base = results(base_parsed, analyze, match, jobs)
    issues, all_variants = [], variants(text, base_parsed)
    for label, changed in all_variants:
        after = results(parse_text(changed), analyze, match, jobs)
        for field, value in base.items():
            if after[field] != value:
                issues.append({"variant": label, "field": field, "before": str(value), "after": str(after[field])})
                break
    return {"checks": len(all_variants), "passed": len(all_variants) - len(issues), "issues": issues}
