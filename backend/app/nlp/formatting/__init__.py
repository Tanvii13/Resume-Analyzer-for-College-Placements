"""
Formatting Quality Analyzer package for Sprint 3 Module B.

Exports:
- FormattingQualityAnalyzer: Main standalone formatting evaluation service.
- analyze_formatting: Top-level convenience evaluation function.
- FormattingAnalysisResult: Top-level result schema.
- FormattingFinding: Granular finding data contract.
- FormattingCategory, FindingSeverity: Dimension and severity enumerations.
- Checkers: SectionStructureChecker, TextReadabilityChecker,
  BulletStructureChecker, ResumeConsistencyChecker.
"""

from app.nlp.formatting.analyzer import FormattingQualityAnalyzer, analyze_formatting
from app.nlp.formatting.limitations import DEFAULT_ANALYZER_LIMITATIONS
from app.nlp.formatting.rules import (
    BulletStructureChecker,
    ResumeConsistencyChecker,
    SectionStructureChecker,
    TextReadabilityChecker,
)
from app.nlp.formatting.schemas import (
    FORMATTING_ANALYZER_VERSION,
    FindingSeverity,
    FormattingAnalysisResult,
    FormattingCategory,
    FormattingFinding,
)

__all__ = [
    "FormattingQualityAnalyzer",
    "analyze_formatting",
    "FormattingAnalysisResult",
    "FormattingFinding",
    "FormattingCategory",
    "FindingSeverity",
    "FORMATTING_ANALYZER_VERSION",
    "DEFAULT_ANALYZER_LIMITATIONS",
    "SectionStructureChecker",
    "TextReadabilityChecker",
    "BulletStructureChecker",
    "ResumeConsistencyChecker",
]
