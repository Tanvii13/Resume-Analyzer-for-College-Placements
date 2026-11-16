"""
Unit tests for Sprint 3 – Module E: Rule-Based Recommendation Engine (US-09).

Covers:
- Every recommendation category (missing section, contact, education, project
  description, experience, content, skills, formatting, extraction)
- Issue -> recommendation mapping and that every Module D issue id has a rule
- Duplicate prevention (same advice from Modules A/B/D merged into one item)
- Deterministic prioritization (severity, component, confidence, actionability)
- Evidence-specific advice (named weak projects, quoted passive bullets)
- No invented skills / metrics / certifications in recommendation text
- Low-confidence findings flagged and down-ranked
- Empty reports and unknown issue ids (generic fallback)
"""

import re

import pytest

from app.nlp.improvement import (
    ImprovementAreasReport,
    ImprovementCategory,
    ImprovementIssue,
    ImprovementPriority,
    ImprovementSeverity,
)
from app.nlp.improvement.deduplicator import CANONICAL_ISSUE_CLUSTERS
from app.nlp.recommendations import (
    RULES,
    RecommendationCategory,
    RecommendationEngine,
    RecommendationPriority,
    generate_recommendations,
)
from app.nlp.recommendations.rules import GENERIC_FALLBACK_RULE_ID

COMPONENT_BY_CATEGORY = {
    ImprovementCategory.SECTION_COMPLETENESS: "section_completeness",
    ImprovementCategory.CONTENT_QUALITY: "content_quality",
    ImprovementCategory.SKILL_VISIBILITY: "skill_visibility",
    ImprovementCategory.FORMATTING: "formatting_readability",
}


def make_issue(
    issue_id,
    category=ImprovementCategory.CONTENT_QUALITY,
    severity=ImprovementSeverity.WARNING,
    priority=ImprovementPriority.MEDIUM,
    section="projects",
    confidence=0.9,
    evidence="detected",
):
    return ImprovementIssue(
        issue_id=issue_id,
        category=category,
        title=issue_id.replace("_", " ").title(),
        description=f"Description of {issue_id}.",
        severity=severity,
        priority=priority,
        affected_section=section,
        evidence=evidence,
        related_score_component=COMPONENT_BY_CATEGORY[category],
        confidence=confidence,
        detection_rule=f"check_{issue_id.lower()}",
    )


def make_report(*issues):
    return ImprovementAreasReport(
        total_issues=len(issues),
        high_priority_issues=sum(i.priority == ImprovementPriority.HIGH for i in issues),
        medium_priority_issues=sum(i.priority == ImprovementPriority.MEDIUM for i in issues),
        low_priority_issues=sum(i.priority == ImprovementPriority.LOW for i in issues),
        issues=list(issues),
        summary="test",
    )


@pytest.fixture(scope="module")
def engine():
    return RecommendationEngine()


# ============================================================================
# Rule registry coverage
# ============================================================================


def all_module_d_issue_ids():
    """Every issue id Module D can emit: detector ids + canonical cluster targets + raw FMT ids."""
    import inspect
    from app.nlp.formatting import rules as fmt_rules
    from app.nlp.improvement import detector

    detector_ids = set(re.findall(r'issue_id="(IMP_[A-Z_]+)"', inspect.getsource(detector)))
    fmt_ids = set(re.findall(r'issue_id="(FMT_[A-Z_]+)"', inspect.getsource(fmt_rules)))
    canonical = set(CANONICAL_ISSUE_CLUSTERS.values())
    # Formatting ids that Module D renames to a canonical IMP_ id never reach Module E raw
    fmt_reaching_e = {f for f in fmt_ids if f not in CANONICAL_ISSUE_CLUSTERS}
    return detector_ids | canonical | fmt_reaching_e


def test_every_module_d_issue_has_a_dedicated_rule(engine):
    missing = []
    for issue_id in sorted(all_module_d_issue_ids()):
        rule, is_fallback = engine._rule_for(make_issue(issue_id, section="projects"))
        if is_fallback:
            missing.append(issue_id)
    assert missing == [], f"issue ids without a recommendation rule: {missing}"


def test_rules_are_student_friendly_and_complete():
    for issue_id, rule in RULES.items():
        assert rule.title and rule.description and rule.why_it_matters and rule.suggested_action, (
            issue_id
        )
        assert 0.0 <= rule.actionability <= 1.0
        assert rule.recommendation_id.startswith("REC_")
        assert len(rule.title) <= 60, f"title too long for {issue_id}"


@pytest.mark.parametrize(
    "issue_id, category, expected_category",
    [
        (
            "IMP_MISSING_PROJECTS",
            ImprovementCategory.SECTION_COMPLETENESS,
            RecommendationCategory.MISSING_SECTION,
        ),
        (
            "IMP_CONTACT_MISSING_EMAIL",
            ImprovementCategory.SECTION_COMPLETENESS,
            RecommendationCategory.CONTACT,
        ),
        (
            "IMP_EDU_MISSING_CGPA",
            ImprovementCategory.SECTION_COMPLETENESS,
            RecommendationCategory.EDUCATION,
        ),
        (
            "IMP_WEAK_PROJECT_DESCRIPTION",
            ImprovementCategory.CONTENT_QUALITY,
            RecommendationCategory.PROJECT_DESCRIPTION,
        ),
        (
            "IMP_PASSIVE_PHRASING",
            ImprovementCategory.CONTENT_QUALITY,
            RecommendationCategory.CONTENT,
        ),
        (
            "IMP_POOR_SKILL_CATEGORIZATION",
            ImprovementCategory.SKILL_VISIBILITY,
            RecommendationCategory.SKILLS,
        ),
        (
            "IMP_INCONSISTENT_HEADINGS",
            ImprovementCategory.FORMATTING,
            RecommendationCategory.FORMATTING,
        ),
        (
            "IMP_EXTRACTION_UNCERTAINTY",
            ImprovementCategory.FORMATTING,
            RecommendationCategory.EXTRACTION,
        ),
    ],
)
def test_each_category_maps_to_issue(engine, issue_id, category, expected_category):
    report = engine.generate(make_report(make_issue(issue_id, category=category)))
    assert report.total_recommendations == 1
    rec = report.recommendations[0]
    assert rec.category == expected_category
    assert rec.related_issue_id == issue_id
    assert rec.related_issue_ids == [issue_id]
    assert rec.rule_id != GENERIC_FALLBACK_RULE_ID


# ============================================================================
# Mapping integrity and dedupe
# ============================================================================


def test_every_recommendation_maps_to_an_input_issue(engine):
    issues = [
        make_issue(i)
        for i in [
            "IMP_WEAK_PROJECT_DESCRIPTION",
            "IMP_PASSIVE_PHRASING",
            "IMP_LACK_OF_MEASURABLE_IMPACT",
            "IMP_DUPLICATE_BULLET_CONTENT",
        ]
    ]
    report = engine.generate(make_report(*issues))
    input_ids = {i.issue_id for i in issues}
    for rec in report.recommendations:
        assert rec.related_issue_id in input_ids
        assert set(rec.related_issue_ids) <= input_ids


def test_missing_section_signals_merge_into_one(engine):
    report = engine.generate(
        make_report(
            make_issue(
                "IMP_MISSING_PROJECTS",
                ImprovementCategory.SECTION_COMPLETENESS,
                ImprovementSeverity.CRITICAL,
                ImprovementPriority.HIGH,
                confidence=1.0,
                evidence="No projects found",
            ),
            make_issue(
                "IMP_MISSING_PRACTICAL_WORK",
                ImprovementCategory.SECTION_COMPLETENESS,
                ImprovementSeverity.CRITICAL,
                ImprovementPriority.HIGH,
                confidence=1.0,
                evidence="projects count = 0",
            ),
            make_issue(
                "FMT_MISSING_SECTION_HEADING",
                ImprovementCategory.FORMATTING,
                ImprovementSeverity.WARNING,
                ImprovementPriority.LOW,
                confidence=0.95,
                evidence="Missing sections: Projects",
            ),
        )
    )
    assert report.total_recommendations == 1
    rec = report.recommendations[0]
    assert rec.recommendation_id == "REC_ADD_PROJECTS_SECTION"
    assert set(rec.related_issue_ids) == {
        "IMP_MISSING_PROJECTS",
        "IMP_MISSING_PRACTICAL_WORK",
        "FMT_MISSING_SECTION_HEADING",
    }
    assert "No projects found" in rec.evidence and "projects count = 0" in rec.evidence


def test_duplicate_bullet_findings_merge(engine):
    report = engine.generate(
        make_report(
            make_issue("IMP_DUPLICATE_BULLET_CONTENT"),
            make_issue("FMT_DUPLICATE_BULLET_CONTENT", ImprovementCategory.FORMATTING),
        )
    )
    assert [r.recommendation_id for r in report.recommendations] == ["REC_REMOVE_DUPLICATE_BULLETS"]


def test_passive_and_few_verbs_merge(engine):
    report = engine.generate(
        make_report(make_issue("IMP_PASSIVE_PHRASING"), make_issue("IMP_LACK_OF_ACTION_VERBS"))
    )
    assert report.total_recommendations == 1
    assert report.recommendations[0].recommendation_id == "REC_USE_ACTION_VERBS"


def test_no_duplicate_recommendation_ids(engine):
    ids = list(RULES)
    report = engine.generate(make_report(*[make_issue(i) for i in ids]))
    rec_ids = [r.recommendation_id for r in report.recommendations]
    assert len(rec_ids) == len(set(rec_ids))


def test_missing_section_from_formatting_heading_uses_section(engine):
    report = engine.generate(
        make_report(
            make_issue(
                "FMT_MISSING_SECTION_HEADING", ImprovementCategory.FORMATTING, section="education"
            )
        )
    )
    rec = report.recommendations[0]
    assert rec.recommendation_id == "REC_ADD_EDUCATION_SECTION"
    assert "Education" in rec.title


# ============================================================================
# Prioritization
# ============================================================================


def test_priority_ordering_is_deterministic(engine):
    issues = [
        make_issue(
            "IMP_MISSING_SOFT_SKILLS",
            ImprovementCategory.SKILL_VISIBILITY,
            ImprovementSeverity.INFO,
            ImprovementPriority.LOW,
        ),
        make_issue(
            "IMP_CONTACT_MISSING_EMAIL",
            ImprovementCategory.SECTION_COMPLETENESS,
            ImprovementSeverity.CRITICAL,
            ImprovementPriority.HIGH,
            confidence=1.0,
        ),
        make_issue("IMP_LACK_OF_MEASURABLE_IMPACT"),
    ]
    a = engine.generate(make_report(*issues))
    b = engine.generate(make_report(*reversed(issues)))
    assert [r.recommendation_id for r in a.recommendations] == [
        r.recommendation_id for r in b.recommendations
    ]
    assert a.model_dump() == b.model_dump() | {"metadata": a.metadata}
    assert [r.recommendation_id for r in a.recommendations] == [
        "REC_ADD_EMAIL",
        "REC_ADD_REAL_OUTCOMES",
        "REC_SHOW_SOFT_SKILLS",
    ]
    assert [r.priority for r in a.recommendations] == [
        RecommendationPriority.HIGH,
        RecommendationPriority.MEDIUM,
        RecommendationPriority.LOW,
    ]


def test_critical_always_high(engine):
    issue = make_issue(
        "IMP_MISSING_SKILLS",
        ImprovementCategory.SECTION_COMPLETENESS,
        ImprovementSeverity.CRITICAL,
        ImprovementPriority.LOW,
        confidence=0.3,
    )
    rec = engine.generate(make_report(issue)).recommendations[0]
    assert rec.priority == RecommendationPriority.HIGH


def test_scores_sorted_descending_and_counts_match(engine):
    report = engine.generate(make_report(*[make_issue(i) for i in list(RULES)[:12]]))
    scores = [r.priority_score for r in report.recommendations]
    assert scores == sorted(scores, reverse=True)
    assert (
        report.high_priority_count + report.medium_priority_count + report.low_priority_count
        == report.total_recommendations
    )


# ============================================================================
# Low confidence
# ============================================================================


def test_low_confidence_issue_is_flagged_and_ranked_lower(engine):
    sure = engine.generate(
        make_report(
            make_issue(
                "IMP_DUPLICATE_SKILLS", ImprovementCategory.SKILL_VISIBILITY, confidence=0.95
            )
        )
    )
    unsure = engine.generate(
        make_report(
            make_issue("IMP_DUPLICATE_SKILLS", ImprovementCategory.SKILL_VISIBILITY, confidence=0.4)
        )
    )
    s, u = sure.recommendations[0], unsure.recommendations[0]
    assert u.low_confidence is True and s.low_confidence is False
    assert "low confidence" in u.description
    assert u.priority_score < s.priority_score


# ============================================================================
# Evidence-specific advice using the real Module A-D chain
# ============================================================================

WEAK_RESUME = """Ravi Kumar
ravi.kumar@gmail.com | +91 98765 43210

EDUCATION
B.Tech in Computer Engineering, Nirma University, 2022 - 2026, CGPA 7.9/10

SKILLS
Python, Java

PROJECTS
Chat App
- Worked on a chat application using modern technologies.
Weather Dashboard
- Responsible for the frontend.

EXPERIENCE
Web Developer Intern
Acme Technologies | May 2025 - Jul 2025
- Worked on the company website.
"""


@pytest.fixture(scope="module")
def chain():
    from app.nlp.content import analyze_content_quality
    from app.nlp.formatting import analyze_formatting
    from app.nlp.improvement import detect_improvement_areas
    from app.nlp.pipeline import ResumeNLPPipeline
    from app.nlp.scoring import score_resume

    profile = ResumeNLPPipeline().process(WEAK_RESUME, "weak.txt")
    fmt = analyze_formatting(WEAK_RESUME, profile=profile)
    score = score_resume(profile, raw_text=WEAK_RESUME, formatting_result=fmt)
    content = analyze_content_quality(profile)
    issues = detect_improvement_areas(profile, score, fmt, content, raw_text=WEAK_RESUME)
    recs = generate_recommendations(issues, score, content, fmt, profile)
    return profile, score, content, issues, recs


def test_weak_projects_are_named(chain):
    *_, recs = chain
    rec = next(
        r for r in recs.recommendations if r.recommendation_id == "REC_IMPROVE_PROJECT_DESCRIPTIONS"
    )
    assert "'Chat App'" in rec.description
    assert any("Chat App" in e for e in rec.evidence)


def test_passive_bullets_are_quoted(chain):
    *_, recs = chain
    rec = next(r for r in recs.recommendations if r.recommendation_id == "REC_USE_ACTION_VERBS")
    assert any("Worked on" in e or "Responsible for" in e for e in rec.evidence)


def test_experience_outcome_recommendation(chain):
    *_, recs = chain
    rec = next(r for r in recs.recommendations if r.recommendation_id == "REC_EXPERIENCE_OUTCOMES")
    assert rec.category == RecommendationCategory.EXPERIENCE
    assert rec.related_issue_id == "IMP_LACK_OF_MEASURABLE_IMPACT"
    assert "Web Developer Intern" in rec.description


def test_potential_gain_never_exceeds_lost_points(chain):
    _, score, _, _, recs = chain
    lost = 100.0 - score.overall_score
    for rec in recs.recommendations:
        if rec.potential_score_gain is not None:
            assert 0 < rec.potential_score_gain <= lost


def test_no_invented_content(chain):
    """Recommendations must not name skills, certifications or numbers absent from the resume."""
    profile, *_, recs = chain
    resume_skills = {s.canonical_name.lower() for s in profile.technical_skills}
    known_tech = {
        "react",
        "docker",
        "aws",
        "kubernetes",
        "tensorflow",
        "django",
        "node.js",
        "mongodb",
        "sql",
    }
    for rec in recs.recommendations:
        text = " ".join([rec.description, rec.suggested_action, *rec.action_steps]).lower()
        for tech in known_tech - resume_skills:
            assert not re.search(rf"\b{re.escape(tech)}\b", text), (
                f"{rec.recommendation_id} suggests {tech}"
            )
        assert "certif" not in text or rec.category != RecommendationCategory.SKILLS
        # numbers only appear as formatting examples, never as claims about the student
        assert not re.search(r"(improved|increased|reduced)[^.]*\d+\s*%", text), (
            rec.recommendation_id
        )


def test_used_skills_not_listed_are_surfaced_without_inventing():
    from app.nlp.pipeline import ResumeNLPPipeline

    text = (
        "A Student\na@b.com | 9876543210\n\nSKILLS\nPython\n\nPROJECTS\n"
        "Inventory Tracker | Spring Boot, MySQL\n- Built inventory APIs.\n"
    )
    profile = ResumeNLPPipeline().process(text, "x.txt")
    issue = make_issue(
        "IMP_LOW_SKILL_INVENTORY", ImprovementCategory.SKILL_VISIBILITY, section="technical_skills"
    )
    rec = generate_recommendations(make_report(issue), profile=profile).recommendations[0]
    joined = " ".join(rec.action_steps)
    assert "MySQL" in joined and "Spring Boot" in joined
    assert "Python" not in joined.split("Skills section:")[-1]


# ============================================================================
# Edge cases
# ============================================================================


def test_empty_report(engine):
    report = engine.generate(make_report())
    assert report.total_recommendations == 0
    assert report.recommendations == []
    assert report.unmapped_issue_ids == []


def test_none_report(engine):
    assert engine.generate(None).total_recommendations == 0


def test_unknown_issue_uses_fallback_but_stays_mapped(engine):
    report = engine.generate(make_report(make_issue("IMP_SOMETHING_NEW")))
    rec = report.recommendations[0]
    assert rec.rule_id == GENERIC_FALLBACK_RULE_ID
    assert rec.related_issue_id == "IMP_SOMETHING_NEW"
    assert report.unmapped_issue_ids == ["IMP_SOMETHING_NEW"]


def test_report_serializes(engine):
    report = engine.generate(make_report(make_issue("IMP_WEAK_PROJECT_DESCRIPTION")))
    again = type(report).model_validate_json(report.model_dump_json())
    assert again == report
