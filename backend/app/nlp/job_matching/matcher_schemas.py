"""
Pydantic v2 data contracts for Sprint 4 Module C: Resume-Job Matching Engine.

Defines schemas for:
- MatchCategory (exact_match, alias_match, equivalent_match, related_match, missing, uncertain)
- RequirementType (required_technical_skill, preferred_technical_skill, soft_skill, experience, education, project, eligibility)
- EvidenceSource (provenance tracking)
- RequirementMatch (individual requirement evaluation with evidence)
- ComponentScore (dimension-level scoring breakdown)
- MatchingWeights (configurable weights with documented rationale)
- JobMatchResult (comprehensive match evaluation payload)
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.nlp.job_matching.schemas import ParsedJobDescription
from app.nlp.schemas import ConfidenceLevel
from app.nlp.versioning import NLPVersionMetadata

MATCHER_ENGINE_VERSION = "4.0.0"

# Type alias for interoperability
JobDescriptionProfile = ParsedJobDescription


class _MatchModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class MatchCategory(str, Enum):
    """Controlled classification categories for each requirement match."""
    EXACT_MATCH = "exact_match"             # Exact canonical match
    ALIAS_MATCH = "alias_match"             # Matches via recognized alias/abbreviation
    EQUIVALENT_MATCH = "equivalent_match"   # Drop-in functional equivalent
    RELATED_MATCH = "related_match"         # Ecosystem companion / prerequisite / partial
    MISSING = "missing"                     # Requirement not found in candidate profile
    UNCERTAIN = "uncertain"                 # Insufficient or ambiguous information in JD


class RequirementType(str, Enum):
    """Dimension category of the job requirement."""
    REQUIRED_TECHNICAL_SKILL = "required_technical_skill"
    PREFERRED_TECHNICAL_SKILL = "preferred_technical_skill"
    SOFT_SKILL = "soft_skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    PROJECT = "project"
    ELIGIBILITY = "eligibility"
    OTHER = "other"


class EvidenceSource(str, Enum):
    """Source location in CandidateProfile where match evidence was found."""
    EXPLICIT_SKILLS_SECTION = "explicit_skills_section"
    PROJECT_TECHNOLOGIES = "project_technologies"
    PROJECT_DESCRIPTION = "project_description"
    EXPERIENCE_TECHNOLOGIES = "experience_technologies"
    EXPERIENCE_RESPONSIBILITIES = "experience_responsibilities"
    INTERNSHIP_TECHNOLOGIES = "internship_technologies"
    INTERNSHIP_RESPONSIBILITIES = "internship_responsibilities"
    EDUCATION_RECORD = "education_record"
    INFERRED_TEXT = "inferred_text"
    NONE = "none"


class RequirementMatch(_MatchModel):
    """
    Detailed evaluation of a single job requirement against candidate evidence.
    """
    requirement_name: str = Field(..., description="Name of the job requirement")
    requirement_type: RequirementType = Field(..., description="Category of requirement")
    category: MatchCategory = Field(..., description="Match category")
    matched_value: str | None = Field(None, description="Candidate skill or qualification that matched")
    score: float = Field(0.0, ge=0.0, le=1.0, description="Match score (0.0 to 1.0)")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence of the match evaluation")
    is_satisfied: bool = Field(False, description="True for exact, alias, or equivalent matches")
    evidence_source: EvidenceSource = Field(EvidenceSource.NONE, description="Location of evidence in candidate profile")
    evidence: str | None = Field(None, description="Specific evidence string with full provenance")
    rationale: str = Field(..., description="Explanation of why this requirement received this evaluation")


class ComponentScore(_MatchModel):
    """
    Scoring breakdown for one dimension of the match evaluation.
    """
    category: str = Field(..., description="Dimension name (e.g. required_technical_skills)")
    earned_score: float = Field(..., ge=0.0, description="Raw earned points in this dimension")
    max_score: float = Field(..., gt=0.0, description="Maximum possible points in this dimension")
    weight: float = Field(..., ge=0.0, le=1.0, description="Configured dimension weight")
    weighted_score: float = Field(..., ge=0.0, description="Earned score scaled by weight")
    percentage: float = Field(..., ge=0.0, le=100.0, description="Earned score as percentage")
    matched_count: int = Field(0, ge=0, description="Number of satisfied requirements")
    total_count: int = Field(0, ge=0, description="Total number of requirements in this dimension")
    explanation: str = Field(..., description="Human-readable explanation of dimension score")


class MatchingWeights(_MatchModel):
    """
    Configurable weights for the deterministic Resume-Job matching engine.

    Rationale:
    - required_skills (0.40): Primary gating factor for job fit is core technical capability.
    - preferred_skills (0.15): Secondary technical pluses that elevate a candidate.
    - relevant_experience (0.15): Practical work or internship duration and relevance.
    - relevant_projects (0.15): Tangible proof of building systems with relevant tech stack.
    - education_alignment (0.10): Degree, major, and placement eligibility (CPI/CGPA).
    - soft_skills (0.05): Essential behavioral, teamwork, and communication competencies.
    Sum = 1.00 (100%).
    """
    required_skills_weight: float = Field(0.40, ge=0.0, le=1.0)
    preferred_skills_weight: float = Field(0.15, ge=0.0, le=1.0)
    experience_weight: float = Field(0.15, ge=0.0, le=1.0)
    projects_weight: float = Field(0.15, ge=0.0, le=1.0)
    education_weight: float = Field(0.10, ge=0.0, le=1.0)
    soft_skills_weight: float = Field(0.05, ge=0.0, le=1.0)


class JobMatchResult(_MatchModel):
    """
    Comprehensive, explainable output from the Resume-Job matching engine.
    """
    job_id: str | None = Field(None, description="Identifier of the job posting")
    job_title: str | None = Field(None, description="Title of the job posting")
    candidate_name: str | None = Field(None, description="Candidate name if available")
    overall_score: float = Field(0.0, ge=0.0, le=100.0, description="Deterministic overall match score (0-100)")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Overall confidence of the match evaluation")
    confidence_level: ConfidenceLevel = Field(ConfidenceLevel.HIGH, description="Confidence categorical tier")
    component_scores: dict[str, ComponentScore] = Field(default_factory=dict, description="Dimension score breakdown")
    matched_requirements: list[RequirementMatch] = Field(default_factory=list, description="Fully satisfied requirements")
    partially_matched_requirements: list[RequirementMatch] = Field(default_factory=list, description="Related / partial requirements")
    missing_requirements: list[RequirementMatch] = Field(default_factory=list, description="Unmet requirements")
    uncertain_requirements: list[RequirementMatch] = Field(default_factory=list, description="Ambiguous or low-confidence requirements")
    all_matches: list[RequirementMatch] = Field(default_factory=list, description="Complete list of requirement matches")
    scoring_explanations: list[str] = Field(default_factory=list, description="Explainability narratives for match score")
    matching_engine_version: str = MATCHER_ENGINE_VERSION
    version_metadata: NLPVersionMetadata | None = None


__all__ = [
    "MATCHER_ENGINE_VERSION",
    "ComponentScore",
    "EvidenceSource",
    "JobDescriptionProfile",
    "JobMatchResult",
    "MatchCategory",
    "MatchingWeights",
    "RequirementMatch",
    "RequirementType",
]
