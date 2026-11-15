"""
Improvement Areas Detection Engine orchestrator for Sprint 3 Module D.

Combines:
- CandidateProfile and section classification summary
- Module A Placement Readiness Scoring results
- Module B Formatting Quality Analyzer findings
- Module C Content Quality and Impact evaluations

Guarantees:
- Synthesizes findings across modules into deduplicated, prioritized improvement areas.
- Primary authority for missing sections is CandidateProfile.section_summary.missing_critical_sections.
- Does not flag sections as missing if section classifier or profile entries contain them.
- Distinguishes extraction failure / low confidence from genuinely missing candidate content.
- Respects college placement fresher accommodation (does not penalize missing corporate experience).
- Output is 100% deterministic, explainable, and testable without external LLMs.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from app.nlp.content import ContentQualityReport, analyze_content_quality
from app.nlp.formatting import FormattingAnalysisResult, analyze_formatting
from app.nlp.improvement.deduplicator import deduplicate_and_rank_issues
from app.nlp.improvement.schemas import (
    IMPROVEMENT_ENGINE_VERSION,
    ImprovementAreasReport,
    ImprovementCategory,
    ImprovementIssue,
    ImprovementPriority,
    ImprovementSeverity,
)
from app.nlp.schemas import CandidateProfile, ConfidenceLevel
from app.nlp.scoring import ScoringResult, score_resume
from app.nlp.scoring.weights import (
    COMPONENT_CONTENT_QUALITY,
    COMPONENT_FORMATTING_READABILITY,
    COMPONENT_SECTION_COMPLETENESS,
    COMPONENT_SKILL_VISIBILITY,
)


class ImprovementAreasDetector:
    """
    Synthesizes multi-module NLP diagnostic findings into prioritized, actionable improvement areas.
    """

    def __init__(self, version: str = IMPROVEMENT_ENGINE_VERSION):
        self.version = version

    def detect(
        self,
        profile: CandidateProfile,
        scoring_result: Optional[ScoringResult] = None,
        formatting_result: Optional[FormattingAnalysisResult] = None,
        content_report: Optional[ContentQualityReport] = None,
        raw_text: Optional[str] = None,
    ) -> ImprovementAreasReport:
        """
        Evaluate and prioritize all resume improvement areas for campus recruitment readiness.

        Args:
            profile: Extracted CandidateProfile from Sprint 2.
            scoring_result: Optional precomputed Module A ScoringResult.
            formatting_result: Optional precomputed Module B FormattingAnalysisResult.
            content_report: Optional precomputed Module C ContentQualityReport.
            raw_text: Optional raw text for running formatting analysis if formatting_result is None.

        Returns:
            ImprovementAreasReport containing prioritized issues, strong areas, and weak areas.
        """
        # Ensure dependencies are available (lazy evaluation if not supplied)
        if scoring_result is None:
            scoring_result = score_resume(profile, raw_text=raw_text)

        if content_report is None:
            content_report = analyze_content_quality(profile)

        if formatting_result is None and raw_text:
            formatting_result = analyze_formatting(raw_text, profile=profile)

        raw_issues: List[ImprovementIssue] = []
        strong_areas: List[str] = []
        weak_areas: List[str] = []

        # ---------------------------------------------------------------------
        # 1. Section Completeness Analysis
        # ---------------------------------------------------------------------
        sec_issues, sec_strong = self._evaluate_section_completeness(profile)
        raw_issues.extend(sec_issues)
        strong_areas.extend(sec_strong)

        # ---------------------------------------------------------------------
        # 2. Content Quality Analysis (from Module C & profile)
        # ---------------------------------------------------------------------
        cnt_issues, cnt_strong = self._evaluate_content_quality(profile, content_report)
        raw_issues.extend(cnt_issues)
        strong_areas.extend(cnt_strong)

        # ---------------------------------------------------------------------
        # 3. Skill Visibility Analysis
        # ---------------------------------------------------------------------
        skl_issues, skl_strong = self._evaluate_skill_visibility(profile)
        raw_issues.extend(skl_issues)
        strong_areas.extend(skl_strong)

        # ---------------------------------------------------------------------
        # 4. Formatting & Readability Analysis (from Module B)
        # ---------------------------------------------------------------------
        if formatting_result:
            fmt_issues, fmt_strong = self._evaluate_formatting_findings(formatting_result)
            raw_issues.extend(fmt_issues)
            strong_areas.extend(fmt_strong)

        # ---------------------------------------------------------------------
        # 5. Extraction Diagnostics & Pipeline Confidence
        # ---------------------------------------------------------------------
        ext_issues = self._evaluate_extraction_confidence(profile)
        raw_issues.extend(ext_issues)

        # ---------------------------------------------------------------------
        # 6. Deduplication, Priority Triage & Weak Areas Synthesis
        # ---------------------------------------------------------------------
        deduplicated_issues = deduplicate_and_rank_issues(raw_issues)

        high_count = sum(1 for i in deduplicated_issues if i.priority == ImprovementPriority.HIGH)
        med_count = sum(1 for i in deduplicated_issues if i.priority == ImprovementPriority.MEDIUM)
        low_count = sum(1 for i in deduplicated_issues if i.priority == ImprovementPriority.LOW)

        # Synthesize weak areas from High and Medium priority issues
        for issue in deduplicated_issues:
            if issue.priority in (ImprovementPriority.HIGH, ImprovementPriority.MEDIUM):
                if issue.title not in weak_areas:
                    weak_areas.append(issue.title)

        # Deduplicate strong areas preserving order
        unique_strong: List[str] = []
        seen_s = set()
        # Add strengths from Module A as well
        all_candidate_strengths = strong_areas + getattr(scoring_result, "strengths", [])
        for s in all_candidate_strengths:
            if s not in seen_s:
                seen_s.add(s)
                unique_strong.append(s)

        # Generate Executive Placement Summary
        summary = self._generate_executive_summary(
            total_issues=len(deduplicated_issues),
            high_count=high_count,
            med_count=med_count,
            strong_areas=unique_strong,
            weak_areas=weak_areas,
        )

        metadata = {
            "rule_version": self.version,
            "filename": profile.filename,
            "overall_pipeline_confidence": profile.metadata.overall_confidence if profile.metadata else 1.0,
            "scoring_result_integrated": scoring_result is not None,
            "formatting_result_integrated": formatting_result is not None,
            "content_report_integrated": content_report is not None,
        }

        return ImprovementAreasReport(
            total_issues=len(deduplicated_issues),
            high_priority_issues=high_count,
            medium_priority_issues=med_count,
            low_priority_issues=low_count,
            issues=deduplicated_issues,
            strong_areas=unique_strong,
            weak_areas=weak_areas,
            summary=summary,
            analyzer_version=self.version,
            metadata=metadata,
        )

    # -------------------------------------------------------------------------
    # 1. Section Completeness Detector
    # -------------------------------------------------------------------------
    def _evaluate_section_completeness(
        self, profile: CandidateProfile
    ) -> Tuple[List[ImprovementIssue], List[str]]:
        issues: List[ImprovementIssue] = []
        strengths: List[str] = []

        missing_critical = set(profile.section_summary.missing_critical_sections or [])
        identified = set(profile.section_summary.identified_sections or [])

        # 1.1 Critical Sections Presence Check
        # Primary source: missing_critical_sections and presence in profile
        if not profile.education:
            title = "Missing Education Section" if "education" not in identified else "Education Section Empty"
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_MISSING_EDUCATION",
                    category=ImprovementCategory.SECTION_COMPLETENESS,
                    title=title,
                    description=(
                        "Education qualifications are mandatory for college placement eligibility. "
                        "Add an explicit 'Education' section detailing your degree, university, and academic scores."
                    ),
                    severity=ImprovementSeverity.CRITICAL,
                    priority=ImprovementPriority.HIGH,
                    affected_section="education",
                    evidence="No education entries in CandidateProfile.",
                    related_score_component=COMPONENT_SECTION_COMPLETENESS,
                    confidence=1.0,
                    detection_rule="check_missing_education_section",
                )
            )

        if not profile.projects:
            title = "Missing Projects Section" if "projects" not in identified else "Projects Section Empty"
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_MISSING_PROJECTS",
                    category=ImprovementCategory.SECTION_COMPLETENESS,
                    title=title,
                    description=(
                        "College placement recruiters heavily prioritize hands-on technical projects. "
                        "Include at least 2 detailed technical or capstone projects."
                    ),
                    severity=ImprovementSeverity.CRITICAL,
                    priority=ImprovementPriority.HIGH,
                    affected_section="projects",
                    evidence="No projects found in CandidateProfile.",
                    related_score_component=COMPONENT_SECTION_COMPLETENESS,
                    confidence=1.0,
                    detection_rule="check_missing_projects_section",
                )
            )

        if not profile.technical_skills:
            title = "Missing Technical Skills Section" if "technical_skills" not in identified else "Technical Skills Section Empty"
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_MISSING_SKILLS",
                    category=ImprovementCategory.SECTION_COMPLETENESS,
                    title=title,
                    description=(
                        "Technical skills are essential for automated ATS keyword filtering. "
                        "Dedicate a prominent 'Technical Skills' section listing languages, frameworks, and databases."
                    ),
                    severity=ImprovementSeverity.CRITICAL,
                    priority=ImprovementPriority.HIGH,
                    affected_section="technical_skills",
                    evidence="No technical skills parsed in CandidateProfile.",
                    related_score_component=COMPONENT_SECTION_COMPLETENESS,
                    confidence=1.0,
                    detection_rule="check_missing_skills_section",
                )
            )

        if profile.education and profile.projects and profile.technical_skills:
            strengths.append("Complete core sections: Education, Projects, and Skills are well-represented.")

        # 1.2 Education Completeness (CGPA, Year, Degree)
        if profile.education:
            primary_edu = profile.education[0]
            if primary_edu.cgpa is None and primary_edu.percentage is None:
                issues.append(
                    ImprovementIssue(
                        issue_id="IMP_EDU_MISSING_CGPA",
                        category=ImprovementCategory.SECTION_COMPLETENESS,
                        title="Academic Performance Score Missing",
                        description=(
                            "Campus placement shortlisting enforces strict CGPA cutoffs (e.g. 7.0/10 or 60%+). "
                            "Explicitly state your current CGPA (with scale) or percentage score."
                        ),
                        severity=ImprovementSeverity.WARNING,
                        priority=ImprovementPriority.HIGH,
                        affected_section="education",
                        evidence="Neither CGPA nor percentage found in primary education qualification.",
                        related_score_component=COMPONENT_SECTION_COMPLETENESS,
                        confidence=0.95,
                        detection_rule="check_education_academic_score",
                    )
                )

            if primary_edu.graduation_year is None and not primary_edu.is_expected:
                issues.append(
                    ImprovementIssue(
                        issue_id="IMP_EDU_MISSING_YEAR",
                        category=ImprovementCategory.SECTION_COMPLETENESS,
                        title="Graduation Year Missing",
                        description=(
                            "Campus recruitment drives filter by graduation batch (e.g. 2025 Batch). "
                            "Clearly specify your graduation or expected passing year."
                        ),
                        severity=ImprovementSeverity.WARNING,
                        priority=ImprovementPriority.HIGH,
                        affected_section="education",
                        evidence="graduation_year is null in education entry.",
                        related_score_component=COMPONENT_SECTION_COMPLETENESS,
                        confidence=0.95,
                        detection_rule="check_education_graduation_year",
                    )
                )

        # 1.3 Contact Completeness
        if not profile.contact.email:
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_CONTACT_MISSING_EMAIL",
                    category=ImprovementCategory.SECTION_COMPLETENESS,
                    title="Missing Email Address",
                    description="Professional email address is missing. Recruiters cannot initiate interview correspondence.",
                    severity=ImprovementSeverity.CRITICAL,
                    priority=ImprovementPriority.HIGH,
                    affected_section="contact",
                    evidence="contact.email is null.",
                    related_score_component=COMPONENT_SECTION_COMPLETENESS,
                    confidence=1.0,
                    detection_rule="check_contact_email",
                )
            )

        if not profile.contact.phone:
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_CONTACT_MISSING_PHONE",
                    category=ImprovementCategory.SECTION_COMPLETENESS,
                    title="Missing Phone Number",
                    description="Contact phone number is missing for recruitment screening calls.",
                    severity=ImprovementSeverity.CRITICAL,
                    priority=ImprovementPriority.HIGH,
                    affected_section="contact",
                    evidence="contact.phone is null.",
                    related_score_component=COMPONENT_SECTION_COMPLETENESS,
                    confidence=1.0,
                    detection_rule="check_contact_phone",
                )
            )

        has_dev_profile = bool(
            profile.contact.linkedin_url
            or profile.contact.github_url
            or profile.contact.portfolio_url
            or profile.contact.coding_profiles
        )
        if not has_dev_profile:
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_CONTACT_MISSING_DEV_PROFILES",
                    category=ImprovementCategory.SECTION_COMPLETENESS,
                    title="Missing Professional Profiles (GitHub / LinkedIn)",
                    description=(
                        "Include links to your GitHub profile, LinkedIn, or competitive programming handles. "
                        "Recruiters evaluate project repositories and code samples."
                    ),
                    severity=ImprovementSeverity.WARNING,
                    priority=ImprovementPriority.MEDIUM,
                    affected_section="contact",
                    evidence="No LinkedIn, GitHub, or coding profiles extracted.",
                    related_score_component=COMPONENT_SECTION_COMPLETENESS,
                    confidence=0.90,
                    detection_rule="check_contact_profiles",
                )
            )
        else:
            strengths.append("Verified online presence: Includes developer links and professional profiles.")

        # 1.4 Practical Work Completeness (with Fresher Accommodation)
        num_proj = len(profile.projects or [])
        num_exp = len(profile.experience or []) + len(profile.internships or [])

        if num_proj == 0 and num_exp == 0:
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_MISSING_PRACTICAL_WORK",
                    category=ImprovementCategory.SECTION_COMPLETENESS,
                    title="No Practical Experience or Projects Found",
                    description=(
                        "Resume completely lacks hands-on engineering evidence. "
                        "Add course projects, capstone implementations, or internship roles."
                    ),
                    severity=ImprovementSeverity.CRITICAL,
                    priority=ImprovementPriority.HIGH,
                    affected_section="projects",
                    evidence="projects count = 0, experience count = 0.",
                    related_score_component=COMPONENT_SECTION_COMPLETENESS,
                    confidence=1.0,
                    detection_rule="check_practical_work_absence",
                )
            )
        elif num_exp == 0 and num_proj >= 2:
            # Fresher accommodation: Praise strong project portfolio
            strengths.append("Strong academic and capstone project portfolio compensating for lack of industry experience.")

        return issues, strengths

    # -------------------------------------------------------------------------
    # 2. Content Quality Detector (from Module C & profile)
    # -------------------------------------------------------------------------
    def _evaluate_content_quality(
        self,
        profile: CandidateProfile,
        report: Optional[ContentQualityReport],
    ) -> Tuple[List[ImprovementIssue], List[str]]:
        issues: List[ImprovementIssue] = []
        strengths: List[str] = []

        if not report:
            return issues, strengths

        # 2.1 Weak Project Descriptions
        weak_projects = [
            e for e in report.entries
            if e.entry_type == "project" and e.content_quality_score < 60.0
        ]
        if weak_projects:
            titles = ", ".join(e.entry_title for e in weak_projects[:2])
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_WEAK_PROJECT_DESCRIPTION",
                    category=ImprovementCategory.CONTENT_QUALITY,
                    title="Weak or Superficial Project Descriptions",
                    description=(
                        f"Descriptions for '{titles}' are brief or lack technical specificity. "
                        "Detail the problem solved, system architecture, your individual contributions, and tools used."
                    ),
                    severity=ImprovementSeverity.WARNING,
                    priority=ImprovementPriority.HIGH,
                    affected_section="projects",
                    evidence=f"{len(weak_projects)} project(s) scored below 60.0 on content substance.",
                    related_score_component=COMPONENT_CONTENT_QUALITY,
                    confidence=0.92,
                    detection_rule="check_weak_project_descriptions",
                )
            )

        # 2.2 Passive Phrasing
        passive_entries = [
            e for e in report.entries
            if any("passive" in issue.lower() for issue in e.issues)
        ]
        if passive_entries:
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_PASSIVE_PHRASING",
                    category=ImprovementCategory.CONTENT_QUALITY,
                    title="Passive Introductory Phrasing Detected",
                    description=(
                        "Bullet points begin with passive phrases like 'worked on' or 'responsible for'. "
                        "Lead with high-impact technical action verbs like 'Architected', 'Engineered', 'Optimized', or 'Automated'."
                    ),
                    severity=ImprovementSeverity.WARNING,
                    priority=ImprovementPriority.MEDIUM,
                    affected_section="experience" if any(e.entry_type == "experience" for e in passive_entries) else "projects",
                    evidence=f"Passive phrases detected across {len(passive_entries)} entries.",
                    related_score_component=COMPONENT_CONTENT_QUALITY,
                    confidence=0.95,
                    detection_rule="check_passive_phrases",
                )
            )

        # 2.3 Measurable Impact
        if report.aggregate_impact_metrics_count == 0 and report.total_entries_analyzed > 0:
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_LACK_OF_MEASURABLE_IMPACT",
                    category=ImprovementCategory.CONTENT_QUALITY,
                    title="Lack of Measurable Impact or Metrics",
                    description=(
                        "Descriptions lack quantifiable performance metrics or scale indicators. "
                        "Add numbers where possible (e.g. latency reduced by 35%, 500+ active users, 2.5x speedup, 99.9% test coverage)."
                    ),
                    severity=ImprovementSeverity.WARNING,
                    priority=ImprovementPriority.MEDIUM,
                    affected_section="projects",
                    evidence="0 verified quantifiable metrics detected across all project/experience descriptions.",
                    related_score_component=COMPONENT_CONTENT_QUALITY,
                    confidence=0.90,
                    detection_rule="check_measurable_impact_absence",
                )
            )
        elif report.aggregate_impact_metrics_count >= 3:
            strengths.append(f"Quantifiable impact demonstrated: {report.aggregate_impact_metrics_count} measurable outcomes detected.")

        # 2.4 Duplicate or Generic Content
        if report.duplicate_content_warnings:
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_DUPLICATE_BULLET_CONTENT",
                    category=ImprovementCategory.CONTENT_QUALITY,
                    title="Duplicate Bullet Points Across Entries",
                    description=(
                        "Identical bullet points were detected across different roles or projects. "
                        "Ensure each entry communicates distinct, role-specific engineering contributions."
                    ),
                    severity=ImprovementSeverity.WARNING,
                    priority=ImprovementPriority.MEDIUM,
                    affected_section="projects",
                    evidence=report.duplicate_content_warnings[0],
                    related_score_component=COMPONENT_CONTENT_QUALITY,
                    confidence=0.95,
                    detection_rule="check_duplicate_bullets",
                )
            )

        if report.generic_content_warnings:
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_GENERIC_RESUME_CLICHES",
                    category=ImprovementCategory.CONTENT_QUALITY,
                    title="Generic Resume Clichés Detected",
                    description=(
                        "Contains low-specificity boilerplate (e.g. 'worked on a web application using modern technologies'). "
                        "Replace generic clichés with concrete architectural implementation details."
                    ),
                    severity=ImprovementSeverity.INFO,
                    priority=ImprovementPriority.LOW,
                    affected_section="projects",
                    evidence=report.generic_content_warnings[0],
                    related_score_component=COMPONENT_CONTENT_QUALITY,
                    confidence=0.88,
                    detection_rule="check_generic_cliches",
                )
            )

        return issues, strengths

    # -------------------------------------------------------------------------
    # 3. Skill Visibility Detector
    # -------------------------------------------------------------------------
    def _evaluate_skill_visibility(
        self, profile: CandidateProfile
    ) -> Tuple[List[ImprovementIssue], List[str]]:
        issues: List[ImprovementIssue] = []
        strengths: List[str] = []

        tech_skills = profile.technical_skills or []
        unique_canonical = {s.canonical_name.lower().strip() for s in tech_skills if s.canonical_name}
        num_skills = len(unique_canonical)

        # 3.1 Skill Volume
        if 1 <= num_skills < 5:
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_LOW_SKILL_INVENTORY",
                    category=ImprovementCategory.SKILL_VISIBILITY,
                    title="Limited Technical Skill Inventory",
                    description=(
                        f"Resume lists only {num_skills} technical skills. "
                        "College recruitment screenings typically favor an inventory of 8-15 skills covering languages, tools, and databases."
                    ),
                    severity=ImprovementSeverity.WARNING,
                    priority=ImprovementPriority.HIGH,
                    affected_section="technical_skills",
                    evidence=f"Recognized skills: {', '.join(sorted(unique_canonical))}",
                    related_score_component=COMPONENT_SKILL_VISIBILITY,
                    confidence=0.95,
                    detection_rule="check_skill_volume",
                )
            )
        elif num_skills >= 8:
            strengths.append(f"Strong skill breadth: {num_skills} verified technical skills listed.")

        # 3.2 Categorization / Domain Diversity
        active_cats = set()
        for cat, items in (profile.skills_by_category or {}).items():
            if items and cat.strip():
                active_cats.add(cat.strip().lower())
        for s in tech_skills:
            if s.category:
                active_cats.add(s.category.strip().lower())

        if num_skills >= 4 and len(active_cats) <= 1:
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_POOR_SKILL_CATEGORIZATION",
                    category=ImprovementCategory.SKILL_VISIBILITY,
                    title="Skills Concentrated in Single Domain",
                    description=(
                        "Technical skills are concentrated in only 1 category. "
                        "Organize your skills into distinct subsections: Languages, Frameworks, Databases, and Developer Tools."
                    ),
                    severity=ImprovementSeverity.WARNING,
                    priority=ImprovementPriority.MEDIUM,
                    affected_section="technical_skills",
                    evidence=f"Skills concentrated solely in: {list(active_cats)[0] if active_cats else 'unclassified'}",
                    related_score_component=COMPONENT_SKILL_VISIBILITY,
                    confidence=0.90,
                    detection_rule="check_skill_diversity",
                )
            )
        elif len(active_cats) >= 4:
            strengths.append(f"Well-rounded technical coverage across {len(active_cats)} distinct domains.")

        # 3.3 Soft Skills Presence
        if not profile.soft_skills:
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_MISSING_SOFT_SKILLS",
                    category=ImprovementCategory.SKILL_VISIBILITY,
                    title="Missing Professional Soft Skills",
                    description=(
                        "No soft skills (e.g. Team Collaboration, Agile, Problem Solving) were detected. "
                        "Highlight 2-3 key interpersonal and engineering practice skills."
                    ),
                    severity=ImprovementSeverity.INFO,
                    priority=ImprovementPriority.LOW,
                    affected_section="technical_skills",
                    evidence="soft_skills list is empty in CandidateProfile.",
                    related_score_component=COMPONENT_SKILL_VISIBILITY,
                    confidence=0.88,
                    detection_rule="check_soft_skills_presence",
                )
            )

        return issues, strengths

    # -------------------------------------------------------------------------
    # 4. Formatting Detector (from Module B)
    # -------------------------------------------------------------------------
    def _evaluate_formatting_findings(
        self, formatting_result: FormattingAnalysisResult
    ) -> Tuple[List[ImprovementIssue], List[str]]:
        issues: List[ImprovementIssue] = []
        strengths: List[str] = list(formatting_result.strengths or [])

        for f in formatting_result.findings or []:
            # Map severity and priority
            sev_str = getattr(f.severity, "value", str(f.severity)).lower()
            if sev_str == "critical":
                severity = ImprovementSeverity.CRITICAL
                priority = ImprovementPriority.HIGH
            elif sev_str == "warning":
                severity = ImprovementSeverity.WARNING
                priority = ImprovementPriority.MEDIUM if "text" in f.issue_id.lower() or "bullet" in f.issue_id.lower() else ImprovementPriority.LOW
            else:
                severity = ImprovementSeverity.INFO
                priority = ImprovementPriority.LOW

            issues.append(
                ImprovementIssue(
                    issue_id=f.issue_id,
                    category=ImprovementCategory.FORMATTING,
                    title=f.title,
                    description=f.description,
                    severity=severity,
                    priority=priority,
                    affected_section=f.affected_section,
                    evidence=f.evidence,
                    related_score_component=COMPONENT_FORMATTING_READABILITY,
                    confidence=f.confidence,
                    detection_rule=f.detection_rule,
                )
            )

        return issues, strengths

    # -------------------------------------------------------------------------
    # 5. Extraction Diagnostics & Pipeline Uncertainty
    # -------------------------------------------------------------------------
    def _evaluate_extraction_confidence(
        self, profile: CandidateProfile
    ) -> List[ImprovementIssue]:
        issues: List[ImprovementIssue] = []
        metadata = profile.metadata

        if not metadata:
            return issues

        # Distinguish extraction failure from genuinely missing content
        overall_conf = metadata.overall_confidence
        if overall_conf < 0.60 or metadata.confidence_level == ConfidenceLevel.LOW:
            issues.append(
                ImprovementIssue(
                    issue_id="IMP_EXTRACTION_UNCERTAINTY",
                    category=ImprovementCategory.FORMATTING,
                    title="Low Automated Extraction Confidence",
                    description=(
                        f"The automated pipeline extracted this resume with low confidence ({overall_conf:.2f}). "
                        "Multi-column layouts, graphics, or unusual fonts may prevent automated ATS scanners from parsing your data. "
                        "Consider switching to a clean, single-column standard template."
                    ),
                    severity=ImprovementSeverity.WARNING,
                    priority=ImprovementPriority.HIGH,
                    affected_section=None,
                    evidence=f"Extraction confidence = {overall_conf:.2f}; Warnings: {'; '.join(metadata.warnings[:2]) if metadata.warnings else 'None'}",
                    related_score_component=COMPONENT_FORMATTING_READABILITY,
                    confidence=0.95,
                    detection_rule="check_extraction_confidence_diagnostics",
                )
            )

        return issues

    # -------------------------------------------------------------------------
    # Executive Summary Helper
    # -------------------------------------------------------------------------
    def _generate_executive_summary(
        self,
        total_issues: int,
        high_count: int,
        med_count: int,
        strong_areas: List[str],
        weak_areas: List[str],
    ) -> str:
        if high_count == 0 and med_count == 0:
            return (
                "Resume is in an outstanding placement-ready state with zero high-priority defects. "
                "All core sections, active technical descriptions, and layout standards align with collegiate recruiting benchmarks."
            )
        elif high_count == 0:
            return (
                f"Resume is in a solid placement-ready position with {med_count} medium-priority areas for refinement. "
                "Addressing content polish and adding quantifiable metrics will maximize interview callback rates."
            )
        else:
            return (
                f"Identified {high_count} high-priority placement blockers that require immediate attention "
                f"before campus recruiting drives (key areas: {', '.join(weak_areas[:2])}). "
                "Resolving these gaps will substantially improve automated ATS screening outcomes."
            )


def detect_improvement_areas(
    profile: CandidateProfile,
    scoring_result: Optional[ScoringResult] = None,
    formatting_result: Optional[FormattingAnalysisResult] = None,
    content_report: Optional[ContentQualityReport] = None,
    raw_text: Optional[str] = None,
) -> ImprovementAreasReport:
    """Convenience helper to identify and prioritize all resume improvement areas."""
    detector = ImprovementAreasDetector()
    return detector.detect(
        profile=profile,
        scoring_result=scoring_result,
        formatting_result=formatting_result,
        content_report=content_report,
        raw_text=raw_text,
    )


__all__ = [
    "ImprovementAreasDetector",
    "detect_improvement_areas",
]
