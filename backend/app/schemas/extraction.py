
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExtractionData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills: list[Any] = Field(...)
    education: list[Any] = Field(...)
    projects: list[Any] = Field(...)
    experience: list[Any] = Field(...)
