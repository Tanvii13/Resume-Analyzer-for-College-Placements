
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExtractionData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: list[Any] = Field(...)
    education: list[Any] = Field(...)
    projects: list[Any] = Field(...)
    experience: list[Any] = Field(...)

class SkillExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technical_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    total_count: int = Field(ge=0)
