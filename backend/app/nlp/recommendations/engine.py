"""
Rule-Based Recommendation Engine for Sprint 3 Module E (US-09).

Turns the ImprovementAreasReport from Module D into prioritized, student-friendly,
evidence-backed recommendations.

Inputs (no new resume analysis is done here):
- ImprovementAreasReport (Module D)          - required; every recommendation maps to one of its issues
- ScoringResult (Module A)                    - optional; potential score gain + component weights
- ContentQualityReport (Module C)             - optional; names the specific weak entries / bullets
- FormattingAnalysisResult (Module B)         - optional; line-level formatting evidence
- CandidateProfile (Sprint 2)                 - optional; names the skills already used in projects

Guarantees:
- Every recommendation has a related_issue_id that exists in the input report.
- Advice that would repeat (same merge key or same recommendation_id) is merged into one item.
- Deterministic: same inputs -> same output, same order.
- Never suggests skills, certifications, achievements or metrics that are not in the resume.
- No job-specific advice (Sprint 4), no LLM calls.

Priority score (0-1), documented so it can be reviewed:
    severity_factor = 0.6 * severity_weight + 0.4 * module_d_priority_weight
    priority_score  = 0.50 * severity_factor
                    + 0.20 * component_weight      (score component's weight / largest weight)
                    + 0.15 * confidence
                    + 0.15 * actionability
    tier: >= 0.78 high, >= 0.55 medium, else low. Critical issues are always high.
"""

import re
from typing import Dict, Iterable, List, Optional, Tuple

from app.nlp.content import ContentQualityReport
from app.nlp.formatting import FormattingAnalysisResult
from app.nlp.improvement import ImprovementAreasReport, ImprovementIssue
from app.nlp.improvement.deduplicator import CANONICAL_ISSUE_CLUSTERS
from app.nlp.recommendations.rules import (
    GENERIC_FALLBACK_RULE_ID,
    RULE_SET_VERSION,
    RecommendationRule,
    get_rule,
    missing_section_rule,
    section_label,
)
from app.nlp.recommendations.schemas import (
    RECOMMENDATION_ENGINE_VERSION,
    Recommendation,
    RecommendationCategory,
    RecommendationPriority,
    RecommendationReport,
)
from app.nlp.schemas import CandidateProfile
from app.nlp.scoring import ScoringResult
from app.nlp.scoring.weights import SPRINT3_DEFAULT_WEIGHTS

SEVERITY_WEIGHT = {"critical": 1.0, "warning": 0.6, "info": 0.25}
ISSUE_PRIORITY_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.25}
HIGH_THRESHOLD = 0.78
MEDIUM_THRESHOLD = 0.55
LOW_CONFIDENCE_THRESHOLD = 0.60

# Module A deduction rule ids -> Module D issue ids, for potential score gain.
# Extends Module D's own cluster map with the rule ids Module A actually emits.
SCORING_RULE_TO_ISSUE: Dict[str, str] = {
    **CANONICAL_ISSUE_CLUSTERS,
    "SEC_MISSING_TECHNICAL_SKILLS": "IMP_MISSING_SKILLS",
    "SEC_EDU_NO_ENTRIES": "IMP_MISSING_EDUCATION",
    "SEC_MISSING_EMAIL": "IMP_CONTACT_MISSING_EMAIL",
    "SEC_MISSING_PHONE": "IMP_CONTACT_MISSING_PHONE",
    "SEC_MISSING_PROFILE_LINKS": "IMP_CONTACT_MISSING_DEV_PROFILES",
    "SEC_NO_PRACTICAL_WORK": "IMP_MISSING_PRACTICAL_WORK",
    "CONTENT_NO_METRICS": "IMP_LACK_OF_MEASURABLE_IMPACT",
    "CONTENT_FEW_ACTION_VERBS": "IMP_LACK_OF_ACTION_VERBS",
    "CONTENT_WEAK_PHRASES": "IMP_PASSIVE_PHRASING",
    "CONTENT_SHALLOW_PROJECTS": "IMP_WEAK_PROJECT_DESCRIPTION",
    "SKILL_UNCATEGORIZED": "IMP_POOR_SKILL_CATEGORIZATION",
    "FMT_WALL_OF_TEXT": "IMP_UNSTRUCTURED_WALL_OF_TEXT",
    "FMT_EXCESSIVE_WHITESPACE": "IMP_EXCESSIVE_WHITESPACE",
    "FMT_LOW_ATS_CONFIDENCE": "IMP_EXTRACTION_UNCERTAINTY",
}

_MAX_EVIDENCE_ITEMS = 5
_MAX_NAMED_ENTRIES = 3


def _value(enum_or_str) -> str:
    return str(getattr(enum_or_str, "value", enum_or_str)).lower()


def _split_evidence(text: Optional[str]) -> List[str]:
    """Module D joins merged evidence with '; '. Split it back into items."""
    if not text:
        return []
    return [part.strip() for part in text.split("; ") if part.strip()]


def _dedupe(items: Iterable[str]) -> List[str]:
    seen, out = set(), []
    for item in items:
        key = item.strip().lower()
        if item and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def _shorten(text: str, limit: int = 90) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


class RecommendationEngine:
    """Deterministic issue -> recommendation mapper."""

    def __init__(self, version: str = RECOMMENDATION_ENGINE_VERSION):
        self.version = version

    # ------------------------------------------------------------------ API

    def generate(
        self,
        improvement_report: ImprovementAreasReport,
        scoring_result: Optional[ScoringResult] = None,
        content_report: Optional[ContentQualityReport] = None,
        formatting_result: Optional[FormattingAnalysisResult] = None,
        profile: Optional[CandidateProfile] = None,
    ) -> RecommendationReport:
        issues = list(improvement_report.issues or []) if improvement_report else []
        component_weights = self._component_weights(scoring_result)
        gains = self._score_gains(scoring_result)

        merged: Dict[str, Recommendation] = {}
        unmapped: List[str] = []

        for issue in issues:
            rule, is_fallback = self._rule_for(issue)
            if is_fallback:
                unmapped.append(issue.issue_id)
            for rec in self._build(issue, rule, component_weights, gains, content_report, profile):
                key = rule.merge_key or rec.recommendation_id
                key = (
                    f"{key}|{rec.affected_section}"
                    if rec.category == RecommendationCategory.EXPERIENCE
                    else key
                )
                if key in merged:
                    merged[key] = self._merge(merged[key], rec)
                else:
                    merged[key] = rec

        # Second pass: identical recommendation ids from different merge keys
        by_id: Dict[str, Recommendation] = {}
        for rec in merged.values():
            if rec.recommendation_id in by_id:
                by_id[rec.recommendation_id] = self._merge(by_id[rec.recommendation_id], rec)
            else:
                by_id[rec.recommendation_id] = rec

        ranked = sorted(
            by_id.values(),
            key=lambda r: (-r.priority_score, r.related_issue_id, r.recommendation_id),
        )
        counts = {p: sum(1 for r in ranked if r.priority == p) for p in RecommendationPriority}
        return RecommendationReport(
            total_recommendations=len(ranked),
            high_priority_count=counts[RecommendationPriority.HIGH],
            medium_priority_count=counts[RecommendationPriority.MEDIUM],
            low_priority_count=counts[RecommendationPriority.LOW],
            recommendations=ranked,
            unmapped_issue_ids=sorted(set(unmapped)),
            engine_version=self.version,
            metadata={
                "rule_set_version": RULE_SET_VERSION,
                "input_issue_count": len(issues),
                "input_issue_ids": [i.issue_id for i in issues],
                "priority_thresholds": {"high": HIGH_THRESHOLD, "medium": MEDIUM_THRESHOLD},
                "inputs_available": {
                    "scoring_result": scoring_result is not None,
                    "content_report": content_report is not None,
                    "formatting_result": formatting_result is not None,
                    "profile": profile is not None,
                },
            },
        )

    # ------------------------------------------------------------ helpers

    @staticmethod
    def _rule_for(issue: ImprovementIssue) -> Tuple[RecommendationRule, bool]:
        rule = get_rule(issue.issue_id)
        if rule is not None:
            return rule, False
        if issue.issue_id.startswith("FMT_MISSING_SECTION_HEADING") or issue.issue_id.startswith(
            "IMP_MISSING_"
        ):
            section = (issue.affected_section or issue.issue_id.split("_")[-1]).lower()
            if section in {"skills", "skill"}:
                section = "technical_skills"
            return missing_section_rule(section, f"RULE_MISSING_SECTION_{section.upper()}"), False
        # Generic fallback: still tied to the issue, uses the issue's own wording.
        return RecommendationRule(
            rule_id=GENERIC_FALLBACK_RULE_ID,
            recommendation_id=f"REC_{re.sub('^(IMP|FMT)_', '', issue.issue_id)}",
            category=RecommendationCategory.FORMATTING
            if issue.issue_id.startswith("FMT_")
            else RecommendationCategory.CONTENT,
            title=issue.title,
            description=issue.description,
            why_it_matters="This was flagged by the resume analysis as something that weakens your resume.",
            suggested_action=issue.description,
            actionability=0.5,
        ), True

    @staticmethod
    def _component_weights(scoring_result: Optional[ScoringResult]) -> Dict[str, float]:
        weights = dict(SPRINT3_DEFAULT_WEIGHTS)
        if scoring_result:
            applied = (scoring_result.scoring_metadata or {}).get("weights_applied") or {}
            weights.update({k: float(v) for k, v in applied.items()})
        top = max(weights.values()) or 1.0
        return {k: v / top for k, v in weights.items()}

    @staticmethod
    def _score_gains(scoring_result: Optional[ScoringResult]) -> Dict[str, float]:
        """Points Module A deducted per Module D issue id (capped by the component's lost points)."""
        if not scoring_result:
            return {}
        gains: Dict[str, float] = {}
        per_issue_component: Dict[str, str] = {}
        for d in scoring_result.deductions:
            issue_id = SCORING_RULE_TO_ISSUE.get(d.rule_id)
            if issue_id is None and d.rule_id.startswith("SEC_MISSING_"):
                issue_id = "IMP_MISSING_" + d.rule_id[len("SEC_MISSING_") :]
            if issue_id is None:
                continue
            gains[issue_id] = gains.get(issue_id, 0.0) + d.points_deducted
            per_issue_component[issue_id] = d.component
        for issue_id, component in per_issue_component.items():
            comp = scoring_result.component_scores.get(component)
            if comp is not None:
                gains[issue_id] = min(gains[issue_id], max(0.0, comp.max_score - comp.score))
        return {k: round(v, 2) for k, v in gains.items()}

    def _priority(
        self, issue: ImprovementIssue, rule: RecommendationRule, component_weights: Dict[str, float]
    ) -> Tuple[float, RecommendationPriority]:
        severity = _value(issue.severity)
        sev_factor = 0.6 * SEVERITY_WEIGHT.get(severity, 0.25) + 0.4 * ISSUE_PRIORITY_WEIGHT.get(
            _value(issue.priority), 0.25
        )
        comp = component_weights.get(issue.related_score_component, 0.5)
        score = (
            0.50 * sev_factor + 0.20 * comp + 0.15 * issue.confidence + 0.15 * rule.actionability
        )
        score = round(max(0.0, min(1.0, score)), 4)
        if severity == "critical" or score >= HIGH_THRESHOLD:
            tier = RecommendationPriority.HIGH
        elif score >= MEDIUM_THRESHOLD:
            tier = RecommendationPriority.MEDIUM
        else:
            tier = RecommendationPriority.LOW
        return score, tier

    def _build(
        self,
        issue: ImprovementIssue,
        rule: RecommendationRule,
        component_weights: Dict[str, float],
        gains: Dict[str, float],
        content_report: Optional[ContentQualityReport],
        profile: Optional[CandidateProfile],
    ) -> List[Recommendation]:
        score, tier = self._priority(issue, rule, component_weights)
        low_conf = issue.confidence < LOW_CONFIDENCE_THRESHOLD
        description = rule.description
        steps = list(rule.action_steps)
        evidence = _split_evidence(issue.evidence)
        extra: List[Recommendation] = []

        # --- make the advice specific to what was actually detected -------------
        entries = list(content_report.entries) if content_report else []
        if issue.issue_id == "IMP_WEAK_PROJECT_DESCRIPTION" and entries:
            weak = [
                e for e in entries if e.entry_type == "project" and e.content_quality_score < 60.0
            ]
            if weak:
                names = ", ".join(f"'{e.entry_title}'" for e in weak[:_MAX_NAMED_ENTRIES])
                description = f"These projects need more detail: {names}. {rule.description}"
                evidence += [
                    f"'{e.entry_title}': content score {e.content_quality_score:.0f}/100, "
                    f"description {_value(e.description_completeness)}"
                    for e in weak[:_MAX_NAMED_ENTRIES]
                ]
        elif issue.issue_id in {"IMP_PASSIVE_PHRASING", "IMP_LACK_OF_ACTION_VERBS"} and entries:
            weak_bullets = [
                b
                for e in entries
                for b in e.bullet_evaluations
                if b.is_passive_or_weak
                or (issue.issue_id == "IMP_LACK_OF_ACTION_VERBS" and b.leading_action_verb is None)
            ]
            if weak_bullets:
                evidence += [
                    f'"{_shorten(b.bullet_text)}"'
                    + (f" (starts with '{b.weak_phrase_found}')" if b.weak_phrase_found else "")
                    for b in weak_bullets[:_MAX_NAMED_ENTRIES]
                ]
        elif issue.issue_id == "IMP_LACK_OF_MEASURABLE_IMPACT" and entries:
            exp_entries = [
                e
                for e in entries
                if e.entry_type in {"experience", "internship"} and not e.impact_metrics_detected
            ]
            if exp_entries:
                extra.append(
                    self._experience_outcome_rec(
                        issue, rule, exp_entries, score, tier, gains, low_conf
                    )
                )
        elif (
            issue.issue_id in {"IMP_LOW_SKILL_INVENTORY", "IMP_POOR_SKILL_CATEGORIZATION"}
            and profile
        ):
            used_not_listed = self._skills_used_but_not_listed(profile)
            if used_not_listed:
                steps.append(
                    "Already used in your projects/experience but not in your Skills section: "
                    + ", ".join(used_not_listed[:8])
                    + "."
                )
                evidence.append(
                    "Skills found only outside the Skills section: "
                    + ", ".join(used_not_listed[:8])
                )
        elif rule.rule_id.startswith("RULE_MISSING_SECTION_") and issue.issue_id.startswith("FMT_"):
            evidence.append(
                f"Formatting analysis found no '{section_label(issue.affected_section)}' heading."
            )

        if low_conf:
            description += " (This was detected with low confidence - please check whether it applies to your resume.)"

        primary = Recommendation(
            recommendation_id=rule.recommendation_id,
            related_issue_id=issue.issue_id,
            related_issue_ids=[issue.issue_id],
            title=rule.title,
            category=rule.category,
            description=description,
            why_it_matters=rule.why_it_matters,
            suggested_action=rule.suggested_action,
            action_steps=_dedupe(steps),
            priority=tier,
            priority_score=score,
            severity=_value(issue.severity),
            affected_section=issue.affected_section,
            related_score_component=issue.related_score_component,
            potential_score_gain=gains.get(issue.issue_id),
            evidence=_dedupe(evidence)[:_MAX_EVIDENCE_ITEMS],
            confidence=issue.confidence,
            low_confidence=low_conf,
            rule_id=rule.rule_id,
        )
        return [primary] + extra

    @staticmethod
    def _experience_outcome_rec(
        issue, rule, exp_entries, score, tier, gains, low_conf
    ) -> Recommendation:
        names = ", ".join(f"'{e.entry_title}'" for e in exp_entries[:_MAX_NAMED_ENTRIES])
        return Recommendation(
            recommendation_id="REC_EXPERIENCE_OUTCOMES",
            related_issue_id=issue.issue_id,
            related_issue_ids=[issue.issue_id],
            title="Describe what your internship/job work achieved",
            category=RecommendationCategory.EXPERIENCE,
            description=f"Your experience entries ({names}) list tasks but not what they achieved.",
            why_it_matters="Recruiters want to know whether your work was used and what difference it made.",
            suggested_action=(
                "For each role, add one bullet on the result of your work - e.g. a feature that shipped, a process you sped up, "
                "or a number from that period if you have it. Do not estimate numbers you did not measure."
            ),
            action_steps=[
                "Make each responsibility a clear action: 'Built X using Y for Z'.",
                "Ask your mentor/manager for real figures if you are unsure.",
            ],
            priority=tier,
            priority_score=round(max(0.0, score - 0.01), 4),
            severity=_value(issue.severity),
            affected_section="experience",
            related_score_component=issue.related_score_component,
            potential_score_gain=None,
            evidence=[
                f"No measurable outcome found in {e.entry_type} entry '{e.entry_title}'."
                for e in exp_entries[:_MAX_NAMED_ENTRIES]
            ],
            confidence=issue.confidence,
            low_confidence=low_conf,
            rule_id="RULE_EXPERIENCE_OUTCOMES",
        )

    @staticmethod
    def _skills_used_but_not_listed(profile: CandidateProfile) -> List[str]:
        """Skills the resume itself shows were used in projects/experience but are missing from the skills list."""
        listed = {
            s.canonical_name
            for s in profile.technical_skills
            if s.source_section == "technical_skills"
        }
        used: List[str] = []
        for entry in list(profile.projects) + list(profile.experience) + list(profile.internships):
            techs = (
                getattr(entry, "technologies", None)
                or getattr(entry, "technologies_used", None)
                or []
            )
            used.extend(t for t in techs if t not in listed)
        return sorted(set(used)) if listed else []

    @staticmethod
    def _merge(a: Recommendation, b: Recommendation) -> Recommendation:
        """Merge two recommendations that give the same advice; keep the stronger one as the base."""
        base, other = (
            (a, b)
            if (a.priority_score, -len(a.related_issue_id))
            >= (b.priority_score, -len(b.related_issue_id))
            else (b, a)
        )
        gain_values = [g for g in (a.potential_score_gain, b.potential_score_gain) if g is not None]
        return base.model_copy(
            update={
                "related_issue_ids": _dedupe(base.related_issue_ids + other.related_issue_ids),
                "evidence": _dedupe(base.evidence + other.evidence)[:_MAX_EVIDENCE_ITEMS],
                "action_steps": _dedupe(base.action_steps + other.action_steps),
                "confidence": max(a.confidence, b.confidence),
                "low_confidence": a.low_confidence and b.low_confidence,
                "potential_score_gain": max(gain_values) if gain_values else None,
                "affected_section": base.affected_section or other.affected_section,
            }
        )


def generate_recommendations(
    improvement_report: ImprovementAreasReport,
    scoring_result: Optional[ScoringResult] = None,
    content_report: Optional[ContentQualityReport] = None,
    formatting_result: Optional[FormattingAnalysisResult] = None,
    profile: Optional[CandidateProfile] = None,
) -> RecommendationReport:
    """Convenience helper using the default engine."""
    return RecommendationEngine().generate(
        improvement_report,
        scoring_result=scoring_result,
        content_report=content_report,
        formatting_result=formatting_result,
        profile=profile,
    )


__all__ = ["RecommendationEngine", "SCORING_RULE_TO_ISSUE", "generate_recommendations"]
