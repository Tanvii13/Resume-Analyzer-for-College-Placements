"""
Run the Sprint 4 job-matching evaluation on the labelled synthetic fixtures.

Usage (from the backend/ folder):
    python scripts/evaluate_nlp_sprint4.py           # markdown summary
    python scripts/evaluate_nlp_sprint4.py --json    # full JSON

All numbers are computed by running the code (see app/nlp/job_matching/evaluation.py).
The set is small and synthetic: results describe these cases only.
"""

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.nlp.job_matching.evaluation import run_job_matching_evaluation  # noqa: E402

FIXTURES = BACKEND / "tests" / "nlp" / "fixtures"


def fmt(x):
    return "n/a" if x is None else f"{x:.3f}"


def to_markdown(r: dict) -> str:
    a, b, d, e, perf = r["jd_parsing"], r["skill_equivalence"], r["skill_gaps"], r["ranking"], r["performance"]
    lines = [
        f"Labelled set: {r['jobs']} job descriptions x {r['candidates']} student resumes",
        "",
        "| Module | Metric | Value |",
        "|---|---|---|",
        f"| A – JD parsing | Skill precision / recall / F1 | {fmt(a['skill_precision'])} / {fmt(a['skill_recall'])} / {fmt(a['skill_f1'])} |",
        f"| | Required-vs-preferred level accuracy | {fmt(a['level_accuracy'])} |",
    ]
    lines += [f"| | Field accuracy: {k} | {fmt(v)} |" for k, v in a["field_accuracy"].items()]
    lines += [
        f"| B – Skill equivalence | Pair accuracy ({b['pairs']} pairs) | {fmt(b['accuracy'])} |",
        f"| | False-equivalence rate | {fmt(b['false_equivalence_rate'])} |",
        f"| | Missed-equivalence rate | {fmt(b['missed_equivalence_rate'])} |",
        f"| D – Skill gaps | Recall of skills the student has | {fmt(d['have_recall'])} |",
        f"| | Recall of skills the student lacks | {fmt(d['missing_recall'])} |",
        f"| | Skills the student has reported as missing | {d['have_reported_as_missing']} |",
        f"| E – Ranking | NDCG@3 | {fmt(e['ndcg_at_3'])} |",
        f"| | Precision@1 | {fmt(e['precision_at_1'])} |",
        f"| | MRR (first reasonable fit) | {fmt(e['mrr'])} |",
        f"| | Pairwise order accuracy ({e['ordered_pairs']} pairs) | {fmt(e['pairwise_order_accuracy'])} |",
        f"| | Suitability precision / recall | {fmt(e['suitability_precision'])} / {fmt(e['suitability_recall'])} |",
        "",
        "Errors found:",
    ]
    for name, items in (("JD skills missed", a["missed_skills"]), ("JD skills wrongly added", a["extra_skills"]),
                        ("Level errors", a["level_errors"]), ("Equivalence errors", b["errors"]),
                        ("Gap errors", d["errors"]), ("Ranking order errors", e["order_errors"])):
        lines.append(f"- {name}: " + ("none" if not items else ""))
        lines += [f"  - {i}" for i in items]
    lines += ["", "Timings (median / max ms):"]
    lines += [f"- {k}: {v['median']} / {v['max']}" for k, v in perf.items()]
    lines += ["", "| Student | Top opening | Grades in ranked order | Marked suitable |", "|---|---|---|---|"]
    for cid, v in e["per_candidate"].items():
        lines.append(f"| {cid} | {v['top']} | {v['grades_in_order']} | {', '.join(v['suitable']) or '-'} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    result = run_job_matching_evaluation(FIXTURES, timing_repeats=args.repeats)
    print(json.dumps(result, indent=2) if args.json else to_markdown(result))


if __name__ == "__main__":
    main()
