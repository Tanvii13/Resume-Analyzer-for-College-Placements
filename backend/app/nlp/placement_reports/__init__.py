"""
Sprint 5 Module D: Placement Reports and Insights (US-15).

Aggregates existing per-student NLP results into a privacy-safe placement report with
statistics, common skill gaps, frequent resume weaknesses, training recommendations,
evidence-backed insights and limitations.
"""

from app.nlp.placement_reports.builder import PlacementReportBuilder, PrivacyViolationError, build_placement_report
from app.nlp.placement_reports.schemas import (
    DEFAULT_MIN_GROUP_SIZE,
    PLACEMENT_REPORT_VERSION,
    SUPPORTING_INFORMATION_NOTE,
    ComponentAverage,
    ConfidenceLevel,
    DataCoverage,
    GroupSummary,
    Insight,
    InsightType,
    LabelShare,
    PlacementReport,
    Priority,
    PrivacySummary,
    ReadinessSummary,
    ScoreStatistics,
    SkillGapStat,
    SkillPresence,
    StudentRecord,
    TrainingRecommendation,
    WeaknessStat,
)
from app.nlp.placement_reports.training_catalog import SKILL_PROGRAMS, WEAKNESS_PROGRAMS, TrainingProgram
from app.nlp.placement_reports.workflow import SPRINT5_WORKFLOW_VERSION, Sprint5Workflow, StudentAnalysis

__all__ = [
    "DEFAULT_MIN_GROUP_SIZE",
    "PLACEMENT_REPORT_VERSION",
    "SKILL_PROGRAMS",
    "SPRINT5_WORKFLOW_VERSION",
    "SUPPORTING_INFORMATION_NOTE",
    "WEAKNESS_PROGRAMS",
    "ComponentAverage",
    "ConfidenceLevel",
    "DataCoverage",
    "GroupSummary",
    "Insight",
    "InsightType",
    "LabelShare",
    "PlacementReport",
    "PlacementReportBuilder",
    "Priority",
    "PrivacySummary",
    "PrivacyViolationError",
    "ReadinessSummary",
    "ScoreStatistics",
    "SkillGapStat",
    "SkillPresence",
    "Sprint5Workflow",
    "StudentAnalysis",
    "StudentRecord",
    "TrainingProgram",
    "TrainingRecommendation",
    "WeaknessStat",
    "build_placement_report",
]
