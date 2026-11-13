"""
Pydantic v2 data contracts for Sprint 3 Module B: Resume Formatting Quality Analyzer.

Defines schemas for:
- FormattingCategory: Dimension of formatting inspection (section, text, bullet, consistency).
- FindingSeverity: Impact tier of a detected formatting issue (critical, warning, info).
- FormattingFinding: Granular, evidence-backed issue finding.
- FormattingAnalysisResult: Top-level result model containing score, findings, strengths,
  and analysis limitations.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

FORMATTING_ANALYZER_VERSION = "3.0.0"


class FormattingCategory(str, Enum):
    """Categorical dimension of formatting inspection."""
    SECTION_STRUCTURE = "section_structure"
    TEXT_READABILITY = "text_readability"
    BULLET_STRUCTURE = "bullet_structure"
    RESUME_CONSISTENCY = "resume_consistency"


class FindingSeverity(str, Enum):
    """Severity tier reflecting impact on ATS parsing and recruiter readability."""
    CRITICAL = "critical"  # Major barrier (e.g. unsegmented wall of text, missing section boundaries)
    WARNING = "warning"    # Notable flaw (e.g. inconsistent bullets, mixed dates, excessive length)
    INFO = "info"          # Stylistic / polish suggestion (e.g. inconsistent terminal punctuation)


class _FormattingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class FormattingFinding(_FormattingModel):
    """
    An individual evidence-backed formatting or readability defect.
    """
    issue_id: str = Field(..., description="Unique machine-readable identifier (e.g. FMT_INCONSISTENT_BULLET_MARKERS)")
    category: FormattingCategory = Field(..., description="Formatting dimension")
    title: str = Field(..., description="Concise headline of the finding")
    description: str = Field(..., description="Actionable explanation of why this affects readability or ATS extraction")
    severity: FindingSeverity = Field(..., description="Impact tier (critical, warning, info)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    evidence: str = Field(..., description="Extracted line or token excerpt triggering the rule")
    line_reference: Optional[int] = Field(None, description="1-indexed line number in source text if identifiable")
    affected_section: Optional[str] = Field(None, description="Affected resume section (e.g. 'projects', 'education')")
    detection_rule: str = Field(..., description="Internal detector rule name")


class FormattingAnalysisResult(_FormattingModel):
    """
    Complete explainable formatting quality assessment.
    """
    formatting_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Overall formatting quality score clamped between 0 and 100",
    )
    max_score: float = Field(default=100.0, description="Maximum possible formatting score")
    findings: List[FormattingFinding] = Field(
        default_factory=list,
        description="Itemized list of detected formatting and readability issues",
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="Observed positive formatting attributes",
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Explicit analysis boundaries reflecting text-only extraction limits",
    )
    analyzer_version: str = Field(
        default=FORMATTING_ANALYZER_VERSION,
        description="Formatting quality analyzer rule set version",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic counts (total lines, blocks, bullet items, detected sections, page count)",
    )


__all__ = [
    "FORMATTING_ANALYZER_VERSION",
    "FormattingCategory",
    "FindingSeverity",
    "FormattingFinding",
    "FormattingAnalysisResult",
]
