"""
Resume Scoring Engine package for Sprint 3 Module A.

Exports:
- ResumeScoringEngine: Main placement readiness scoring coordinator.
- score_resume: Top-level convenience evaluation function.
- ScoringWeights: Configurable weight model.
- Data contracts: ScoringResult, ComponentScore, ScoreDeduction, ScoreLabel.
- Individual component scorers: SectionCompletenessScorer, ContentQualityScorer,
  SkillVisibilityScorer, FormattingReadabilityScorer.
"""

from app.nlp.scoring.content_scoring import ContentQualityScorer
from app.nlp.scoring.engine import ResumeScoringEngine, score_resume
from app.nlp.scoring.formatting_scoring import FormattingReadabilityScorer
from app.nlp.scoring.schemas import (
    ComponentScore,
    ScoreDeduction,
    ScoreLabel,
    ScoringResult,
)
from app.nlp.scoring.section_scoring import SectionCompletenessScorer
from app.nlp.scoring.skill_scoring import SkillVisibilityScorer
from app.nlp.scoring.weights import (
    COMPONENT_CONTENT_QUALITY,
    COMPONENT_FORMATTING_READABILITY,
    COMPONENT_JOB_ALIGNMENT,
    COMPONENT_SECTION_COMPLETENESS,
    COMPONENT_SKILL_VISIBILITY,
    REFERENCE_WEIGHTS,
    SCORING_RULE_VERSION,
    SPRINT3_DEFAULT_WEIGHTS,
    ScoringWeights,
)

__all__ = [
    "ResumeScoringEngine",
    "score_resume",
    "ScoringWeights",
    "SCORING_RULE_VERSION",
    "REFERENCE_WEIGHTS",
    "SPRINT3_DEFAULT_WEIGHTS",
    "COMPONENT_SECTION_COMPLETENESS",
    "COMPONENT_CONTENT_QUALITY",
    "COMPONENT_SKILL_VISIBILITY",
    "COMPONENT_FORMATTING_READABILITY",
    "COMPONENT_JOB_ALIGNMENT",
    "ScoreLabel",
    "ScoreDeduction",
    "ComponentScore",
    "ScoringResult",
    "SectionCompletenessScorer",
    "ContentQualityScorer",
    "SkillVisibilityScorer",
    "FormattingReadabilityScorer",
]
