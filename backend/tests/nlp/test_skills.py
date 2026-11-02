"""
Tests for Sprint 2 - Module E2: Symbol-Safe Skill Extraction Engine (NLP-05).

Validates:
- Symbol-safe boundaries (C++, C#, .NET, Node.js, CI/CD)
- Context-aware disambiguation for ambiguous tokens (C, Go, R)
- Prevention of false positives (digital != Git, Vitamin C != C, go to != Go)
- Longest match first (PostgreSQL != SQL, Objective-C != C)
- Alias normalization (k8s -> Kubernetes, reactjs -> React, postgres -> PostgreSQL)
- Section-aware confidence weighting (technical_skills > projects > education)
- Duplicate elimination and occurrence tracking across sections
- Separation of technical vs soft skills
- Handling empty sections and unknown skills
"""

import pytest

from app.nlp.extractors.skills import ExtractedSkill, SkillExtractor, SkillProfile
from app.nlp.sections import (
    SECTION_ACHIEVEMENTS,
    SECTION_CERTIFICATIONS,
    SECTION_EDUCATION,
    SECTION_EXPERIENCE,
    SECTION_PERSONAL_INFO,
    SECTION_PROJECTS,
    SECTION_SOFT_SKILLS,
    SECTION_TECHNICAL_SKILLS,
    ClassifiedSection,
    SectionMap,
)


@pytest.fixture(scope="session")
def extractor() -> SkillExtractor:
    """Fixture providing a session-scoped instance of SkillExtractor."""
    return SkillExtractor()


# =============================================================================
# 1. SPECIAL PROGRAMMING LANGUAGE TESTS: C, C++, C#, Objective-C
# =============================================================================

class TestCProgrammingDisambiguation:
    """Tests verifying C programming language disambiguation vs letters and symbols."""

    def test_c_extracted_in_technical_skills(self, extractor):
        """C in a technical skills list should be extracted as C."""
        text = "Languages: C, C++, Java, Python"
        skills = extractor.extract_from_text(text, section_name=SECTION_TECHNICAL_SKILLS)
        names = {s.canonical_name for s in skills}
        assert "C" in names
        assert "C++" in names
        assert "Java" in names
        assert "Python" in names

    def test_c_slash_cpp_both_extracted(self, extractor):
        """C/C++ should extract both C and C++ as distinct skills."""
        text = "Proficient in C/C++ and Linux"
        skills = extractor.extract_from_text(text, section_name=SECTION_TECHNICAL_SKILLS)
        names = {s.canonical_name for s in skills}
        assert "C" in names
        assert "C++" in names
        assert "Linux" in names

    def test_c_with_embedded_programming_context(self, extractor):
        """In projects, C with programming indicators should be extracted."""
        text = "Developed embedded firmware in C using FreeRTOS on ARM microcontroller."
        skills = extractor.extract_from_text(text, section_name=SECTION_PROJECTS)
        names = {s.canonical_name for s in skills}
        assert "C" in names

    def test_cpp_alone_does_not_extract_c(self, extractor):
        """When only C++ is present, C must NOT be extracted."""
        text = "Backend services implemented using modern C++17."
        skills = extractor.extract_from_text(text, section_name=SECTION_PROJECTS)
        names = {s.canonical_name for s in skills}
        assert "C++" in names
        assert "C" not in names

    def test_csharp_alone_does_not_extract_c(self, extractor):
        """When only C# is present, C must NOT be extracted."""
        text = "Developed desktop applications in C# and .NET Core."
        skills = extractor.extract_from_text(text, section_name=SECTION_PROJECTS)
        names = {s.canonical_name for s in skills}
        assert "C#" in names
        assert "C" not in names

    def test_objective_c_does_not_extract_c(self, extractor):
        """Objective-C must not trigger false positive extraction of C."""
        text = "Maintained legacy iOS mobile applications written in Objective-C."
        skills = extractor.extract_from_text(text, section_name=SECTION_EXPERIENCE)
        names = {s.canonical_name for s in skills}
        assert "Objective-C" in names
        assert "C" not in names

    def test_grade_c_rejected(self, extractor):
        """'Grade C' in education must NOT be extracted as C."""
        text = "Completed coursework: Data Structures (Grade A), Physics (Grade C)."
        skills = extractor.extract_from_text(text, section_name=SECTION_EDUCATION)
        names = {s.canonical_name for s in skills}
        assert "C" not in names

    def test_section_c_rejected(self, extractor):
        """'Section C' or 'Room C' must NOT be extracted as C."""
        text = "Address: Block B, Section C, Room 204, Campus Hostel."
        skills = extractor.extract_from_text(text, section_name=SECTION_PERSONAL_INFO)
        names = {s.canonical_name for s in skills}
        assert "C" not in names

    def test_vitamin_c_rejected(self, extractor):
        """'Vitamin C' must NOT be extracted as C."""
        text = "Researched vitamin C synthesis in biochemistry lab."
        skills = extractor.extract_from_text(text, section_name=SECTION_PROJECTS)
        names = {s.canonical_name for s in skills}
        assert "C" not in names

    def test_middle_initial_c_rejected(self, extractor):
        """Middle initial 'David C. Smith' must NOT be extracted as C."""
        text = "Candidate Name: David C. Smith"
        skills = extractor.extract_from_text(text, section_name=SECTION_PERSONAL_INFO)
        names = {s.canonical_name for s in skills}
        assert "C" not in names

    def test_bullet_c_rejected(self, extractor):
        """Bullet point like 'c) Handled client meetings' must NOT match C."""
        text = "Responsibilities:\na) Led sprints\nb) Code reviews\nc) Handled meetings"
        skills = extractor.extract_from_text(text, section_name=SECTION_EXPERIENCE)
        names = {s.canonical_name for s in skills}
        assert "C" not in names


# =============================================================================
# 2. SPECIAL PROGRAMMING LANGUAGE TESTS: Go vs English "go"
# =============================================================================

class TestGoProgrammingDisambiguation:
    """Tests distinguishing Go / Golang from the common English verb 'go'."""

    def test_go_in_technical_skills_list(self, extractor):
        """'Go' in technical skills list should be extracted as Go."""
        text = "Programming Languages: Python, Go, Rust, Java"
        skills = extractor.extract_from_text(text, section_name=SECTION_TECHNICAL_SKILLS)
        names = {s.canonical_name for s in skills}
        assert "Go" in names
        assert "Python" in names

    def test_golang_alias_extracted(self, extractor):
        """'Golang' should resolve to canonical 'Go'."""
        text = "Senior Golang backend engineer designing high-throughput microservices."
        skills = extractor.extract_from_text(text, section_name=SECTION_EXPERIENCE)
        go_skills = [s for s in skills if s.canonical_name == "Go"]
        assert len(go_skills) == 1
        assert go_skills[0].canonical_name == "Go"
        assert go_skills[0].category == "Programming Languages"

    def test_go_with_programming_context_in_projects(self, extractor):
        """'built with Go and Docker' in projects should extract Go."""
        text = "Backend microservices built with Go and Docker for containerized deployment."
        skills = extractor.extract_from_text(text, section_name=SECTION_PROJECTS)
        names = {s.canonical_name for s in skills}
        assert "Go" in names
        assert "Docker" in names

    def test_lowercase_go_in_prose_rejected(self, extractor):
        """Lowercase 'go' in sentences must NEVER match Go."""
        text = "Eager to go to work in a dynamic team and go through new challenges."
        skills = extractor.extract_from_text(text, section_name=SECTION_EXPERIENCE)
        names = {s.canonical_name for s in skills}
        assert "Go" not in names

    def test_capitalized_go_with_verb_preposition_rejected(self, extractor):
        """'Go to', 'Go for', 'Go ahead' must NOT match Go."""
        text = "Ready to Go for interview rounds and Go ahead with campus placement."
        skills = extractor.extract_from_text(text, section_name=SECTION_ACHIEVEMENTS)
        names = {s.canonical_name for s in skills}
        assert "Go" not in names

    def test_ongoing_and_good_boundaries(self, extractor):
        """Words containing 'go' like 'ongoing' or 'good' must NOT match Go."""
        text = "Ongoing research with good outcomes and algorithms."
        skills = extractor.extract_from_text(text, section_name=SECTION_PROJECTS)
        names = {s.canonical_name for s in skills}
        assert "Go" not in names


# =============================================================================
# 3. SPECIAL PROGRAMMING LANGUAGE TESTS: R vs Letters & Words
# =============================================================================

class TestRProgrammingDisambiguation:
    """Tests distinguishing R programming language from initials, R&D, and letters."""

    def test_r_in_technical_skills_list(self, extractor):
        """'R' listed with Python and SQL in technical skills should be extracted."""
        text = "Data Science & Analytics: Python, R, SQL, Tableau"
        skills = extractor.extract_from_text(text, section_name=SECTION_TECHNICAL_SKILLS)
        names = {s.canonical_name for s in skills}
        assert "R" in names
        assert "Python" in names
        assert "SQL" in names

    def test_r_programming_phrase_extracted(self, extractor):
        """'R programming' in projects should be extracted."""
        text = "Conducted hypothesis testing using R programming and ggplot2."
        skills = extractor.extract_from_text(text, section_name=SECTION_PROJECTS)
        names = {s.canonical_name for s in skills}
        assert "R" in names

    def test_r_and_d_rejected(self, extractor):
        """'R&D' must NOT be extracted as R."""
        text = "Intern at Siemens R&D Department working on IoT sensor data."
        skills = extractor.extract_from_text(text, section_name=SECTION_EXPERIENCE)
        names = {s.canonical_name for s in skills}
        assert "R" not in names

    def test_middle_initial_r_rejected(self, extractor):
        """'John R. Doe' must NOT match R."""
        text = "Recommendation by Prof. John R. Doe, HOD Computer Science."
        skills = extractor.extract_from_text(text, section_name=SECTION_PERSONAL_INFO)
        names = {s.canonical_name for s in skills}
        assert "R" not in names

    def test_grade_r_rejected(self, extractor):
        """'Grade R' in education must NOT match R."""
        text = "Secured Grade R in special research elective."
        skills = extractor.extract_from_text(text, section_name=SECTION_EDUCATION)
        names = {s.canonical_name for s in skills}
        assert "R" not in names


# =============================================================================
# 4. FALSE POSITIVES: Git, SQL, Substring Protection
# =============================================================================

class TestFalsePositiveSubstrings:
    """Tests ensuring substrings within ordinary words are never extracted."""

    def test_git_not_extracted_from_digital_or_legitimate(self, extractor):
        """Git must NOT be extracted from digital, legitimate, agile, or digit."""
        text = "Worked on digital marketing strategies with agile teams for legitimate apps."
        skills = extractor.extract_from_text(text, section_name=SECTION_EXPERIENCE)
        names = {s.canonical_name for s in skills}
        assert "Git" not in names

    def test_git_extracted_when_standalone_and_github(self, extractor):
        """Standalone Git and GitHub must both be cleanly extracted."""
        text = "Version control: Git, GitHub, GitLab"
        skills = extractor.extract_from_text(text, section_name=SECTION_TECHNICAL_SKILLS)
        names = {s.canonical_name for s in skills}
        assert "Git" in names
        assert "GitHub" in names
        assert "GitLab" in names

    def test_sql_not_double_extracted_from_postgresql_or_mysql(self, extractor):
        """PostgreSQL and MySQL must NOT falsely trigger independent SQL matches from their names."""
        text = "Database design using PostgreSQL and MySQL."
        skills = extractor.extract_from_text(text, section_name=SECTION_TECHNICAL_SKILLS)
        names = {s.canonical_name for s in skills}
        assert "PostgreSQL" in names
        assert "MySQL" in names
        assert "SQL" not in names

    def test_sql_extracted_when_standalone_with_other_databases(self, extractor):
        """When SQL is explicitly mentioned standalone, it should be extracted."""
        text = "Databases: PostgreSQL, MySQL, and SQL"
        skills = extractor.extract_from_text(text, section_name=SECTION_TECHNICAL_SKILLS)
        names = {s.canonical_name for s in skills}
        assert "PostgreSQL" in names
        assert "MySQL" in names
        assert "SQL" in names

    def test_java_not_extracted_from_javascript(self, extractor):
        """JavaScript must NOT trigger a false positive match for Java."""
        text = "Frontend interactive components written in JavaScript and React."
        skills = extractor.extract_from_text(text, section_name=SECTION_TECHNICAL_SKILLS)
        names = {s.canonical_name for s in skills}
        assert "JavaScript" in names
        assert "Java" not in names

    def test_both_java_and_javascript_extracted(self, extractor):
        """When both Java and JavaScript appear, both should be extracted."""
        text = "Languages: Java, JavaScript, Python"
        skills = extractor.extract_from_text(text, section_name=SECTION_TECHNICAL_SKILLS)
        names = {s.canonical_name for s in skills}
        assert "Java" in names
        assert "JavaScript" in names
        assert "Python" in names


# =============================================================================
# 5. SYMBOL-SAFE MATCHING: C++, C#, .NET, Node.js, Vue.js, CI/CD
# =============================================================================

class TestSymbolSafeMatching:
    """Tests verifying symbol-safe matching for languages and frameworks."""

    @pytest.mark.parametrize(
        "token,expected_canonical,expected_category",
        [
            ("C++", "C++", "Programming Languages"),
            ("C#", "C#", "Programming Languages"),
            (".NET", ".NET", "Backend Development"),
            (".NET Core", ".NET Core", "Backend Development"),
            ("ASP.NET", "ASP.NET", "Backend Development"),
            ("ASP.NET Core", "ASP.NET Core", "Backend Development"),
            ("Node.js", "Node.js", "Backend Development"),
            ("Vue.js", "Vue.js", "Frontend Development"),
            ("Next.js", "Next.js", "Frontend Development"),
            ("Nuxt.js", "Nuxt.js", "Frontend Development"),
            ("CI/CD", "CI/CD", "DevOps"),
            ("PL/SQL", "PL/SQL", "Programming Languages"),
            ("SSL/TLS", "SSL/TLS", "Cybersecurity"),
        ],
    )
    def test_symbol_bearing_skills(self, extractor, token, expected_canonical, expected_category):
        """Test extraction of symbol-bearing technologies."""
        text = f"Experience with {token} in production environments."
        skills = extractor.extract_from_text(text, section_name=SECTION_EXPERIENCE)
        matched = [s for s in skills if s.canonical_name == expected_canonical]
        assert len(matched) == 1
        assert matched[0].canonical_name == expected_canonical
        assert matched[0].category == expected_category
        assert matched[0].extraction_method in {"symbol_regex", "exact"}


# =============================================================================
# 6. ALIAS RESOLUTION TESTS
# =============================================================================

class TestAliasResolution:
    """Tests verifying normalization of colloquial aliases to canonical names."""

    @pytest.mark.parametrize(
        "alias,expected_canonical,expected_category",
        [
            ("k8s", "Kubernetes", "DevOps"),
            ("reactjs", "React", "Frontend Development"),
            ("react.js", "React", "Frontend Development"),
            ("postgres", "PostgreSQL", "Databases"),
            ("py", "Python", "Programming Languages"),
            ("ts", "TypeScript", "Programming Languages"),
            ("js", "JavaScript", "Programming Languages"),
            ("cpp", "C++", "Programming Languages"),
            ("csharp", "C#", "Programming Languages"),
            ("ml", "Machine Learning", "Machine Learning"),
            ("dl", "Deep Learning", "Artificial Intelligence"),
            ("dsa", "Data Structures", "Software Engineering"),
            ("oops", "Object-Oriented Programming (OOP)", "Software Engineering"),
            ("qa", "Quality Assurance", "Testing & QA"),
            ("aws", "Amazon Web Services (AWS)", "Cloud Computing"),
            ("gcp", "Google Cloud Platform (GCP)", "Cloud Computing"),
        ],
    )
    def test_alias_normalization(self, extractor, alias, expected_canonical, expected_category):
        """Verify alias normalizes accurately to canonical name and category."""
        text = f"Technical proficiency: {alias}"
        skills = extractor.extract_from_text(text, section_name=SECTION_TECHNICAL_SKILLS)
        matched = [s for s in skills if s.canonical_name == expected_canonical]
        assert len(matched) == 1, f"Failed to resolve alias '{alias}' to '{expected_canonical}'"
        assert matched[0].canonical_name == expected_canonical
        assert matched[0].category == expected_category
        assert matched[0].extraction_method == "alias"


# =============================================================================
# 7. SECTION-AWARE EXTRACTION & CONFIDENCE WEIGHTING
# =============================================================================

class TestSectionAwareness:
    """Tests verifying section confidence scaling and short-alias guardrails."""

    def test_technical_skills_section_has_highest_confidence(self, extractor):
        """Skills in technical_skills should have maximum confidence (1.0)."""
        text = "Languages: Python, Docker"
        skills = extractor.extract_from_text(text, section_name=SECTION_TECHNICAL_SKILLS)
        for s in skills:
            assert s.confidence >= 0.98

    def test_projects_section_confidence(self, extractor):
        """Skills in projects section should have high confidence (~0.90)."""
        text = "Built web scraper using Python and Docker."
        skills = extractor.extract_from_text(text, section_name=SECTION_PROJECTS)
        for s in skills:
            assert 0.85 <= s.confidence <= 0.95

    def test_education_section_confidence_is_lower(self, extractor):
        """Skills mentioned in education have lower confidence (~0.78)."""
        text = "Completed undergraduate coursework in Python and Operating Systems."
        skills = extractor.extract_from_text(text, section_name=SECTION_EDUCATION)
        for s in skills:
            assert s.confidence <= 0.80

    def test_bs_in_education_does_not_extract_bootstrap(self, extractor):
        """'BS in Computer Science' in education must NOT extract Bootstrap."""
        text = "BS in Computer Science and Engineering, GPA 3.8/4.0."
        skills = extractor.extract_from_text(text, section_name=SECTION_EDUCATION)
        names = {s.canonical_name for s in skills}
        assert "Bootstrap" not in names

    def test_cv_in_personal_info_does_not_extract_computer_vision(self, extractor):
        """'My CV' in personal info must NOT extract Computer Vision."""
        text = "Curriculum Vitae / CV of John Doe."
        skills = extractor.extract_from_text(text, section_name=SECTION_PERSONAL_INFO)
        names = {s.canonical_name for s in skills}
        assert "Computer Vision" not in names


# =============================================================================
# 8. DUPLICATE ELIMINATION & OCCURRENCE TRACKING ACROSS SECTIONS
# =============================================================================

class TestDeduplicationAndAggregation:
    """Tests verifying duplicate elimination, occurrence aggregation, and provenance."""

    def test_skill_repeated_across_multiple_sections(self, extractor):
        """A skill appearing in technical_skills, projects, and experience is returned once with count 3."""
        sec_map = SectionMap(
            sections=[
                ClassifiedSection(
                    canonical_name=SECTION_TECHNICAL_SKILLS,
                    original_heading="Technical Skills",
                    content="Languages: Python, PostgreSQL",
                    raw_content="Languages: Python, PostgreSQL",
                ),
                ClassifiedSection(
                    canonical_name=SECTION_PROJECTS,
                    original_heading="Projects",
                    content="1. Analytics Platform: Built using Python and FastAPI.",
                    raw_content="1. Analytics Platform: Built using Python and FastAPI.",
                ),
                ClassifiedSection(
                    canonical_name=SECTION_EXPERIENCE,
                    original_heading="Work Experience",
                    content="Software Intern: Wrote backend services in Python.",
                    raw_content="Software Intern: Wrote backend services in Python.",
                ),
            ]
        )

        profile = extractor.extract(sec_map)
        python_skills = [s for s in profile.technical_skills if s.canonical_name == "Python"]

        assert len(python_skills) == 1
        py = python_skills[0]
        assert py.canonical_name == "Python"
        assert py.occurrences == 3
        assert py.source_section == SECTION_TECHNICAL_SKILLS
        assert py.confidence >= 0.98
        assert SECTION_TECHNICAL_SKILLS in py.sections
        assert SECTION_PROJECTS in py.sections
        assert SECTION_EXPERIENCE in py.sections

    def test_skill_profile_partition_technical_vs_soft(self, extractor):
        """Technical skills and soft skills must be partitioned cleanly."""
        sec_map = SectionMap(
            sections=[
                ClassifiedSection(
                    canonical_name=SECTION_TECHNICAL_SKILLS,
                    original_heading="Skills",
                    content="Python, Docker, React, PostgreSQL",
                    raw_content="Python, Docker, React, PostgreSQL",
                ),
                ClassifiedSection(
                    canonical_name=SECTION_SOFT_SKILLS,
                    original_heading="Soft Skills",
                    content="Problem Solving, Teamwork, Leadership, Communication",
                    raw_content="Problem Solving, Teamwork, Leadership, Communication",
                ),
            ]
        )

        profile = extractor.extract(sec_map)
        tech_names = {s.canonical_name for s in profile.technical_skills}
        soft_names = {s.canonical_name for s in profile.soft_skills}

        assert "Python" in tech_names
        assert "Docker" in tech_names
        assert "React" in tech_names
        assert "PostgreSQL" in tech_names
        assert "Problem Solving" not in tech_names

        assert "Problem Solving" in soft_names
        assert "Teamwork" in soft_names
        assert "Leadership" in soft_names
        assert "Communication" in soft_names
        assert "Python" not in soft_names

        assert profile.total_skills == 8
        assert "Programming Languages" in profile.skills_by_category
        assert "Soft Skills" in profile.skills_by_category

    def test_serialization_to_dict(self, extractor):
        """Test to_dict serialization of ExtractedSkill and SkillProfile."""
        text = "Languages: Python, Docker"
        skills = extractor.extract_from_text(text, section_name=SECTION_TECHNICAL_SKILLS)
        skill_dict = skills[0].to_dict()
        assert "canonical_name" in skill_dict
        assert "category" in skill_dict
        assert "matched_text" in skill_dict
        assert "confidence" in skill_dict
        assert "extraction_method" in skill_dict
        assert "occurrences" in skill_dict
        assert "sections" in skill_dict

        profile = SkillProfile(
            technical_skills=skills,
            soft_skills=[],
            skills_by_category={"Programming Languages": ["Python"]},
            total_skills=len(skills),
            all_skills=skills,
        )
        p_dict = profile.to_dict()
        assert "technical_skills" in p_dict
        assert "soft_skills" in p_dict
        assert "skills_by_category" in p_dict
        assert p_dict["total_skills"] == len(skills)


# =============================================================================
# 9. EDGE CASES: Empty Sections & Unknown Skills
# =============================================================================

class TestEdgeCasesAndRobustness:
    """Tests verifying handling of empty sections, whitespace, and unknown inputs."""

    def test_empty_string_returns_empty_list(self, extractor):
        """Extracting from empty string or whitespace returns empty list."""
        assert extractor.extract_from_text("") == []
        assert extractor.extract_from_text("   \n\t  ") == []

    def test_empty_section_map_returns_empty_profile(self, extractor):
        """Extracting from empty SectionMap returns empty SkillProfile."""
        profile = extractor.extract(SectionMap(sections=[]))
        assert profile.total_skills == 0
        assert profile.technical_skills == []
        assert profile.soft_skills == []

    def test_none_inputs_handled_gracefully(self, extractor):
        """None input returns empty SkillProfile."""
        profile = extractor.extract(None)
        assert profile.total_skills == 0

    def test_unknown_skills_are_ignored(self, extractor):
        """Non-existent skill strings must be completely ignored."""
        text = "Expert in NonExistentFrameworkXYZ123 and RandomMadeUpLibrary99."
        skills = extractor.extract_from_text(text, section_name=SECTION_TECHNICAL_SKILLS)
        assert skills == []
