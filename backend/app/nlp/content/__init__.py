"""
Content Quality and Impact Analyzer package for Sprint 3 Module C.

Exports:
- ContentQualityAnalyzer: Main standalone content quality evaluation service.
- analyze_content_quality: Top-level convenience evaluation function.
- Schemas: ContentQualityReport, EntryQualityEvaluation, BulletPointEvaluation,
  DescriptionCompleteness, VerbCategory, ActionVerbMatch, ImpactMetricMatch,
  CONTENT_ANALYZER_VERSION.
- Action Verbs: ACTION_VERB_TAXONOMY, check_leading_action_verb,
  detect_weak_introductory_phrase, find_action_verbs_in_text.
- Impact Metrics: detect_impact_metrics, NON_IMPACT_NUMERIC_PATTERNS.
- Similarity: compute_jaccard_similarity, find_duplicate_bullets_across_entries,
  detect_generic_content, evaluate_description_substance.
"""

from app.nlp.content.action_verbs import (
    ACTION_VERB_TAXONOMY,
    check_leading_action_verb,
    detect_weak_introductory_phrase,
    find_action_verbs_in_text,
)
from app.nlp.content.analyzer import (
    ContentQualityAnalyzer,
    analyze_content_quality,
)
from app.nlp.content.impact_metrics import (
    NON_IMPACT_NUMERIC_PATTERNS,
    detect_impact_metrics,
)
from app.nlp.content.schemas import (
    CONTENT_ANALYZER_VERSION,
    ActionVerbMatch,
    BulletPointEvaluation,
    ContentQualityReport,
    DescriptionCompleteness,
    EntryQualityEvaluation,
    ImpactMetricMatch,
    VerbCategory,
)
from app.nlp.content.similarity import (
    compute_jaccard_similarity,
    detect_generic_content,
    evaluate_description_substance,
    find_duplicate_bullets_across_entries,
)

__all__ = [
    "ContentQualityAnalyzer",
    "analyze_content_quality",
    "CONTENT_ANALYZER_VERSION",
    "DescriptionCompleteness",
    "VerbCategory",
    "ActionVerbMatch",
    "ImpactMetricMatch",
    "BulletPointEvaluation",
    "EntryQualityEvaluation",
    "ContentQualityReport",
    "ACTION_VERB_TAXONOMY",
    "check_leading_action_verb",
    "detect_weak_introductory_phrase",
    "find_action_verbs_in_text",
    "detect_impact_metrics",
    "NON_IMPACT_NUMERIC_PATTERNS",
    "compute_jaccard_similarity",
    "detect_generic_content",
    "evaluate_description_substance",
    "find_duplicate_bullets_across_entries",
]
