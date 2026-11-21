"""Deterministic, read-only Sprint 5 staff analysis builder."""

from collections.abc import Iterable
from typing import Optional

from app.nlp.analysis import Sprint3AnalysisResult
from app.nlp.job_matching import JobMatchResult, RequirementType
from app.nlp.schemas import CandidateProfile, SkillItem

from .schemas import (
    Availability,
    AvailabilityNote,
    EvidenceItem,
    ImprovementOverview,
    JobMatchingOverview,
    JobOpportunity,
    MeasurableAchievements,
    QualityDimension,
    ResumeOverview,
    ScoreOverview,
    SkillEvidence,
    SkillsOverview,
    StaffAnalysisResult,
    StaffFriendlySummary,
)


class UnsupportedSchemaVersionError(ValueError):
    """Raised before adaptation when an upstream major schema version is unknown."""


class StaffAnalysisBuilder:
    """Prepare existing Sprint 2--4 outputs for a placement officer.

    This class does not invoke parsing, scoring, or matching engines and never
    writes to its input models.
    """

    def build(
        self,
        profile: CandidateProfile,
        analysis: Optional[Sprint3AnalysisResult] = None,
        job_matches: Optional[Iterable[JobMatchResult]] = None,
    ) -> StaffAnalysisResult:
        matches = None if job_matches is None else list(job_matches)
        self._validate_versions(profile, analysis, matches)
        skills = self._skills(profile)
        return StaffAnalysisResult(
            filename=profile.filename,
            candidate_name=profile.contact.full_name,
            resume_overview=self._resume_overview(analysis),
            improvement_overview=self._improvements(analysis),
            skills_overview=skills,
            job_matching_overview=self._job_matching(matches),
            summary=self._summary(analysis, skills),
            source_versions={
                "candidate_profile": profile.pipeline_version,
                "sprint3_analysis": analysis.analyzer_version if analysis else None,
                "job_matching": (matches[0].matching_engine_version if matches else None),
            },
        )

    @staticmethod
    def _validate_major(value: str, expected: str, source: str) -> None:
        if value.split(".", 1)[0] != expected:
            raise UnsupportedSchemaVersionError(
                f"Unsupported {source} schema version {value!r}; expected major version {expected}."
            )

    def _validate_versions(self, profile, analysis, matches) -> None:
        self._validate_major(profile.pipeline_version, "2", "CandidateProfile")
        if analysis:
            self._validate_major(analysis.analyzer_version, "3", "Sprint3AnalysisResult")
        for match in matches or []:
            self._validate_major(match.matching_engine_version, "4", "JobMatchResult")

    @staticmethod
    def _unavailable(reason: str) -> AvailabilityNote:
        return AvailabilityNote(status=Availability.UNAVAILABLE, reason=reason)

    @staticmethod
    def _component(analysis, key: str, name: str) -> QualityDimension:
        if analysis is None:
            return QualityDimension(name=name, availability=StaffAnalysisBuilder._unavailable("Sprint 3 analysis was not supplied."))
        component = analysis.component_scores.get(key)
        if component is None:
            return QualityDimension(name=name, availability=StaffAnalysisBuilder._unavailable(f"The {key} scoring component is unavailable."))
        return QualityDimension(
            name=name, score=component.score, max_score=component.max_score,
            percentage=round((component.score / component.max_score) * 100, 2),
            explanation=component.reason, evidence=list(component.evidence),
            availability=AvailabilityNote(status=Availability.AVAILABLE),
        )

    def _resume_overview(self, analysis) -> ResumeOverview:
        score = (ScoreOverview(overall_score=analysis.overall_score, max_score=analysis.max_score,
                 score_label=analysis.score_label.value if analysis.score_label else None,
                 availability=AvailabilityNote(status=Availability.AVAILABLE)) if analysis and analysis.overall_score is not None
                 else ScoreOverview(availability=self._unavailable("Overall score was not produced by Sprint 3.")))
        formatting = (QualityDimension(name="Formatting quality", score=analysis.formatting_analysis.formatting_score,
                      max_score=analysis.formatting_analysis.max_score,
                      percentage=round(analysis.formatting_analysis.formatting_score / analysis.formatting_analysis.max_score * 100, 2),
                      explanation=("Formatting analysis completed with "
                                   f"{len(analysis.formatting_analysis.findings)} finding(s)."),
                      evidence=list(analysis.formatting_analysis.strengths),
                      availability=AvailabilityNote(status=Availability.AVAILABLE))
                      if analysis and analysis.formatting_analysis else QualityDimension(name="Formatting quality", availability=self._unavailable("Formatting analysis was not supplied or was skipped.")))
        return ResumeOverview(overall_score=score,
            section_completeness=self._component(analysis, "section_completeness", "Section completeness"),
            content_quality=self._component(analysis, "content_quality", "Content quality"),
            skill_visibility=self._component(analysis, "skill_visibility", "Skill visibility"),
            formatting_quality=formatting,
            strengths=list(analysis.strengths) if analysis else [])

    @staticmethod
    def _issue_item(issue) -> EvidenceItem:
        return EvidenceItem(item_id=issue.issue_id, title=issue.title, description=issue.description,
            affected_section=issue.affected_section, severity=issue.severity.value,
            priority=issue.priority.value, evidence=[issue.evidence], confidence=issue.confidence)

    def _improvements(self, analysis) -> ImprovementOverview:
        achievements = MeasurableAchievements(availability=self._unavailable("Content quality analysis was not supplied."))
        if analysis and analysis.content_quality_analysis:
            count = analysis.content_quality_analysis.aggregate_impact_metrics_count
            achievements = MeasurableAchievements(detected=count > 0, count=count, availability=AvailabilityNote(status=Availability.AVAILABLE))
        issues = analysis.improvement_areas.issues if analysis and analysis.improvement_areas else []
        critical = [self._issue_item(i) for i in issues if i.category.value == "section_completeness" and i.severity.value == "critical"]
        weak = [self._issue_item(i) for i in issues if i.category.value == "section_completeness" and i not in [x for x in issues if x.category.value == "section_completeness" and x.severity.value == "critical"]]
        content = [self._issue_item(i) for i in issues if i.category.value in ("content_quality", "skill_visibility")]
        formatting = [self._issue_item(i) for i in issues if i.category.value == "formatting"]
        if analysis and analysis.formatting_analysis:
            existing_ids = {item.item_id for item in formatting}
            formatting.extend(
                EvidenceItem(
                    item_id=finding.issue_id,
                    title=finding.title,
                    description=finding.description,
                    affected_section=finding.affected_section,
                    severity=finding.severity.value,
                    evidence=[finding.evidence],
                    confidence=finding.confidence,
                )
                for finding in analysis.formatting_analysis.findings
                if finding.issue_id not in existing_ids
            )
        recs = []
        if analysis and analysis.recommendations:
            recs = [EvidenceItem(item_id=r.recommendation_id, title=r.title, description=r.description,
                affected_section=r.affected_section, severity=r.severity, priority=r.priority.value,
                evidence=list(r.evidence), confidence=r.confidence) for r in analysis.recommendations.recommendations]
        return ImprovementOverview(critical_missing_sections=critical, weak_resume_sections=weak,
            content_issues=content, formatting_issues=formatting,
            missing_measurable_achievements=achievements, actionable_recommendations=recs)

    @staticmethod
    def _skill_evidence(skill: SkillItem, profile: CandidateProfile) -> SkillEvidence:
        needle = skill.canonical_name.casefold()
        evidence = []
        for project in profile.projects:
            if any(needle == t.casefold() for t in project.technologies):
                evidence.append(f"Project: {project.title or 'untitled project'}")
        for entry in [*profile.experience, *profile.internships]:
            if any(needle == t.casefold() for t in entry.technologies_used):
                evidence.append(f"Experience: {entry.job_title or entry.company_name or 'untitled entry'}")
        return SkillEvidence(name=skill.canonical_name, category=skill.category,
            extraction_confidence=skill.confidence, source_section=skill.source_section,
            supported=bool(evidence), evidence=evidence)

    def _skills(self, profile: CandidateProfile) -> SkillsOverview:
        technical = [self._skill_evidence(s, profile) for s in profile.technical_skills]
        soft = [self._skill_evidence(s, profile) for s in profile.soft_skills]
        all_skills = [*technical, *soft]
        return SkillsOverview(technical_skills=technical, soft_skills=soft,
            supported_skills=[s for s in all_skills if s.supported],
            insufficiently_supported_skills=[s for s in all_skills if not s.supported])

    @staticmethod
    def _match_item(requirement) -> EvidenceItem:
        return EvidenceItem(item_id=requirement.requirement_name, title=requirement.requirement_name,
            description=requirement.rationale, severity=None, priority=None,
            evidence=[requirement.evidence] if requirement.evidence else [], confidence=requirement.confidence)

    def _job_matching(self, matches) -> JobMatchingOverview:
        if matches is None:
            return JobMatchingOverview(availability=self._unavailable("No Sprint 4 job matching results were supplied."))
        opportunities = []
        for match in sorted(matches, key=lambda m: (-m.overall_score, m.job_title or "", m.job_id or "")):
            missing_required = [self._match_item(r) for r in match.missing_requirements if r.requirement_type == RequirementType.REQUIRED_TECHNICAL_SKILL]
            qualification = [self._match_item(r) for r in match.missing_requirements if r.requirement_type not in (RequirementType.REQUIRED_TECHNICAL_SKILL, RequirementType.PREFERRED_TECHNICAL_SKILL, RequirementType.SOFT_SKILL)]
            opportunities.append(JobOpportunity(job_id=match.job_id, job_title=match.job_title,
                matching_score=match.overall_score, matching_skills=[self._match_item(r) for r in match.matched_requirements],
                missing_required_skills=missing_required, qualification_gaps=qualification,
                explanations=list(match.scoring_explanations)))
        return JobMatchingOverview(availability=AvailabilityNote(status=Availability.AVAILABLE), best_matching_opportunities=opportunities)

    @staticmethod
    def _summary(analysis, skills: SkillsOverview) -> StaffFriendlySummary:
        doing_well = list(analysis.strengths) if analysis else []
        needs = []
        priorities = []
        if analysis and analysis.improvement_areas:
            needs = [i.title for i in analysis.improvement_areas.issues]
        if analysis and analysis.recommendations:
            priorities = [r.suggested_action for r in analysis.recommendations.recommendations if r.priority.value == "high"]
        demonstrated = [s.name for s in skills.supported_skills]
        insufficient = [s.name for s in skills.insufficiently_supported_skills]
        clauses = []
        if doing_well: clauses.append("Strengths: " + "; ".join(doing_well[:3]) + ".")
        if needs: clauses.append("Needs attention: " + "; ".join(needs[:3]) + ".")
        if demonstrated: clauses.append("Demonstrated skills: " + ", ".join(demonstrated[:5]) + ".")
        if insufficient: clauses.append("Skills needing evidence: " + ", ".join(insufficient[:5]) + ".")
        if not clauses: clauses.append("No Sprint 3 analysis or supported skill evidence was supplied.")
        return StaffFriendlySummary(doing_well=doing_well, needs_improvement=needs,
            demonstrated_skills=demonstrated, skills_requiring_evidence=insufficient,
            next_priorities=priorities, narrative=" ".join(clauses))


def build_staff_analysis(profile: CandidateProfile, analysis: Optional[Sprint3AnalysisResult] = None,
                         job_matches: Optional[Iterable[JobMatchResult]] = None) -> StaffAnalysisResult:
    """Build a staff-facing analysis without changing or reprocessing upstream outputs."""
    return StaffAnalysisBuilder().build(profile, analysis, job_matches)
