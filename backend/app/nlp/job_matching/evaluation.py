"""
Sprint 4 Module F: evaluation of job matching and ranking quality.

Runs the full Sprint 4 workflow on the labelled synthetic set in
tests/nlp/fixtures/sprint4/ (8 job descriptions, 7 student resumes, labels.json) and reports:

- JD parsing (Module A):       skill precision / recall / F1, required-vs-preferred level
                               accuracy, field accuracy (title, company, type, CGPA, batches)
- Skill equivalence (Module B): pair accuracy, false-equivalence rate, missed-equivalence rate
- Skill gaps (Module D):       recall of skills the student has / lacks, wrong-missing count
- Ranking (Module E):          NDCG@3, precision@1, MRR, pairwise order accuracy,
                               suitability precision / recall (is_suitable vs relevance >= 2)
- Performance:                 compare / rank timings

All numbers are computed by running the code; nothing is hard-coded. The set is small and
synthetic, so the figures describe these cases only and are not real-world accuracy.
"""

from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

from app.nlp.job_matching.ranking_schemas import JobOpportunity
from app.nlp.job_matching.skill_engine import (
    evaluate_skill_equivalence,
    normalize_skill,
)
from app.nlp.job_matching.skill_gap_schemas import SkillGapStatus
from app.nlp.job_matching.skill_normalization_schemas import SkillRelationshipType
from app.nlp.job_matching.workflow import JobMatchingWorkflow

INTERCHANGEABLE = {SkillRelationshipType.EXACT_MATCH, SkillRelationshipType.EXACT_ALIAS, SkillRelationshipType.EQUIVALENT}


def _r(x: float | None, d: int = 3) -> float | None:
    return None if x is None else round(x, d)


def _div(a: float, b: float) -> float | None:
    return None if b == 0 else a / b


def _canon(name: str) -> str:
    return (normalize_skill(name).canonical_name or name).lower()


def dcg(grades: list[int]) -> float:
    return sum((2**g - 1) / math.log2(i + 2) for i, g in enumerate(grades))


def ndcg_at_k(ranked_grades: list[int], all_grades: list[int], k: int) -> float | None:
    ideal = dcg(sorted(all_grades, reverse=True)[:k])
    return None if ideal == 0 else dcg(ranked_grades[:k]) / ideal


class JobMatchingEvaluator:
    def __init__(self, fixtures_root: Path, workflow: JobMatchingWorkflow | None = None):
        self.root = Path(fixtures_root)
        self.sprint4 = self.root / "sprint4"
        self.labels = json.loads((self.sprint4 / "labels.json").read_text(encoding="utf-8"))
        self.workflow = workflow or JobMatchingWorkflow()
        self.job_texts = {p.stem: p.read_text(encoding="utf-8") for p in sorted((self.sprint4 / "jobs").glob("*.txt"))}

    def run(self, timing_repeats: int = 3) -> dict[str, Any]:
        profiles = {
            cid: self.workflow._pipeline().process((self.root / rel).read_text(encoding="utf-8"), Path(rel).name)
            for cid, rel in self.labels["candidates"].items()
        }
        opportunities = [JobOpportunity(opportunity_id=jid, description=t) for jid, t in self.job_texts.items()]
        rankings = {cid: self.workflow.rank(p, opportunities, include_details=True) for cid, p in profiles.items()}
        return {
            "jobs": len(self.job_texts),
            "candidates": len(profiles),
            "jd_parsing": self._jd_parsing(),
            "skill_equivalence": self._equivalence(),
            "skill_gaps": self._gaps(rankings),
            "ranking": self._ranking(rankings),
            "performance": self._timings(profiles, opportunities, timing_repeats),
        }

    # ------------------------------------------------------------ Module A

    def _jd_parsing(self) -> dict[str, Any]:
        tp = fp = fn = level_ok = level_total = 0
        field_hits: dict[str, list[bool]] = {k: [] for k in ("title", "company", "job_type", "min_cgpa", "batches", "experience")}
        misses, extras, level_errors = [], [], []
        for jid, label in self.labels["jobs"].items():
            parsed = self.workflow.parser.parse(self.job_texts[jid], job_id=jid)
            got_req = {s.canonical_name.lower() for s in parsed.required_technical_skills}
            got_pref = {s.canonical_name.lower() for s in parsed.preferred_technical_skills}
            exp_req = {_canon(s) for s in label["required"]}
            exp_pref = {_canon(s) for s in label["preferred"]}
            ok_extra = {_canon(s) for s in label["acceptable"]}
            detected, expected = got_req | got_pref, exp_req | exp_pref
            tp += len(detected & expected)
            fn += len(expected - detected)
            fp += len(detected - expected - ok_extra)
            misses += [f"{jid}:{s}" for s in sorted(expected - detected)]
            extras += [f"{jid}:{s}" for s in sorted(detected - expected - ok_extra)]
            for s in detected & expected:
                level_total += 1
                correct = (s in exp_req and s in got_req) or (s in exp_pref and s in got_pref)
                level_ok += correct
                if not correct:
                    level_errors.append(f"{jid}:{s}")

            field_hits["title"].append(label["title"].lower() in (parsed.title or "").lower())
            field_hits["company"].append((parsed.company_name or "").lower() == label["company"].lower())
            field_hits["job_type"].append(parsed.job_type.value == label["job_type"])
            field_hits["min_cgpa"].append(parsed.eligibility.min_cgpa == label["min_cgpa"])
            batches = sorted(set(parsed.eligibility.allowed_batches)) or (
                list(range(parsed.education.min_graduation_year, (parsed.education.max_graduation_year or parsed.education.min_graduation_year) + 1))
                if parsed.education.min_graduation_year else [])
            field_hits["batches"].append(batches == label["batches"])
            exp_ok = parsed.experience.is_fresher_eligible == label["fresher_eligible"]
            if label.get("min_years"):
                exp_ok = exp_ok and parsed.experience.min_years == label["min_years"]
            field_hits["experience"].append(exp_ok)

        p, r = _div(tp, tp + fp), _div(tp, tp + fn)
        f1 = None if not p or not r else 2 * p * r / (p + r)
        return {
            "skill_precision": _r(p), "skill_recall": _r(r), "skill_f1": _r(f1),
            "tp": tp, "fp": fp, "fn": fn,
            "level_accuracy": _r(_div(level_ok, level_total)),
            "field_accuracy": {k: _r(_div(sum(v), len(v))) for k, v in field_hits.items()},
            "missed_skills": misses, "extra_skills": extras, "level_errors": level_errors,
        }

    # ------------------------------------------------------------ Module B

    def _equivalence(self) -> dict[str, Any]:
        correct, false_eq, missed_eq, errors = 0, 0, 0, []
        pairs = self.labels["skill_pairs"]
        neg = sum(1 for *_, eq in pairs if not eq)
        pos = len(pairs) - neg
        for a, b, expected in pairs:
            ev = evaluate_skill_equivalence(a, b)
            got = ev.relationship_type in INTERCHANGEABLE
            correct += got == expected
            if got and not expected:
                false_eq += 1
                errors.append(f"'{a}' ~ '{b}' treated as interchangeable ({ev.relationship_type.value})")
            if expected and not got:
                missed_eq += 1
                errors.append(f"'{a}' ~ '{b}' not recognised as the same skill ({ev.relationship_type.value})")
        return {
            "pairs": len(pairs),
            "accuracy": _r(correct / len(pairs)),
            "false_equivalence_rate": _r(_div(false_eq, neg)),
            "missed_equivalence_rate": _r(_div(missed_eq, pos)),
            "errors": errors,
        }

    # ------------------------------------------------------------ Module D

    def _gaps(self, rankings) -> dict[str, Any]:
        have_found = have_total = miss_found = miss_total = wrong_missing = 0
        errors = []
        for key, label in self.labels.get("gaps", {}).items():
            cid, jid = key.split("|")
            item = next(r for r in rankings[cid].ranked_opportunities if r.opportunity_id == jid)
            gap = item.skill_gap
            status = {i.skill.lower(): i.status for i in gap.matched_required + gap.partial_required + gap.missing_required + gap.uncertain}
            for s in label["have"]:
                have_total += 1
                st = status.get(_canon(s))
                if st in {SkillGapStatus.MATCHED, SkillGapStatus.SATISFIED_BY_ALTERNATIVE}:
                    have_found += 1
                else:
                    errors.append(f"{key}: has {s}, reported {st.value if st else 'not in JD skills'}")
                    if st == SkillGapStatus.MISSING:
                        wrong_missing += 1
            for s in label["missing"]:
                miss_total += 1
                st = status.get(_canon(s))
                if st in {SkillGapStatus.MISSING, SkillGapStatus.PARTIAL}:
                    miss_found += 1
                else:
                    errors.append(f"{key}: lacks {s}, reported {st.value if st else 'not in JD skills'}")
        return {
            "labelled_pairs": len(self.labels.get("gaps", {})),
            "have_recall": _r(_div(have_found, have_total)),
            "missing_recall": _r(_div(miss_found, miss_total)),
            "have_reported_as_missing": wrong_missing,
            "errors": errors,
        }

    # ------------------------------------------------------------ Module E

    def _ranking(self, rankings) -> dict[str, Any]:
        ndcgs, p_at_1, rr, pair_ok, pair_total = [], [], [], 0, 0
        s_tp = s_fp = s_fn = 0
        per_candidate, errors = {}, []
        for cid, report in rankings.items():
            grades = self.labels["relevance"][cid]
            order = [r.opportunity_id for r in report.ranked_opportunities]
            ranked_grades = [grades[j] for j in order]
            ndcgs.append(ndcg_at_k(ranked_grades, list(grades.values()), 3))
            p_at_1.append(ranked_grades[0] == max(grades.values()))
            first_good = next((i for i, g in enumerate(ranked_grades) if g >= 2), None)
            rr.append(0.0 if first_good is None else 1.0 / (first_good + 1))
            pos = {j: i for i, j in enumerate(order)}
            for a in grades:
                for b in grades:
                    if grades[a] > grades[b]:
                        pair_total += 1
                        if pos[a] < pos[b]:
                            pair_ok += 1
                        else:
                            errors.append(f"{cid}: {b} (grade {grades[b]}) ranked above {a} (grade {grades[a]})")
            for r in report.ranked_opportunities:
                good = grades[r.opportunity_id] >= 2
                s_tp += r.is_suitable and good
                s_fp += r.is_suitable and not good
                s_fn += good and not r.is_suitable
            per_candidate[cid] = {"order": order, "grades_in_order": ranked_grades,
                                  "top": order[0], "suitable": [r.opportunity_id for r in report.ranked_opportunities if r.is_suitable]}
        return {
            "ndcg_at_3": _r(statistics.mean(x for x in ndcgs if x is not None)),
            "precision_at_1": _r(sum(p_at_1) / len(p_at_1)),
            "mrr": _r(statistics.mean(rr)),
            "pairwise_order_accuracy": _r(_div(pair_ok, pair_total)),
            "ordered_pairs": pair_total,
            "suitability_precision": _r(_div(s_tp, s_tp + s_fp)),
            "suitability_recall": _r(_div(s_tp, s_tp + s_fn)),
            "per_candidate": per_candidate,
            "order_errors": errors,
        }

    def _timings(self, profiles, opportunities, repeats) -> dict[str, Any]:
        compare_ms, rank_ms = [], []
        for _ in range(max(1, repeats)):
            for p in profiles.values():
                start = time.perf_counter()
                self.workflow.compare(p, opportunities[0].description)
                compare_ms.append((time.perf_counter() - start) * 1000)
                start = time.perf_counter()
                self.workflow.rank(p, opportunities)
                rank_ms.append((time.perf_counter() - start) * 1000)
        return {
            "compare_ms": {"median": _r(statistics.median(compare_ms), 2), "max": _r(max(compare_ms), 2)},
            f"rank_{len(opportunities)}_jobs_ms": {"median": _r(statistics.median(rank_ms), 2), "max": _r(max(rank_ms), 2)},
        }


def run_job_matching_evaluation(fixtures_root: Path, timing_repeats: int = 3) -> dict[str, Any]:
    return JobMatchingEvaluator(fixtures_root).run(timing_repeats=timing_repeats)


__all__ = ["JobMatchingEvaluator", "dcg", "ndcg_at_k", "run_job_matching_evaluation"]
