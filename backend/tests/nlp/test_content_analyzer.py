"""
Comprehensive test suite for Sprint 3 Module C: Content Quality & Impact Analyzer.

Tests all required scenarios:
1. Project titles without descriptions (incomplete tier, 0 score).
2. Strong project descriptions (high completeness, active voice, high score).
3. Action-oriented bullet points (leading action verbs categorized).
4. Bullet points without action verbs and passive introductory phrases.
5. Measurable outcomes (percentages, speedups, user scale, latency, throughput, cost).
6. Numeric values that are NOT actual impact metrics (years, ports, versions, models).
7. Repeated bullet points (cross-entry duplication detection).
8. Different experience descriptions (experience vs internship).
9. Empty projects and experience sections (graceful handling, 0 score).
10. Student project accommodation (technical depth without production metrics).
11. Generic / cliché content detection.
12. Deterministic evaluation.
"""

import copy
import pytest
from app.nlp.content import (
    CONTENT_ANALYZER_VERSION,
    ContentQualityAnalyzer,
    DescriptionCompleteness,
    VerbCategory,
    analyze_content_quality,
    check_leading_action_verb,
    detect_generic_content,
    detect_impact_metrics,
    detect_weak_introductory_phrase,
    find_action_verbs_in_text,
)
from app.nlp.schemas import (
    CandidateProfile,
    ExperienceEntry,
    ProjectEntry,
)


# =============================================================================
# 1. Project Titles Without Descriptions Test
# =============================================================================
def test_project_titles_without_descriptions():
    """Project with only a title and no description or highlights should score 0 and be incomplete."""
    profile = CandidateProfile(
        filename="sparse.pdf",
        projects=[
            ProjectEntry(
                title="Distributed File System",
                description=None,
                highlights=[],
                technologies=[],
            )
        ],
    )

    analyzer = ContentQualityAnalyzer()
    report = analyzer.analyze(profile)

    assert report.total_entries_analyzed == 1
    entry = report.entries[0]
    assert entry.entry_title == "Distributed File System"
    assert entry.entry_type == "project"
    assert entry.content_quality_score == 0.0
    assert entry.description_completeness == DescriptionCompleteness.INCOMPLETE
    assert any("missing description" in issue.lower() for issue in entry.issues)


# =============================================================================
# 2. Strong Project Descriptions Test
# =============================================================================
def test_strong_project_descriptions():
    """Detailed technical descriptions with action verbs and metrics should achieve high score."""
    profile = CandidateProfile(
        filename="strong.pdf",
        projects=[
            ProjectEntry(
                title="Distributed Key-Value Store",
                description="Designed and deployed a fault-tolerant distributed object store replicating AWS S3 semantics.",
                technologies=["Go", "gRPC", "Docker", "Raft", "Redis"],
                highlights=[
                    "Architected Raft consensus algorithm across 5 nodes achieving 99.9% uptime during network partitions.",
                    "Benchmarked system throughput exceeding 10,500 operations per second with sub-25ms response latency.",
                    "Implemented custom chunk hashing and deduplication algorithm saving 35% disk storage.",
                ],
            )
        ],
    )

    report = analyze_content_quality(profile)
    assert report.total_entries_analyzed == 1
    entry = report.entries[0]

    assert entry.content_quality_score >= 88.0
    assert entry.description_completeness == DescriptionCompleteness.HIGH
    assert len(entry.action_verbs_detected) >= 3
    assert len(entry.impact_metrics_detected) >= 2
    assert len(entry.evidence) >= 3
    assert len(entry.issues) == 0


# =============================================================================
# 3. Action-Oriented Bullet Points Test
# =============================================================================
def test_action_oriented_bullet_points():
    """Leading action verbs should be identified and mapped to functional categories."""
    b1 = "Engineered real-time telemetry ingestion microservice using FastAPI and Apache Kafka."
    b2 = "Optimized PostgreSQL query indices and caching strategies, reducing latency by 42%."
    b3 = "Automated CI/CD deployment pipelines using Docker and GitHub Actions."

    v1 = check_leading_action_verb(b1)
    assert v1 is not None
    assert v1.verb == "engineered"
    assert v1.category == VerbCategory.ENGINEERING
    assert v1.is_leading is True

    v2 = check_leading_action_verb(b2)
    assert v2 is not None
    assert v2.verb == "optimized"
    assert v2.category == VerbCategory.OPTIMIZATION

    v3 = check_leading_action_verb(b3)
    assert v3 is not None
    assert v3.verb == "automated"
    assert v3.category == VerbCategory.AUTOMATION


# =============================================================================
# 4. Bullet Points Without Action Verbs and Passive Phrases Test
# =============================================================================
def test_passive_and_weak_phrases():
    """Weak opening phrases (e.g. 'worked on', 'responsible for') must be detected and penalized."""
    weak_bullets = [
        "Worked on a web application for booking appointments.",
        "Responsible for bug fixing and testing code.",
        "Helped with database migration to PostgreSQL.",
        "Assisted in development of front-end components.",
    ]

    for b in weak_bullets:
        weak_found = detect_weak_introductory_phrase(b)
        assert weak_found is not None, f"Expected weak phrase in: {b}"

    # Verify impact on entry evaluation
    profile = CandidateProfile(
        filename="weak.pdf",
        projects=[
            ProjectEntry(
                title="Clinic Portal",
                description="worked on a web application for local clinic",
                technologies=["React"],
                highlights=[
                    "Responsible for bug fixing and helping with UI.",
                    "Assisted in development of the backend.",
                ],
            )
        ],
    )

    report = analyze_content_quality(profile)
    entry = report.entries[0]
    assert entry.content_quality_score < 60.0
    assert any("passive" in issue.lower() for issue in entry.issues)


# =============================================================================
# 5. Measurable Outcomes Detection Test
# =============================================================================
def test_measurable_outcomes_detection():
    """Detects percentages, speedups, scale, latency, throughput, and accuracy."""
    test_cases = [
        ("Reduced API response latency by 35%.", ["35%"]),
        ("Platform currently serves 10,000 active students.", ["10,000 active students"]),
        ("Achieved a 3x speedup in batch processing time.", ["3x"]),
        ("Processed 15,000 requests/sec with sub-20ms latency.", ["15,000 requests/sec", "sub-20ms"]),
        ("Improved image classification accuracy from 82% to 94.5%.", ["82%", "94.5%"]),
        ("Saved $4,500 annually in AWS cloud spend.", ["$4,500"]),
    ]

    for text, expected_matches in test_cases:
        matches = detect_impact_metrics(text)
        assert len(matches) >= 1, f"Failed to detect impact metric in: '{text}'"
        matched_raw = [m.raw_match for m in matches]
        for exp in expected_matches:
            assert any(exp in raw for raw in matched_raw), f"Expected '{exp}' in {matched_raw} for '{text}'"


# =============================================================================
# 6. Numeric Values That Are NOT Impact Metrics (False Positive Safety)
# =============================================================================
def test_non_impact_numeric_values_not_classified():
    """
    CRITICAL: Years, versions, port numbers, HTTP codes, and model names
    MUST NOT be classified as measurable outcomes.
    """
    non_metrics = [
        "Developed web application using Python 3.11 and React 18.",
        "Configured development server listening on port 8080.",
        "Graduated from college in 2024 after studying from 2021 - 2025.",
        "Integrated OAuth 2.0 authentication and HTML5 canvas API.",
        "Fine-tuned ResNet-50 and GPT-4 architectures for CS 101 coursework.",
        "Handled HTTP 200 and 404 response codes gracefully.",
    ]

    for sentence in non_metrics:
        detected = detect_impact_metrics(sentence)
        assert len(detected) == 0, (
            f"False positive impact metric detected in '{sentence}': {[m.raw_match for m in detected]}"
        )


# =============================================================================
# 7. Repeated Bullet Points Across Entries Test
# =============================================================================
def test_repeated_bullet_points_detection():
    """Identical or near-identical bullet points across projects must trigger duplicate warnings."""
    repeated_bullet = "Automated integration testing suites in Docker containers, increasing CI pipeline reliability."

    profile = CandidateProfile(
        filename="dup.pdf",
        projects=[
            ProjectEntry(
                title="Project Alpha",
                highlights=[repeated_bullet, "Built user dashboard."],
                technologies=["Docker"],
            ),
            ProjectEntry(
                title="Project Beta",
                highlights=[repeated_bullet, "Configured SQL database."],
                technologies=["Docker"],
            ),
        ],
    )

    report = analyze_content_quality(profile)
    assert len(report.duplicate_content_warnings) >= 1
    assert any("Project Alpha" in w and "Project Beta" in w for w in report.duplicate_content_warnings)
    assert any("eliminate repeated bullet points" in r.lower() for r in report.recommendations_summary)


# =============================================================================
# 8. Different Experience Descriptions Test
# =============================================================================
def test_experience_and_internship_evaluation():
    """Evaluates both full-time experience and internship entries distinctly."""
    profile = CandidateProfile(
        filename="exp.pdf",
        experience=[
            ExperienceEntry(
                company_name="Acme Corp",
                job_title="Software Developer",
                is_internship=False,
                responsibilities=[
                    "Engineered payment gateway microservice handling $200,000 in daily transactions.",
                    "Refactored legacy database models into PostgreSQL partitioned tables.",
                ],
                technologies_used=["Python", "FastAPI", "PostgreSQL"],
            )
        ],
        internships=[
            ExperienceEntry(
                company_name="Startup Labs",
                job_title="Research Intern",
                is_internship=True,
                responsibilities=[
                    "Benchmarked Transformer attention heads, achieving 18% speedup.",
                    "Implemented attention head pruning algorithm reducing model memory footprint.",
                ],
                technologies_used=["PyTorch"],
            )
        ],
    )

    report = analyze_content_quality(profile)
    assert report.total_entries_analyzed == 2

    exp_entry = next(e for e in report.entries if e.entry_type == "experience")
    intern_entry = next(e for e in report.entries if e.entry_type == "internship")

    assert exp_entry.content_quality_score >= 80.0
    assert intern_entry.content_quality_score >= 75.0
    assert len(exp_entry.action_verbs_detected) >= 2


# =============================================================================
# 9. Empty Projects and Experience Sections Test
# =============================================================================
def test_empty_projects_and_experience():
    """Empty candidate profiles must evaluate gracefully without exceptions."""
    empty_profile = CandidateProfile(filename="empty.pdf")

    report = analyze_content_quality(empty_profile)
    assert report.overall_content_quality_score == 0.0
    assert report.total_entries_analyzed == 0
    assert len(report.entries) == 0
    assert len(report.recommendations_summary) > 0


# =============================================================================
# 10. Student Project Accommodation Test
# =============================================================================
def test_student_project_accommodation():
    """
    Student academic projects with deep technical architecture and action verbs
    must NOT be severely penalized simply because they lack production user counts.
    """
    profile = CandidateProfile(
        filename="student.pdf",
        projects=[
            ProjectEntry(
                title="C-Compiler Implementation",
                description="Designed and implemented a recursive descent compiler for a subset of the C programming language.",
                technologies=["C++", "LLVM", "Flex", "Bison"],
                highlights=[
                    "Architected lexical analyzer and abstract syntax tree generator supporting control flow and pointers.",
                    "Implemented three-address code intermediate representation and register allocation algorithms.",
                    "Constructed extensive test suite of 80 synthetic programs verifying semantic analysis and type checking.",
                ],
            )
        ],
    )

    report = analyze_content_quality(profile)
    entry = report.entries[0]

    # Student project with strong technical depth should still score well (>= 80)
    assert entry.content_quality_score >= 80.0
    assert entry.description_completeness == DescriptionCompleteness.HIGH
    assert any("student" in ev.lower() or "technical implementation" in ev.lower() for ev in entry.evidence)


# =============================================================================
# 11. Generic Cliché Content Detection Test
# =============================================================================
def test_generic_cliche_content_detection():
    """Detects generic phrases like 'worked on a web application' or 'responsible for features'."""
    cliches = detect_generic_content("Worked on a web application using modern technologies.")
    assert len(cliches) >= 1
    assert any("web application" in c.lower() for c in cliches)

    profile = CandidateProfile(
        filename="cliche.pdf",
        projects=[
            ProjectEntry(
                title="Web Project",
                description="Worked on a web application using modern technologies.",
                highlights=["Responsible for developing features and fixing bugs."],
            )
        ],
    )

    report = analyze_content_quality(profile)
    entry = report.entries[0]
    assert entry.content_quality_score < 55.0
    assert any("generic" in issue.lower() for issue in entry.issues)


# =============================================================================
# 12. Deterministic Content Evaluation Test
# =============================================================================
def test_deterministic_content_evaluation():
    """Identical candidate profiles evaluated multiple times must produce identical results."""
    profile = CandidateProfile(
        filename="det.pdf",
        projects=[
            ProjectEntry(
                title="Telemetry Pipeline",
                description="Engineered real-time telemetry streaming service.",
                technologies=["Go", "Kafka"],
                highlights=["Reduced latency by 35%."],
            )
        ],
    )

    analyzer = ContentQualityAnalyzer()
    r1 = analyzer.analyze(profile)
    r2 = analyzer.analyze(profile)

    assert r1.overall_content_quality_score == r2.overall_content_quality_score
    assert len(r1.entries) == len(r2.entries)
    assert r1.entries[0].action_verbs_detected == r2.entries[0].action_verbs_detected
    assert r1.entries[0].impact_metrics_detected == r2.entries[0].impact_metrics_detected
    assert r1.entries[0].content_quality_score == r2.entries[0].content_quality_score
