"""
Pydantic v2 data contracts for Sprint 3 Module C: Content Quality & Impact Analyzer.

Defines schemas for:
- DescriptionCompleteness: Completeness tier for an individual entry.
- VerbCategory: Functional category of action verbs.
- ActionVerbMatch: Details of an identified action verb.
- ImpactMetricMatch: Details of a verified measurable outcome.
- EntryQualityEvaluation: Granular evaluation of a single project or experience entry.
- ContentQualityReport: Aggregate content quality summary report.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

CONTENT_ANALYZER_VERSION = "3.0.0"


class DescriptionCompleteness(str, Enum):
    """Tier of descriptive completeness for a project or experience entry."""
    HIGH = "high"            # Clear problem, architecture, contributions, and technical details
    MODERATE = "moderate"    # Decent technical explanation, minor gaps in depth or outcomes
    LOW = "low"              # Sparse, vague, or short descriptions with limited technical details
    INCOMPLETE = "incomplete" # Missing description or title-only


class VerbCategory(str, Enum):
    """Functional category of technical and leadership action verbs."""
    ENGINEERING = "engineering"       # develop, architect, build, design, implement, refactor
    OPTIMIZATION = "optimization"     # optimize, accelerate, reduce, enhance, scale
    AUTOMATION = "automation"         # automate, deploy, containerize, orchestrate, integrate
    ANALYSIS = "analysis"             # analyze, evaluate, benchmark, audit, profile, test
    LEADERSHIP = "leadership"         # lead, spearhead, coordinate, mentor, collaborate
    CREATION = "creation"             # create, author, devise, formulate, launch


class _ContentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ActionVerbMatch(_ContentModel):
    """An identified technical or leadership action verb."""
    verb: str = Field(..., description="Matched verb token (e.g. 'architected', 'developed')")
    lemma: str = Field(..., description="Canonical base form (e.g. 'architect', 'develop')")
    category: VerbCategory = Field(..., description="Functional verb category")
    is_leading: bool = Field(False, description="True if the verb leads the sentence or bullet item")


class ImpactMetricMatch(_ContentModel):
    """A detected and verified quantifiable outcome or performance metric."""
    raw_match: str = Field(..., description="Matched metric string (e.g. '35%', '15,000 requests/sec', '2.4x')")
    metric_type: str = Field(
        ...,
        description="Type of metric: percentage, speedup, latency, volume, scale, accuracy, cost",
    )
    context: str = Field(..., description="Surrounding phrase providing outcome context")


class BulletPointEvaluation(_ContentModel):
    """Linguistic and impact evaluation of a single bullet point."""
    bullet_text: str = Field(..., description="Full text of the bullet point")
    word_count: int = Field(..., ge=0, description="Number of words in bullet")
    leading_action_verb: Optional[ActionVerbMatch] = Field(None, description="Leading action verb if present")
    action_verbs: List[ActionVerbMatch] = Field(default_factory=list, description="All action verbs in bullet")
    impact_metrics: List[ImpactMetricMatch] = Field(default_factory=list, description="Measurable outcomes detected")
    is_passive_or_weak: bool = Field(False, description="True if leading with weak phrases like 'worked on'")
    weak_phrase_found: Optional[str] = Field(None, description="Weak phrase found if applicable")


class EntryQualityEvaluation(_ContentModel):
    """Detailed content quality and impact evaluation for one project or work experience entry."""
    entry_id: str = Field(..., description="Unique entry identifier (e.g. 'proj_1', 'exp_0')")
    entry_title: str = Field(..., description="Title of the project or job role")
    entry_type: str = Field(..., description="Type of entry: 'project', 'experience', or 'internship'")
    content_quality_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Content quality score for this entry clamped between 0 and 100",
    )
    action_verbs_detected: List[str] = Field(
        default_factory=list,
        description="Unique action verbs identified in this entry",
    )
    impact_metrics_detected: List[str] = Field(
        default_factory=list,
        description="Unique impact metrics identified in this entry",
    )
    technology_mentions: List[str] = Field(
        default_factory=list,
        description="Technical tools, languages, and frameworks identified in this entry",
    )
    description_completeness: DescriptionCompleteness = Field(
        ...,
        description="Qualitative completeness tier",
    )
    issues: List[str] = Field(
        default_factory=list,
        description="Identified weaknesses, passive phrases, or gaps in this entry",
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Positive evidence justifying the score",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score in the evaluation",
    )
    bullet_evaluations: List[BulletPointEvaluation] = Field(
        default_factory=list,
        description="Granular evaluation of each bullet point in this entry",
    )


class ContentQualityReport(_ContentModel):
    """Complete explainable content quality and impact assessment for a candidate profile."""
    overall_content_quality_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Aggregate placement content quality score out of 100",
    )
    total_entries_analyzed: int = Field(..., ge=0, description="Total project and experience entries evaluated")
    entries: List[EntryQualityEvaluation] = Field(
        default_factory=list,
        description="Itemized evaluations for each individual entry",
    )
    aggregate_action_verb_count: int = Field(
        default=0,
        ge=0,
        description="Total distinct action verbs detected across all entries",
    )
    aggregate_impact_metrics_count: int = Field(
        default=0,
        ge=0,
        description="Total verifiable impact metrics detected across all entries",
    )
    generic_content_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings regarding boilerplate or unspecific descriptions",
    )
    duplicate_content_warnings: List[str] = Field(
        default_factory=list,
        description="Warnings regarding duplicate or repetitive bullet points",
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="Observed content strengths across the candidate's portfolio",
    )
    recommendations_summary: List[str] = Field(
        default_factory=list,
        description="Actionable improvement suggestions for strengthening descriptions",
    )
    analyzer_version: str = Field(
        default=CONTENT_ANALYZER_VERSION,
        description="Content analyzer rule set version",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic counts and execution details",
    )


__all__ = [
    "CONTENT_ANALYZER_VERSION",
    "DescriptionCompleteness",
    "VerbCategory",
    "ActionVerbMatch",
    "ImpactMetricMatch",
    "BulletPointEvaluation",
    "EntryQualityEvaluation",
    "ContentQualityReport",
]
