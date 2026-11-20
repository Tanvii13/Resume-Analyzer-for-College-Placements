"""
Pydantic v2 schemas for Skill Normalization and Equivalence Engine.

Sprint 4 Module B (NLP-JobMatching).
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SkillRelationshipType(str, Enum):
    """Controlled relationship types between skills."""
    EXACT_MATCH = "exact_match"       # Identical canonical skill (e.g. Python == Python)
    EXACT_ALIAS = "exact_alias"       # Recognized alias/abbreviation (e.g. JS -> JavaScript)
    EQUIVALENT = "equivalent"         # Functionally interchangeable (e.g. MariaDB <=> MySQL)
    RELATED = "related"               # Ecosystem companion (e.g. Docker <=> Kubernetes)
    PREREQUISITE = "prerequisite"     # Foundational dependency (e.g. Python -> Django)
    UNRELATED = "unrelated"           # No equivalence or relationship


class SkillMatchMethod(str, Enum):
    """Method used by the normalizer to match a raw skill string."""
    EXACT_CANONICAL = "exact_canonical"             # Matches taxonomy canonical name directly
    ALIAS = "alias"                                 # Matches taxonomy alias table
    ABBREVIATION = "abbreviation"                   # Recognized short form / acronym
    SYMBOL_NORMALIZED = "symbol_normalized"         # Casing, punctuation, or symbol cleanup
    EXPLICIT_EQUIVALENCE = "explicit_equivalence"   # Configured equivalence rule
    UNRECOGNIZED = "unrecognized"                   # Not found in taxonomy or rules


class EquivalenceRule(_Model):
    """Single curated equivalence or relationship rule between two skills."""
    canonical_skill: str = Field(..., description="Primary canonical skill name")
    equivalent_skill: str = Field(..., description="Related or equivalent skill name")
    relationship_type: SkillRelationshipType = Field(..., description="Type of relationship")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    bidirectional: bool = Field(True, description="Whether relationship holds symmetrically")
    source: str = Field("curated", description="Source of the rule")
    rationale: str = Field(..., description="Domain rationale for the relationship")
    version: str = Field("1.0.0", description="Configuration version")


class NormalizedSkill(_Model):
    """Result of normalizing a raw skill mention."""
    raw_mention: str = Field(..., description="Original raw text verbatim")
    canonical_name: str | None = Field(None, description="Resolved canonical name in taxonomy")
    category: str | None = Field(None, description="Taxonomy category if recognized")
    is_recognized: bool = Field(False, description="Whether skill was resolved in taxonomy")
    matched_alias: str | None = Field(None, description="Matched alias if resolved via alias")
    match_method: SkillMatchMethod = Field(
        SkillMatchMethod.UNRECOGNIZED,
        description="Method used for normalization",
    )
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Resolution confidence")
    evidence: str | None = Field(None, description="Explanation or provenance of the match")


class EquivalenceEvaluation(_Model):
    """Detailed evaluation between two skills (candidate vs requirement)."""
    skill_a: str = Field(..., description="First skill name or raw mention")
    skill_b: str = Field(..., description="Second skill name or raw mention")
    canonical_a: str | None = Field(None, description="Canonical name of first skill")
    canonical_b: str | None = Field(None, description="Canonical name of second skill")
    is_equivalent: bool = Field(
        False,
        description="True for exact_match, exact_alias, or equivalent",
    )
    is_related: bool = Field(
        False,
        description="True for related or prerequisite relationships",
    )
    relationship_type: SkillRelationshipType = Field(
        SkillRelationshipType.UNRELATED,
        description="Classified relationship",
    )
    similarity_score: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Match score: 1.0 for exact/alias, ~0.95 for equivalent, ~0.60-0.85 for related, 0.0 for unrelated",
    )
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Confidence of the relationship evaluation",
    )
    rationale: str = Field(..., description="Detailed explanation of the relationship decision")
    evidence: str | None = Field(None, description="Evidence / provenance")
    version: str = Field("1.0.0", description="Rule or engine version")


class SkillSetComparison(_Model):
    """Comprehensive comparison between Candidate skills and Job Description requirements."""
    candidate_skills: list[str] = Field(default_factory=list)
    job_required_skills: list[str] = Field(default_factory=list)
    job_preferred_skills: list[str] = Field(default_factory=list)
    matched_required: list[EquivalenceEvaluation] = Field(default_factory=list)
    matched_preferred: list[EquivalenceEvaluation] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    missing_preferred: list[str] = Field(default_factory=list)
    related_matches: list[EquivalenceEvaluation] = Field(default_factory=list)
    unmatched_candidate: list[str] = Field(default_factory=list)
    required_coverage_ratio: float = Field(0.0, ge=0.0, le=1.0)
    overall_coverage_ratio: float = Field(0.0, ge=0.0, le=1.0)


__all__ = [
    "EquivalenceEvaluation",
    "EquivalenceRule",
    "NormalizedSkill",
    "SkillMatchMethod",
    "SkillRelationshipType",
    "SkillSetComparison",
]
