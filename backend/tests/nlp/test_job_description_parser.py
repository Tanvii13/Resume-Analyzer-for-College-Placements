"""
Comprehensive tests for Sprint 4 Module A: Job Description Processing.

Validates:
- Valid and full job descriptions (campus placements and industry roles)
- Missing sections handling and missing_critical_sections detection
- Required vs. preferred technical skills distinction (headers and inline cues)
- Soft skills separation and evidence preservation
- Multiple technical skills across languages, frameworks, databases, cloud, devops
- Experience extraction (ranges, minimums, maximums, freshers, entry level)
- Educational qualifications (degrees, degree levels, fields of study, batches)
- Internship descriptions (job type, fresher status, stipend, duration)
- Noisy, malformed, and unformatted job descriptions
- Empty and whitespace-only input
- Duplicate requirements deduplication and occurrence tracking
- Representation of unavailable information (None / empty lists, no hallucination)
- Independence of parsing across multiple job descriptions
- Prevention of false positives (company names, URLs, headers, English homonyms: next, react, spring, cv)
"""

import pytest

from app.nlp.job_matching import (
    JOB_PARSER_VERSION,
    EducationRequirement,
    EligibilityCriteria,
    ExperienceRequirement,
    JobDescriptionParser,
    JobParsingMetadata,
    JobSkillRequirement,
    JobType,
    LocationRequirement,
    OtherJobRequirements,
    ParsedJobDescription,
    WorkplaceType,
    parse_job_description,
    parse_multiple_job_descriptions,
)
from app.nlp.schemas import ConfidenceLevel


@pytest.fixture(scope="session")
def parser() -> JobDescriptionParser:
    """Session-scoped parser instance."""
    return JobDescriptionParser()


# =============================================================================
# 1. VALID FULL JOB DESCRIPTIONS
# =============================================================================

class TestValidJobDescriptions:
    """Tests for complete, well-formed job descriptions."""

    def test_full_campus_placement_jd(self, parser):
        jd_text = """
Job Title: Graduate Software Engineer Trainee
Company: Infosys Technologies Ltd
Location: Bengaluru, Karnataka (Hybrid)
Job Type: Full-Time

About Us:
Infosys is a global leader in next-generation digital services and consulting.

Responsibilities:
• Develop high-performance backend microservices and RESTful APIs.
• Collaborate with cross-functional teams to design, develop, test, and deploy features.
• Write clean, maintainable code with unit tests.
• Troubleshoot production bugs and improve system latency.

Eligibility Criteria:
• B.Tech / B.E. / M.Tech in Computer Science, Information Technology, or ICT.
• 2025 graduating batch only.
• Minimum CPI: 7.0 / 10 or 65% aggregate throughout academics (10th, 12th, graduation).
• Maximum 1 active backlog permitted at the time of interview.

Required Technical Skills:
• Strong foundation in Data Structures, Algorithms, and OOP concepts.
• Proficiency in Python or Java.
• Hands-on experience with SQL and relational databases (PostgreSQL or MySQL).
• Good understanding of Git and Linux command line.

Preferred Technical Skills:
• Familiarity with Docker and Kubernetes is a plus.
• Experience with FastAPI, React, or cloud platforms (AWS / Azure) is desirable.

Soft Skills:
• Strong communication, problem-solving skills, and adaptability.
• Willingness to learn new frameworks quickly and work in an agile team.

Other Details:
• CTC: 9.5 LPA
• Bond: 1 year service agreement.
• Selection Process: 1. Online Coding Round, 2. Technical Interview, 3. HR Round.
"""
        parsed = parser.parse(jd_text, job_id="jd-001")

        assert isinstance(parsed, ParsedJobDescription)
        assert parsed.job_id == "jd-001"
        assert parsed.title == "Graduate Software Engineer Trainee"
        assert parsed.company_name == "Infosys Technologies Ltd"
        assert parsed.job_type == JobType.FULL_TIME

        # Location
        assert parsed.location.city == "Bengaluru"
        assert parsed.location.state == "Karnataka"
        assert parsed.location.workplace_type == WorkplaceType.HYBRID
        assert not parsed.location.is_remote

        # Skills - Required
        req_names = {s.canonical_name for s in parsed.required_technical_skills}
        assert "Python" in req_names
        assert "Java" in req_names
        assert "SQL" in req_names
        assert "PostgreSQL" in req_names
        assert "Data Structures" in req_names
        assert "Algorithms" in req_names
        assert "Git" in req_names
        assert "Linux" in req_names
        for s in parsed.required_technical_skills:
            assert s.is_required is True
            assert s.evidence is not None

        # Skills - Preferred
        pref_names = {s.canonical_name for s in parsed.preferred_technical_skills}
        assert "Docker" in pref_names
        assert "Kubernetes" in pref_names
        assert "FastAPI" in pref_names
        assert "React" in pref_names
        assert "Amazon Web Services (AWS)" in pref_names
        for s in parsed.preferred_technical_skills:
            assert s.is_required is False

        # Soft Skills
        soft_names = {s.canonical_name for s in parsed.soft_skills}
        assert "Communication" in soft_names
        assert "Problem Solving" in soft_names
        assert "Adaptability" in soft_names

        # Education
        assert "B.Tech" in parsed.education.degrees
        assert "bachelors" in parsed.education.degree_levels
        assert any("Computer Science" in f for f in parsed.education.fields_of_study)

        # Eligibility
        assert parsed.eligibility.min_cgpa == 7.0
        assert parsed.eligibility.cgpa_scale == 10.0
        assert parsed.eligibility.min_percentage == 65.0
        assert 2025 in parsed.eligibility.allowed_batches
        assert parsed.eligibility.backlog_policy is not None
        assert "1 active backlog" in parsed.eligibility.backlog_policy.lower()

        # Responsibilities
        assert len(parsed.responsibilities) == 4
        assert any("microservices" in r.lower() for r in parsed.responsibilities)

        # Other requirements
        assert parsed.other_requirements.salary_or_stipend is not None
        assert "9.5 LPA" in parsed.other_requirements.salary_or_stipend
        assert parsed.other_requirements.bond_or_service_agreement is not None
        assert "1 year" in parsed.other_requirements.bond_or_service_agreement
        assert len(parsed.other_requirements.selection_process) >= 3

        # Metadata
        assert parsed.metadata.overall_confidence >= 0.85
        assert parsed.metadata.confidence_level == ConfidenceLevel.HIGH
        assert len(parsed.metadata.missing_critical_sections) == 0

    def test_industry_cloud_devops_jd(self, parser):
        jd_text = """
Job Title: Cloud & DevOps Engineer
Company: CloudNative Solutions Inc.
Location: Remote (Work from home)
Job Type: Full-Time

About Us:
We specialize in Kubernetes and cloud infrastructure automation.

Job Summary:
Looking for a DevOps Engineer with 3-5 years of experience in AWS and Terraform.

Key Responsibilities:
- Build and maintain CI/CD pipelines using GitHub Actions and GitLab CI.
- Deploy and monitor microservices clusters on Amazon Web Services (AWS) using Kubernetes and Helm.
- Manage infrastructure as code with Terraform.

Must Have:
- 3+ years experience with Linux, Bash, and Python scripting.
- Deep expertise in Docker, Kubernetes, and AWS (EC2, S3, RDS).
- Hands-on experience with CI/CD and Git.

Nice to Have:
- Knowledge of Prometheus, Grafana, and ELK Stack.
- Experience with Go (Golang) programming.

Salary: 18 - 24 LPA
"""
        parsed = parser.parse(jd_text)

        assert parsed.title == "Cloud & DevOps Engineer"
        assert parsed.company_name == "CloudNative Solutions Inc."
        assert parsed.location.is_remote is True
        assert parsed.location.workplace_type == WorkplaceType.REMOTE
        assert parsed.experience.min_years == 3.0
        assert parsed.experience.max_years == 5.0

        req_names = {s.canonical_name for s in parsed.required_technical_skills}
        assert "Docker" in req_names
        assert "Kubernetes" in req_names
        assert "Amazon Web Services (AWS)" in req_names
        assert "Terraform" in req_names
        assert "Git" in req_names

        pref_names = {s.canonical_name for s in parsed.preferred_technical_skills}
        assert "Prometheus" in pref_names or "Grafana" in pref_names or "ELK Stack" in pref_names


# =============================================================================
# 2. REQUIRED VS PREFERRED SKILLS SEPARATION
# =============================================================================

class TestRequiredVsPreferredSkills:
    """Tests verifying accurate classification of required vs. preferred skills."""

    def test_separate_sections(self, parser):
        jd = """
Role: Data Analyst
Must Have:
• Python, SQL, Tableau
Good to Have:
• Power BI, Machine Learning, R
"""
        parsed = parser.parse(jd)
        req = {s.canonical_name for s in parsed.required_technical_skills}
        pref = {s.canonical_name for s in parsed.preferred_technical_skills}

        assert "Python" in req
        assert "SQL" in req
        assert "Tableau" in req
        assert "Power BI" in pref
        assert "Machine Learning" in pref

    def test_inline_preference_cues_in_single_section(self, parser):
        jd = """
Job Title: Frontend Developer
Requirements:
• Strong proficiency in JavaScript, TypeScript, and React.
• Hands-on experience with HTML5, CSS3, and Redux is required.
• Familiarity with Next.js and Tailwind CSS is a plus.
• Knowledge of GraphQL and Docker is desirable.
• Bonus points for AWS experience.
"""
        parsed = parser.parse(jd)
        req = {s.canonical_name for s in parsed.required_technical_skills}
        pref = {s.canonical_name for s in parsed.preferred_technical_skills}

        assert "JavaScript" in req
        assert "TypeScript" in req
        assert "React" in req
        assert "HTML5" in req
        assert "CSS3" in req

        assert "Tailwind CSS" in pref
        assert "GraphQL" in pref
        assert "Docker" in pref
        assert "Amazon Web Services (AWS)" in pref

    def test_inline_semicolon_clause_preference_switch(self, parser):
        jd = """
Title: Full Stack Engineer
Key Requirements:
• Must be proficient in Python and Django; experience with React is a plus.
• Strong knowledge of PostgreSQL; Redis is desirable.
"""
        parsed = parser.parse(jd)
        req = {s.canonical_name for s in parsed.required_technical_skills}
        pref = {s.canonical_name for s in parsed.preferred_technical_skills}

        assert "Python" in req
        assert "Django" in req
        assert "PostgreSQL" in req
        assert "React" in pref
        assert "Redis" in pref

    def test_promotion_of_preferred_to_required_on_conflict(self, parser):
        jd = """
Title: Backend Developer
Preferred Skills:
• Python, FastAPI
Mandatory Requirements:
• Python is strictly required.
"""
        parsed = parser.parse(jd)
        req = {s.canonical_name for s in parsed.required_technical_skills}
        pref = {s.canonical_name for s in parsed.preferred_technical_skills}

        # Python should be promoted to required
        assert "Python" in req
        assert "Python" not in pref
        assert "FastAPI" in pref


# =============================================================================
# 3. INTERNSHIP SPECIFIC DESCRIPTIONS
# =============================================================================

class TestInternshipDescriptions:
    """Tests handling campus and industry internships."""

    def test_summer_internship_with_stipend_and_fresher(self, parser):
        jd = """
Summer Internship 2025: Software Development Engineer Intern
Company: Amazon Development Centre India
Duration: 6 months (Jan - June 2025)
Stipend: ₹80,000 / month
Location: Hyderabad (On-site)
Open to pre-final year students (2026 batch).

Requirements:
• Strong problem-solving skills and expertise in C++ or Java.
• Understanding of Data Structures and Algorithms.
• Basic knowledge of Linux and Git.

Nice to have:
• Cloud knowledge (AWS) and Docker.
"""
        parsed = parser.parse(jd)

        assert parsed.job_type == JobType.INTERNSHIP
        assert parsed.experience.is_fresher_eligible is True
        assert parsed.experience.min_years == 0.0
        assert parsed.location.city == "Hyderabad"
        assert parsed.location.workplace_type == WorkplaceType.ON_SITE
        assert "₹80,000" in (parsed.other_requirements.salary_or_stipend or "")
        assert 2026 in parsed.eligibility.allowed_batches

        req = {s.canonical_name for s in parsed.required_technical_skills}
        assert "C++" in req
        assert "Java" in req
        assert "Data Structures" in req
        assert "Algorithms" in req

    def test_internship_followed_by_fte(self, parser):
        jd = """
Role: Member of Technical Staff - Intern + Full Time
Company: Oracle India
Location: Pune, Maharashtra
Job Type: Internship followed by FTE placement

About the Role:
6-month internship with performance-based PPO conversion to Full-Time role.
Open to 2025 graduating B.Tech students.
CPI criteria: 7.5 and above.
Required: Java, SQL, Operating Systems.
"""
        parsed = parser.parse(jd)

        assert parsed.job_type == JobType.INTERNSHIP
        assert parsed.experience.is_fresher_eligible is True
        assert parsed.eligibility.min_cgpa == 7.5
        assert 2025 in parsed.eligibility.allowed_batches
        req = {s.canonical_name for s in parsed.required_technical_skills}
        assert "Java" in req
        assert "SQL" in req
        assert "Operating Systems" in req


# =============================================================================
# 4. EXPERIENCE EXTRACTION
# =============================================================================

class TestExperienceExtraction:
    """Tests extracting various experience specifications."""

    def test_experience_range(self, parser):
        jd = "Role: Software Engineer\nExperience: 2-4 years of relevant experience in software engineering."
        parsed = parser.parse(jd)
        assert parsed.experience.min_years == 2.0
        assert parsed.experience.max_years == 4.0
        assert parsed.experience.is_fresher_eligible is False

    def test_experience_minimum_plus(self, parser):
        jd = "Role: Senior SDE\nRequirements: 5+ years of experience in distributed systems."
        parsed = parser.parse(jd)
        assert parsed.experience.min_years == 5.0
        assert parsed.experience.max_years is None
        assert parsed.experience.is_fresher_eligible is False

    def test_experience_at_least(self, parser):
        jd = "Position: Backend Developer\nAt least 1 year experience with Node.js and PostgreSQL."
        parsed = parser.parse(jd)
        assert parsed.experience.min_years == 1.0
        assert parsed.experience.is_fresher_eligible is False

    def test_experience_up_to(self, parser):
        jd = "Role: Junior Developer\nExperience: Up to 2 years of experience. Freshers may also apply."
        parsed = parser.parse(jd)
        assert parsed.experience.min_years == 0.0
        assert parsed.experience.max_years == 2.0
        assert parsed.experience.is_fresher_eligible is True

    def test_fresher_explicit_no_experience(self, parser):
        jd = "Role: Graduate Trainee\nNo prior experience required. Open to freshers."
        parsed = parser.parse(jd)
        assert parsed.experience.min_years == 0.0
        assert parsed.experience.max_years == 0.0
        assert parsed.experience.is_fresher_eligible is True


# =============================================================================
# 5. EDUCATION AND ELIGIBILITY CRITERIA
# =============================================================================

class TestEducationAndEligibility:
    """Tests extracting academic qualifications and placement eligibility."""

    def test_multiple_degrees_and_branches(self, parser):
        jd = """
Role: Associate Systems Engineer
Academic Criteria:
• Candidates must possess B.Tech / B.E. / M.Tech / MCA in CSE, IT, or ECE.
• Minimum 60% aggregate in Class X, XII and Graduation.
• CPI: 6.5 / 10 and above.
• Eligible Batches: 2024 and 2025 passouts.
• No active backlogs allowed at the time of selection.
"""
        parsed = parser.parse(jd)

        # Degrees
        assert "B.Tech" in parsed.education.degrees
        assert "B.E." in parsed.education.degrees
        assert "M.Tech" in parsed.education.degrees
        assert "MCA" in parsed.education.degrees
        assert "10th (SSC)" not in parsed.education.degrees

        # Eligibility
        assert parsed.eligibility.min_cgpa == 6.5
        assert parsed.eligibility.cgpa_scale == 10.0
        assert parsed.eligibility.min_percentage == 60.0
        assert 2024 in parsed.eligibility.allowed_batches
        assert 2025 in parsed.eligibility.allowed_batches
        assert parsed.eligibility.backlog_policy is not None
        assert "no active backlogs" in parsed.eligibility.backlog_policy.lower()
        branches = {b.upper() for b in parsed.eligibility.allowed_branches}
        assert "CSE" in branches
        assert "IT" in branches

    def test_us_gpa_scale(self, parser):
        jd = """
Position: Research Intern
Qualifications:
• Bachelor's or Master's degree in Computer Science.
• Minimum GPA 3.5 / 4.0.
"""
        parsed = parser.parse(jd)
        assert parsed.eligibility.min_cgpa == 3.5
        assert parsed.eligibility.cgpa_scale == 4.0


# =============================================================================
# 6. LOCATION AND WORKPLACE TYPE
# =============================================================================

class TestLocationExtraction:
    """Tests extracting locations and workplace models."""

    def test_remote_workplace(self, parser):
        jd = "Role: Python Developer\nLocation: Remote / Work from Home\nRequirements: Python, Django."
        parsed = parser.parse(jd)
        assert parsed.location.is_remote is True
        assert parsed.location.workplace_type == WorkplaceType.REMOTE

    def test_hybrid_workplace(self, parser):
        jd = "Role: SDE\nLocation: Pune, Maharashtra (Hybrid)\nRequirements: C++, Linux."
        parsed = parser.parse(jd)
        assert parsed.location.city == "Pune"
        assert parsed.location.state == "Maharashtra"
        assert parsed.location.workplace_type == WorkplaceType.HYBRID
        assert parsed.location.is_remote is False

    def test_onsite_workplace(self, parser):
        jd = "Role: QA Engineer\nWork Location: Gandhinagar, Gujarat\nIn-office full-time role."
        parsed = parser.parse(jd)
        assert parsed.location.city == "Gandhinagar"
        assert parsed.location.state == "Gujarat"
        assert parsed.location.workplace_type == WorkplaceType.ON_SITE


# =============================================================================
# 7. PREVENTION OF FALSE POSITIVES
# =============================================================================

class TestFalsePositivePrevention:
    """Tests ensuring non-skill words, URLs, emails, and company names are not extracted."""

    def test_english_homonyms_not_skills(self, parser):
        jd = """
Company: Acme Technologies Ltd
Role: Backend Engineer
About Us:
Acme is a global leader in next-generation cloud solutions.
Our engineers must react quickly to production incidents and adapt to the next phase of growth.
Internship starts in Spring 2025.
Please send your updated CV to careers@acme.com.

Requirements:
• Python, Java, and Docker.
"""
        parsed = parser.parse(jd)
        tech_names = {s.canonical_name for s in parsed.required_technical_skills + parsed.preferred_technical_skills}

        assert "Next.js" not in tech_names, "next-generation must not trigger Next.js"
        assert "React" not in tech_names, "react quickly must not trigger React"
        assert "Spring Framework" not in tech_names, "Spring 2025 must not trigger Spring Framework"
        assert "Computer Vision" not in tech_names, "send your CV must not trigger Computer Vision"
        assert "Git" not in tech_names, "careers@acme.com or URLs must not trigger Git"
        assert "Acme Technologies Ltd" not in tech_names, "Company name must not be a skill"

        # Legitimate skills are extracted
        assert "Python" in tech_names
        assert "Java" in tech_names
        assert "Docker" in tech_names

    def test_company_name_not_extracted_as_skill(self, parser):
        jd = """
Company: Docker Inc
Job Title: Systems Developer
Requirements:
• Knowledge of Linux and Kubernetes.
"""
        parsed = parser.parse(jd)
        req_names = {s.canonical_name for s in parsed.required_technical_skills}
        assert "Linux" in req_names
        assert "Kubernetes" in req_names
        assert "Docker Inc" not in req_names


# =============================================================================
# 8. NOISY, MALFORMED, AND UNFORMATTED INPUTS
# =============================================================================

class TestMalformedAndNoisyInputs:
    """Tests robustness on messy, badly formatted, and unstructured job descriptions."""

    def test_unstructured_one_liner(self, parser):
        jd = "URGENT HIRING!!! developer needed... must know PYTHON, DJANGO, REACT... 2-4 yrs exp... pune office... send cv to hr@startup.io"
        parsed = parser.parse(jd)

        assert parsed.experience.min_years == 2.0
        assert parsed.experience.max_years == 4.0
        assert parsed.location.city == "Pune"
        req = {s.canonical_name for s in parsed.required_technical_skills}
        assert "Python" in req
        assert "Django" in req
        assert "React" in req
        assert "Computer Vision" not in req

    def test_unicode_and_inconsistent_spacing(self, parser):
        jd = """
  \u200b  Job Title:    Data   Engineer  \u200b
  Company:   DataCorp \u00a0 Pvt Ltd
  \u2022 Required Skills: Python \u2013 SQL \u2013 Spark
  \u25cf Preferred: Airflow; AWS
"""
        parsed = parser.parse(jd)
        assert parsed.title == "Data Engineer"
        assert parsed.company_name == "DataCorp Pvt Ltd"
        req = {s.canonical_name for s in parsed.required_technical_skills}
        assert "Python" in req
        assert "SQL" in req
        assert "Apache Spark" in req


# =============================================================================
# 9. EMPTY AND EDGE-CASE INPUTS
# =============================================================================

class TestEmptyAndEdgeCaseInputs:
    """Tests handling empty string, whitespace, and minimal descriptions."""

    def test_empty_string(self, parser):
        parsed = parser.parse("")
        assert parsed.title is None
        assert parsed.company_name is None
        assert parsed.job_type == JobType.UNKNOWN
        assert len(parsed.required_technical_skills) == 0
        assert len(parsed.metadata.warnings) > 0
        assert parsed.metadata.overall_confidence == 0.0
        assert parsed.metadata.confidence_level == ConfidenceLevel.LOW

    def test_whitespace_only(self, parser):
        parsed = parser.parse("   \n\t   \n  ")
        assert parsed.title is None
        assert parsed.metadata.overall_confidence == 0.0

    def test_minimal_uninformative_text(self, parser):
        parsed = parser.parse("Hello, we are hiring.")
        assert parsed.title is None
        assert len(parsed.required_technical_skills) == 0
        assert "job_title" in parsed.metadata.missing_critical_sections
        assert "required_technical_skills" in parsed.metadata.missing_critical_sections


# =============================================================================
# 10. DUPLICATE REQUIREMENTS AND OCCURRENCES
# =============================================================================

class TestDuplicateRequirements:
    """Tests deduplication of repeated skills and responsibilities."""

    def test_duplicate_skills_across_sections(self, parser):
        jd = """
Job Title: Python Developer
Responsibilities:
• Write scalable services in Python.
• Maintain PostgreSQL databases.
Requirements:
• 2+ years of Python experience.
• Hands-on with PostgreSQL and Git.
"""
        parsed = parser.parse(jd)
        py_skills = [s for s in parsed.required_technical_skills if s.canonical_name == "Python"]
        assert len(py_skills) == 1
        assert py_skills[0].occurrences >= 2

        pg_skills = [s for s in parsed.required_technical_skills if s.canonical_name == "PostgreSQL"]
        assert len(pg_skills) == 1
        assert pg_skills[0].occurrences >= 2

    def test_duplicate_responsibilities_removed(self, parser):
        jd = """
Responsibilities:
• Develop high-performance backend microservices.
• Develop high-performance backend microservices.
• Write clean unit tests.
"""
        parsed = parser.parse(jd)
        assert len(parsed.responsibilities) == 2


# =============================================================================
# 11. INDEPENDENCE AND MULTIPLE PARSING
# =============================================================================

class TestIndependentParsing:
    """Tests statelessness and parsing multiple job descriptions."""

    def test_parse_multiple_job_descriptions(self, parser):
        jd1 = """
Job Title: Python Developer
Company: Alpha Corp
Requirements: Python, FastAPI
"""
        jd2 = """
Job Title: Java Architect
Company: Beta Solutions
Requirements: Java, Spring Boot
"""
        results = parser.parse_multiple([jd1, jd2])
        assert len(results) == 2

        assert results[0].title == "Python Developer"
        assert results[0].company_name == "Alpha Corp"
        r1_skills = {s.canonical_name for s in results[0].required_technical_skills}
        assert "Python" in r1_skills
        assert "Java" not in r1_skills

        assert results[1].title == "Java Architect"
        assert results[1].company_name == "Beta Solutions"
        r2_skills = {s.canonical_name for s in results[1].required_technical_skills}
        assert "Java" in r2_skills
        assert "Python" not in r2_skills

    def test_convenience_functions(self):
        jd = "Job Title: ML Engineer\nRequirements: Python, PyTorch, TensorFlow"
        parsed = parse_job_description(jd, job_id="ml-101")
        assert parsed.job_id == "ml-101"
        assert parsed.title == "ML Engineer"
        skills = {s.canonical_name for s in parsed.required_technical_skills}
        assert "PyTorch" in skills
        assert "TensorFlow" in skills

        batch = parse_multiple_job_descriptions([jd, jd])
        assert len(batch) == 2
