from pydantic import BaseModel, Field
from typing import List, Optional


class OpportunityBase(BaseModel):
    id: str
    title: str
    company: str
    location: str
    opportunity_type: str  # "Internship" or "Full-time"
    required_skills: List[str]
    preferred_skills: List[str] = []
    min_cgpa: Optional[float] = None


class SkillCategoryBreakdown(BaseModel):
    matched_required: List[str]
    related_required: List[str]  # e.g., "PostgreSQL (Alternative: MySQL)"
    missing_required: List[str]
    matched_preferred: List[str]
    related_preferred: List[str]
    missing_preferred: List[str]


class OpportunityMatchCard(BaseModel):
    opportunity_id: str
    title: str
    company: str
    location: str
    opportunity_type: str
    match_percentage: float = Field(ge=0.0, le=100.0)
    relevance_tier: str  # "High Fit", "Moderate Fit", "Developing Fit"
    skills_breakdown: SkillCategoryBreakdown


class OpportunityRecommendationsResponse(BaseModel):
    total_opportunities_evaluated: int
    matched_opportunities_count: int
    has_suitable_matches: bool
    guidance_message: Optional[str] = None
    recommended_opportunities: List[OpportunityMatchCard]


class SingleOpportunityMatchRequest(BaseModel):
    opportunity_id: str
    required_skills: List[str] = []
    preferred_skills: List[str] = []
