"""
Comprehensive test suite for Sprint 3 Module D: Resume Improvement Areas Detection Engine.

Tests all required scenarios:
1. Missing critical sections (flagged with high priority / critical severity).
2. Present but incomplete sections (missing CGPA, graduation year, contact details).
3. Present sections not incorrectly flagged as missing (accuracy safeguard).
4. Low-confidence extraction and parsing uncertainty diagnostics.
5. Weak project descriptions (passive verbs, no metrics).
6. Formatting problems integration (walls of text, mixed bullets).
7. Duplicate findings deduplication across modules.
8. Profiles with no experience (fresher accommodation verified).
9. Profiles with no projects.
10. Complete resumes (0 high-priority blockers, prominent strong areas).
11. Deterministic improvement detection.
"""

import copy
import pytest
from app.nlp.content import ContentQualityReport, EntryQualityEvaluation, analyze_content_quality
from app.nlp.formatting import FindingSeverity as FmtSeverity, FormattingAnalysisResult, FormattingCategory as FmtCat, FormattingFinding
from app.nlp.improvement import (
    IMPROVEMENT_ENGINE_VERSION,
    ImprovementAreasDetector,
    ImprovementCategory,
    ImprovementIssue,
    ImprovementPriority,
    ImprovementSeverity,
    deduplicate_and_rank_issues,
    detect_improvement_areas,
)
from app.nlp.schemas import (
    CandidateProfile,
    ConfidenceLevel,
    ContactSchema,
    EducationEntry,
    ExperienceEntry,
    PipelineMetadata,
    ProjectEntry,
    SectionSummary,
    SkillItem,
)
from app.nlp.scoring import score_resume


@pytest.fixture
def base_complete_profile() -> CandidateProfile:
    """Fixture providing a complete, placement-ready profile."""
    return CandidateProfile(
        filename="priya_sharma.pdf",
        contact=ContactSchema(
            full_name="Priya Sharma",
            email="priya.sharma@example.com",
            phone="+91 9876543210",
            linkedin_url="https://linkedin.com/in/priyasharma",
            github_url="https://github.com/priyasharma",
            confidence=0.95,
        ),
        education=[
            EducationEntry(
                institution="Indian Institute of Technology Bombay",
                degree="Bachelor of Technology",
                field_of_study="Computer Science and Engineering",
                graduation_year=2025,
                cgpa=8.95,
                cgpa_scale=10.0,
                confidence=0.95,
            )
        ],
        experience=[
            ExperienceEntry(
                company_name="TechCorp Solutions",
                job_title="Software Engineering Intern",
                is_internship=True,
                responsibilities=[
                    "Engineered real-time telemetry ingestion microservice using FastAPI, handling 15,000 events/sec.",
                    "Optimized PostgreSQL queries, cutting latency by 42%.",
                ],
                technologies_used=["Python", "FastAPI", "PostgreSQL", "Docker"],
            )
        ],
        projects=[
            ProjectEntry(
                title="Distributed Key-Value Store",
                description="Designed and deployed a fault-tolerant distributed object store.",
                technologies=["Go", "Raft", "gRPC", "Docker"],
                highlights=[
                    "Architected Raft consensus algorithm across 5 nodes achieving 99.9% uptime.",
                    "Benchmarked system throughput exceeding 10,500 operations per second with sub-25ms latency.",
                ],
            ),
            ProjectEntry(
                title="Placement Preparation Platform",
                description="Built an analytics engine serving campus students.",
                technologies=["React", "TypeScript", "Python"],
                highlights=[
                    "Developed interactive interview dashboard serving 2,500 active university students.",
                ],
            ),
        ],
        technical_skills=[
            SkillItem(canonical_name="Python", matched_alias="python", category="languages"),
            SkillItem(canonical_name="Go", matched_alias="golang", category="languages"),
            SkillItem(canonical_name="FastAPI", matched_alias="fastapi", category="frameworks_and_libraries"),
            SkillItem(canonical_name="React", matched_alias="react", category="frameworks_and_libraries"),
            SkillItem(canonical_name="PostgreSQL", matched_alias="postgresql", category="databases"),
            SkillItem(canonical_name="Redis", matched_alias="redis", category="databases"),
            SkillItem(canonical_name="Docker", matched_alias="docker", category="cloud_and_devops"),
            SkillItem(canonical_name="Git", matched_alias="git", category="tools_and_platforms"),
        ],
        soft_skills=[
            SkillItem(canonical_name="Problem Solving", matched_alias="problem solving", category="soft_skills"),
            SkillItem(canonical_name="Team Collaboration", matched_alias="team collaboration", category="soft_skills"),
        ],
        skills_by_category={
            "languages": ["Python", "Go"],
            "frameworks_and_libraries": ["FastAPI", "React"],
            "databases": ["PostgreSQL", "Redis"],
            "cloud_and_devops": ["Docker"],
            "tools_and_platforms": ["Git"],
        },
        section_summary=SectionSummary(
            identified_sections=["contact", "education", "technical_skills", "experience", "projects"],
            missing_critical_sections=[],
        ),
        metadata=PipelineMetadata(
            overall_confidence=0.92,
            confidence_level=ConfidenceLevel.HIGH,
            warnings=[],
        ),
    )


# =============================================================================
# 1. Missing Critical Sections Test
# =============================================================================
def test_missing_critical_sections(base_complete_profile):
    """Missing critical sections must be flagged with HIGH priority and CRITICAL severity."""
    profile = copy.deepcopy(base_complete_profile)
    profile.projects = []
    profile.technical_skills = []
    profile.section_summary.missing_critical_sections = ["projects", "technical_skills"]
    profile.section_summary.identified_sections = ["contact", "education"]

    detector = ImprovementAreasDetector()
    report = detector.detect(profile)

    issue_ids = [i.issue_id for i in report.issues]
    assert "IMP_MISSING_PROJECTS" in issue_ids
    assert "IMP_MISSING_SKILLS" in issue_ids

    proj_issue = next(i for i in report.issues if i.issue_id == "IMP_MISSING_PROJECTS")
    assert proj_issue.priority == ImprovementPriority.HIGH
    assert proj_issue.severity == ImprovementSeverity.CRITICAL
    assert proj_issue.category == ImprovementCategory.SECTION_COMPLETENESS


# =============================================================================
# 2. Present but Incomplete Sections Test
# =============================================================================
def test_present_but_incomplete_sections(base_complete_profile):
    """Missing CGPA, graduation year, or phone must be flagged as high priority."""
    profile = copy.deepcopy(base_complete_profile)
    profile.education[0].cgpa = None
    profile.education[0].percentage = None
    profile.education[0].graduation_year = None
    profile.contact.phone = None

    detector = ImprovementAreasDetector()
    report = detector.detect(profile)

    issue_ids = [i.issue_id for i in report.issues]
    assert "IMP_EDU_MISSING_CGPA" in issue_ids
    assert "IMP_EDU_MISSING_YEAR" in issue_ids
    assert "IMP_CONTACT_MISSING_PHONE" in issue_ids

    cgpa_issue = next(i for i in report.issues if i.issue_id == "IMP_EDU_MISSING_CGPA")
    assert cgpa_issue.priority == ImprovementPriority.HIGH


# =============================================================================
# 3. Present Section Not Flagged as Missing (Accuracy Safeguard)
# =============================================================================
def test_present_section_not_flagged_as_missing(base_complete_profile):
    """Sections that exist in the profile MUST NOT be flagged as missing."""
    detector = ImprovementAreasDetector()
    report = detector.detect(base_complete_profile)

    issue_ids = [i.issue_id for i in report.issues]
    assert "IMP_MISSING_EDUCATION" not in issue_ids
    assert "IMP_MISSING_PROJECTS" not in issue_ids
    assert "IMP_MISSING_SKILLS" not in issue_ids


# =============================================================================
# 4. Low-Confidence Extraction & Parsing Uncertainty
# =============================================================================
def test_low_confidence_extraction(base_complete_profile):
    """Low pipeline confidence must generate an extraction uncertainty diagnostic."""
    profile = copy.deepcopy(base_complete_profile)
    profile.metadata = PipelineMetadata(
        overall_confidence=0.48,
        confidence_level=ConfidenceLevel.LOW,
        warnings=["Non-standard two-column layout detected", "Possible truncated line headers"],
    )

    detector = ImprovementAreasDetector()
    report = detector.detect(profile)

    issue_ids = [i.issue_id for i in report.issues]
    assert "IMP_EXTRACTION_UNCERTAINTY" in issue_ids

    uncertainty_issue = next(i for i in report.issues if i.issue_id == "IMP_EXTRACTION_UNCERTAINTY")
    assert uncertainty_issue.priority == ImprovementPriority.HIGH
    assert "low confidence" in uncertainty_issue.description.lower()


# =============================================================================
# 5. Weak Project Descriptions Test
# =============================================================================
def test_weak_project_descriptions(base_complete_profile):
    """Superficial, passive descriptions should trigger content quality issues."""
    profile = copy.deepcopy(base_complete_profile)
    profile.projects = [
        ProjectEntry(
            title="Book Store App",
            description="worked on a web application for ordering books",
            technologies=[],
            highlights=["Responsible for bug fixing and helping with UI."],
        )
    ]

    detector = ImprovementAreasDetector()
    report = detector.detect(profile)

    issue_ids = [i.issue_id for i in report.issues]
    assert "IMP_WEAK_PROJECT_DESCRIPTION" in issue_ids or "IMP_PASSIVE_PHRASING" in issue_ids
    assert report.high_priority_issues >= 1


# =============================================================================
# 6. Formatting Problems Integration Test
# =============================================================================
def test_formatting_problems_integration(base_complete_profile):
    """Formatting defects from Module B must be integrated and prioritized."""
    formatting_result = FormattingAnalysisResult(
        formatting_score=68.0,
        max_score=100.0,
        findings=[
            FormattingFinding(
                issue_id="FMT_UNSEGMENTED_WALL_OF_TEXT",
                category=FmtCat.TEXT_READABILITY,
                title="Unsegmented Wall of Text",
                description="Dense block with 160 continuous words.",
                severity=FmtSeverity.CRITICAL,
                confidence=0.95,
                evidence="Paragraph with 160 words",
                detection_rule="check_unsegmented_blocks",
            ),
            FormattingFinding(
                issue_id="FMT_INCONSISTENT_BULLET_MARKERS",
                category=FmtCat.BULLET_STRUCTURE,
                title="Inconsistent Bullet Markers",
                description="Mixed bullet marker symbols.",
                severity=FmtSeverity.WARNING,
                confidence=0.95,
                evidence="Mixed: •, -",
                detection_rule="check_bullets",
            ),
        ],
        strengths=[],
        limitations=[],
    )

    detector = ImprovementAreasDetector()
    report = detector.detect(base_complete_profile, formatting_result=formatting_result)

    issue_ids = [i.issue_id for i in report.issues]
    assert "IMP_UNSTRUCTURED_WALL_OF_TEXT" in issue_ids
    assert "IMP_INCONSISTENT_BULLET_FORMATTING" in issue_ids

    wall_issue = next(i for i in report.issues if i.issue_id == "IMP_UNSTRUCTURED_WALL_OF_TEXT")
    assert wall_issue.priority == ImprovementPriority.HIGH
    assert wall_issue.severity == ImprovementSeverity.CRITICAL


# =============================================================================
# 7. Deduplication of Findings Test
# =============================================================================
def test_deduplication_of_findings():
    """Duplicate/overlapping findings must be merged into a single canonical issue."""
    issues = [
        ImprovementIssue(
            issue_id="SEC_MISSING_PROJECTS",
            category=ImprovementCategory.SECTION_COMPLETENESS,
            title="Missing Projects Section",
            description="Projects section is missing from the resume.",
            severity=ImprovementSeverity.CRITICAL,
            priority=ImprovementPriority.HIGH,
            affected_section="projects",
            evidence="CandidateProfile has 0 projects.",
            related_score_component="section_completeness",
            confidence=0.95,
            detection_rule="rule_a",
        ),
        ImprovementIssue(
            issue_id="FMT_MISSING_SECTION_HEADING_PROJECTS",
            category=ImprovementCategory.FORMATTING,
            title="Projects Heading Missing",
            description="Could not find a project heading.",
            severity=ImprovementSeverity.WARNING,
            priority=ImprovementPriority.MEDIUM,
            affected_section="projects",
            evidence="identified_sections missing projects.",
            related_score_component="formatting",
            confidence=0.90,
            detection_rule="rule_b",
        ),
    ]

    deduped = deduplicate_and_rank_issues(issues)
    # Should collapse into exactly 1 issue
    assert len(deduped) == 1
    merged = deduped[0]
    assert merged.issue_id == "IMP_MISSING_PROJECTS"
    assert merged.priority == ImprovementPriority.HIGH
    assert merged.severity == ImprovementSeverity.CRITICAL
    assert "0 projects" in merged.evidence


# =============================================================================
# 8. Profiles with No Experience (Fresher Accommodation)
# =============================================================================
def test_profiles_with_no_experience_fresher_accommodation(base_complete_profile):
    """
    College placement candidates lacking experience who have 2+ projects
    MUST NOT be flagged with a high-priority missing experience blocker.
    """
    fresher = copy.deepcopy(base_complete_profile)
    fresher.experience = []
    fresher.internships = []
    assert len(fresher.projects) >= 2

    detector = ImprovementAreasDetector()
    report = detector.detect(fresher)

    issue_ids = [i.issue_id for i in report.issues]
    # Should not flag a critical missing practical work issue
    assert "IMP_MISSING_PRACTICAL_WORK" not in issue_ids

    # Strong areas should acknowledge the project portfolio
    assert any("project portfolio" in s.lower() for s in report.strong_areas)


# =============================================================================
# 9. Profiles with No Projects Test
# =============================================================================
def test_profiles_with_no_projects(base_complete_profile):
    """Profile with zero projects must trigger high-priority blocker."""
    profile = copy.deepcopy(base_complete_profile)
    profile.projects = []
    profile.section_summary.missing_critical_sections = ["projects"]

    report = detect_improvement_areas(profile)
    issue_ids = [i.issue_id for i in report.issues]
    assert "IMP_MISSING_PROJECTS" in issue_ids
    assert report.high_priority_issues >= 1


# =============================================================================
# 10. Complete Resumes Test
# =============================================================================
def test_complete_resumes(base_complete_profile):
    """Complete, high-scoring resumes should have 0 high-priority blockers."""
    report = detect_improvement_areas(base_complete_profile)

    assert report.high_priority_issues == 0
    assert len(report.strong_areas) >= 3
    assert "outstanding placement-ready state" in report.summary.lower() or "solid" in report.summary.lower()


# =============================================================================
# 11. Deterministic Improvement Detection Test
# =============================================================================
def test_deterministic_improvement_detection(base_complete_profile):
    """Repeated evaluations of the exact same profile must produce identical reports."""
    r1 = detect_improvement_areas(base_complete_profile)
    r2 = detect_improvement_areas(base_complete_profile)

    assert r1.total_issues == r2.total_issues
    assert r1.high_priority_issues == r2.high_priority_issues
    assert r1.medium_priority_issues == r2.medium_priority_issues
    assert r1.strong_areas == r2.strong_areas

    for i in range(len(r1.issues)):
        assert r1.issues[i].issue_id == r2.issues[i].issue_id
        assert r1.issues[i].priority == r2.issues[i].priority
        assert r1.issues[i].evidence == r2.issues[i].evidence
