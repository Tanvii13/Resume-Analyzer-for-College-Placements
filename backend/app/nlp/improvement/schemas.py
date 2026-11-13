"""
Pydantic v2 data contracts for Sprint 3 Module D: Improvement Areas Detection Engine.

Defines schemas for:
- ImprovementCategory: Classification of improvement area.
- ImprovementSeverity: Structural severity of the defect (critical, warning, info).
- ImprovementPriority: Triage priority for campus placements (high, medium, low).
- ImprovementIssue: Explainable, evidence-backed defect item.
- ImprovementAreasReport: Comprehensive aggregate improvement areas summary report.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

IMPROVEMENT_ENGINE_VERSION = "3.0.0"


class ImprovementCategory(str, Enum):
    """Categorical dimensions of resume improvement."""
    SECTION_COMPLETENESS = "section_completeness"
    CONTENT_QUALITY = "content_quality"
    SKILL_VISIBILITY = "skill_visibility"
    FORMATTING = "formatting"


class ImprovementSeverity(str, Enum):
    """Severity tier reflecting structural defect impact."""
    CRITICAL = "critical"  # Major barrier (e.g. missing critical sections, unreadable layout)
    WARNING = "warning"    # Noticeable defect (e.g. passive verbs, unquantified bullets)
    INFO = "info"          # Polish or minor competitive advantage enhancement


class ImprovementPriority(str, Enum):
    """Actionable placement triage priority for the candidate."""
    HIGH = "high"          # Urgent fix required before campus recruitment drives
    MEDIUM = "medium"      # Important for recruiter review and shortlisting ranking
    LOW = "low"            # Stylistic polish and optional enhancements


class _ImprovementModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class ImprovementIssue(_ImprovementModel):
    """
    An individual explainable improvement area with supporting evidence and triage priority.
    """
    issue_id: str = Field(..., description="Unique machine-readable issue identifier (e.g. IMP_MISSING_PROJECTS)")
    category: ImprovementCategory = Field(..., description="Improvement category dimension")
    title: str = Field(..., description="Short, actionable headline for the issue")
    description: str = Field(..., description="Detailed explanation of the gap and why it matters for placement")
    severity: ImprovementSeverity = Field(..., description="Defect severity: critical, warning, info")
    priority: ImprovementPriority = Field(..., description="Placement triage priority: high, medium, low")
    affected_section: Optional[str] = Field(None, description="Affected resume section (e.g. 'education', 'projects')")
    evidence: str = Field(..., description="Specific extracted profile evidence or verified gap")
    related_score_component: str = Field(..., description="Associated scoring component name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    detection_rule: str = Field(..., description="Internal detector rule name")


class ImprovementAreasReport(_ImprovementModel):
    """
    Comprehensive aggregate improvement areas report combining Modules A, B, and C.
    """
    total_issues: int = Field(..., ge=0, description="Total deduplicated improvement issues identified")
    high_priority_issues: int = Field(..., ge=0, description="Count of urgent high-priority issues")
    medium_priority_issues: int = Field(..., ge=0, description="Count of medium-priority issues")
    low_priority_issues: int = Field(..., ge=0, description="Count of low-priority / polish issues")
    issues: List[ImprovementIssue] = Field(
        default_factory=list,
        description="Deduplicated list of prioritized improvement issues",
    )
    strong_areas: List[str] = Field(
        default_factory=list,
        description="Key positive dimensions where the resume excels",
    )
    weak_areas: List[str] = Field(
        default_factory=list,
        description="Key dimensions requiring candidate attention and revision",
    )
    summary: str = Field(..., description="Executive placement readiness summary")
    analyzer_version: str = Field(
        default=IMPROVEMENT_ENGINE_VERSION,
        description="Improvement engine rule set version",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostics, source module status, and execution metadata",
    )


__all__ = [
    "IMPROVEMENT_ENGINE_VERSION",
    "ImprovementCategory",
    "ImprovementSeverity",
    "ImprovementPriority",
    "ImprovementIssue",
    "ImprovementAreasReport",
]
