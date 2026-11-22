from uuid import UUID
from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field


class AnonymizedResumeResponse(BaseModel):
    """
    US-17: Privacy-compliant anonymized candidate view
    for blind screening by recruiters and placement staff.
    """
    resume_id: Union[UUID, str]
    candidate_id_hash: str = Field(
        ..., 
        description="Deterministic pseudonymous identifier (e.g., CAND-A1B2C3)"
    )
    anonymized_text: str = Field(
        ..., 
        description="Resume raw text with contact PII safely redacted"
    )
    skills: List[str] = Field(
        default_factory=list, 
        description="Preserved technical and soft skills"
    )
    experience_years: Optional[float] = None
    cgpa: Optional[float] = None
    degree: Optional[str] = None
    masked_fields: List[str] = Field(
        default_factory=list, 
        description="List of PII entity types that were redacted"
    )
    detected_pii_counts: Dict[str, int] = Field(
        default_factory=dict, 
        description="Breakdown of redacted entities count"
    )
    is_anonymized: bool = True
    status: str = "success"


class DirectMaskRequest(BaseModel):
    """
    Payload for directly sanitizing/masking raw text.
    """
    raw_text: str = Field(..., min_length=1, description="Raw resume text to redact")
    candidate_name: Optional[str] = Field(None, description="Optional candidate full name to scrub")
    mask_style: Optional[str] = Field("tag", description="'tag' ([REDACTED_EMAIL]) or 'partial' (u***r@domain.com)")


class DirectMaskResponse(BaseModel):
    """
    Response schema for direct text masking.
    """
    original_length: int
    masked_length: int
    masked_text: str
    detected_pii_counts: Dict[str, int] = Field(default_factory=dict)
    is_safe: bool = True
