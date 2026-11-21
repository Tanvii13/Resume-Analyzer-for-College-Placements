"""
Explanation builder for Sprint 3 Module F (US-10: understand the score and recommendations).

Builds plain-language explanations from the outputs of Modules A-E. It only re-describes
what those modules found - it never adds new findings - and it runs consistency checks so a
contradiction between modules is reported instead of shown to a student.
"""

from typing import Dict, List, Optional, Tuple

from app.nlp.improvement import ImprovementAreasReport, ImprovementIssue
from app.nlp.recommendations import (
    RULES,
    SCORING_RULE_TO_ISSUE,
    Recommendation,
    RecommendationReport,
)
from app.nlp.recommendations.engine import HIGH_THRESHOLD, MEDIUM_THRESHOLD
from app.nlp.analysis.schemas import (
    AnalysisExplanations,
    ComponentExplanation,
    DeductionExplanation,
    IssueExplanation,
    RecommendationExplanation,
)
from app.nlp.schemas import CandidateProfile
from app.nlp.scoring import ScoringResult
from app.nlp.scoring.weights import (
    COMPONENT_CONTENT_QUALITY,
    COMPONENT_FORMATTING_READABILITY,
    COMPONENT_SECTION_COMPLETENESS,
    COMPONENT_SKILL_VISIBILITY,
)

COMPONENT_INFO: Dict[str, Tuple[str, str]] = {
    COMPONENT_SECTION_COMPLETENESS: (
        "Section completeness",
        "Whether the resume has the core sections (education, skills, projects), complete contact "
        "details and complete education entries.",
    ),
    COMPONENT_CONTENT_QUALITY: (
        "Content quality",
        "How well project and experience bullets describe your work: action verbs, specific technical "
        "detail and real, measurable results.",
    ),
    COMPONENT_SKILL_VISIBILITY: (
        "Skill visibility",
        "How clearly your technical and soft skills are listed and organized, and whether your projects "
        "and experience back them up.",
    ),
    COMPONENT_FORMATTING_READABILITY: (
        "Formatting & readability",
        "How easy the resume is to read and for software to parse: headings, section boundaries, bullet "
        "structure and spacing. Visual design (fonts, colours) cannot be judged from text.",
    ),
}

SEVERITY_WHY = {
    "critical": "This can stop your resume from being shortlisted at all.",
    "warning": "This makes your resume noticeably weaker when compared with other candidates.",
    "info": "This is a small polish item that makes the resume look more careful.",
}

MISSING_SECTION_CHECKS = {
    "IMP_MISSING_PROJECTS": lambda p: bool(p.projects),
    "IMP_MISSING_EDUCATION": lambda p: bool(p.education),
    "IMP_MISSING_SKILLS": lambda p: bool(p.technical_skills),
    "IMP_CONTACT_MISSING_EMAIL": lambda p: bool(p.contact.email),
    "IMP_CONTACT_MISSING_PHONE": lambda p: bool(p.contact.phone),
}


def _value(x) -> str:
    return str(getattr(x, "value", x)).lower()


def confidence_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.60:
        return "medium"
    return "low"


SIGNIFICANT_DEDUCTION = 2.0

# Deductions whose advice is already covered by another issue Module D raises.
DEDUCTION_COVERED_BY = {
    "SEC_NO_PRACTICAL_WORK": {"IMP_MISSING_PROJECTS", "IMP_MISSING_PRACTICAL_WORK"},
    "SEC_NO_STANDALONE_PROJECTS": {"IMP_MISSING_PROJECTS", "IMP_WEAK_PROJECT_DESCRIPTION", "IMP_MISSING_PRACTICAL_WORK"},
    "SEC_FEW_PROJECTS": {"IMP_WEAK_PROJECT_DESCRIPTION", "IMP_MISSING_PROJECTS"},
    "CONTENT_NO_PROJECT_DEPTH": {
        "IMP_WEAK_PROJECT_DESCRIPTION",
        "IMP_MISSING_PROJECTS",
        "IMP_MISSING_PRACTICAL_WORK",
    },
    "FMT_AMBIGUOUS_SECTION_BOUNDARIES": {
        "FMT_MISSING_SECTION_HEADING",
        "IMP_MISSING_PROJECTS",
        "IMP_MISSING_SKILLS",
        "IMP_MISSING_EDUCATION",
    },
    "FMT_EXTRACTION_WARNINGS": {
        "IMP_EXTRACTION_UNCERTAINTY",
        "IMP_CONTACT_MISSING_EMAIL",
        "IMP_CONTACT_MISSING_PHONE",
        "IMP_MISSING_PROJECTS",
    },
    "FMT_MISSING_SECTION_HEADING": {
        "FMT_MISSING_SECTION_HEADING",
        "IMP_MISSING_PROJECTS",
        "IMP_MISSING_SKILLS",
        "IMP_MISSING_EDUCATION",
    },
    "SKILL_POOR_DIVERSITY": {
        "IMP_POOR_SKILL_CATEGORIZATION",
        "IMP_MISSING_SKILLS",
        "IMP_LOW_SKILL_INVENTORY",
    },
    "FMT_POOR_SEGMENTATION": {"IMP_EXTRACTION_UNCERTAINTY", "IMP_UNSTRUCTURED_WALL_OF_TEXT"},
    "FMT_LOW_ATS_CONFIDENCE": {"IMP_EXTRACTION_UNCERTAINTY"},
    # With no projects/experience there is nothing to add verbs or metrics to; "add projects" covers it.
    "CONTENT_NO_METRICS": {"IMP_MISSING_PRACTICAL_WORK"},
    "CONTENT_FEW_ACTION_VERBS": {"IMP_LACK_OF_ACTION_VERBS", "IMP_PASSIVE_PHRASING", "IMP_MISSING_PRACTICAL_WORK"},
    "SKILL_UNSUBSTANTIATED": {"IMP_UNSUBSTANTIATED_SKILLS", "IMP_MISSING_PROJECTS", "IMP_MISSING_PRACTICAL_WORK"},
}


def _covered_by_section_rule(rule_id: str, issue_ids) -> bool:
    return bool(DEDUCTION_COVERED_BY.get(rule_id, set()) & set(issue_ids))


def _deduction_issue(rule_id: str) -> Optional[str]:
    issue = SCORING_RULE_TO_ISSUE.get(rule_id)
    if issue is None and rule_id.startswith("SEC_MISSING_"):
        issue = "IMP_MISSING_" + rule_id[len("SEC_MISSING_") :]
    return issue


class ExplanationBuilder:
    """Builds AnalysisExplanations and runs cross-module consistency checks."""

    def build(
        self,
        scoring_result: Optional[ScoringResult],
        improvement_report: Optional[ImprovementAreasReport],
        recommendation_report: Optional[RecommendationReport],
    ) -> AnalysisExplanations:
        issues = list(improvement_report.issues) if improvement_report else []
        recs = list(recommendation_report.recommendations) if recommendation_report else []

        recs_by_issue: Dict[str, List[str]] = {}
        for rec in recs:
            for issue_id in rec.related_issue_ids:
                recs_by_issue.setdefault(issue_id, []).append(rec.recommendation_id)

        return AnalysisExplanations(
            score_summary=self._score_summary(scoring_result, issues),
            score_breakdown=self._components(scoring_result, recs),
            improvement_areas=[self._issue(i, recs_by_issue.get(i.issue_id, [])) for i in issues],
            recommendations=[self._recommendation(r, issues) for r in recs],
        )

    # ------------------------------------------------------------- pieces

    @staticmethod
    def _score_summary(
        scoring_result: Optional[ScoringResult], issues: List[ImprovementIssue]
    ) -> str:
        if scoring_result is None:
            return "The score could not be calculated for this resume, so only the detected issues are shown."
        lost = sorted(
            (
                (COMPONENT_INFO.get(name, (name, ""))[0], comp.max_score - comp.score)
                for name, comp in scoring_result.component_scores.items()
            ),
            key=lambda x: (-x[1], x[0]),
        )
        losses = [f"{label} (-{points:.1f})" for label, points in lost if points >= 0.05][:2]
        label = _value(scoring_result.score_label).title()
        parts = [f"Your resume scored {scoring_result.overall_score:.1f} out of 100 ({label})."]
        if losses:
            parts.append("Most points were lost in " + " and ".join(losses) + ".")
        else:
            parts.append("No points were lost in any scoring component.")
        high = sum(1 for i in issues if _value(i.priority) == "high")
        if high:
            parts.append(
                f"{high} high-priority issue{'s' if high > 1 else ''} should be fixed first."
            )
        return " ".join(parts)

    @staticmethod
    def _components(
        scoring_result: Optional[ScoringResult], recs: List[Recommendation]
    ) -> List[ComponentExplanation]:
        if scoring_result is None:
            return []
        out: List[ComponentExplanation] = []
        for name, comp in scoring_result.component_scores.items():
            label, measured = COMPONENT_INFO.get(
                name, (name.replace("_", " ").title(), "See scoring rules.")
            )
            deductions = [
                DeductionExplanation(
                    rule_id=d.rule_id,
                    points_deducted=d.points_deducted,
                    reason=d.reason,
                    evidence=d.evidence,
                    related_issue_id=_deduction_issue(d.rule_id),
                )
                for d in scoring_result.deductions
                if d.component == name
            ]
            out.append(
                ComponentExplanation(
                    component=name,
                    label=label,
                    what_is_measured=measured,
                    score=round(comp.score, 2),
                    max_score=comp.max_score,
                    weight=comp.weight,
                    percentage=round(100.0 * comp.score / comp.max_score, 1)
                    if comp.max_score
                    else 0.0,
                    points_lost=round(max(0.0, comp.max_score - comp.score), 2),
                    reason=comp.reason,
                    evidence=list(comp.evidence),
                    deductions=deductions,
                    how_to_improve=list(comp.how_to_improve),
                    related_recommendation_ids=[
                        r.recommendation_id for r in recs if r.related_score_component == name
                    ],
                )
            )
        return out

    @staticmethod
    def _issue(issue: ImprovementIssue, rec_ids: List[str]) -> IssueExplanation:
        rule = RULES.get(issue.issue_id)
        severity = _value(issue.severity)
        why = rule.why_it_matters if rule else SEVERITY_WHY.get(severity, SEVERITY_WHY["info"])
        where = (issue.affected_section or "").replace("_", " ") or "whole resume"
        return IssueExplanation(
            issue_id=issue.issue_id,
            title=issue.title,
            what_was_detected=issue.description,
            where=where,
            evidence=[e.strip() for e in (issue.evidence or "").split("; ") if e.strip()],
            confidence=issue.confidence,
            confidence_label=confidence_label(issue.confidence),
            why_it_matters=why,
            severity=severity,
            priority=_value(issue.priority),
            related_score_component=issue.related_score_component,
            recommendation_ids=rec_ids,
        )

    @staticmethod
    def _recommendation(
        rec: Recommendation, issues: List[ImprovementIssue]
    ) -> RecommendationExplanation:
        titles = [i.title for i in issues if i.issue_id in rec.related_issue_ids]
        reason = (
            "Suggested because the analysis detected: " + "; ".join(titles) + "."
            if titles
            else "Suggested because of a detected issue."
        )
        tier = _value(rec.priority)
        if rec.severity == "critical":
            why_priority = "High priority because the related issue is critical."
        else:
            band = {
                "high": f">= {HIGH_THRESHOLD}",
                "medium": f">= {MEDIUM_THRESHOLD}",
                "low": f"< {MEDIUM_THRESHOLD}",
            }[tier]
            why_priority = (
                f"{tier.title()} priority (score {rec.priority_score:.2f}, {band}) from severity '{rec.severity}', "
                f"the {rec.related_score_component or 'related'} component's weight, detection confidence "
                f"{rec.confidence:.2f} and how easy the fix is."
            )
        return RecommendationExplanation(
            recommendation_id=rec.recommendation_id,
            title=rec.title,
            related_issue_ids=list(rec.related_issue_ids),
            reason=reason,
            suggested_action=rec.suggested_action,
            supporting_evidence=list(rec.evidence),
            priority=tier,
            why_this_priority=why_priority,
        )

    # ----------------------------------------------------- consistency

    @staticmethod
    def consistency_checks(
        profile: CandidateProfile,
        scoring_result: Optional[ScoringResult],
        improvement_report: Optional[ImprovementAreasReport],
        recommendation_report: Optional[RecommendationReport],
        explanations: AnalysisExplanations,
    ) -> Tuple[Dict[str, bool], List[str]]:
        """Return (check_name -> passed, warnings for failed checks)."""
        checks: Dict[str, bool] = {}
        warnings: List[str] = []
        issue_ids = {i.issue_id for i in (improvement_report.issues if improvement_report else [])}
        recs = recommendation_report.recommendations if recommendation_report else []

        unmapped = [r.recommendation_id for r in recs if not set(r.related_issue_ids) <= issue_ids]
        checks["recommendations_map_to_detected_issues"] = not unmapped
        if unmapped:
            warnings.append(f"Recommendations without a detected issue: {unmapped}")

        rec_ids = [r.recommendation_id for r in recs]
        checks["no_duplicate_recommendations"] = len(rec_ids) == len(set(rec_ids))
        if not checks["no_duplicate_recommendations"]:
            warnings.append("Duplicate recommendation ids in output.")

        contradictions = [
            iid
            for iid, present in MISSING_SECTION_CHECKS.items()
            if iid in issue_ids and present(profile)
        ]
        checks["no_missing_section_contradictions"] = not contradictions
        if contradictions:
            warnings.append(
                f"Issues claim something is missing that was extracted: {contradictions}"
            )

        if scoring_result is not None:
            total = sum(c.score for c in scoring_result.component_scores.values())
            checks["component_scores_sum_to_overall"] = (
                abs(min(100.0, total) - scoring_result.overall_score) <= 0.05
            )
            explained = sum(len(c.deductions) for c in explanations.score_breakdown)
            checks["every_deduction_explained"] = explained == len(scoring_result.deductions)
            checks["every_deduction_has_reason"] = all(
                d.reason.strip() for d in scoring_result.deductions
            )
            for name in (
                "component_scores_sum_to_overall",
                "every_deduction_explained",
                "every_deduction_has_reason",
            ):
                if not checks[name]:
                    warnings.append(f"Consistency check failed: {name}")

            # Score deductions worth >= SIGNIFICANT_DEDUCTION points should be visible to the student
            # as an improvement area; otherwise points are lost with no advice on how to get them back.
            uncovered = sorted(
                {
                    d.rule_id
                    for d in scoring_result.deductions
                    if d.points_deducted >= SIGNIFICANT_DEDUCTION
                    and _deduction_issue(d.rule_id) not in issue_ids
                    and not _covered_by_section_rule(d.rule_id, issue_ids)
                }
            )
            checks["significant_deductions_have_improvement_area"] = not uncovered
            if uncovered:
                warnings.append(f"Score deductions with no matching improvement area: {uncovered}")

        explained_issues = {e.issue_id for e in explanations.improvement_areas}
        checks["every_issue_explained"] = explained_issues == issue_ids
        if not checks["every_issue_explained"]:
            warnings.append("Some detected issues have no explanation.")
        return checks, warnings


__all__ = ["COMPONENT_INFO", "ExplanationBuilder", "confidence_label"]
