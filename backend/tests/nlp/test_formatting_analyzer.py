"""
Comprehensive test suite for Sprint 3 Module B: Resume Formatting Quality Analyzer.

Tests all required fixture conditions:
1. Well-structured resumes.
2. Inconsistent section headings (mixed casing, trailing colons).
3. Excessive whitespace (3+ blank lines).
4. Long paragraphs (>90 words without breaks) and walls of text.
5. Inconsistent bullets (mixed markers, empty bullets, >60 word bullets).
6. Missing section boundaries (missing critical headers).
7. Multiple / repeated section headings.
8. Two-column extraction artifacts (handling without false penalties).
9. Empty and whitespace-only text inputs.
10. Different PDF/DOCX extracted-text patterns (ResumeParseResult integration).
11. Inconsistent date representations.
12. Duplicate bullet content.
13. Integration with Module A (FormattingReadabilityScorer).
14. Deterministic formatting analysis.
"""

from typing import List
import pytest
from app.nlp.formatting import (
    DEFAULT_ANALYZER_LIMITATIONS,
    FindingSeverity,
    FormattingAnalysisResult,
    FormattingCategory,
    FormattingQualityAnalyzer,
    analyze_formatting,
)
from app.nlp.schemas import CandidateProfile, SectionSummary
from app.nlp.scoring.formatting_scoring import FormattingReadabilityScorer
from app.services.resume_parser import ResumeParseResult


# =============================================================================
# Synthetic Resume Fixtures
# =============================================================================
WELL_STRUCTURED_RESUME = """
RAHUL SHARMA
Email: rahul.sharma@example.com | Phone: +91 9876543210
LinkedIn: linkedin.com/in/rahulsharma | GitHub: github.com/rahulsharma

EDUCATION
Bachelor of Technology in Computer Science and Engineering
Indian Institute of Technology Bombay, Mumbai
2021 - 2025 | CGPA: 9.12 / 10.0

TECHNICAL SKILLS
Languages: Python, Go, C++, JavaScript, SQL
Frameworks: FastAPI, React, Node.js, Django
Databases & Cloud: PostgreSQL, Redis, Docker, AWS

EXPERIENCE
Software Engineering Intern | TechCorp Solutions
May 2024 - July 2024 | Bangalore, India
• Architected a real-time event streaming pipeline using Kafka and FastAPI handling 12,000 requests per second.
• Optimized database indexing and query caching in PostgreSQL, cutting median API response latency by 45%.
• Automated integration testing suites in Docker containers, increasing CI pipeline reliability to 99.8%.

PROJECTS
Distributed Key-Value Store | Go, Raft, gRPC
January 2024 - March 2024
• Implemented the Raft consensus algorithm with leader election, log replication, and heartbeat monitoring across 5 nodes.
• Designed snapshotting and log compaction mechanism saving 40% memory usage during prolonged execution runs.
• Benchmarked cluster throughput reaching 10,500 operations per second under network partition simulations.

Smart Campus Placement Assistant | Python, FastAPI, React
August 2023 - November 2023
• Built an end-to-end recruitment preparation platform serving 2,500 active university students.
• Integrated full-text search indexing and structured resume analytics for personalized placement recommendations.
"""

INCONSISTENT_HEADINGS_RESUME = """
ANANYA VERMA
ananya@example.com | +91 9123456789

EDUCATION:
B.Tech in Information Technology, 2025
CGPA: 8.7

technical skills
Python, Java, Spring Boot, MySQL, Docker

Experience:
Intern at CloudWorks
May 2024 - July 2024
• Developed REST APIs for internal resource management.

PROJECTS
Automated Testing Framework
January 2024
• Built test automation suites in Python.
"""

EXCESSIVE_WHITESPACE_RESUME = """
VIKRAM ADITYA
vikram@example.com




EDUCATION
B.E. Computer Science, 2025




SKILLS
Python, C++, SQL




EXPERIENCE
• Developed backend services using Python.




PROJECTS
• Built distributed task queue in Redis.
"""

LONG_PARAGRAPHS_RESUME = """
PRIYA PATEL
priya@example.com | +91 9988776655

EDUCATION
B.Tech in Computer Science, 2025

TECHNICAL SKILLS
Python, JavaScript, React, Node.js, MongoDB

EXPERIENCE
Software Developer Intern at Alpha Systems
May 2024 - August 2024
During my time as an intern at Alpha Systems I was primarily responsible for leading the backend development of the entire customer analytics platform where I worked closely with senior architects and product managers to redesign our core customer ingestion service which previously suffered from frequent bottlenecks whenever peak traffic exceeded five thousand requests per minute so I completely refactored the relational database schema and wrote brand new asynchronous microservices in Python using FastAPI while simultaneously configuring Redis queues and background worker pools to process batches asynchronously which ultimately eliminated server crashes during flash sales and reduced page load latencies significantly across the board.

PROJECTS
• Built web application for student course registration.
"""

INCONSISTENT_BULLETS_RESUME = """
ROHAN MEHTA
rohan@example.com | +91 9876501234

EDUCATION
B.Tech Computer Science, 2025

TECHNICAL SKILLS
Python, Go, Docker

EXPERIENCE
Software Intern
May 2024 - July 2024
• Developed microservices using FastAPI.
- Configured Docker containers for deployment.
* Wrote unit tests and integration tests.
• 

PROJECTS
Cloud Storage Engine
• Implemented custom object store in Go with raft consensus achieving sub-20ms latency while simultaneously configuring automatic failover protocols across multiple geographical regions and conducting rigorous stress benchmarks under simulated packet drops to guarantee maximum fault tolerance for enterprise customers during high volume writes, which required extensive profiling of memory allocations, kernel socket parameters, garbage collection pauses, and distributed lock contention under heavy concurrency loads across multiple cloud providers.
"""

REPEATED_HEADINGS_RESUME = """
SIDDHARTH RAO
siddharth@example.com

EDUCATION
B.Tech Computer Science, 2025

EXPERIENCE
Intern at Company A
May 2024 - July 2024
• Built backend APIs.

PROJECTS
Project 1
• Built chat app.

EXPERIENCE
Intern at Company B
Dec 2023 - Jan 2024
• Implemented frontend features.
"""

TWO_COLUMN_RESUME_TEXT = """
Amit Joshi
amit@example.com | +91 9876543210

EDUCATION
B.Tech in Computer Science
XYZ Institute of Technology
2021 - 2025 | CGPA: 8.8

SKILLS
Languages: Python, Java
Tools: Git, Docker, Linux
Databases: PostgreSQL, MongoDB

EXPERIENCE
Software Engineering Intern | NextGen Tech
June 2024 - August 2024
• Developed microservice endpoints in Python.
• Wrote SQL queries and optimized table schemas.

PROJECTS
E-Commerce Engine
January 2024 - March 2024
• Implemented payment gateway integration.
• Deployed application using Docker containers.
"""


# =============================================================================
# 1. Well-Structured Resume Test
# =============================================================================
def test_well_structured_resume():
    """A clean, well-formatted resume should earn a high score with no critical findings."""
    analyzer = FormattingQualityAnalyzer()
    result = analyzer.analyze(WELL_STRUCTURED_RESUME)

    assert result.formatting_score >= 88.0
    assert result.max_score == 100.0
    assert len(result.strengths) >= 3

    # Ensure no critical or major warning defects
    critical_findings = [f for f in result.findings if f.severity == FindingSeverity.CRITICAL]
    assert len(critical_findings) == 0

    # Verify documented limitations
    assert len(result.limitations) == len(DEFAULT_ANALYZER_LIMITATIONS)
    assert any("text-only" in lim.lower() for lim in result.limitations)


# =============================================================================
# 2. Inconsistent Section Headings Test
# =============================================================================
def test_inconsistent_section_headings():
    """Mixed casing (UPPERCASE vs lowercase/Title Case) and trailing colons should be flagged."""
    analyzer = FormattingQualityAnalyzer()
    result = analyzer.analyze(INCONSISTENT_HEADINGS_RESUME)

    issue_ids = [f.issue_id for f in result.findings]
    assert "FMT_INCONSISTENT_HEADING_CASING" in issue_ids or "FMT_INCONSISTENT_HEADING_PUNCTUATION" in issue_ids

    casing_finding = next(
        (f for f in result.findings if "HEADING" in f.issue_id), None
    )
    assert casing_finding is not None
    assert casing_finding.category == FormattingCategory.SECTION_STRUCTURE
    assert casing_finding.confidence >= 0.85
    assert casing_finding.evidence is not None


# =============================================================================
# 3. Excessive Whitespace Test
# =============================================================================
def test_excessive_whitespace():
    """4+ consecutive blank lines should trigger FMT_EXCESSIVE_BLANK_LINES with line reference."""
    analyzer = FormattingQualityAnalyzer()
    result = analyzer.analyze(EXCESSIVE_WHITESPACE_RESUME)

    ws_finding = next((f for f in result.findings if f.issue_id == "FMT_EXCESSIVE_BLANK_LINES"), None)
    assert ws_finding is not None
    assert ws_finding.category == FormattingCategory.TEXT_READABILITY
    assert ws_finding.severity == FindingSeverity.WARNING
    assert ws_finding.line_reference is not None
    assert ws_finding.confidence == 1.0


# =============================================================================
# 4. Long Paragraphs & Dense Text Test
# =============================================================================
def test_long_paragraphs():
    """Paragraphs exceeding 90 words without bullet points should trigger readability warnings."""
    analyzer = FormattingQualityAnalyzer()
    result = analyzer.analyze(LONG_PARAGRAPHS_RESUME)

    long_para_finding = next(
        (f for f in result.findings if f.issue_id in ("FMT_LONG_PARAGRAPH", "FMT_UNSEGMENTED_WALL_OF_TEXT")),
        None,
    )
    assert long_para_finding is not None
    assert long_para_finding.category == FormattingCategory.TEXT_READABILITY
    assert long_para_finding.confidence >= 0.90
    assert "words" in long_para_finding.description.lower()


# =============================================================================
# 5. Inconsistent Bullets Test
# =============================================================================
def test_inconsistent_bullets():
    """Mixing •, -, * bullet markers, empty bullets, and >60 word bullets must be flagged."""
    analyzer = FormattingQualityAnalyzer()
    result = analyzer.analyze(INCONSISTENT_BULLETS_RESUME)

    issue_ids = [f.issue_id for f in result.findings]
    # Check mixed markers
    assert "FMT_INCONSISTENT_BULLET_MARKERS" in issue_ids
    # Check empty bullet
    assert "FMT_EMPTY_BULLET_POINT" in issue_ids
    # Check overly long bullet
    assert "FMT_EXCESSIVE_BULLET_LENGTH" in issue_ids

    empty_bullet = next(f for f in result.findings if f.issue_id == "FMT_EMPTY_BULLET_POINT")
    assert empty_bullet.line_reference is not None
    assert empty_bullet.confidence == 1.0


# =============================================================================
# 6. Missing Section Boundaries Test
# =============================================================================
def test_missing_section_boundaries():
    """Resume with no headings or missing core sections should register missing headings finding."""
    unsegmented_text = """
    John Doe
    john@example.com
    Went to ABC University and studied computer engineering from 2021 to 2025.
    Knows Python, Java, and Docker.
    Worked at a startup building backend services.
    """
    analyzer = FormattingQualityAnalyzer()
    result = analyzer.analyze(unsegmented_text)

    issue_ids = [f.issue_id for f in result.findings]
    assert "FMT_MISSING_SECTION_HEADING" in issue_ids


# =============================================================================
# 7. Multiple / Repeated Section Headings Test
# =============================================================================
def test_multiple_section_headings():
    """Repeated non-contiguous section headings should be flagged for consolidation."""
    analyzer = FormattingQualityAnalyzer()
    result = analyzer.analyze(REPEATED_HEADINGS_RESUME)

    repeated_finding = next((f for f in result.findings if f.issue_id == "FMT_REPEATED_SECTION_HEADING"), None)
    assert repeated_finding is not None
    assert repeated_finding.affected_section == "experience"
    assert repeated_finding.confidence >= 0.90


# =============================================================================
# 8. Two-Column Extraction Artifacts Test
# =============================================================================
def test_two_column_extraction_artifacts():
    """
    Two-column layouts that flatten cleanly into standard sections
    MUST NOT be classified as unreadable or given false critical penalties.
    """
    analyzer = FormattingQualityAnalyzer()
    result = analyzer.analyze(TWO_COLUMN_RESUME_TEXT)

    # Score should remain strong (>= 80.0)
    assert result.formatting_score >= 80.0
    critical_findings = [f for f in result.findings if f.severity == FindingSeverity.CRITICAL]
    assert len(critical_findings) == 0


# =============================================================================
# 9. Empty and Whitespace-Only Text Test
# =============================================================================
def test_empty_and_whitespace_text():
    """Empty or whitespace text inputs should return a valid result with score 0 without raising."""
    analyzer = FormattingQualityAnalyzer()

    for empty_input in ("", "   \n\n\t  \n  "):
        result = analyzer.analyze(empty_input)
        assert isinstance(result, FormattingAnalysisResult)
        assert result.formatting_score == 0.0
        assert len(result.findings) == 1
        assert result.findings[0].issue_id == "FMT_EMPTY_TEXT"
        assert result.findings[0].severity == FindingSeverity.CRITICAL


# =============================================================================
# 10. ResumeParseResult Integration Test
# =============================================================================
def test_resume_parse_result_integration():
    """Analyzer seamlessly accepts Sprint 1 ResumeParseResult object and captures metadata."""
    parse_result = ResumeParseResult.create(
        filename="rahul_sharma.pdf",
        file_type="pdf",
        text=WELL_STRUCTURED_RESUME,
        page_count=1,
    )
    result = analyze_formatting(parse_result)

    assert result.formatting_score >= 85.0
    assert result.metadata["filename"] == "rahul_sharma.pdf"
    assert result.metadata["page_count"] == 1
    assert result.metadata["total_lines"] > 0


# =============================================================================
# 11. Inconsistent Date Representations Test
# =============================================================================
def test_inconsistent_date_representations():
    """Mixing written month names ('May 2024') with numeric slashes ('05/2023') should be flagged."""
    mixed_dates_resume = """
    HARSH VARDHAN
    harsh@example.com

    EDUCATION
    B.Tech Computer Science
    08/2021 - 05/2025

    EXPERIENCE
    Software Intern
    May 2024 - July 2024
    • Developed backend APIs in Python.

    PROJECTS
    Web Platform
    2023-11 - 2024-02
    • Built web app.
    """
    analyzer = FormattingQualityAnalyzer()
    result = analyzer.analyze(mixed_dates_resume)

    issue_ids = [f.issue_id for f in result.findings]
    assert "FMT_INCONSISTENT_DATE_FORMATS" in issue_ids
    date_finding = next(f for f in result.findings if f.issue_id == "FMT_INCONSISTENT_DATE_FORMATS")
    assert date_finding.category == FormattingCategory.RESUME_CONSISTENCY


# =============================================================================
# 12. Duplicate Bullet Content Test
# =============================================================================
def test_duplicate_bullet_content():
    """Identical bullet points appearing multiple times should trigger duplicate warnings."""
    duplicate_bullets_resume = """
    KAVITA SINGH
    kavita@example.com

    EDUCATION
    B.Tech Computer Science, 2025

    EXPERIENCE
    Intern at TechCorp
    • Automated integration testing suites in Docker containers, increasing CI pipeline reliability to 99.8%.

    PROJECTS
    Project Alpha
    • Automated integration testing suites in Docker containers, increasing CI pipeline reliability to 99.8%.
    """
    analyzer = FormattingQualityAnalyzer()
    result = analyzer.analyze(duplicate_bullets_resume)

    issue_ids = [f.issue_id for f in result.findings]
    assert "FMT_DUPLICATE_BULLET_CONTENT" in issue_ids
    dup_finding = next(f for f in result.findings if f.issue_id == "FMT_DUPLICATE_BULLET_CONTENT")
    assert dup_finding.severity == FindingSeverity.WARNING


# =============================================================================
# 13. Integration with Module A FormattingReadabilityScorer
# =============================================================================
def test_integration_with_formatting_scorer():
    """FormattingReadabilityScorer in Module A consumes FormattingQualityAnalyzer findings."""
    from app.nlp.pipeline import ResumeNLPPipeline

    pipeline = ResumeNLPPipeline()
    profile_clean = pipeline.process(WELL_STRUCTURED_RESUME, "clean.pdf")
    profile_flawed = pipeline.process(INCONSISTENT_BULLETS_RESUME, "flawed.pdf")

    scorer = FormattingReadabilityScorer(max_score=18.75)

    # Score with well-structured text
    score_clean, ded_clean, str_clean = scorer.score(profile_clean, raw_text=WELL_STRUCTURED_RESUME)
    assert score_clean.score >= 15.0

    # Score with inconsistent bullets text
    score_flawed, ded_flawed, str_flawed = scorer.score(profile_flawed, raw_text=INCONSISTENT_BULLETS_RESUME)
    # Deductions should include granular issues from Module B
    ded_rules = [d.rule_id for d in ded_flawed]
    assert any("BULLET" in r for r in ded_rules)
    assert score_flawed.score < score_clean.score


# =============================================================================
# 14. Deterministic Formatting Analysis Test
# =============================================================================
def test_deterministic_formatting_analysis():
    """Repeated analysis of the exact same resume text must yield identical outputs."""
    analyzer = FormattingQualityAnalyzer()

    res1 = analyzer.analyze(WELL_STRUCTURED_RESUME)
    res2 = analyzer.analyze(WELL_STRUCTURED_RESUME)

    assert res1.formatting_score == res2.formatting_score
    assert len(res1.findings) == len(res2.findings)
    assert len(res1.strengths) == len(res2.strengths)

    for i in range(len(res1.findings)):
        assert res1.findings[i].issue_id == res2.findings[i].issue_id
        assert res1.findings[i].severity == res2.findings[i].severity
        assert res1.findings[i].line_reference == res2.findings[i].line_reference
