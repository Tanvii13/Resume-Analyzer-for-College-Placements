"""
Improvement Areas Detection Engine package for Sprint 3 Module D.

Exports:
- ImprovementAreasDetector: Main multi-module improvement detection service.
- detect_improvement_areas: Top-level convenience detection function.
- Schemas: ImprovementAreasReport, ImprovementIssue, ImprovementCategory,
  ImprovementSeverity, ImprovementPriority, IMPROVEMENT_ENGINE_VERSION.
- Deduplication: deduplicate_and_rank_issues.
"""

from app.nlp.improvement.deduplicator import deduplicate_and_rank_issues
from app.nlp.improvement.detector import (
    ImprovementAreasDetector,
    detect_improvement_areas,
)
from app.nlp.improvement.schemas import (
    IMPROVEMENT_ENGINE_VERSION,
    ImprovementAreasReport,
    ImprovementCategory,
    ImprovementIssue,
    ImprovementPriority,
    ImprovementSeverity,
)

__all__ = [
    "ImprovementAreasDetector",
    "detect_improvement_areas",
    "IMPROVEMENT_ENGINE_VERSION",
    "ImprovementCategory",
    "ImprovementSeverity",
    "ImprovementPriority",
    "ImprovementIssue",
    "ImprovementAreasReport",
    "deduplicate_and_rank_issues",
]
