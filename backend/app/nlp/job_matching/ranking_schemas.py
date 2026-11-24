"""
Pydantic v2 data contracts for Sprint 4 Module E: Job/Internship Relevance Ranking (US-12).

- JobOpportunity:        one opening, as raw JD text and/or the structured fields the backend
                         stores (title, company, required_skills, preferred_skills, min_cgpa, ...)
- RankingPreferences:    optional filters (job type, location / remote, minimum relevance)
- RankedOpportunity:     one ranked opening with relevance score, fit tier, eligibility,
                         matched / missing skills and the reasons for its position
- OpportunityRankingReport: the ranked list, filtered-out openings, skills missing across
                         many openings, and a clear message when nothing is a good match
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.nlp.job_matching.matcher_schemas import JobMatchResult
from app.nlp.job_matching.skill_gap_schemas import EligibilityStatus, SkillGapReport

RANKER_VERSION = "4.0.0"


class _RankModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class FitTier(str, Enum):
    HIGH = "High Fit"
    MODERATE = "Moderate Fit"
    DEVELOPING = "Developing Fit"


class JobOpportunity(_RankModel):
    """An opening to rank. Give `description` (raw JD text), structured fields, or both."""

    opportunity_id: str
    title: str | None = None
    company: str | None = None
    location: str | None = None
    opportunity_type: str | None = Field(None, description="'Internship', 'Full-time', ...")
    description: str | None = Field(None, description="Full job description text, if available")
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_cgpa: float | None = Field(None, ge=0.0, le=10.0)
    deadline: str | None = None

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "JobOpportunity":
        """Build from a backend `opportunities` row / OpportunityBase dict (extra keys ignored)."""
        oid = record.get("opportunity_id") or record.get("id")
        return cls(
            opportunity_id=str(oid) if oid is not None else (record.get("title") or "opportunity"),
            title=record.get("title"),
            company=record.get("company") or record.get("company_name"),
            location=record.get("location"),
            opportunity_type=record.get("opportunity_type") or record.get("job_type"),
            description=record.get("description"),
            required_skills=list(record.get("required_skills") or []),
            preferred_skills=list(record.get("preferred_skills") or []),
            min_cgpa=record.get("min_cgpa"),
            deadline=str(record["deadline"]) if record.get("deadline") else None,
        )


class RankingPreferences(_RankModel):
    job_types: list[str] = Field(default_factory=list, description="e.g. ['internship']; empty = any")
    locations: list[str] = Field(default_factory=list, description="Preferred cities; remote always allowed")
    include_ineligible: bool = Field(True, description="Keep not-eligible openings (ranked last)")
    min_relevance: float = Field(0.0, ge=0.0, le=100.0, description="Drop openings below this relevance")
    top_k: int | None = Field(None, ge=1)


class RankedOpportunity(_RankModel):
    rank: int = Field(..., ge=1)
    opportunity_id: str
    title: str | None = None
    company: str | None = None
    location: str | None = None
    opportunity_type: str | None = None
    relevance_score: float = Field(..., ge=0.0, le=100.0)
    fit_tier: FitTier
    match_score: float = Field(..., ge=0.0, le=100.0, description="Module C overall job-match score")
    required_coverage: float = Field(..., ge=0.0, le=1.0)
    preferred_coverage: float = Field(..., ge=0.0, le=1.0)
    eligibility_status: EligibilityStatus
    eligibility_issues: list[str] = Field(default_factory=list)
    is_suitable: bool
    matched_required: list[str] = Field(default_factory=list)
    partial_required: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    matched_preferred: list[str] = Field(default_factory=list)
    partial_preferred: list[str] = Field(default_factory=list)
    missing_preferred: list[str] = Field(default_factory=list)
    top_gaps: list[str] = Field(default_factory=list)
    ranking_reasons: list[str] = Field(default_factory=list)
    summary: str
    match_result: JobMatchResult | None = None
    skill_gap: SkillGapReport | None = None

    def to_backend_card(self) -> dict[str, Any]:
        """Shape of the backend's existing `OpportunityMatchCard` schema."""
        return {
            "opportunity_id": self.opportunity_id,
            "title": self.title or "",
            "company": self.company or "",
            "location": self.location or "",
            "opportunity_type": self.opportunity_type or "",
            "match_percentage": round(self.relevance_score, 2),
            "relevance_tier": self.fit_tier.value,
            "skills_breakdown": {
                "matched_required": self.matched_required,
                "related_required": self.partial_required,
                "missing_required": self.missing_required,
                "matched_preferred": self.matched_preferred,
                "related_preferred": self.partial_preferred,
                "missing_preferred": self.missing_preferred,
            },
        }


class FilteredOpportunity(_RankModel):
    opportunity_id: str
    title: str | None = None
    reason: str


class CommonGap(_RankModel):
    skill: str
    missing_in: int = Field(..., ge=1, description="Number of relevant openings that require it and you lack it")
    opportunity_titles: list[str] = Field(default_factory=list)


class OpportunityRankingReport(_RankModel):
    total_evaluated: int = 0
    suitable_count: int = 0
    has_suitable_matches: bool = False
    guidance_message: str
    ranked_opportunities: list[RankedOpportunity] = Field(default_factory=list)
    filtered_out: list[FilteredOpportunity] = Field(default_factory=list)
    common_gaps: list[CommonGap] = Field(default_factory=list)
    errors: list[dict[str, str]] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    ranker_version: str = RANKER_VERSION

    def to_backend_response(self) -> dict[str, Any]:
        """Shape of the backend's existing `OpportunityRecommendationsResponse` schema."""
        return {
            "total_opportunities_evaluated": self.total_evaluated,
            "matched_opportunities_count": self.suitable_count,
            "has_suitable_matches": self.has_suitable_matches,
            "guidance_message": self.guidance_message,
            "recommended_opportunities": [r.to_backend_card() for r in self.ranked_opportunities],
        }


__all__ = [
    "RANKER_VERSION",
    "CommonGap",
    "FilteredOpportunity",
    "FitTier",
    "JobOpportunity",
    "OpportunityRankingReport",
    "RankedOpportunity",
    "RankingPreferences",
]
