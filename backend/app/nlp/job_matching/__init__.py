"""
Job Matching and Job Description Processing Package.

Sprint 4 NLP components for Resume Analyzer for College Placements.
"""

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
from app.nlp.job_matching.skill_engine import (
    ENGINE_VERSION as SKILL_ENGINE_VERSION,
)
from app.nlp.job_matching.skill_engine import (
    SkillEquivalenceEngine,
    SkillNormalizer,
    compare_candidate_to_job_skills,
    evaluate_skill_equivalence,
    get_equivalence_engine,
    get_skill_normalizer,
    normalize_skill,
)
from app.nlp.job_matching.skill_normalization_schemas import (
    EquivalenceEvaluation,
    EquivalenceRule,
    NormalizedSkill,
    SkillMatchMethod,
    SkillRelationshipType,
    SkillSetComparison,
)


def parse_job_description(text: str, job_id: str | None = None) -> ParsedJobDescription:
    """
    Convenience function to parse a raw job description string into a validated ParsedJobDescription.

    Args:
        text: Raw job description text.
        job_id: Optional identifier for the job posting.

    Returns:
        Validated ParsedJobDescription instance.
    """
    return JobDescriptionParser().parse(text, job_id=job_id)


def parse_multiple_job_descriptions(texts: list[str]) -> list[ParsedJobDescription]:
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
    "SKILL_ENGINE_VERSION",
    "EducationRequirement",
    "EligibilityCriteria",
    "EquivalenceEvaluation",
    "EquivalenceRule",
    "ExperienceRequirement",
    "JobDescriptionParser",
    "JobParsingMetadata",
    "JobSkillRequirement",
    "JobType",
    "LocationRequirement",
    "NormalizedSkill",
    "OtherJobRequirements",
    "ParsedJobDescription",
    "SkillEquivalenceEngine",
    "SkillMatchMethod",
    "SkillNormalizer",
    "SkillRelationshipType",
    "SkillSetComparison",
    "WorkplaceType",
    "compare_candidate_to_job_skills",
    "evaluate_skill_equivalence",
    "get_equivalence_engine",
    "get_skill_normalizer",
    "normalize_skill",
    "parse_job_description",
    "parse_multiple_job_descriptions",
]
