"""
Run the Sprint 3 NLP evaluation on the labelled synthetic fixtures and print the results.

Usage (from the backend/ folder):
    python scripts/evaluate_nlp_sprint3.py            # markdown summary
    python scripts/evaluate_nlp_sprint3.py --json     # full JSON, including per-case details

All numbers are computed by running the code; see app/nlp/evaluation/evaluator.py for the
methodology. The set is small and synthetic - results describe these cases only.
"""

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.nlp.evaluation import run_evaluation  # noqa: E402

FIXTURES = BACKEND / "tests" / "nlp" / "fixtures" / "sprint3"


def fmt(x):
    return "n/a" if x is None else f"{x:.3f}"


def to_markdown(r: dict) -> str:
    imp, fmt_d, cq, rec, sc, perf = (
        r["improvement_detection"],
        r["formatting_detection"],
        r["content_quality"],
        r["recommendations"],
        r["scoring"],
        r["performance"],
    )
    lines = [
        f"Labelled cases: {r['cases']} resumes, {cq.get('labelled_bullets', 0)} bullets",
        "",
        "| Area | Metric | Value |",
        "|---|---|---|",
        f"| Improvement detection (Module D) | Precision | {fmt(imp['precision'])} |",
        f"| | Recall | {fmt(imp['recall'])} |",
        f"| | F1 | {fmt(imp['f1'])} |",
        f"| | TP / FP / FN / TN | {imp['tp']} / {imp['fp']} / {imp['fn']} / {imp['tn']} |",
        f"| Formatting detection (Module B) | Precision | {fmt(fmt_d['precision'])} |",
        f"| | Recall | {fmt(fmt_d['recall'])} |",
        f"| | False-positive rate | {fmt(fmt_d['false_positive_rate'])} |",
        f"| Content quality (Module C) | Band agreement with labels | {fmt(cq['band_agreement'])} ({cq['labelled_cases']} cases) |",
        f"| | Action-verb detection accuracy | {fmt(cq.get('action_verb_detection_accuracy'))} |",
        f"| | Impact-metric detection accuracy | {fmt(cq.get('impact_metric_detection_accuracy'))} |",
        f"| | Weak-opening detection accuracy | {fmt(cq.get('weak_opening_detection_accuracy'))} |",
        f"| Recommendations (Module E) | Issue-to-recommendation mapping accuracy | {fmt(rec['issue_to_recommendation_mapping_accuracy'])} ({rec['mapping_checks']} checks) |",
        f"| | Duplicate recommendation rate | {fmt(rec['duplicate_recommendation_rate'])} ({rec['total_recommendations']} recs) |",
        f"| | Recall of manually expected recommendations | {fmt(rec['expected_recommendation_recall'])} |",
        f"| Scoring (Module A) | Strong > average > weak pairwise ordering | {fmt(sc['pairwise_ordering_accuracy'])} ({sc['ordering_pairs']} pairs) |",
        "",
        "Errors found:",
    ]
    for name, items in (
        ("Improvement false negatives", imp["false_negatives"]),
        ("Improvement false positives", imp["false_positives"]),
        ("Formatting false positives", fmt_d["false_positives"]),
        ("Formatting false negatives", fmt_d["false_negatives"]),
        ("Content band disagreements", cq["disagreements"]),
        ("Bullet detector errors", cq.get("bullet_errors", [])),
        ("Missing expected recommendations", rec["missing_expected_recommendations"]),
    ):
        lines.append(f"- {name}: " + ("none" if not items else ""))
        lines += [f"  - {i}" for i in items]
    lines += [
        "",
        "Timings (median / max ms):",
        f"- End to end incl. Sprint 2 extraction: {perf['end_to_end_ms_including_sprint2']['median']} / "
        f"{perf['end_to_end_ms_including_sprint2']['max']} over {perf['runs']} runs",
    ]
    lines += [f"- {m}: {v['median']} / {v['max']}" for m, v in perf["sprint3_module_ms"].items()]
    lines += ["", "| Case | Score | Content band (pred / label) | Issues |", "|---|---|---|---|"]
    for case, d in r["per_case"].items():
        lines.append(
            f"| {d['case']} | {d['overall_score']} | {d['content_band_predicted']} / {d['content_band_label']} | "
            f"{', '.join(d['issues']) or '-'} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    result = run_evaluation(FIXTURES, timing_repeats=args.repeats)
    print(json.dumps(result, indent=2) if args.json else to_markdown(result))


if __name__ == "__main__":
    main()
