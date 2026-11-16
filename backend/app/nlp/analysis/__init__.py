"""
Sprint 3 Module F: Explainability & NLP Pipeline Integration.

Exports:
- ResumeAnalysisPipeline / run_sprint3_analysis: CandidateProfile -> Sprint3AnalysisResult
- ExplanationBuilder: score, issue and recommendation explanations + consistency checks
- Schemas: Sprint3AnalysisResult, AnalysisExplanations, ComponentExplanation,
  IssueExplanation, RecommendationExplanation, AnalysisMetadata, ModuleError
"""

from app.nlp.analysis.explainability import ExplanationBuilder
from app.nlp.analysis.pipeline import ResumeAnalysisPipeline, run_sprint3_analysis
from app.nlp.analysis.schemas import (
    SPRINT3_ANALYZER_VERSION,
    AnalysisExplanations,
    AnalysisMetadata,
    ComponentExplanation,
    DeductionExplanation,
    IssueExplanation,
    ModuleError,
    RecommendationExplanation,
    Sprint3AnalysisResult,
)

__all__ = [
    "SPRINT3_ANALYZER_VERSION",
    "AnalysisExplanations",
    "AnalysisMetadata",
    "ComponentExplanation",
    "DeductionExplanation",
    "ExplanationBuilder",
    "IssueExplanation",
    "ModuleError",
    "RecommendationExplanation",
    "ResumeAnalysisPipeline",
    "Sprint3AnalysisResult",
    "run_sprint3_analysis",
]
