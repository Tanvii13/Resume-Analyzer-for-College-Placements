"""
Natural Language Processing (NLP) package for Resume Analyzer for College Placements.

Provides modular text preprocessing, section classification, entity extraction,
skill normalization, and candidate profile aggregation.
"""

from app.nlp.extractors import (
    BaseExtractor,
    CertificationsExtractor,
    ContactExtractor,
    ContactInfo,
    EducationExtractor,
    ExperienceExtractor,
    ExtractedSkill,
    ListSections,
    ProjectExtractor,
    SkillExtractor,
    SkillProfile,
)
from app.nlp.preprocessing import (
    BlockType,
    LineType,
    PROTECTED_TECHNICAL_PATTERNS,
    SegmentedDocument,
    TextBlock,
    TextLine,
    is_bullet,
    normalize_line,
    normalize_text,
    segment_text,
    split_bullet,
)
from app.nlp.sections import (
    CANONICAL_SECTIONS,
    ClassifiedSection,
    SectionMap,
    classify_heading,
    classify_sections,
)
from app.nlp.taxonomy import (
    get_all_canonical_skills,
    get_all_categories,
    get_canonical_skill,
    get_skill_category,
    get_skills_by_category,
    is_valid_skill,
    load_degrees,
    load_skill_aliases,
    load_skills_taxonomy,
    resolve_degree,
)
from app.nlp.schemas import (
    CandidateProfile,
    ConfidenceLevel,
    ContactSchema,
    EducationEntry,
    ExperienceEntry,
    NLPProcessingRequest,
    PipelineMetadata,
    ProjectEntry,
    SectionSummary,
    SkillItem,
)
from app.nlp.pipeline import ResumeNLPPipeline, analyze_resume
from app.nlp.scoring import (
    ComponentScore,
    ResumeScoringEngine,
    ScoreDeduction,
    ScoreLabel,
    ScoringResult,
    ScoringWeights,
    score_resume,
)
from app.nlp.formatting import (
    DEFAULT_ANALYZER_LIMITATIONS,
    FORMATTING_ANALYZER_VERSION,
    FindingSeverity,
    FormattingAnalysisResult,
    FormattingCategory,
    FormattingFinding,
    FormattingQualityAnalyzer,
    analyze_formatting,
)

__all__ = [
    # Preprocessing (Module A)
    "normalize_text",
    "normalize_line",
    "is_bullet",
    "split_bullet",
    "PROTECTED_TECHNICAL_PATTERNS",
    "segment_text",
    "SegmentedDocument",
    "TextBlock",
    "TextLine",
    "LineType",
    "BlockType",
    # Section Classification (Module B)
    "classify_sections",
    "classify_heading",
    "ClassifiedSection",
    "SectionMap",
    "CANONICAL_SECTIONS",
    # Entity Extractors (Module C & E2)
    "BaseExtractor",
    "ContactExtractor",
    "ContactInfo",
    "SkillExtractor",
    "ExtractedSkill",
    "SkillProfile",
    # Entity Extractors (Module D)
    "EducationExtractor",
    "ExperienceExtractor",
    "ProjectExtractor",
    "CertificationsExtractor",
    "ListSections",
    # Profile Aggregation (Module F)
    "ResumeNLPPipeline",
    "analyze_resume",
    "CandidateProfile",
    "ConfidenceLevel",
    "ContactSchema",
    "EducationEntry",
    "ExperienceEntry",
    "NLPProcessingRequest",
    "PipelineMetadata",
    "ProjectEntry",
    "SectionSummary",
    "SkillItem",
    # Skill & Degree Taxonomy (Module E1)
    "load_skills_taxonomy",
    "load_skill_aliases",
    "load_degrees",
    "get_canonical_skill",
    "is_valid_skill",
    "get_skill_category",
    "get_skills_by_category",
    "get_all_canonical_skills",
    "get_all_categories",
    "resolve_degree",
    # Scoring Engine (Sprint 3 Module A)
    "ResumeScoringEngine",
    "score_resume",
    "ScoringWeights",
    "ScoringResult",
    "ComponentScore",
    "ScoreDeduction",
    "ScoreLabel",
    # Formatting Quality Analyzer (Sprint 3 Module B)
    "FormattingQualityAnalyzer",
    "analyze_formatting",
    "FormattingAnalysisResult",
    "FormattingFinding",
    "FormattingCategory",
    "FindingSeverity",
    "FORMATTING_ANALYZER_VERSION",
    "DEFAULT_ANALYZER_LIMITATIONS",
]
