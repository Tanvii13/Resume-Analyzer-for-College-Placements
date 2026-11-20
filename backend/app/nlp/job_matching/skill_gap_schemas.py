"""
Pydantic v2 data contracts for Sprint 4 Module D: Skill Gap Analysis (US-13).

- SkillGapItem:      one JD skill with the candidate's status, evidence, importance and advice
- AlternativeGroup:  "Python or Java" style either-or requirements from the JD
- EligibilityCheck:  CGPA / batch / branch / degree checks against the JD's eligibility rules
- SkillGapReport:    matched, partial and missing skills (required vs preferred kept separate),
                     prioritized gaps, coverage figures and a plain-language summary
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

SKILL_GAP_ANALYZER_VERSION = "4.0.0"


class _GapModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SkillRequirementLevel(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    SOFT_SKILL = "soft_skill"


class SkillGapStatus(str, Enum):
    MATCHED = "matched"  # exact / alias / equivalent skill found
    PARTIAL = "partial"  # only a related skill found
    SATISFIED_BY_ALTERNATIVE = "satisfied_by_alternative"  # JD said "X or Y" and the candidate has Y
    MISSING = "missing"
    UNCERTAIN = "uncertain"


class GapImportance(str, Enum):
    CRITICAL = "critical"
    IMPORTANT = "important"
    NICE_TO_HAVE = "nice_to_have"


class EligibilityStatus(str, Enum):
    MET = "met"
    NOT_MET = "not_met"
    UNKNOWN = "unknown"


class SkillGapItem(_GapModel):
    skill: str = Field(..., description="Canonical skill name from the job description")
    level: SkillRequirementLevel
    status: SkillGapStatus
    match_category: str = Field(..., description="Module C match category (exact_match, related_match, ...)")
    candidate_evidence: str | None = Field(None, description="Candidate skill/entry that matched, if any")
    evidence_source: str | None = Field(None, description="Where in the resume the evidence was found")
    listed_in_skills_section: bool = Field(False, description="True if the evidence came from the Skills section")
    jd_evidence: str | None = Field(None, description="JD line that mentions this skill")
    from_responsibilities_only: bool = Field(
        False, description="Only mentioned in the responsibilities text, so it may not be a hard requirement"
    )
    alternative_group_id: str | None = None
    importance: GapImportance
    importance_score: float = Field(..., ge=0.0, le=1.0)
    related_skills_you_have: list[str] = Field(default_factory=list)
    explanation: str
    how_to_improve: str | None = Field(None, description="Actionable advice; None when nothing needs doing")


class AlternativeGroup(_GapModel):
    group_id: str
    level: SkillRequirementLevel
    skills: list[str]
    jd_evidence: str
    satisfied: bool
    satisfied_by: list[str] = Field(default_factory=list)


class EligibilityCheck(_GapModel):
    criterion: str = Field(..., description="cgpa / percentage / graduation_batch / branch / degree / backlogs")
    requirement: str
    candidate_value: str | None = None
    status: EligibilityStatus
    explanation: str


class SkillCoverage(_GapModel):
    required_total: int = 0
    required_satisfied: int = 0
    required_partial: int = 0
    required_coverage: float = Field(0.0, ge=0.0, le=1.0, description="Alternative-aware, partial counts half")
    preferred_total: int = 0
    preferred_satisfied: int = 0
    preferred_partial: int = 0
    preferred_coverage: float = Field(0.0, ge=0.0, le=1.0)
    soft_total: int = 0
    soft_satisfied: int = 0


class SkillGapReport(_GapModel):
    job_id: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    matched_required: list[SkillGapItem] = Field(default_factory=list)
    partial_required: list[SkillGapItem] = Field(default_factory=list)
    missing_required: list[SkillGapItem] = Field(default_factory=list)
    matched_preferred: list[SkillGapItem] = Field(default_factory=list)
    partial_preferred: list[SkillGapItem] = Field(default_factory=list)
    missing_preferred: list[SkillGapItem] = Field(default_factory=list)
    soft_skills: list[SkillGapItem] = Field(default_factory=list)
    uncertain: list[SkillGapItem] = Field(default_factory=list)
    alternative_groups: list[AlternativeGroup] = Field(default_factory=list)
    priority_gaps: list[SkillGapItem] = Field(
        default_factory=list, description="Missing/partial skills, most important first"
    )
    visibility_tips: list[str] = Field(
        default_factory=list, description="Skills the candidate has used but not listed in the Skills section"
    )
    experience_gap: str | None = None
    eligibility_checks: list[EligibilityCheck] = Field(default_factory=list)
    eligibility_status: EligibilityStatus = EligibilityStatus.UNKNOWN
    coverage: SkillCoverage = Field(default_factory=SkillCoverage)
    summary: str = ""
    warnings: list[str] = Field(default_factory=list)
    analyzer_version: str = SKILL_GAP_ANALYZER_VERSION


__all__ = [
    "SKILL_GAP_ANALYZER_VERSION",
    "AlternativeGroup",
    "EligibilityCheck",
    "EligibilityStatus",
    "GapImportance",
    "SkillCoverage",
    "SkillGapItem",
    "SkillGapReport",
    "SkillGapStatus",
    "SkillRequirementLevel",
]
