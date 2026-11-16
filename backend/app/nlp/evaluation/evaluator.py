"""
Sprint 3 NLP evaluation (Module G).

Runs the Sprint 3 analysis on a labelled synthetic resume set and computes:

- Improvement detection:   precision / recall / F1 (Module D issue ids vs labels)
- Formatting detection:    precision / recall / false-positive rate (Module B finding ids)
- Content quality:         agreement of the content-quality band with manual labels
- Action verbs / metrics:  per-bullet accuracy of Module C detectors on labelled bullets
- Recommendations:         issue-to-recommendation mapping accuracy, duplicate rate,
                           recall of manually expected recommendations
- Scoring:                 ordering of strong > average > weak resumes
- Performance:             per-module and end-to-end timings

All numbers come from actually running the code on the labelled files; nothing is
hard-coded. The labelled set is small and synthetic, so metrics describe behaviour on these
cases only - they are not a claim of real-world accuracy.
"""

import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.nlp.analysis import ResumeAnalysisPipeline, Sprint3AnalysisResult
from app.nlp.content.action_verbs import check_leading_action_verb, detect_weak_introductory_phrase
from app.nlp.content.impact_metrics import detect_impact_metrics
from app.nlp.evaluation.metrics import ConfusionCounts, accuracy, rnd
from app.nlp.improvement.deduplicator import CANONICAL_ISSUE_CLUSTERS
from app.nlp.recommendations import RULES

CONTENT_BANDS = {"strong": 65.0, "weak": 35.0}  # percent of content_quality max; between = moderate
QUALITY_ORDER = {"strong": 3, "average": 2, "weak": 1}


def content_band(percentage: float) -> str:
    if percentage >= CONTENT_BANDS["strong"]:
        return "strong"
    if percentage < CONTENT_BANDS["weak"]:
        return "weak"
    return "moderate"


class Sprint3Evaluator:
    def __init__(self, fixtures_dir: Path, pipeline: Optional[ResumeAnalysisPipeline] = None):
        self.fixtures_dir = Path(fixtures_dir)
        self.pipeline = pipeline or ResumeAnalysisPipeline()
        self.labels = json.loads((self.fixtures_dir / "labels.json").read_text(encoding="utf-8"))
        bullets_path = self.fixtures_dir / "labelled_bullets.json"
        self.bullets = (
            json.loads(bullets_path.read_text(encoding="utf-8"))["bullets"]
            if bullets_path.exists()
            else []
        )

    def cases(self) -> List[str]:
        return sorted(k for k in self.labels if not k.startswith("_"))

    def analyze_case(self, case: str) -> Sprint3AnalysisResult:
        text = (self.fixtures_dir / f"{case}.txt").read_text(encoding="utf-8")
        return self.pipeline.analyze_text(text, f"{case}.txt")

    def run(self, timing_repeats: int = 3) -> Dict[str, Any]:
        issues = ConfusionCounts()
        formatting = ConfusionCounts()
        rec_expected = ConfusionCounts()
        mapping_checks: List[bool] = []
        duplicate_recs = total_recs = 0
        band_pairs = []
        per_case: Dict[str, Any] = {}
        scores: Dict[str, float] = {}

        for case in self.cases():
            label = self.labels[case]
            result = self.analyze_case(case)
            issue_ids = (
                {i.issue_id for i in result.improvement_areas.issues}
                if result.improvement_areas
                else set()
            )
            fmt_ids = (
                {f.issue_id for f in result.formatting_analysis.findings}
                if result.formatting_analysis
                else set()
            )
            recs = result.recommendations.recommendations if result.recommendations else []
            rec_ids = [r.recommendation_id for r in recs]

            # Labels may name raw or canonical ids; compare in canonical space (Module D merges clusters).
            canon = lambda ids: {CANONICAL_ISSUE_CLUSTERS.get(i, i) for i in ids}  # noqa: E731
            issues.add(
                case,
                canon(issue_ids),
                canon(label["expected_issues"]),
                canon(label["forbidden_issues"]),
            )
            formatting.add(
                case, fmt_ids, label["expected_formatting"], label["forbidden_formatting"]
            )
            rec_expected.add(case, set(rec_ids), label["expected_recommendations"], [])

            # Mapping: every detected issue that has a dedicated rule must be addressed by the rule's recommendation
            for issue_id in sorted(issue_ids):
                rule = RULES.get(issue_id)
                if rule is None:
                    continue
                addressed = [r for r in recs if issue_id in r.related_issue_ids]
                mapping_checks.append(
                    bool(addressed)
                    and (
                        any(r.recommendation_id == rule.recommendation_id for r in addressed)
                        or (
                            rule.merge_key is not None
                            and any(r.related_issue_id != issue_id for r in addressed)
                        )
                    )
                )
            total_recs += len(rec_ids)
            duplicate_recs += len(rec_ids) - len(set(rec_ids))

            comp = result.component_scores.get("content_quality")
            pct = 100.0 * comp.score / comp.max_score if comp else None
            if label.get("content_band") and pct is not None:
                band_pairs.append((content_band(pct), label["content_band"]))

            scores[case] = result.overall_score
            per_case[case] = {
                "case": label["case"],
                "overall_score": result.overall_score,
                "score_label": getattr(result.score_label, "value", None),
                "content_quality_pct": rnd(pct, 1),
                "content_band_predicted": content_band(pct) if pct is not None else None,
                "content_band_label": label.get("content_band"),
                "issues": sorted(issue_ids),
                "formatting_findings": sorted(fmt_ids),
                "recommendations": rec_ids,
                "failed_consistency_checks": sorted(
                    k for k, v in result.analysis_metadata.consistency_checks.items() if not v
                ),
                "module_errors": [e.model_dump() for e in result.analysis_metadata.errors],
            }

        ordering = self._ordering(scores)
        return {
            "cases": len(per_case),
            "improvement_detection": issues.as_dict(),
            "formatting_detection": formatting.as_dict(),
            "content_quality": {
                "band_agreement": rnd(accuracy(band_pairs)),
                "labelled_cases": len(band_pairs),
                "band_thresholds_pct": CONTENT_BANDS,
                "disagreements": [f"predicted {p} vs label {a}" for p, a in band_pairs if p != a],
                **self._bullet_metrics(),
            },
            "recommendations": {
                "issue_to_recommendation_mapping_accuracy": rnd(
                    accuracy((ok, True) for ok in mapping_checks)
                ),
                "mapping_checks": len(mapping_checks),
                "duplicate_recommendation_rate": rnd(duplicate_recs / total_recs)
                if total_recs
                else 0.0,
                "total_recommendations": total_recs,
                "expected_recommendation_recall": rnd(rec_expected.recall),
                "missing_expected_recommendations": rec_expected.false_negatives,
            },
            "scoring": {"scores": scores, **ordering},
            "performance": self._timings(timing_repeats),
            "per_case": per_case,
        }

    # ------------------------------------------------------------- pieces

    def _ordering(self, scores: Dict[str, float]) -> Dict[str, Any]:
        bands = {c: self.labels[c]["quality_band"] for c in scores}
        pairs = ok = 0
        violations = []
        for a in scores:
            for b in scores:
                if QUALITY_ORDER[bands[a]] > QUALITY_ORDER[bands[b]]:
                    pairs += 1
                    if scores[a] > scores[b]:
                        ok += 1
                    else:
                        violations.append(
                            f"{a} ({bands[a]}, {scores[a]}) <= {b} ({bands[b]}, {scores[b]})"
                        )
        return {
            "pairwise_ordering_accuracy": rnd(ok / pairs) if pairs else None,
            "ordering_pairs": pairs,
            "ordering_violations": violations,
        }

    def _bullet_metrics(self) -> Dict[str, Any]:
        if not self.bullets:
            return {}
        verb, metric, weak = [], [], []
        errors = []
        for b in self.bullets:
            v = check_leading_action_verb(b["text"]) is not None
            m = bool(detect_impact_metrics(b["text"]))
            w = detect_weak_introductory_phrase(b["text"]) is not None
            verb.append((v, b["has_leading_action_verb"]))
            metric.append((m, b["has_impact_metric"]))
            weak.append((w, b["has_weak_opening"]))
            for name, pred, actual in (
                ("verb", v, b["has_leading_action_verb"]),
                ("metric", m, b["has_impact_metric"]),
                ("weak_opening", w, b["has_weak_opening"]),
            ):
                if pred != actual:
                    errors.append(f'{name}: predicted {pred}, label {actual}: "{b["text"]}"')
        return {
            "labelled_bullets": len(self.bullets),
            "action_verb_detection_accuracy": rnd(accuracy(verb)),
            "impact_metric_detection_accuracy": rnd(accuracy(metric)),
            "weak_opening_detection_accuracy": rnd(accuracy(weak)),
            "bullet_errors": errors,
        }

    def _timings(self, repeats: int) -> Dict[str, Any]:
        per_module: Dict[str, List[float]] = {}
        totals: List[float] = []
        for _ in range(max(1, repeats)):
            for case in self.cases():
                start = time.perf_counter()
                result = self.analyze_case(case)
                totals.append((time.perf_counter() - start) * 1000)
                for module, ms in result.analysis_metadata.module_timings_ms.items():
                    per_module.setdefault(module, []).append(ms)
        return {
            "runs": len(totals),
            "end_to_end_ms_including_sprint2": {
                "median": rnd(statistics.median(totals), 2),
                "max": rnd(max(totals), 2),
            },
            "sprint3_module_ms": {
                m: {"median": rnd(statistics.median(v), 2), "max": rnd(max(v), 2)}
                for m, v in per_module.items()
            },
        }


def run_evaluation(fixtures_dir: Path, timing_repeats: int = 3) -> Dict[str, Any]:
    return Sprint3Evaluator(fixtures_dir).run(timing_repeats=timing_repeats)


__all__ = ["CONTENT_BANDS", "Sprint3Evaluator", "content_band", "run_evaluation"]
