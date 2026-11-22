"""
Sprint 5 NLP evaluation (Module E).

Runs the integrated Sprint 5 workflow on the labelled fixture resumes and checks the
aggregated placement report against the hand-written labels:

1. Weakness prevalence - for every issue in the Sprint 3 labels, the report's student count
   must lie between the number of resumes labelled as having it (expected_issues) and the
   number not labelled as forbidden for it (forbidden_issues).
2. Skill-gap prevalence - for the labelled Sprint 4 resume/job pairs, the report's count of
   students missing each skill must lie between the labelled 'missing' count and the number of
   pairs where the skill was not labelled 'have'.
3. Privacy - no name, email, phone, filename or student reference appears in the report.
4. Determinism - building twice gives identical JSON.

Usage (from backend/):  python scripts/evaluate_nlp_sprint5.py [--json]
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.nlp.placement_reports import Sprint5Workflow  # noqa: E402

FIXTURES = BACKEND / "tests" / "nlp" / "fixtures"
CREATED = datetime(2026, 11, 22, tzinfo=timezone.utc)


def _sprint3_cohort(wf: Sprint5Workflow):
    labels = {k: v for k, v in json.loads((FIXTURES / "sprint3" / "labels.json").read_text()).items()
              if not k.startswith("_")}
    students = []
    for i, name in enumerate(sorted(labels)):
        path = FIXTURES / "sprint3" / f"{name}.txt"
        students.append(wf.analyze_student(path.read_text(encoding="utf-8"), path.name, student_ref=f"eval-{i}",
                                           department="CSE" if i % 2 else "ICT", batch_year=2026,
                                           created_at=CREATED))
    return labels, students


def _weakness_check(labels, report):
    counts = {w.issue_id: w.students_affected for w in report.resume_weaknesses}
    issues = sorted({i for v in labels.values() for i in v.get("expected_issues", []) + v.get("forbidden_issues", [])})
    rows, ok = [], 0
    for issue in issues:
        lower = sum(issue in v.get("expected_issues", []) for v in labels.values())
        upper = len(labels) - sum(issue in v.get("forbidden_issues", []) for v in labels.values())
        got = counts.get(issue)
        # The report lists the top issues only; an issue missing from it is fine when its lower bound is
        # no higher than the smallest listed count.
        floor = min(counts.values()) if counts else 0
        passed = (lower <= got <= upper) if got is not None else (lower <= floor)
        ok += passed
        rows.append({"issue_id": issue, "labelled_min": lower, "labelled_max": upper, "report": got, "pass": passed})
    return {"checked": len(rows), "passed": ok, "accuracy": round(ok / len(rows), 3) if rows else None,
            "rows": rows}


def _gap_check(wf: Sprint5Workflow):
    labels = json.loads((FIXTURES / "sprint4" / "labels.json").read_text())
    pairs = labels["gaps"]
    by_student: dict[str, list[str]] = {}
    for key in pairs:
        cand, job = key.split("|")
        by_student.setdefault(cand, []).append(job)
    students = []
    for i, (cand, jobs) in enumerate(sorted(by_student.items())):
        text = (FIXTURES / labels["candidates"][cand]).read_text(encoding="utf-8")
        jds = [(FIXTURES / "sprint4" / "jobs" / f"{j}.txt").read_text(encoding="utf-8") for j in jobs]
        students.append(wf.analyze_student(text, f"{cand}.txt", jds, student_ref=f"gap-{i}", department="CSE",
                                           created_at=CREATED))
    report = wf.build_report(students, generated_at="evaluation")
    got = {g.skill: g.students_missing for g in report.common_skill_gaps if g.level == "required"}
    skills = sorted({s for v in pairs.values() for s in v["missing"] + v["have"]})
    rows, ok = [], 0
    for skill in skills:
        # count per student (a student is counted once even if several jobs need the skill)
        lower = sum(any(skill in pairs[f"{c}|{j}"]["missing"] for j in js) for c, js in by_student.items())
        upper = sum(any(skill not in pairs[f"{c}|{j}"]["have"] for j in js) for c, js in by_student.items())
        value = got.get(skill, 0)
        passed = lower <= value <= upper
        ok += passed
        rows.append({"skill": skill, "labelled_min": lower, "labelled_max": upper, "report": value, "pass": passed})
    return {"checked": len(rows), "passed": ok, "accuracy": round(ok / len(rows), 3) if rows else None,
            "rows": rows}, students


def _privacy_check(report, students):
    text = report.model_dump_json().lower()
    leaks = []
    for s in students:
        r = s.record
        c = r.profile.contact if r.profile else None
        for v in ([c.full_name, c.email, c.phone] if c else []) + [r.student_ref, r.profile and r.profile.filename]:
            if v and len(v) >= 4 and v.lower() in text:
                leaks.append(v)
    return {"values_checked": sum(1 for _ in students) * 5, "leaks": len(leaks)}


def evaluate() -> dict:
    started = time.perf_counter()
    wf = Sprint5Workflow()
    labels, students = _sprint3_cohort(wf)
    report = wf.build_report(students, generated_at="evaluation")
    again = wf.build_report(students, generated_at="evaluation")
    gaps, gap_students = _gap_check(wf)
    stage_failures = sum(1 for s in students + gap_students for v in s.stage_status.values() if v == "failed")
    return {
        "students": len(students),
        "weakness_prevalence": _weakness_check(labels, report),
        "skill_gap_prevalence": gaps,
        "privacy": _privacy_check(report, students + gap_students),
        "deterministic": report.model_dump_json() == again.model_dump_json(),
        "stage_failures": stage_failures,
        "training_recommendations": len(report.training_recommendations),
        "insights": len(report.insights),
        "limitations": len(report.limitations),
        "seconds": round(time.perf_counter() - started, 2),
    }


def main() -> None:
    result = evaluate()
    if "--json" in sys.argv:
        print(json.dumps(result, indent=2))
        return
    w, g = result["weakness_prevalence"], result["skill_gap_prevalence"]
    print(f"Students analysed:           {result['students']}")
    print(f"Weakness prevalence in label range: {w['passed']}/{w['checked']} ({w['accuracy']})")
    for r in w["rows"]:
        if not r["pass"]:
            print(f"   outside range: {r['issue_id']} report={r['report']} labels={r['labelled_min']}-{r['labelled_max']}")
    print(f"Skill-gap prevalence in label range: {g['passed']}/{g['checked']} ({g['accuracy']})")
    for r in g["rows"]:
        if not r["pass"]:
            print(f"   outside range: {r['skill']} report={r['report']} labels={r['labelled_min']}-{r['labelled_max']}")
    print(f"Privacy leaks:               {result['privacy']['leaks']}")
    print(f"Deterministic:               {result['deterministic']}")
    print(f"Stage failures:              {result['stage_failures']}")
    print(f"Recommendations / insights / limitations: {result['training_recommendations']} / "
          f"{result['insights']} / {result['limitations']}")
    print(f"Time: {result['seconds']} s")


if __name__ == "__main__":
    main()
