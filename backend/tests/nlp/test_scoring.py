"""
Comprehensive test suite for Sprint 3 Module A: Resume Scoring Engine.

Validates:
1. Complete candidate profiles.
2. Profiles with missing critical sections.
3. Profiles with limited / vague project descriptions.
4. Profiles with strong project descriptions (action verbs, metrics, tech stack).
5. Profiles with no experience (fresher accommodation).
6. Profiles with no internships.
7. Profiles with different skill distributions (single vs multiple categories).
8. Empty profiles (handled gracefully without throwing).
9. Low-confidence extraction and warning diagnostics.
10. Score boundaries (clamped strictly within 0-100).
11. Deterministic scoring (identical inputs produce identical scores).
12. Exclusion of personal attributes (candidate name, gender, college, email domain, phone).
"""

import copy
import pytest
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
from app.nlp.scoring import (
    COMPONENT_CONTENT_QUALITY,
    COMPONENT_FORMATTING_READABILITY,
    COMPONENT_SECTION_COMPLETENESS,
    COMPONENT_SKILL_VISIBILITY,
    ResumeScoringEngine,
    ScoreLabel,
    ScoringWeights,
    score_resume,
)


@pytest.fixture
def high_quality_candidate_profile() -> CandidateProfile:
    """Fixture providing a well-rounded, complete candidate profile."""
    return CandidateProfile(
        filename="john_doe_resume.pdf",
        contact=ContactSchema(
            full_name="John Doe",
            email="john.doe@example.com",
            phone="+91 9876543210",
            linkedin_url="https://linkedin.com/in/johndoe",
            github_url="https://github.com/johndoe",
            coding_profiles={"leetcode": "https://leetcode.com/johndoe"},
            confidence=0.95,
        ),
        education=[
            EducationEntry(
                institution="National Institute of Technology",
                degree="Bachelor of Technology",
                degree_level="bachelors",
                field_of_study="Computer Science and Engineering",
                graduation_year=2025,
                cgpa=8.95,
                cgpa_scale=10.0,
                confidence=0.92,
            )
        ],
        experience=[
            ExperienceEntry(
                company_name="Tech Solutions Inc.",
                job_title="Software Engineering Intern",
                is_internship=True,
                start_date="2024-05",
                end_date="2024-07",
                responsibilities=[
                    "Engineered real-time telemetry ingestion microservice using FastAPI and Apache Kafka, handling 15,000 events/sec.",
                    "Optimized PostgreSQL query indices and caching strategies, reducing latency by 42%.",
                    "Automated CI/CD deployment pipelines using Docker and GitHub Actions.",
                ],
                technologies_used=["Python", "FastAPI", "PostgreSQL", "Kafka", "Docker"],
                confidence=0.90,
            )
        ],
        internships=[],
        projects=[
            ProjectEntry(
                title="Distributed File Storage Platform",
                description="Designed and deployed a fault-tolerant distributed object store replicating AWS S3 semantics.",
                technologies=["Go", "gRPC", "Docker", "Raft", "Redis"],
                github_url="https://github.com/johndoe/distributed-storage",
                highlights=[
                    "Architected Raft consensus algorithm across 5 nodes achieving 99.9% uptime during network partitions.",
                    "Benchmarked system throughput exceeding 8,500 operations per second with sub-25ms response latency.",
                    "Implemented custom chunk hashing and deduplication algorithm saving 35% disk storage.",
                ],
                confidence=0.93,
            ),
            ProjectEntry(
                title="E-Commerce Performance Optimizer",
                description="Built full-stack analytics engine tracking checkout abandonment.",
                technologies=["React", "TypeScript", "Python", "PostgreSQL"],
                highlights=[
                    "Developed interactive checkout funnel dashboard serving 10,000 active sessions.",
                    "Refactored legacy REST endpoints into batch queries, improving page load speed by 2.4x.",
                ],
                confidence=0.90,
            ),
        ],
        technical_skills=[
            SkillItem(canonical_name="Python", matched_alias="python", category="languages", occurrences=4),
            SkillItem(canonical_name="Go", matched_alias="golang", category="languages", occurrences=3),
            SkillItem(canonical_name="FastAPI", matched_alias="fastapi", category="frameworks_and_libraries", occurrences=2),
            SkillItem(canonical_name="React", matched_alias="react", category="frameworks_and_libraries", occurrences=2),
            SkillItem(canonical_name="PostgreSQL", matched_alias="postgresql", category="databases", occurrences=3),
            SkillItem(canonical_name="Redis", matched_alias="redis", category="databases", occurrences=2),
            SkillItem(canonical_name="Docker", matched_alias="docker", category="cloud_and_devops", occurrences=3),
            SkillItem(canonical_name="Git", matched_alias="git", category="tools_and_platforms", occurrences=2),
        ],
        soft_skills=[
            SkillItem(canonical_name="Problem Solving", matched_alias="problem solving", category="soft_skills", occurrences=2),
            SkillItem(canonical_name="Team Collaboration", matched_alias="team collaboration", category="soft_skills", occurrences=1),
            SkillItem(canonical_name="Communication", matched_alias="communication", category="soft_skills", occurrences=1),
        ],
        skills_by_category={
            "languages": ["Python", "Go"],
            "frameworks_and_libraries": ["FastAPI", "React"],
            "databases": ["PostgreSQL", "Redis"],
            "cloud_and_devops": ["Docker"],
            "tools_and_platforms": ["Git"],
        },
        certifications=["AWS Certified Solutions Architect - Associate"],
        achievements=["Ranked top 1% in Global Coding Challenge out of 45,000 participants"],
        section_summary=SectionSummary(
            identified_sections=["contact", "education", "technical_skills", "experience", "projects", "certifications"],
            missing_critical_sections=[],
        ),
        metadata=PipelineMetadata(
            processing_time_ms=85.0,
            overall_confidence=0.92,
            confidence_level=ConfidenceLevel.HIGH,
            warnings=[],
        ),
    )


# =============================================================================
# 1. Complete Candidate Profiles Test
# =============================================================================
def test_complete_profile_scoring(high_quality_candidate_profile):
    """A comprehensive, high-quality profile should score in the Excellent tier (>= 85.0)."""
    engine = ResumeScoringEngine()
    result = engine.evaluate(high_quality_candidate_profile)

    assert result.overall_score >= 85.0
    assert result.score_label == ScoreLabel.EXCELLENT
    assert len(result.strengths) >= 4
    assert result.component_scores[COMPONENT_SECTION_COMPLETENESS].score >= 22.0
    assert result.component_scores[COMPONENT_CONTENT_QUALITY].score >= 26.0
    assert result.component_scores[COMPONENT_SKILL_VISIBILITY].score >= 22.0
    assert result.component_scores[COMPONENT_FORMATTING_READABILITY].score >= 16.0


# =============================================================================
# 2. Missing Critical Sections Test
# =============================================================================
def test_missing_critical_sections_scoring(high_quality_candidate_profile):
    """Removing projects and technical skills should trigger deductions and lower score."""
    profile = copy.deepcopy(high_quality_candidate_profile)
    profile.projects = []
    profile.technical_skills = []
    profile.skills_by_category = {}
    profile.section_summary.identified_sections = ["contact", "education"]
    profile.section_summary.missing_critical_sections = ["projects", "technical_skills"]

    engine = ResumeScoringEngine()
    result = engine.evaluate(profile)

    assert result.overall_score < 65.0
    # Deductions should explicitly flag missing sections
    deduction_rules = [d.rule_id for d in result.deductions]
    assert "SEC_MISSING_PROJECTS" in deduction_rules
    assert "SEC_MISSING_SKILLS" in deduction_rules or "SKILL_NONE_DETECTED" in deduction_rules


# =============================================================================
# 3. Limited / Vague Project Descriptions Test
# =============================================================================
def test_limited_project_descriptions(high_quality_candidate_profile):
    """Vague bullets without action verbs or metrics should score poorly on content quality."""
    profile = copy.deepcopy(high_quality_candidate_profile)
    profile.projects = [
        ProjectEntry(
            title="Online Store",
            description="worked on an e-commerce website for books",
            technologies=[],
            highlights=[
                "Responsible for bug fixing and helping with UI.",
                "Participated in team discussions and handled tasks.",
            ],
        )
    ]
    profile.experience = []

    engine = ResumeScoringEngine()
    result = engine.evaluate(profile)

    content_score = result.component_scores[COMPONENT_CONTENT_QUALITY]
    assert content_score.score < (content_score.max_score * 0.50)

    deduction_rules = [d.rule_id for d in result.deductions]
    assert any("WEAK" in r or "VAGUE" in r or "ACTION_VERBS" in r or "METRICS" in r for r in deduction_rules)


# =============================================================================
# 4. Strong Project Descriptions Test
# =============================================================================
def test_strong_project_descriptions(high_quality_candidate_profile):
    """Action verbs, quantifiable numbers, and deep tech stack should earn high content marks."""
    engine = ResumeScoringEngine()
    result = engine.evaluate(high_quality_candidate_profile)

    content_score = result.component_scores[COMPONENT_CONTENT_QUALITY]
    assert content_score.score >= (content_score.max_score * 0.85)

    # Check evidence contains metrics and action verbs
    ev_text = " ".join(content_score.evidence).lower()
    assert "action verbs" in ev_text
    assert "quantified" in ev_text or "metrics" in ev_text


# =============================================================================
# 5. Profiles with No Experience (Fresher Accommodation)
# =============================================================================
def test_no_experience_fresher_accommodation(high_quality_candidate_profile):
    """
    College placement candidates lacking industry experience should receive
    full practical work credit if they have 2+ detailed technical projects.
    """
    fresher = copy.deepcopy(high_quality_candidate_profile)
    fresher.experience = []
    fresher.internships = []
    # Ensure candidate has 2 solid projects
    assert len(fresher.projects) >= 2

    engine = ResumeScoringEngine()
    result = fresher_result = engine.evaluate(fresher)

    # Section completeness should still score highly due to fresher accommodation
    sec_score = fresher_result.component_scores[COMPONENT_SECTION_COMPLETENESS]
    assert sec_score.score >= 23.0  # Out of 25.0

    # No punitive deduction for missing industry experience
    deduction_rules = [d.rule_id for d in fresher_result.deductions]
    assert "SEC_NO_PRACTICAL_EXPERIENCE" not in deduction_rules
    assert any("fresher accommodation" in ev.lower() for ev in sec_score.evidence)


# =============================================================================
# 6. Profiles with No Internships
# =============================================================================
def test_no_internships_scoring(high_quality_candidate_profile):
    """Having zero internships should not penalize candidate when projects/experience exist."""
    profile = copy.deepcopy(high_quality_candidate_profile)
    profile.internships = []

    engine = ResumeScoringEngine()
    result = engine.evaluate(profile)

    assert result.overall_score >= 80.0
    deduction_rules = [d.rule_id for d in result.deductions]
    assert not any("internship" in r.lower() for r in deduction_rules)


# =============================================================================
# 7. Profiles with Different Skill Distributions
# =============================================================================
def test_skill_distribution_diversity(high_quality_candidate_profile):
    """Single category skills should be penalized compared to multi-domain skills."""
    engine = ResumeScoringEngine()

    # Multi-domain profile (Languages, Frameworks, Databases, Cloud)
    multi_res = engine.evaluate(high_quality_candidate_profile)
    multi_skill_score = multi_res.component_scores[COMPONENT_SKILL_VISIBILITY].score

    # Monolithic single-category profile (Only 3 Python libraries)
    single_cat_profile = copy.deepcopy(high_quality_candidate_profile)
    single_cat_profile.technical_skills = [
        SkillItem(canonical_name="NumPy", matched_alias="numpy", category="ai_ml_data_science", occurrences=1),
        SkillItem(canonical_name="Pandas", matched_alias="pandas", category="ai_ml_data_science", occurrences=1),
        SkillItem(canonical_name="SciPy", matched_alias="scipy", category="ai_ml_data_science", occurrences=1),
    ]
    single_cat_profile.skills_by_category = {
        "ai_ml_data_science": ["NumPy", "Pandas", "SciPy"],
    }
    single_cat_profile.soft_skills = []

    single_res = engine.evaluate(single_cat_profile)
    single_skill_score = single_res.component_scores[COMPONENT_SKILL_VISIBILITY].score

    assert single_skill_score < (multi_skill_score * 0.60)
    single_deductions = [d.rule_id for d in single_res.deductions]
    assert "SKILL_POOR_DIVERSITY" in single_deductions or "SKILL_LIMITED_INVENTORY" in single_deductions


# =============================================================================
# 8. Empty Candidate Profile Test
# =============================================================================
def test_empty_candidate_profile():
    """An empty profile should be handled gracefully without raising exceptions."""
    empty_profile = CandidateProfile(filename="empty_resume.pdf")

    engine = ResumeScoringEngine()
    result = engine.evaluate(empty_profile)

    assert isinstance(result.overall_score, float)
    assert 0.0 <= result.overall_score <= 100.0
    assert result.score_label == ScoreLabel.NEEDS_IMPROVEMENT
    assert len(result.deductions) > 0

    # Ensure all components exist and are non-negative
    for comp_name in (
        COMPONENT_SECTION_COMPLETENESS,
        COMPONENT_CONTENT_QUALITY,
        COMPONENT_SKILL_VISIBILITY,
        COMPONENT_FORMATTING_READABILITY,
    ):
        assert comp_name in result.component_scores
        cs = result.component_scores[comp_name]
        assert 0.0 <= cs.score <= cs.max_score


# =============================================================================
# 9. Low-Confidence Extraction Handling
# =============================================================================
def test_low_confidence_extraction(high_quality_candidate_profile):
    """Low extraction confidence and parser warnings should register formatting deductions."""
    profile = copy.deepcopy(high_quality_candidate_profile)
    profile.metadata = PipelineMetadata(
        processing_time_ms=120.0,
        overall_confidence=0.45,
        confidence_level=ConfidenceLevel.LOW,
        warnings=["Unusual two-column layout detected", "Low OCR text clarity"],
    )

    engine = ResumeScoringEngine()
    result = engine.evaluate(profile)

    fmt_score = result.component_scores[COMPONENT_FORMATTING_READABILITY]
    deduction_rules = [d.rule_id for d in result.deductions]

    assert "FMT_LOW_ATS_CONFIDENCE" in deduction_rules
    assert "FMT_EXTRACTION_WARNINGS" in deduction_rules
    assert fmt_score.score < 14.0


# =============================================================================
# 10. Score Boundaries & Clamping Test
# =============================================================================
def test_score_boundaries(high_quality_candidate_profile):
    """Overall score and all component scores must be strictly clamped within valid boundaries."""
    engine = ResumeScoringEngine()
    result = engine.evaluate(high_quality_candidate_profile)

    assert 0.0 <= result.overall_score <= 100.0
    assert result.max_score == 100.0

    for comp in result.component_scores.values():
        assert 0.0 <= comp.score <= comp.max_score
        assert comp.weight == comp.max_score


# =============================================================================
# 11. Deterministic Scoring Test
# =============================================================================
def test_deterministic_scoring(high_quality_candidate_profile):
    """Repeated evaluations of the exact same profile must yield identical outputs."""
    engine = ResumeScoringEngine()

    result1 = engine.evaluate(high_quality_candidate_profile)
    result2 = engine.evaluate(high_quality_candidate_profile)
    result3 = score_resume(high_quality_candidate_profile)

    assert result1.overall_score == result2.overall_score == result3.overall_score
    assert result1.score_label == result2.score_label == result3.score_label
    assert len(result1.deductions) == len(result2.deductions)

    for i in range(len(result1.deductions)):
        assert result1.deductions[i].rule_id == result2.deductions[i].rule_id
        assert result1.deductions[i].points_deducted == result2.deductions[i].points_deducted


# =============================================================================
# 12. Exclusion of Personal Attributes (Fairness & Bias Check)
# =============================================================================
def test_exclusion_of_personal_attributes(high_quality_candidate_profile):
    """
    Changing candidate name, gender pronouns, college identity, email domain,
    or phone number MUST NOT alter any scores or deductions.
    """
    profile_a = copy.deepcopy(high_quality_candidate_profile)
    profile_a.contact.full_name = "Alice Smith"
    profile_a.contact.email = "alice.smith@stanford.edu"
    profile_a.contact.phone = "+1 650 123 4567"
    profile_a.education[0].institution = "Stanford University"

    profile_b = copy.deepcopy(high_quality_candidate_profile)
    profile_b.contact.full_name = "Rajesh Kumar"
    profile_b.contact.email = "rajesh.kumar@ruralcollege.ac.in"
    profile_b.contact.phone = "+91 9988776655"
    profile_b.education[0].institution = "Government Engineering College, Bilaspur"

    engine = ResumeScoringEngine()
    result_a = engine.evaluate(profile_a)
    result_b = engine.evaluate(profile_b)

    assert result_a.overall_score == result_b.overall_score
    assert result_a.score_label == result_b.score_label

    for comp_key in result_a.component_scores:
        score_a = result_a.component_scores[comp_key].score
        score_b = result_b.component_scores[comp_key].score
        assert score_a == score_b, f"Score mismatch in component {comp_key}"

    # Ensure deduction count and rule IDs match identically
    ded_a = [d.rule_id for d in result_a.deductions]
    ded_b = [d.rule_id for d in result_b.deductions]
    assert ded_a == ded_b


# =============================================================================
# 13. Configurable Weights Test
# =============================================================================
def test_configurable_weights(high_quality_candidate_profile):
    """Test engine with custom weights configuration."""
    custom_weights = ScoringWeights(
        section_completeness=20.0,
        content_quality=40.0,
        skill_visibility=20.0,
        formatting_readability=20.0,
        job_alignment=0.0,
    )
    assert custom_weights.total_weight == 100.0

    engine = ResumeScoringEngine(weights=custom_weights)
    result = engine.evaluate(high_quality_candidate_profile)

    assert result.component_scores[COMPONENT_CONTENT_QUALITY].max_score == 40.0
    assert result.component_scores[COMPONENT_SECTION_COMPLETENESS].max_score == 20.0
    assert 0.0 <= result.overall_score <= 100.0


# =============================================================================
# 14. Real Pipeline Integration on Fixture Resumes
# =============================================================================
def test_pipeline_fixture_resumes_scoring():
    """Score all synthetic golden fixture resumes processed by ResumeNLPPipeline."""
    from pathlib import Path
    from app.nlp.pipeline import ResumeNLPPipeline

    fixtures_dir = Path(__file__).parent / "fixtures" / "resumes"
    resume_files = sorted(fixtures_dir.glob("*.txt"))
    assert len(resume_files) >= 6

    pipeline = ResumeNLPPipeline()
    engine = ResumeScoringEngine()

    for path in resume_files:
        text = path.read_text(encoding="utf-8")
        profile = pipeline.process(text, path.name)
        result = engine.evaluate(profile)

        assert isinstance(result.overall_score, float)
        assert 0.0 <= result.overall_score <= 100.0
        assert result.score_label in (
            ScoreLabel.EXCELLENT,
            ScoreLabel.GOOD,
            ScoreLabel.FAIR,
            ScoreLabel.NEEDS_IMPROVEMENT,
        )
        assert len(result.component_scores) == 4
        # Validate that model dumps to clean JSON
        dumped = result.model_dump()
        assert dumped["overall_score"] == result.overall_score

