"""
Job Matching and Job Description Processing Package.

Sprint 4 NLP components for Resume Analyzer for College Placements.
"""

from app.nlp.job_matching.job_description_parser import JobDescriptionParser
from app.nlp.job_matching.matcher_schemas import (
    MATCHER_ENGINE_VERSION,
    ComponentScore,
    EvidenceSource,
    JobDescriptionProfile,
    JobMatchResult,
    MatchCategory,
    MatchingWeights,
    RequirementMatch,
    RequirementType,
)
from app.nlp.job_matching.resume_job_matcher import (
    ResumeJobMatcher,
    calculate_text_similarity,
    match_resume_to_job,
)
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


__all__ = [  # noqa: RUF022
    # Module A: Job Description Processing
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
    # Module B: Skill Normalization and Equivalence Engine
    "SKILL_ENGINE_VERSION",
    "SkillRelationshipType",
    "SkillMatchMethod",
    "EquivalenceRule",
    "NormalizedSkill",
    "EquivalenceEvaluation",
    "SkillSetComparison",
    "SkillNormalizer",
    "SkillEquivalenceEngine",
    "get_skill_normalizer",
    "get_equivalence_engine",
    "normalize_skill",
    "evaluate_skill_equivalence",
    "compare_candidate_to_job_skills",
    # Module C: Resume-Job Matching Engine
    "MATCHER_ENGINE_VERSION",
    "JobDescriptionProfile",
    "MatchCategory",
    "RequirementType",
    "EvidenceSource",
    "RequirementMatch",
    "ComponentScore",
    "MatchingWeights",
    "JobMatchResult",
    "ResumeJobMatcher",
    "match_resume_to_job",
    "calculate_text_similarity",
]
