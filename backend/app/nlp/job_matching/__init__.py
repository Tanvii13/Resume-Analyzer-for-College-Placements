"""
Job Matching and Job Description Processing Package.

Sprint 4 NLP components for Resume Analyzer for College Placements.
"""

from typing import List, Optional

from app.nlp.job_matching.job_description_parser import JobDescriptionParser
from app.nlp.job_matching.schemas import (
    JOB_PARSER_VERSION,
    EducationRequirement,
    EligibilityCriteria,
    ExperienceRequirement,
    JobParsingMetadata,
    JobSkillRequirement,
    JobType,
    LocationRequirement,
    OtherJobRequirements,
    ParsedJobDescription,
    WorkplaceType,
)


def parse_job_description(text: str, job_id: Optional[str] = None) -> ParsedJobDescription:
    """
    Convenience function to parse a raw job description string into a validated ParsedJobDescription.

    Args:
        text: Raw job description text.
        job_id: Optional identifier for the job posting.

    Returns:
        Validated ParsedJobDescription instance.
    """
    return JobDescriptionParser().parse(text, job_id=job_id)


def parse_multiple_job_descriptions(texts: List[str]) -> List[ParsedJobDescription]:
    """
    Convenience function to parse a list of raw job descriptions independently.

    Args:
        texts: List of raw job description strings.

    Returns:
        List of validated ParsedJobDescription instances.
    """
    return JobDescriptionParser().parse_multiple(texts)


__all__ = [
    "JOB_PARSER_VERSION",
    "JobType",
    "WorkplaceType",
    "JobSkillRequirement",
    "ExperienceRequirement",
    "EducationRequirement",
    "EligibilityCriteria",
    "LocationRequirement",
    "OtherJobRequirements",
    "JobParsingMetadata",
    "ParsedJobDescription",
    "JobDescriptionParser",
    "parse_job_description",
    "parse_multiple_job_descriptions",
]
