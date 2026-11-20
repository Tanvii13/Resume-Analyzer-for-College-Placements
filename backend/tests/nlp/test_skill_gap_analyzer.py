"""
Unit tests for Sprint 4 – Module D: Skill Gap Analysis (US-13).

Covers:
- Required / preferred / soft skills reported separately (US-13 AC 1, 2)
- Matched vs partial (related) vs missing (US-13 AC 3)
- Either-or requirements ("Python or Java") satisfied by one alternative
- Skills only mentioned in responsibilities are flagged and down-ranked
- Importance ranking and collapsing of unmet either-or groups
- Alternative-aware coverage figures
- Visibility tips for skills used in projects but not listed
- Eligibility: CGPA (with scale conversion), batch, branch aliases, degree, backlogs, unknowns
- Experience gap for roles that need years of full-time experience
- Advice never claims the student already has a missing skill
"""

from pathlib import Path

import pytest
from app.nlp import ResumeNLPPipeline
from app.nlp.job_matching import ResumeJobMatcher, parse_job_description
from app.nlp.job_matching.schemas import (
    EducationRequirement,
    EligibilityCriteria,
    ExperienceRequirement,
    JobSkillRequirement,
    ParsedJobDescription,
)
from app.nlp.job_matching.skill_gap_analyzer import (
    SkillGapAnalyzer,
    branch_key,
    main_degree,
)
from app.nlp.job_matching.skill_gap_schemas import (
    EligibilityStatus,
    GapImportance,
    SkillGapStatus,
    SkillRequirementLevel,
)

FIX = Path(__file__).parent / "fixtures"


def skill(name, required=True, evidence=None, occurrences=1, category="Programming Languages", conf=1.0):
    return JobSkillRequirement(canonical_name=name, matched_alias=name, category=category, is_required=required,
                               confidence=conf, occurrences=occurrences, evidence=evidence or f"- {name}")


def job(required=(), preferred=(), soft=(), responsibilities=(), **kw):
    return ParsedJobDescription(
        job_id=kw.pop("job_id", "test-job"),
        title=kw.pop("title", "Test Role"),
        required_technical_skills=list(required),
        preferred_technical_skills=list(preferred),
        soft_skills=list(soft),
        responsibilities=list(responsibilities),
        **kw,
    )


RESUME = """Asha Verma
asha.verma@gmail.com | +91 98765 43210 | github.com/ashav

EDUCATION
B.Tech in Information and Communication Technology, DA-IICT, 2022 - 2026, CPI 8.4/10

TECHNICAL SKILLS
Languages: Python, SQL, JavaScript
Frameworks: Flask
Tools: Git

PROJECTS
Inventory Tracker | Flask, PostgreSQL, Docker
- Built inventory REST APIs with Flask and PostgreSQL.
- Containerised the service with Docker.
"""


@pytest.fixture(scope="module")
def profile():
    return ResumeNLPPipeline().process(RESUME, "asha.txt")


@pytest.fixture(scope="module")
def analyze():
    matcher, analyzer = ResumeJobMatcher(), SkillGapAnalyzer()

    def run(profile, parsed):
        return analyzer.analyze(profile, parsed, matcher.match(profile, parsed))

    return run


# ============================================================================
# Separation and categories
# ============================================================================

def test_required_preferred_and_soft_are_separate(profile, analyze):
    rep = analyze(profile, job(
        required=[skill("Python"), skill("Java")],
        preferred=[skill("Docker", required=False, category="DevOps"), skill("Kubernetes", required=False, category="DevOps")],
        soft=[skill("Teamwork", category="Soft Skills")],
    ))
    assert [i.skill for i in rep.matched_required] == ["Python"]
    assert [i.skill for i in rep.missing_required] == ["Java"]
    assert {i.skill for i in rep.matched_preferred} == {"Docker"}
    assert {i.level for i in rep.soft_skills} == {SkillRequirementLevel.SOFT_SKILL}
    for i in rep.matched_required + rep.missing_required:
        assert i.level == SkillRequirementLevel.REQUIRED
    for i in rep.matched_preferred + rep.missing_preferred:
        assert i.level == SkillRequirementLevel.PREFERRED


def test_matched_items_carry_resume_evidence(profile, analyze):
    rep = analyze(profile, job(required=[skill("Python"), skill("Docker", category="DevOps")]))
    by = {i.skill: i for i in rep.matched_required}
    assert by["Python"].listed_in_skills_section is True
    assert by["Python"].candidate_evidence
    assert by["Docker"].evidence_source != "explicit_skills_section"
    assert by["Docker"].listed_in_skills_section is False


def test_skill_used_but_not_listed_gives_visibility_tip(profile, analyze):
    rep = analyze(profile, job(required=[skill("Docker", category="DevOps")]))
    assert any("Docker" in t and "Skills section" in t for t in rep.visibility_tips)
    assert "Skills section" in rep.matched_required[0].how_to_improve


def test_related_skill_is_partial_not_missing(profile, analyze):
    rep = analyze(profile, job(required=[skill("Django", category="Backend Development")]))
    assert [i.skill for i in rep.partial_required] == ["Django"]
    item = rep.partial_required[0]
    assert item.status == SkillGapStatus.PARTIAL
    assert item.candidate_evidence  # e.g. Python / Flask
    assert "related" in item.explanation


# ============================================================================
# Either-or requirements
# ============================================================================

def test_either_or_group_satisfied_by_alternative(profile, analyze):
    line = "- Strong programming skills in Python or Java"
    rep = analyze(profile, job(required=[skill("Python", evidence=line), skill("Java", evidence=line)]))
    statuses = {i.skill: i.status for i in rep.matched_required}
    assert statuses == {"Python": SkillGapStatus.MATCHED, "Java": SkillGapStatus.SATISFIED_BY_ALTERNATIVE}
    assert rep.missing_required == []
    assert rep.coverage.required_total == 1 and rep.coverage.required_coverage == 1.0
    group = rep.alternative_groups[0]
    assert group.satisfied and group.satisfied_by == ["Python"]


def test_unmet_either_or_group_counts_once_in_priority(profile, analyze):
    line = "- Experience with Go or Rust"
    rep = analyze(profile, job(required=[skill("Go", evidence=line), skill("Rust", evidence=line), skill("Python")]))
    assert {i.skill for i in rep.missing_required} == {"Go", "Rust"}
    group_items = [g for g in rep.priority_gaps if g.alternative_group_id]
    assert len(group_items) == 1
    assert "Any one of" in group_items[0].how_to_improve
    assert rep.coverage.required_total == 2 and rep.coverage.required_coverage == 0.5


def test_comma_list_is_not_an_either_or_group(profile, analyze):
    line = "- Python, Java and Go"
    rep = analyze(profile, job(required=[skill("Python", evidence=line), skill("Java", evidence=line)]))
    assert rep.alternative_groups == []
    assert [i.skill for i in rep.missing_required] == ["Java"]


# ============================================================================
# Importance
# ============================================================================

def test_responsibilities_only_skill_is_flagged_and_down_ranked(profile, analyze):
    resp = "Work with product and QA teams to ship features."
    rep = analyze(profile, job(
        required=[skill("Rust"), skill("Quality Assurance", evidence=f"- {resp}", category="Testing & QA")],
        responsibilities=[resp],
    ))
    qa = next(i for i in rep.missing_required if i.skill == "Quality Assurance")
    k8s = next(i for i in rep.missing_required if i.skill == "Rust")
    assert qa.from_responsibilities_only and not k8s.from_responsibilities_only
    assert qa.importance_score < k8s.importance_score
    assert k8s.importance == GapImportance.CRITICAL and qa.importance != GapImportance.CRITICAL
    assert rep.priority_gaps[0].skill == "Rust"
    assert rep.warnings


def test_required_outranks_preferred_and_strong_wording_boosts(profile, analyze):
    rep = analyze(profile, job(
        required=[skill("Java", evidence="- Strong knowledge of Java"), skill("Kotlin")],
        preferred=[skill("Kubernetes", required=False, category="DevOps")],
    ))
    order = [g.skill for g in rep.priority_gaps]
    assert order.index("Java") < order.index("Kotlin") < order.index("Kubernetes")


def test_advice_never_claims_missing_skill(profile, analyze):
    rep = analyze(profile, job(required=[skill("Kotlin"), skill("Go")], preferred=[skill("Rust", required=False)]))
    for g in rep.priority_gaps:
        assert g.how_to_improve
        assert "only once you have actually used it" in g.how_to_improve or g.level != SkillRequirementLevel.REQUIRED
        assert "you have experience with " + g.skill.lower() not in g.how_to_improve.lower()


# ============================================================================
# Eligibility
# ============================================================================

@pytest.mark.parametrize("name, key", [
    ("Computer Science and Engineering", "cse"), ("CSE", "cse"), ("Computer Science", "cse"),
    ("Information and Communication Technology", "ict"), ("ICT", "ict"),
    ("Electronics and Communication Engineering", "ece"), ("ECE", "ece"), ("Information Technology", "it"),
])
def test_branch_aliases(name, key):
    assert branch_key(name) == key


def test_eligibility_all_met(profile, analyze):
    rep = analyze(profile, job(
        required=[skill("Python")],
        eligibility=EligibilityCriteria(min_cgpa=7.0, cgpa_scale=10.0, allowed_branches=["Computer Science", "ICT"],
                                        allowed_batches=[2026, 2027]),
        education=EducationRequirement(degrees=["B.Tech", "B.E."], degree_levels=["bachelors"]),
    ))
    status = {c.criterion: c.status for c in rep.eligibility_checks}
    assert status == {"cgpa": EligibilityStatus.MET, "graduation_batch": EligibilityStatus.MET,
                      "branch": EligibilityStatus.MET, "degree": EligibilityStatus.MET}
    assert rep.eligibility_status == EligibilityStatus.MET


def test_eligibility_not_met_cgpa_batch_branch(profile, analyze):
    rep = analyze(profile, job(
        required=[skill("Python")],
        eligibility=EligibilityCriteria(min_cgpa=9.0, cgpa_scale=10.0, allowed_branches=["Mechanical Engineering"],
                                        allowed_batches=[2027]),
    ))
    failed = {c.criterion for c in rep.eligibility_checks if c.status == EligibilityStatus.NOT_MET}
    assert failed == {"cgpa", "graduation_batch", "branch"}
    assert rep.eligibility_status == EligibilityStatus.NOT_MET
    assert "eligibility" in rep.summary


def test_cgpa_scale_conversion(profile, analyze):
    rep = analyze(profile, job(required=[skill("Python")],
                               eligibility=EligibilityCriteria(min_cgpa=3.2, cgpa_scale=4.0)))
    assert rep.eligibility_checks[0].status == EligibilityStatus.MET  # 8.4/10 = 3.36/4


def test_missing_resume_data_is_unknown_not_failed(analyze):
    p = ResumeNLPPipeline().process("Rahul\nrahul@gmail.com\n\nEDUCATION\nB.Tech\n\nSKILLS\nPython\n", "r.txt")
    rep = analyze(p, job(required=[skill("Python")],
                         eligibility=EligibilityCriteria(min_cgpa=7.0, cgpa_scale=10.0, allowed_batches=[2026],
                                                         backlog_policy="No active backlogs")))
    status = {c.criterion: c.status for c in rep.eligibility_checks}
    assert status["cgpa"] == EligibilityStatus.UNKNOWN
    assert status["graduation_batch"] == EligibilityStatus.UNKNOWN
    assert status["backlogs"] == EligibilityStatus.UNKNOWN
    assert rep.eligibility_status == EligibilityStatus.UNKNOWN


def test_non_branch_field_values_are_ignored(profile, analyze):
    """The JD parser can put skill words like 'Statistics' into fields_of_study."""
    rep = analyze(profile, job(required=[skill("Python")], education=EducationRequirement(fields_of_study=["Statistics"])))
    assert "branch" not in {c.criterion for c in rep.eligibility_checks}


def test_any_branch_skips_branch_check(profile, analyze):
    rep = analyze(profile, job(required=[skill("Python")], eligibility=EligibilityCriteria(
        allowed_branches=["Mechanical Engineering"], raw_criteria=["- B.Tech in any branch"])))
    assert "branch" not in {c.criterion for c in rep.eligibility_checks}


def test_main_degree_ignores_school(profile):
    assert main_degree(profile).degree == "B.Tech"


# ============================================================================
# Experience, coverage edge cases, real JD
# ============================================================================

def test_experience_gap_for_senior_role(profile, analyze):
    rep = analyze(profile, job(required=[skill("Python")],
                               experience=ExperienceRequirement(min_years=2.0, is_fresher_eligible=False)))
    assert rep.experience_gap and "2 years" in rep.experience_gap
    fresher = analyze(profile, job(required=[skill("Python")], experience=ExperienceRequirement(is_fresher_eligible=True)))
    assert fresher.experience_gap is None


def test_job_without_skills(profile, analyze):
    rep = analyze(profile, job())
    assert rep.priority_gaps == [] and rep.coverage.required_total == 0
    assert "does not list required" in rep.summary


def test_real_jd_end_to_end(profile, analyze):
    parsed = parse_job_description((FIX / "sprint4" / "jobs" / "j01_backend_intern.txt").read_text(encoding="utf-8"))
    rep = analyze(profile, parsed)
    groups = {tuple(sorted(g.skills)) for g in rep.alternative_groups}
    assert ("Java", "Python") in groups
    assert next(i for i in rep.matched_required if i.skill == "Java").status == SkillGapStatus.SATISFIED_BY_ALTERNATIVE
    qa = [i for i in rep.missing_required if i.skill == "Quality Assurance"]
    assert qa and qa[0].from_responsibilities_only
    assert rep.eligibility_status == EligibilityStatus.MET  # backlog rule is advisory, not part of the verdict
    assert next(c for c in rep.eligibility_checks if c.criterion == "backlogs").status == EligibilityStatus.UNKNOWN
    assert {c.criterion for c in rep.eligibility_checks if c.status == EligibilityStatus.MET} == {
        "cgpa", "graduation_batch", "branch", "degree"}


def test_deterministic(profile, analyze):
    parsed = parse_job_description((FIX / "sprint4" / "jobs" / "j06_devops_intern.txt").read_text(encoding="utf-8"))
    assert analyze(profile, parsed).model_dump() == analyze(profile, parsed).model_dump()
