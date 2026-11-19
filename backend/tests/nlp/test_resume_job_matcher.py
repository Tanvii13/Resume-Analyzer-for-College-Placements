"""
Unit Tests for Resume-Job Description Matching Engine.

Sprint 4 Module C (NLP-JobMatching).

Test suite covers:
- Perfect skill match
- Partial skill match
- No skill match (unrelated skills)
- Equivalent skills (e.g. MariaDB <=> MySQL)
- Related skills (e.g. Docker <=> Kubernetes, is_satisfied=False)
- Required vs. preferred skills weight differentiation
- Candidate with strong projects but no work experience (fresh graduate)
- Candidate with work experience but few/no projects (experienced professional)
- Missing education requirements / degree level mismatch
- Incomplete CandidateProfile (empty sections)
- Uncertain extraction (low-confidence requirements)
- Empty / sparse job requirements with reduced confidence reporting
- Different job types (Internship vs Full-Time)
- Deterministic scoring across repeated runs
- Full evidence provenance and source verification
"""

import pytest
from app.nlp.job_matching.matcher_schemas import (
    MatchCategory,
    RequirementType,
)
from app.nlp.job_matching.resume_job_matcher import (
    ResumeJobMatcher,
    calculate_text_similarity,
)
from app.nlp.job_matching.schemas import (
    EducationRequirement,
    ExperienceRequirement,
    JobParsingMetadata,
    JobSkillRequirement,
    JobType,
    ParsedJobDescription,
)
from app.nlp.schemas import (
    CandidateProfile,
    ConfidenceLevel,
    ContactSchema,
    EducationEntry,
    ExperienceEntry,
    ProjectEntry,
    SkillItem,
)


@pytest.fixture
def matcher():
    return ResumeJobMatcher()


# ============================================================================
# 1. Perfect Skill Match
# ============================================================================

def test_perfect_skill_match(matcher):
    """Candidate with all required, preferred, and soft skills achieves high score."""
    candidate = CandidateProfile(
        filename="alice_resume.pdf",
        contact=ContactSchema(full_name="Alice Smith"),
        technical_skills=[
            SkillItem(canonical_name="Python", matched_alias="python", category="Programming Languages", confidence=1.0),
            SkillItem(canonical_name="PostgreSQL", matched_alias="postgres", category="Databases", confidence=1.0),
            SkillItem(canonical_name="Docker", matched_alias="docker", category="DevOps", confidence=1.0),
        ],
        soft_skills=[
            SkillItem(canonical_name="Communication", matched_alias="communication", category="Soft Skills", confidence=1.0)
        ],
        education=[
            EducationEntry(degree="B.Tech", degree_level="bachelors", field_of_study="Computer Science", cgpa=8.8)
        ],
        projects=[
            ProjectEntry(title="E-Commerce API", technologies=["Python", "PostgreSQL", "Docker"])
        ],
    )

    job = ParsedJobDescription(
        title="Python Backend Developer",
        required_technical_skills=[
            JobSkillRequirement(canonical_name="Python", matched_alias="python", category="Programming Languages", is_required=True, confidence=1.0),
            JobSkillRequirement(canonical_name="PostgreSQL", matched_alias="postgresql", category="Databases", is_required=True, confidence=1.0),
        ],
        preferred_technical_skills=[
            JobSkillRequirement(canonical_name="Docker", matched_alias="docker", category="DevOps", is_required=False, confidence=1.0),
        ],
        soft_skills=[
            JobSkillRequirement(canonical_name="Communication", matched_alias="communication", category="Soft Skills", is_required=True, confidence=1.0)
        ],
        education=EducationRequirement(degrees=["B.Tech"], degree_levels=["bachelors"], fields_of_study=["Computer Science"]),
    )

    result = matcher.match(candidate, job)

    assert result.overall_score >= 90.0
    assert result.confidence_level == ConfidenceLevel.HIGH
    assert len(result.missing_requirements) == 0
    assert len(result.matched_requirements) >= 4
    for m in result.matched_requirements:
        assert m.is_satisfied is True
        assert m.evidence is not None


# ============================================================================
# 2. Partial Skill Match
# ============================================================================

def test_partial_skill_match(matcher):
    """Candidate possesses some required skills while missing others."""
    candidate = CandidateProfile(
        filename="bob_resume.pdf",
        technical_skills=[
            SkillItem(canonical_name="Python", matched_alias="python", category="Programming Languages", confidence=1.0),
        ],
        education=[
            EducationEntry(degree="B.Tech", degree_level="bachelors", field_of_study="Information Technology")
        ],
    )

    job = ParsedJobDescription(
        title="Full Stack Engineer",
        required_technical_skills=[
            JobSkillRequirement(canonical_name="Python", matched_alias="python", category="Programming Languages", is_required=True, confidence=1.0),
            JobSkillRequirement(canonical_name="React", matched_alias="react", category="Frontend Development", is_required=True, confidence=1.0),
        ],
    )

    result = matcher.match(candidate, job)

    assert 30.0 <= result.overall_score <= 75.0
    assert any(m.requirement_name == "Python" and m.is_satisfied for m in result.matched_requirements)
    assert any(m.requirement_name == "React" and not m.is_satisfied for m in result.missing_requirements)


# ============================================================================
# 3. No Skill Match (Unrelated Domain)
# ============================================================================

def test_no_skill_match(matcher):
    """Candidate has skills completely unrelated to the job requirement."""
    candidate = CandidateProfile(
        filename="designer_resume.pdf",
        technical_skills=[
            SkillItem(canonical_name="Figma", matched_alias="figma", category="UI/UX Design", confidence=1.0),
            SkillItem(canonical_name="Adobe Photoshop", matched_alias="photoshop", category="Design", confidence=1.0),
        ],
    )

    job = ParsedJobDescription(
        title="Systems Programmer",
        required_technical_skills=[
            JobSkillRequirement(canonical_name="Rust", matched_alias="rust", category="Programming Languages", is_required=True, confidence=1.0),
            JobSkillRequirement(canonical_name="C++", matched_alias="c++", category="Programming Languages", is_required=True, confidence=1.0),
        ],
    )

    result = matcher.match(candidate, job)

    assert result.overall_score < 40.0
    assert len(result.missing_requirements) >= 2
    assert all(m.score == 0.0 for m in result.missing_requirements)


# ============================================================================
# 4. Equivalent Skills Matching
# ============================================================================

def test_equivalent_skill_match(matcher):
    """Configured drop-in equivalent skills count as satisfied with EQUIVALENT_MATCH."""
    candidate = CandidateProfile(
        filename="db_resume.pdf",
        technical_skills=[
            SkillItem(canonical_name="MariaDB", matched_alias="mariadb", category="Databases", confidence=1.0)
        ],
    )

    job = ParsedJobDescription(
        title="Database Specialist",
        required_technical_skills=[
            JobSkillRequirement(canonical_name="MySQL", matched_alias="mysql", category="Databases", is_required=True, confidence=1.0)
        ],
    )

    result = matcher.match(candidate, job)

    equiv_match = next((m for m in result.matched_requirements if m.requirement_name == "MySQL"), None)
    assert equiv_match is not None
    assert equiv_match.category == MatchCategory.EQUIVALENT_MATCH
    assert equiv_match.score == 0.95
    assert equiv_match.is_satisfied is True
    assert "MariaDB" in equiv_match.evidence


# ============================================================================
# 5. Related but Non-Equivalent Skills
# ============================================================================

def test_related_skill_not_fully_satisfied(matcher):
    """Related ecosystem tools are classified as RELATED_MATCH and NOT fully satisfied."""
    candidate = CandidateProfile(
        filename="devops_resume.pdf",
        technical_skills=[
            SkillItem(canonical_name="Docker", matched_alias="docker", category="DevOps", confidence=1.0)
        ],
    )

    job = ParsedJobDescription(
        title="Kubernetes Administrator",
        required_technical_skills=[
            JobSkillRequirement(canonical_name="Kubernetes", matched_alias="kubernetes", category="DevOps", is_required=True, confidence=1.0)
        ],
    )

    result = matcher.match(candidate, job)

    rel_match = next((m for m in result.partially_matched_requirements if m.requirement_name == "Kubernetes"), None)
    assert rel_match is not None
    assert rel_match.category == MatchCategory.RELATED_MATCH
    assert rel_match.is_satisfied is False
    assert 0.50 <= rel_match.score <= 0.85
    assert "Docker" in rel_match.evidence


# ============================================================================
# 6. Required vs. Preferred Skill Influence
# ============================================================================

def test_required_skills_have_greater_influence(matcher):
    """Missing a required skill incurs a larger penalty than missing a preferred skill."""
    # Candidate A: Has required, missing preferred
    cand_a = CandidateProfile(
        filename="cand_a.pdf",
        technical_skills=[
            SkillItem(canonical_name="Python", matched_alias="python", category="Programming Languages", confidence=1.0),
        ],
    )

    # Candidate B: Missing required, has preferred
    cand_b = CandidateProfile(
        filename="cand_b.pdf",
        technical_skills=[
            SkillItem(canonical_name="Docker", matched_alias="docker", category="DevOps", confidence=1.0),
        ],
    )

    job = ParsedJobDescription(
        title="Backend Role",
        required_technical_skills=[
            JobSkillRequirement(canonical_name="Python", matched_alias="python", category="Programming Languages", is_required=True, confidence=1.0)
        ],
        preferred_technical_skills=[
            JobSkillRequirement(canonical_name="Docker", matched_alias="docker", category="DevOps", is_required=False, confidence=1.0)
        ],
    )

    res_a = matcher.match(cand_a, job)
    res_b = matcher.match(cand_b, job)

    assert res_a.overall_score > res_b.overall_score


# ============================================================================
# 7. Candidate with Strong Projects but No Work Experience
# ============================================================================

def test_strong_projects_fresher_credit(matcher):
    """A fresh graduate with strong technical projects receives project and partial experience credit."""
    candidate = CandidateProfile(
        filename="fresher_resume.pdf",
        technical_skills=[
            SkillItem(canonical_name="Python", matched_alias="python", category="Programming Languages", confidence=1.0),
            SkillItem(canonical_name="FastAPI", matched_alias="fastapi", category="Backend Development", confidence=1.0),
        ],
        projects=[
            ProjectEntry(title="College Placement Portal", technologies=["Python", "FastAPI"], description="Built scalable microservices"),
            ProjectEntry(title="AI Chatbot", technologies=["Python"], description="Natural language assistant"),
        ],
        experience=[],  # 0 professional work experience
    )

    job = ParsedJobDescription(
        title="Software Engineer",
        required_technical_skills=[
            JobSkillRequirement(canonical_name="Python", matched_alias="python", category="Programming Languages", is_required=True, confidence=1.0),
            JobSkillRequirement(canonical_name="FastAPI", matched_alias="fastapi", category="Backend Development", is_required=True, confidence=1.0),
        ],
        experience=ExperienceRequirement(min_years=1.0),
    )

    result = matcher.match(candidate, job)

    # Candidate should not receive zero for experience because projects substitute partially
    comp_exp = result.component_scores["relevant_experience"]
    assert comp_exp.earned_score > 0.0

    comp_proj = result.component_scores["relevant_projects"]
    assert comp_proj.percentage >= 85.0


# ============================================================================
# 8. Candidate with Experience but Few Projects
# ============================================================================

def test_experienced_candidate_few_projects(matcher):
    """An experienced professional with strong job history compensates for lack of standalone projects."""
    candidate = CandidateProfile(
        filename="senior_resume.pdf",
        technical_skills=[
            SkillItem(canonical_name="Java", matched_alias="java", category="Programming Languages", confidence=1.0),
            SkillItem(canonical_name="Spring Boot", matched_alias="springboot", category="Backend Development", confidence=1.0),
        ],
        experience=[
            ExperienceEntry(
                company_name="Enterprise Corp",
                job_title="Software Engineer",
                duration_months=36,
                technologies_used=["Java", "Spring Boot"],
            )
        ],
        projects=[],  # No personal projects
    )

    job = ParsedJobDescription(
        title="Senior Java Developer",
        required_technical_skills=[
            JobSkillRequirement(canonical_name="Java", matched_alias="java", category="Programming Languages", is_required=True, confidence=1.0),
        ],
        experience=ExperienceRequirement(min_years=2.0),
    )

    result = matcher.match(candidate, job)

    assert result.component_scores["relevant_experience"].percentage == 100.0
    # Projects dimension should not completely zero out because experience substitutes
    assert result.component_scores["relevant_projects"].earned_score >= 0.70


# ============================================================================
# 9. Missing Education Requirements
# ============================================================================

def test_missing_education_requirements(matcher):
    """Degree or degree-level mismatch is flagged as missing or partial."""
    candidate = CandidateProfile(
        filename="diploma_resume.pdf",
        education=[
            EducationEntry(degree="Diploma", degree_level="diploma", field_of_study="Mechanical")
        ],
    )

    job = ParsedJobDescription(
        title="Graduate Engineer Trainee",
        education=EducationRequirement(
            degrees=["B.Tech", "B.E."],
            degree_levels=["bachelors"],
            fields_of_study=["Computer Science"],
        ),
    )

    result = matcher.match(candidate, job)

    edu_comp = result.component_scores["education_alignment"]
    assert edu_comp.percentage < 60.0
    assert any(m.category in {MatchCategory.RELATED_MATCH, MatchCategory.MISSING} for m in result.all_matches if m.requirement_type == RequirementType.EDUCATION)


# ============================================================================
# 10. Incomplete CandidateProfile
# ============================================================================

def test_incomplete_candidate_profile(matcher):
    """Empty CandidateProfile handles all dimensions gracefully without raising exceptions."""
    empty_candidate = CandidateProfile(
        filename="empty.pdf",
        technical_skills=[],
        soft_skills=[],
        education=[],
        experience=[],
        projects=[],
    )

    job = ParsedJobDescription(
        title="Developer",
        required_technical_skills=[
            JobSkillRequirement(canonical_name="Python", matched_alias="python", category="Programming Languages", is_required=True, confidence=1.0)
        ],
    )

    result = matcher.match(empty_candidate, job)

    assert result.overall_score == 0.0
    assert result.confidence_level == ConfidenceLevel.LOW
    assert len(result.missing_requirements) >= 1


# ============================================================================
# 11. Uncertain Extraction in Job Requirements
# ============================================================================

def test_uncertain_job_requirement(matcher):
    """Job requirements with low extraction confidence are flagged as UNCERTAIN."""
    candidate = CandidateProfile(filename="cand.pdf")

    job = ParsedJobDescription(
        title="Role with Ambiguous Requirement",
        required_technical_skills=[
            JobSkillRequirement(
                canonical_name="SomeObscureSkill",
                matched_alias="obscure",
                category="General",
                is_required=True,
                confidence=0.45,  # Low confidence
            )
        ],
    )

    result = matcher.match(candidate, job)

    assert len(result.uncertain_requirements) == 1
    assert result.uncertain_requirements[0].category == MatchCategory.UNCERTAIN


# ============================================================================
# 12. Empty Job Requirements (Sparse Job Description)
# ============================================================================

def test_empty_job_requirements(matcher):
    """A job description with minimal/empty requirements reports limited confidence."""
    candidate = CandidateProfile(
        filename="cand.pdf",
        technical_skills=[
            SkillItem(canonical_name="Python", matched_alias="python", category="Programming Languages", confidence=1.0)
        ],
    )

    empty_job = ParsedJobDescription(
        title="Unspecified Role",
        metadata=JobParsingMetadata(raw_text_length=40),
    )

    result = matcher.match(candidate, empty_job)

    assert result.confidence_level == ConfidenceLevel.LOW
    assert result.confidence <= 0.50
    assert any("limited confidence" in exp.lower() for exp in result.scoring_explanations)


# ============================================================================
# 13. Internship vs. Full-Time Job Types
# ============================================================================

def test_internship_job_type_matching(matcher):
    """Internships explicitly welcoming freshers grant full experience score to freshers."""
    fresher = CandidateProfile(
        filename="fresher.pdf",
        experience=[],
        internships=[
            ExperienceEntry(company_name="Startup", job_title="Intern", duration_months=3, is_internship=True)
        ],
        projects=[ProjectEntry(title="School App", technologies=["Python"])],
    )

    internship_job = ParsedJobDescription(
        title="Summer Intern",
        job_type=JobType.INTERNSHIP,
        experience=ExperienceRequirement(is_fresher_eligible=True, min_years=0.0),
    )

    result = matcher.match(fresher, internship_job)

    assert result.component_scores["relevant_experience"].percentage == 100.0
    assert any(m.category == MatchCategory.EXACT_MATCH for m in result.matched_requirements if m.requirement_type == RequirementType.EXPERIENCE)


# ============================================================================
# 14. Deterministic Scoring
# ============================================================================

def test_deterministic_scoring(matcher):
    """Running match multiple times on identical inputs yields identical scores."""
    candidate = CandidateProfile(
        filename="repeat_resume.pdf",
        technical_skills=[
            SkillItem(canonical_name="Python", matched_alias="python", category="Programming Languages", confidence=1.0),
            SkillItem(canonical_name="Docker", matched_alias="docker", category="DevOps", confidence=1.0),
        ],
        education=[EducationEntry(degree="B.Tech", degree_level="bachelors")],
    )

    job = ParsedJobDescription(
        title="DevOps Junior",
        required_technical_skills=[
            JobSkillRequirement(canonical_name="Python", matched_alias="python", category="Programming Languages", is_required=True, confidence=1.0),
            JobSkillRequirement(canonical_name="Kubernetes", matched_alias="kubernetes", category="DevOps", is_required=True, confidence=1.0),
        ],
    )

    run1 = matcher.match(candidate, job)
    run2 = matcher.match(candidate, job)

    assert run1.overall_score == run2.overall_score
    assert run1.confidence == run2.confidence
    assert len(run1.matched_requirements) == len(run2.matched_requirements)
    assert len(run1.partially_matched_requirements) == len(run2.partially_matched_requirements)


# ============================================================================
# 15. Text Similarity Helper
# ============================================================================

def test_text_similarity_helper():
    """Text similarity computes deterministic Jaccard token overlap."""
    score1 = calculate_text_similarity("Python FastAPI backend microservices", "Python FastAPI REST microservices")
    assert score1 >= 0.50

    score2 = calculate_text_similarity("Graphic design Photoshop Illustrator", "Kubernetes Docker Terraform")
    assert score2 == 0.0

    score_empty = calculate_text_similarity("", "Python")
    assert score_empty == 0.0
