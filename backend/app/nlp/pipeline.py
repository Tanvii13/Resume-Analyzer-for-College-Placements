"""
Structured candidate profile pipeline.

Module F (NLP-10) of the Sprint 2 NLP pipeline.

Runs Modules A to E on extracted resume text and assembles one validated
`CandidateProfile`:

    raw text
      -> Module A  normalize + segment            (segment_text)
      -> Module B  classify sections              (classify_sections)
      -> Module C  contact                        (ContactExtractor)
      -> Module D  education / experience /
                   projects / certifications      (Education/Experience/Project/CertificationsExtractor)
      -> Module E  skills                         (SkillExtractor)
      -> CandidateProfile (Pydantic v2)

Each extractor runs in isolation: if one raises, its part of the profile is
left empty, the failure is recorded in `metadata.warnings` and
`metadata.module_status`, and the rest of the profile is still returned.

The pipeline has no knowledge of HTTP or the database, so the backend can call
it from a route, a background job or a test in the same way:

    from app.nlp.pipeline import ResumeNLPPipeline
    profile = ResumeNLPPipeline().process(parse_result.text, "resume.pdf")
    profile.model_dump()        # dict for the API / DB layer
    profile.model_dump_json()   # JSON string
"""

from datetime import date
import logging
import time
from typing import Any, Callable, List, Optional, TypeVar

from app.nlp.extractors.certifications import CertificationsExtractor, ListSections
from app.nlp.extractors.contact import ContactExtractor, ContactInfo
from app.nlp.extractors.education import EducationExtractor
from app.nlp.extractors.experience import ExperienceExtractor
from app.nlp.extractors.projects import ProjectExtractor
from app.nlp.extractors.skills import ExtractedSkill, SkillExtractor, SkillProfile
from app.nlp.preprocessing import SegmentedDocument, segment_text
from app.nlp.schemas import (
    CandidateProfile,
    ConfidenceLevel,
    ContactSchema,
    NLPProcessingRequest,
    PipelineMetadata,
    SectionSummary,
    SkillItem,
)
from app.nlp.sections import (
    SECTION_EDUCATION,
    SECTION_PROJECTS,
    SECTION_TECHNICAL_SKILLS,
    SectionMap,
    classify_sections,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Sections a placement resume is expected to have. Missing ones are reported
# in `section_summary.missing_critical_sections` for the feedback module.
CRITICAL_SECTIONS = [SECTION_EDUCATION, SECTION_TECHNICAL_SKILLS, SECTION_PROJECTS]


def contact_to_schema(contact: ContactInfo) -> ContactSchema:
    """Convert Module C's dataclass into the validated contract model."""
    return ContactSchema(
        full_name=contact.full_name,
        email=contact.email,
        phone=contact.phone,
        linkedin_url=contact.linkedin_url,
        github_url=contact.github_url,
        portfolio_url=contact.portfolio_url,
        coding_profiles=dict(contact.coding_profiles or {}),
        confidence=max(0.0, min(1.0, float(contact.confidence))),
    )


def skill_to_schema(skill: ExtractedSkill) -> SkillItem:
    """Convert Module E's dataclass into the validated contract model."""
    return SkillItem(
        canonical_name=skill.canonical_name,
        matched_alias=skill.matched_text,
        category=skill.category,
        confidence=max(0.0, min(1.0, float(skill.confidence))),
        source_section=skill.source_section,
        occurrences=max(1, int(skill.occurrences or 1)),
    )


class ResumeNLPPipeline:
    """
    Orchestrates Modules A to E into a CandidateProfile.

    Create one instance and reuse it: building the skill-matching patterns is
    the only costly step and happens once in __init__.
    """

    def __init__(
        self,
        enable_spacy: bool = False,
        skill_extractor: Optional[SkillExtractor] = None,
        today: Optional[date] = None,
    ):
        self.skill_extractor = skill_extractor or SkillExtractor()
        self.contact_extractor = ContactExtractor(enable_spacy=enable_spacy)
        self.education_extractor = EducationExtractor()
        self.experience_extractor = ExperienceExtractor(self.skill_extractor, today=today)
        self.project_extractor = ProjectExtractor(self.skill_extractor)
        self.list_extractor = CertificationsExtractor()

    # -- public API --------------------------------------------------------

    def process(self, text: Optional[str], filename: str, resume_id: Optional[str] = None) -> CandidateProfile:
        """
        Turn extracted resume text into a CandidateProfile.

        Never raises for bad or empty text; problems are reported in
        `profile.metadata.warnings`.
        """
        started = time.perf_counter()
        metadata = PipelineMetadata(resume_id=resume_id)
        profile = CandidateProfile(filename=filename or "resume")

        if not text or not text.strip():
            metadata.warnings.append("Resume text is empty; nothing to extract.")
            for module in ("preprocessing", "sections", "contact", "education", "experience",
                           "projects", "skills", "lists"):
                metadata.module_status[module] = "skipped"
            profile.section_summary = SectionSummary(missing_critical_sections=list(CRITICAL_SECTIONS))
            return self._finish(profile, metadata, started)

        document: Optional[SegmentedDocument] = self._run(
            "preprocessing", metadata, lambda: segment_text(text), None)
        sections: SectionMap = self._run(
            "sections", metadata,
            lambda: classify_sections(document if document is not None else text), SectionMap())

        contact = self._run("contact", metadata,
                            lambda: self.contact_extractor.extract(sections, document), None)
        if contact is not None:
            profile.contact = self._run("contact", metadata, lambda: contact_to_schema(contact), ContactSchema())

        profile.education = self._run("education", metadata,
                                      lambda: self.education_extractor.extract(sections, document), [])

        experience = self._run("experience", metadata,
                               lambda: self.experience_extractor.extract(sections, document), [])
        profile.experience = [e for e in experience if not e.is_internship]
        profile.internships = [e for e in experience if e.is_internship]

        profile.projects = self._run("projects", metadata,
                                     lambda: self.project_extractor.extract(sections, document), [])

        skills: SkillProfile = self._run("skills", metadata,
                                         lambda: self.skill_extractor.extract(sections, document), SkillProfile())
        profile.technical_skills = [skill_to_schema(s) for s in skills.technical_skills]
        profile.soft_skills = [skill_to_schema(s) for s in skills.soft_skills]
        profile.skills_by_category = {k: list(v) for k, v in (skills.skills_by_category or {}).items()}

        lists: ListSections = self._run("lists", metadata,
                                        lambda: self.list_extractor.extract(sections, document), ListSections())
        profile.certifications = lists.certifications
        profile.achievements = lists.achievements
        profile.extracurricular = lists.extracurricular

        identified = list(dict.fromkeys(s.canonical_name for s in sections.sections))
        profile.section_summary = SectionSummary(
            identified_sections=identified,
            missing_critical_sections=[s for s in CRITICAL_SECTIONS if s not in identified],
        )
        self._add_quality_warnings(profile, metadata)
        return self._finish(profile, metadata, started)

    def process_request(self, request: NLPProcessingRequest) -> CandidateProfile:
        """Process a validated NLPProcessingRequest."""
        return self.process(request.text, request.filename, resume_id=request.resume_id)

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _run(module: str, metadata: PipelineMetadata, fn: Callable[[], T], fallback: Any) -> T:
        """Run one module; on failure log it, record a warning and return `fallback`."""
        try:
            result = fn()
            metadata.module_status.setdefault(module, "ok")
            return result
        except Exception as exc:  # noqa: BLE001 - one module must not break the profile
            logger.exception("NLP module '%s' failed", module)
            metadata.module_status[module] = "failed"
            metadata.warnings.append(f"{module} extraction failed: {type(exc).__name__}: {exc}")
            return fallback

    @staticmethod
    def _add_quality_warnings(profile: CandidateProfile, metadata: PipelineMetadata) -> None:
        if not profile.contact.email:
            metadata.warnings.append("No email address found.")
        if not profile.contact.phone:
            metadata.warnings.append("No phone number found.")
        for missing in profile.section_summary.missing_critical_sections:
            metadata.warnings.append(f"Missing section: {missing}.")
        for i, edu in enumerate(profile.education):
            if edu.degree and edu.cgpa is None and edu.percentage is None and edu.degree_level != "secondary":
                metadata.warnings.append(f"Education entry {i + 1} ({edu.degree}) has no CGPA/percentage.")
        for entry in profile.experience + profile.internships:
            if entry.job_title is None or entry.company_name is None:
                metadata.warnings.append("An experience entry is missing its job title or company name.")
                break

    @staticmethod
    def _overall_confidence(profile: CandidateProfile) -> float:
        """Average confidence of everything that was extracted (0 if nothing was)."""
        scores: List[float] = []
        if any([profile.contact.full_name, profile.contact.email, profile.contact.phone]):
            scores.append(profile.contact.confidence)
        scores.extend(e.confidence for e in profile.education)
        scores.extend(e.confidence for e in profile.experience + profile.internships)
        scores.extend(p.confidence for p in profile.projects)
        if profile.technical_skills:
            scores.append(sum(s.confidence for s in profile.technical_skills) / len(profile.technical_skills))
        return round(sum(scores) / len(scores), 3) if scores else 0.0

    def _finish(self, profile: CandidateProfile, metadata: PipelineMetadata, started: float) -> CandidateProfile:
        metadata.overall_confidence = self._overall_confidence(profile)
        metadata.confidence_level = ConfidenceLevel.from_score(metadata.overall_confidence)
        metadata.processing_time_ms = round((time.perf_counter() - started) * 1000, 2)
        profile.metadata = metadata
        return profile


_default_pipeline: Optional[ResumeNLPPipeline] = None


def analyze_resume(text: Optional[str], filename: str = "resume", resume_id: Optional[str] = None) -> CandidateProfile:
    """Process text with a shared, lazily created pipeline instance."""
    global _default_pipeline
    if _default_pipeline is None:
        _default_pipeline = ResumeNLPPipeline()
    return _default_pipeline.process(text, filename, resume_id=resume_id)


__all__ = ["CRITICAL_SECTIONS", "ResumeNLPPipeline", "analyze_resume", "contact_to_schema", "skill_to_schema"]
