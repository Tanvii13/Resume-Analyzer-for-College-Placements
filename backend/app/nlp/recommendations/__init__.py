"""
Rule-Based Recommendation Engine package for Sprint 3 Module E (US-09).

Exports:
- RecommendationEngine / generate_recommendations: Module D issues -> prioritized recommendations.
- Schemas: Recommendation, RecommendationReport, RecommendationCategory, RecommendationPriority.
- Rule registry: RULES, RecommendationRule.
"""

from app.nlp.recommendations.engine import (
    SCORING_RULE_TO_ISSUE,
    RecommendationEngine,
    generate_recommendations,
)
from app.nlp.recommendations.rules import RULES, RULE_SET_VERSION, RecommendationRule
from app.nlp.recommendations.schemas import (
    RECOMMENDATION_ENGINE_VERSION,
    Recommendation,
    RecommendationCategory,
    RecommendationPriority,
    RecommendationReport,
)

__all__ = [
    "RECOMMENDATION_ENGINE_VERSION",
    "RULES",
    "RULE_SET_VERSION",
    "SCORING_RULE_TO_ISSUE",
    "Recommendation",
    "RecommendationCategory",
    "RecommendationEngine",
    "RecommendationPriority",
    "RecommendationReport",
    "RecommendationRule",
    "generate_recommendations",
]
