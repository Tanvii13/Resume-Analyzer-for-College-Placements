"""
Issue deduplication and synthesis engine for Sprint 3 Module D.

Combines signals across:
- Section completeness & extraction metadata
- Module A ScoringEngine deductions
- Module B FormattingQualityAnalyzer findings
- Module C ContentQualityAnalyzer evaluations

Guarantees:
- Deduplicates overlapping findings across modules to prevent redundant advice.
- Preserves the highest priority (HIGH > MEDIUM > LOW) and severity (CRITICAL > WARNING > INFO).
- Merges supporting evidence strings for complete explainability.
- Deterministic output ordering sorted by priority and category.
"""

from typing import Dict, List
from app.nlp.improvement.schemas import (
    ImprovementIssue,
    ImprovementPriority,
    ImprovementSeverity,
)

# Priority ranking hierarchy
PRIORITY_ORDER: Dict[ImprovementPriority, int] = {
    ImprovementPriority.HIGH: 3,
    ImprovementPriority.MEDIUM: 2,
    ImprovementPriority.LOW: 1,
}

# Severity ranking hierarchy
SEVERITY_ORDER: Dict[ImprovementSeverity, int] = {
    ImprovementSeverity.CRITICAL: 3,
    ImprovementSeverity.WARNING: 2,
    ImprovementSeverity.INFO: 1,
}

# Normalization map for clustering related defect IDs from different modules
CANONICAL_ISSUE_CLUSTERS: Dict[str, str] = {
    # Missing sections
    "SEC_MISSING_EDUCATION": "IMP_MISSING_EDUCATION",
    "FMT_MISSING_SECTION_HEADING_EDUCATION": "IMP_MISSING_EDUCATION",
    "SEC_MISSING_PROJECTS": "IMP_MISSING_PROJECTS",
    "FMT_MISSING_SECTION_HEADING_PROJECTS": "IMP_MISSING_PROJECTS",
    "SEC_MISSING_SKILLS": "IMP_MISSING_SKILLS",
    "SKILL_NONE_DETECTED": "IMP_MISSING_SKILLS",
    "FMT_MISSING_SECTION_HEADING_TECHNICAL_SKILLS": "IMP_MISSING_SKILLS",
    # Academic records
    "SEC_EDU_MISSING_CGPA": "IMP_EDU_MISSING_CGPA",
    "SEC_EDU_MISSING_YEAR": "IMP_EDU_MISSING_YEAR",
    "SEC_EDU_MISSING_DEGREE": "IMP_EDU_MISSING_DEGREE",
    # Contact
    "SEC_CONTACT_MISSING_EMAIL": "IMP_CONTACT_MISSING_EMAIL",
    "SEC_CONTACT_MISSING_PHONE": "IMP_CONTACT_MISSING_PHONE",
    "SEC_CONTACT_MISSING_LINKS": "IMP_CONTACT_MISSING_DEV_PROFILES",
    # Content & Action Verbs
    "CNT_FEW_ACTION_VERBS": "IMP_LACK_OF_ACTION_VERBS",
    "CNT_WEAK_PASSIVE_PHRASES": "IMP_PASSIVE_PHRASING",
    "CNT_UNQUANTIFIED_BULLETS": "IMP_LACK_OF_MEASURABLE_IMPACT",
    "CNT_VAGUE_PROJECT_BULLETS": "IMP_WEAK_PROJECT_DESCRIPTION",
    # Skills
    "SKILL_LIMITED_INVENTORY": "IMP_LOW_SKILL_INVENTORY",
    "SKILL_VERY_LOW_INVENTORY": "IMP_LOW_SKILL_INVENTORY",
    "SKILL_POOR_DIVERSITY": "IMP_POOR_SKILL_CATEGORIZATION",
    "SKILL_UNSUBSTANTIATED": "IMP_UNSUBSTANTIATED_SKILLS",
    "SKILL_NO_SOFT_SKILLS": "IMP_MISSING_SOFT_SKILLS",
    "SKILL_DUPLICATE_PRESENTATION": "IMP_DUPLICATE_SKILLS",
    # Formatting
    "FMT_INCONSISTENT_HEADING_CASING": "IMP_INCONSISTENT_HEADINGS",
    "FMT_INCONSISTENT_HEADING_PUNCTUATION": "IMP_INCONSISTENT_HEADINGS",
    "FMT_UNSEGMENTED_WALL_OF_TEXT": "IMP_UNSTRUCTURED_WALL_OF_TEXT",
    "FMT_LONG_PARAGRAPH": "IMP_UNSTRUCTURED_WALL_OF_TEXT",
    "FMT_INCONSISTENT_BULLET_MARKERS": "IMP_INCONSISTENT_BULLET_FORMATTING",
    "FMT_EMPTY_BULLET_POINT": "IMP_INCONSISTENT_BULLET_FORMATTING",
    "FMT_EXCESSIVE_BULLET_LENGTH": "IMP_INCONSISTENT_BULLET_FORMATTING",
    "FMT_EXCESSIVE_BLANK_LINES": "IMP_EXCESSIVE_WHITESPACE",
    "FMT_IRREGULAR_WHITESPACE": "IMP_EXCESSIVE_WHITESPACE",
    "FMT_INCONSISTENT_DATE_FORMATS": "IMP_INCONSISTENT_DATE_FORMATS",
}


def deduplicate_and_rank_issues(issues: List[ImprovementIssue]) -> List[ImprovementIssue]:
    """
    Deduplicate related issues across modules and rank deterministically by priority.

    Args:
        issues: Raw list of detected improvement issues.

    Returns:
        Deduplicated, prioritized list of ImprovementIssue instances.
    """
    merged_map: Dict[str, ImprovementIssue] = {}

    for issue in issues:
        # Determine canonical key for deduplication
        canonical_key = CANONICAL_ISSUE_CLUSTERS.get(issue.issue_id, issue.issue_id)

        if canonical_key in merged_map:
            existing = merged_map[canonical_key]

            # 1. Resolve Priority (take highest)
            new_prio_val = PRIORITY_ORDER.get(issue.priority, 1)
            old_prio_val = PRIORITY_ORDER.get(existing.priority, 1)
            final_priority = issue.priority if new_prio_val > old_prio_val else existing.priority

            # 2. Resolve Severity (take highest)
            new_sev_val = SEVERITY_ORDER.get(issue.severity, 1)
            old_sev_val = SEVERITY_ORDER.get(existing.severity, 1)
            final_severity = issue.severity if new_sev_val > old_sev_val else existing.severity

            # 3. Combine Evidence
            combined_evidence = existing.evidence
            if issue.evidence and issue.evidence not in existing.evidence:
                combined_evidence = f"{existing.evidence}; {issue.evidence}"

            # 4. Take higher confidence
            final_confidence = max(existing.confidence, issue.confidence)

            # 5. Take longer / more descriptive description
            final_desc = issue.description if len(issue.description) > len(existing.description) else existing.description

            merged_map[canonical_key] = ImprovementIssue(
                issue_id=canonical_key,
                category=existing.category,
                title=existing.title,
                description=final_desc,
                severity=final_severity,
                priority=final_priority,
                affected_section=existing.affected_section or issue.affected_section,
                evidence=combined_evidence,
                related_score_component=existing.related_score_component,
                confidence=final_confidence,
                detection_rule=f"{existing.detection_rule}+{issue.detection_rule}",
            )
        else:
            # First time seeing this canonical issue
            normalized_issue = issue.model_copy(update={"issue_id": canonical_key})
            merged_map[canonical_key] = normalized_issue

    # Sort deterministically:
    # 1. Priority descending (HIGH=3, MEDIUM=2, LOW=1)
    # 2. Severity descending (CRITICAL=3, WARNING=2, INFO=1)
    # 3. Issue ID alphabetically
    sorted_issues = sorted(
        merged_map.values(),
        key=lambda item: (
            -PRIORITY_ORDER.get(item.priority, 0),
            -SEVERITY_ORDER.get(item.severity, 0),
            item.issue_id,
        ),
    )

    return sorted_issues


__all__ = [
    "PRIORITY_ORDER",
    "SEVERITY_ORDER",
    "CANONICAL_ISSUE_CLUSTERS",
    "deduplicate_and_rank_issues",
]
