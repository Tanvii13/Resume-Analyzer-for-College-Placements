"""
Unit Tests for Skill Normalization and Equivalence Engine.

Sprint 4 Module B (NLP-JobMatching).

Covers:
- Exact matches (canonical and verbatim)
- Aliases (alternative spellings, framework variants)
- Abbreviations (JS, K8s, TS, AWS, etc.)
- Explicit equivalences (MariaDB <=> MySQL, OpenSearch <=> Elasticsearch)
- Related but non-equivalent skills (Docker <=> Kubernetes, React <=> Redux, Python != JavaScript)
- Prerequisite relationships (Python -> Django, JavaScript -> React, SQL -> PostgreSQL)
- Unknown / uncanonical skills
- Ambiguous short names (C, Go, R vs Vitamin C, Grade C, Go to)
- Case variations (lower, upper, mixed)
- Punctuation & bullet variations (react-js, node-js, ci-cd, - Python, (AWS))
- Technical symbols (C++, C#, .NET, Node.js, CI/CD)
- Duplicate skills deduplication in comparisons
- False-positive prevention (Java vs JavaScript, Rust vs Trust)
- Runtime rule registration
- CandidateProfile SkillItem and JobSkillRequirement integration
"""

import pytest
from app.nlp.job_matching.schemas import JobSkillRequirement
from app.nlp.job_matching.skill_engine import (
    SkillEquivalenceEngine,
    SkillNormalizer,
)
from app.nlp.job_matching.skill_normalization_schemas import (
    EquivalenceRule,
    SkillMatchMethod,
    SkillRelationshipType,
)
from app.nlp.schemas import SkillItem


@pytest.fixture
def normalizer():
    return SkillNormalizer()


@pytest.fixture
def engine(normalizer):
    return SkillEquivalenceEngine(normalizer)


# ============================================================================
# 1. Exact Canonical Matches
# ============================================================================

def test_exact_canonical_match(normalizer):
    """Verbatim canonical skill names match with EXACT_CANONICAL and confidence 1.0."""
    res = normalizer.normalize_skill("Python")
    assert res.is_recognized is True
    assert res.canonical_name == "Python"
    assert res.category == "Programming Languages"
    assert res.match_method == SkillMatchMethod.EXACT_CANONICAL
    assert res.confidence == 1.0

    res_k8s = normalizer.normalize_skill("Kubernetes")
    assert res_k8s.is_recognized is True
    assert res_k8s.canonical_name == "Kubernetes"
    assert res_k8s.category == "DevOps"
    assert res_k8s.match_method == SkillMatchMethod.EXACT_CANONICAL


def test_exact_canonical_evaluation(engine):
    """Identical canonical skills evaluate to EXACT_MATCH with score 1.0."""
    eval_res = engine.evaluate_equivalence("Python", "Python")
    assert eval_res.is_equivalent is True
    assert eval_res.is_related is False
    assert eval_res.relationship_type == SkillRelationshipType.EXACT_MATCH
    assert eval_res.similarity_score == 1.0
    assert eval_res.confidence == 1.0

    eval_pytorch = engine.evaluate_equivalence("PyTorch", "PyTorch")
    assert eval_pytorch.is_equivalent is True
    assert eval_pytorch.relationship_type == SkillRelationshipType.EXACT_MATCH
    assert eval_pytorch.similarity_score == 1.0


# ============================================================================
# 2. Alias Matches
# ============================================================================

def test_alias_matches(normalizer):
    """Standard naming aliases resolve to canonical skills."""
    # Postgres -> PostgreSQL
    res_pg = normalizer.normalize_skill("Postgres")
    assert res_pg.is_recognized is True
    assert res_pg.canonical_name == "PostgreSQL"
    assert res_pg.matched_alias == "Postgres"
    assert res_pg.match_method == SkillMatchMethod.ALIAS
    assert res_pg.confidence == 1.0

    # React.js -> React
    res_react = normalizer.normalize_skill("React.js")
    assert res_react.is_recognized is True
    assert res_react.canonical_name == "React"
    assert res_react.matched_alias == "React.js"
    assert res_react.confidence == 1.0

    # golang -> Go
    res_go = normalizer.normalize_skill("golang")
    assert res_go.is_recognized is True
    assert res_go.canonical_name == "Go"

    # nodejs -> Node.js
    res_node = normalizer.normalize_skill("nodejs")
    assert res_node.is_recognized is True
    assert res_node.canonical_name == "Node.js"


def test_alias_equivalence_evaluation(engine):
    """Skills matching through aliases evaluate to EXACT_ALIAS with score 1.0."""
    eval_pg = engine.evaluate_equivalence("Postgres", "PostgreSQL")
    assert eval_pg.is_equivalent is True
    assert eval_pg.relationship_type == SkillRelationshipType.EXACT_ALIAS
    assert eval_pg.similarity_score == 1.0
    assert eval_pg.canonical_a == "PostgreSQL"
    assert eval_pg.canonical_b == "PostgreSQL"

    eval_react = engine.evaluate_equivalence("React.js", "React")
    assert eval_react.is_equivalent is True
    assert eval_react.relationship_type == SkillRelationshipType.EXACT_ALIAS
    assert eval_react.similarity_score == 1.0


# ============================================================================
# 3. Abbreviations and Acronyms
# ============================================================================

def test_abbreviation_matches(normalizer):
    """Short acronyms and abbreviations resolve with ABBREVIATION match method."""
    # JS -> JavaScript
    res_js = normalizer.normalize_skill("JS")
    assert res_js.is_recognized is True
    assert res_js.canonical_name == "JavaScript"
    assert res_js.match_method == SkillMatchMethod.ABBREVIATION
    assert res_js.confidence == 1.0

    # K8s -> Kubernetes
    res_k8s = normalizer.normalize_skill("K8s")
    assert res_k8s.is_recognized is True
    assert res_k8s.canonical_name == "Kubernetes"
    assert res_k8s.match_method == SkillMatchMethod.ABBREVIATION
    assert res_k8s.confidence == 1.0

    # TS -> TypeScript
    res_ts = normalizer.normalize_skill("TS")
    assert res_ts.is_recognized is True
    assert res_ts.canonical_name == "TypeScript"
    assert res_ts.match_method == SkillMatchMethod.ABBREVIATION

    # AWS -> Amazon Web Services (AWS)
    res_aws = normalizer.normalize_skill("AWS")
    assert res_aws.is_recognized is True
    assert res_aws.canonical_name == "Amazon Web Services (AWS)"
    assert res_aws.match_method == SkillMatchMethod.ABBREVIATION


def test_abbreviation_equivalence(engine):
    """Abbreviation and canonical skill pair evaluates to EXACT_ALIAS with score 1.0."""
    eval_js = engine.evaluate_equivalence("JS", "JavaScript")
    assert eval_js.is_equivalent is True
    assert eval_js.relationship_type == SkillRelationshipType.EXACT_ALIAS
    assert eval_js.similarity_score == 1.0

    eval_k8s = engine.evaluate_equivalence("K8s", "Kubernetes")
    assert eval_k8s.is_equivalent is True
    assert eval_k8s.relationship_type == SkillRelationshipType.EXACT_ALIAS
    assert eval_k8s.similarity_score == 1.0


# ============================================================================
# 4. Explicitly Configured Equivalences
# ============================================================================

def test_explicit_equivalences(engine):
    """Explicitly configured equivalent technologies evaluate to EQUIVALENT."""
    # MariaDB <=> MySQL
    eval_maria = engine.evaluate_equivalence("MariaDB", "MySQL")
    assert eval_maria.is_equivalent is True
    assert eval_maria.is_related is False
    assert eval_maria.relationship_type == SkillRelationshipType.EQUIVALENT
    assert eval_maria.similarity_score == 0.95
    assert "MariaDB is a drop-in binary-compatible" in eval_maria.rationale

    # Symmetry check
    eval_maria_rev = engine.evaluate_equivalence("MySQL", "MariaDB")
    assert eval_maria_rev.is_equivalent is True
    assert eval_maria_rev.relationship_type == SkillRelationshipType.EQUIVALENT
    assert eval_maria_rev.similarity_score == 0.95

    # OpenSearch <=> Elasticsearch
    eval_os = engine.evaluate_equivalence("OpenSearch", "Elasticsearch")
    assert eval_os.is_equivalent is True
    assert eval_os.relationship_type == SkillRelationshipType.EQUIVALENT
    assert eval_os.similarity_score == 0.95


def test_query_equivalent_skills(engine):
    """Engine queries list of configured equivalent skills."""
    equivs = engine.get_equivalent_skills("MySQL")
    assert "MariaDB" in equivs

    equivs_k8s = engine.get_equivalent_skills("Kubernetes")
    assert "K8s" in equivs_k8s


# ============================================================================
# 5. Related but Non-Equivalent Skills
# ============================================================================

def test_related_skills_are_not_equivalent(engine):
    """Related ecosystem companions are classified as RELATED, not EQUIVALENT."""
    # Docker <=> Kubernetes
    eval_dk = engine.evaluate_equivalence("Docker", "Kubernetes")
    assert eval_dk.is_equivalent is False
    assert eval_dk.is_related is True
    assert eval_dk.relationship_type in {
        SkillRelationshipType.RELATED,
        SkillRelationshipType.PREREQUISITE,
    }
    assert eval_dk.similarity_score >= 0.70

    # React <=> Redux
    eval_rr = engine.evaluate_equivalence("React", "Redux")
    assert eval_rr.is_equivalent is False
    assert eval_rr.is_related is True
    assert eval_rr.relationship_type == SkillRelationshipType.RELATED
    assert eval_rr.similarity_score == 0.70

    # FastAPI <=> Pydantic
    eval_fp = engine.evaluate_equivalence("FastAPI", "Pydantic")
    assert eval_fp.is_equivalent is False
    assert eval_fp.is_related is True
    assert eval_fp.relationship_type == SkillRelationshipType.RELATED
    assert eval_fp.similarity_score == 0.75

    # PyTorch <=> TensorFlow
    eval_pt = engine.evaluate_equivalence("PyTorch", "TensorFlow")
    assert eval_pt.is_equivalent is False
    assert eval_pt.is_related is True
    assert eval_pt.relationship_type == SkillRelationshipType.RELATED


def test_unrelated_skills_same_category(engine):
    """
    CRITICAL INVARIANT: Python and JavaScript are both Programming Languages,
    but they are strictly UNRELATED without a configured rule.
    """
    eval_py_js = engine.evaluate_equivalence("Python", "JavaScript")
    assert eval_py_js.is_equivalent is False
    assert eval_py_js.is_related is False
    assert eval_py_js.relationship_type == SkillRelationshipType.UNRELATED
    assert eval_py_js.similarity_score == 0.0

    eval_cpp_java = engine.evaluate_equivalence("C++", "Java")
    assert eval_cpp_java.is_equivalent is False
    assert eval_cpp_java.relationship_type == SkillRelationshipType.UNRELATED
    assert eval_cpp_java.similarity_score == 0.0


# ============================================================================
# 6. Prerequisite Relationships
# ============================================================================

def test_prerequisite_relationships(engine):
    """Prerequisites are recognized as foundational dependencies, not exact matches."""
    # Python -> Django
    eval_pd = engine.evaluate_equivalence("Python", "Django")
    assert eval_pd.is_equivalent is False
    assert eval_pd.is_related is True
    assert eval_pd.relationship_type == SkillRelationshipType.PREREQUISITE
    assert eval_pd.similarity_score == 0.75
    assert "foundational prerequisite" in eval_pd.rationale

    # JavaScript -> React
    eval_jr = engine.evaluate_equivalence("JavaScript", "React")
    assert eval_jr.is_equivalent is False
    assert eval_jr.is_related is True
    assert eval_jr.relationship_type == SkillRelationshipType.PREREQUISITE
    assert eval_jr.similarity_score == 0.75

    # SQL -> PostgreSQL
    eval_sp = engine.evaluate_equivalence("SQL", "PostgreSQL")
    assert eval_sp.is_equivalent is False
    assert eval_sp.is_related is True
    assert eval_sp.relationship_type == SkillRelationshipType.PREREQUISITE
    assert eval_sp.similarity_score == 0.80


def test_query_prerequisites_and_dependents(engine):
    """Engine queries prerequisites and dependent skills."""
    prereqs_django = engine.get_prerequisites("Django")
    assert "Python" in prereqs_django

    dependents_py = engine.get_dependents("Python")
    assert "Django" in dependents_py
    assert "FastAPI" in dependents_py


# ============================================================================
# 7. Unknown & Uncanonical Skills
# ============================================================================

def test_unknown_skills(normalizer, engine):
    """Unrecognized skills are safely parsed with 0.0 confidence."""
    res = normalizer.normalize_skill("QuantumFlapdoodle123")
    assert res.is_recognized is False
    assert res.canonical_name is None
    assert res.match_method == SkillMatchMethod.UNRECOGNIZED
    assert res.confidence == 0.0
    assert res.raw_mention == "QuantumFlapdoodle123"

    # Empty inputs
    res_empty = normalizer.normalize_skill("")
    assert res_empty.is_recognized is False
    assert res_empty.confidence == 0.0

    res_spaces = normalizer.normalize_skill("     ")
    assert res_spaces.is_recognized is False
    assert res_spaces.confidence == 0.0

    # Unknown vs known skill in equivalence engine
    eval_unk = engine.evaluate_equivalence("QuantumFlapdoodle123", "Python")
    assert eval_unk.is_equivalent is False
    assert eval_unk.relationship_type == SkillRelationshipType.UNRELATED
    assert eval_unk.similarity_score == 0.0

    # Two identical unknown skills evaluate to verbatim match
    eval_same_unk = engine.evaluate_equivalence("InHouseInternalTool", "InHouseInternalTool")
    assert eval_same_unk.is_equivalent is True
    assert eval_same_unk.relationship_type == SkillRelationshipType.EXACT_MATCH
    assert eval_same_unk.similarity_score == 1.0


# ============================================================================
# 8. Ambiguous Short Names & Context Protection
# ============================================================================

def test_ambiguous_short_names(normalizer):
    """
    Standalone single letters / words resolve to canonical programming languages,
    while non-technical phrases are rejected.
    """
    # Standalone programming languages
    assert normalizer.normalize_skill("C").is_recognized is True
    assert normalizer.normalize_skill("C").canonical_name == "C"

    assert normalizer.normalize_skill("Go").is_recognized is True
    assert normalizer.normalize_skill("Go").canonical_name == "Go"

    assert normalizer.normalize_skill("R").is_recognized is True
    assert normalizer.normalize_skill("R").canonical_name == "R"

    # Non-technical phrases falsely mentioning C
    assert normalizer.normalize_skill("Vitamin C").is_recognized is False
    assert normalizer.normalize_skill("Grade C").is_recognized is False
    assert normalizer.normalize_skill("Section C").is_recognized is False
    assert normalizer.normalize_skill("Schedule C").is_recognized is False

    # English phrases falsely mentioning Go
    assert normalizer.normalize_skill("Go to").is_recognized is False
    assert normalizer.normalize_skill("Go ahead").is_recognized is False
    assert normalizer.normalize_skill("Go back").is_recognized is False


# ============================================================================
# 9. Case Variations
# ============================================================================

def test_case_insensitivity(normalizer, engine):
    """Skills in any casing normalize to canonical capitalization."""
    for variant in ["python", "PYTHON", "PyThOn", "pYtHoN"]:
        norm = normalizer.normalize_skill(variant)
        assert norm.is_recognized is True
        assert norm.canonical_name == "Python"
        assert norm.confidence == 1.0

    for variant in ["k8s", "K8S", "K8s"]:
        norm = normalizer.normalize_skill(variant)
        assert norm.is_recognized is True
        assert norm.canonical_name == "Kubernetes"

    eval_case = engine.evaluate_equivalence("python", "PYTHON")
    assert eval_case.is_equivalent is True
    assert eval_case.relationship_type == SkillRelationshipType.EXACT_MATCH


# ============================================================================
# 10. Punctuation & Bullets Normalization
# ============================================================================

def test_punctuation_and_bullets(normalizer):
    """Bullets, brackets, and punctuation variations are safely stripped/normalized."""
    # Leading bullets and numbering
    assert normalizer.normalize_skill("- Python").canonical_name == "Python"
    assert normalizer.normalize_skill("• Docker").canonical_name == "Docker"
    assert normalizer.normalize_skill("1. Kubernetes").canonical_name == "Kubernetes"
    assert normalizer.normalize_skill("- .NET").canonical_name == ".NET"

    # Surrounding brackets & quotes
    assert normalizer.normalize_skill("(AWS)").canonical_name == "Amazon Web Services (AWS)"
    assert normalizer.normalize_skill("[Docker]").canonical_name == "Docker"
    assert normalizer.normalize_skill("'Python'").canonical_name == "Python"
    assert normalizer.normalize_skill('"PostgreSQL"').canonical_name == "PostgreSQL"

    # Trailing punctuation
    assert normalizer.normalize_skill("Python,").canonical_name == "Python"
    assert normalizer.normalize_skill("Java;").canonical_name == "Java"
    assert normalizer.normalize_skill("Docker!").canonical_name == "Docker"

    # Hyphen & underscore variations
    assert normalizer.normalize_skill("react-js").canonical_name == "React"
    assert normalizer.normalize_skill("node-js").canonical_name == "Node.js"
    assert normalizer.normalize_skill("ci - cd").canonical_name == "CI/CD"
    assert normalizer.normalize_skill("ci-cd").canonical_name == "CI/CD"


# ============================================================================
# 11. Technical Symbols Preservation
# ============================================================================

def test_technical_symbols_preservation(normalizer):
    """Technical symbols (C++, C#, .NET, Node.js, CI/CD) are preserved without damage."""
    # C++
    res_cpp = normalizer.normalize_skill("C++")
    assert res_cpp.is_recognized is True
    assert res_cpp.canonical_name == "C++"
    assert res_cpp.category == "Programming Languages"

    # C#
    res_cs = normalizer.normalize_skill("C#")
    assert res_cs.is_recognized is True
    assert res_cs.canonical_name == "C#"
    assert res_cs.category == "Programming Languages"

    # .NET
    res_dotnet = normalizer.normalize_skill(".NET")
    assert res_dotnet.is_recognized is True
    assert res_dotnet.canonical_name == ".NET"

    # Node.js
    res_node = normalizer.normalize_skill("Node.js")
    assert res_node.is_recognized is True
    assert res_node.canonical_name == "Node.js"

    # CI/CD
    res_cicd = normalizer.normalize_skill("CI/CD")
    assert res_cicd.is_recognized is True
    assert res_cicd.canonical_name == "CI/CD"


# ============================================================================
# 12. False-Positive Prevention
# ============================================================================

def test_false_positive_prevention(normalizer, engine):
    """Substring and partial matches do not bleed into unrelated skills."""
    # Java should NOT match JavaScript
    eval_j_js = engine.evaluate_equivalence("Java", "JavaScript")
    assert eval_j_js.is_equivalent is False
    assert eval_j_js.relationship_type == SkillRelationshipType.UNRELATED

    # "Trust" or "Crust" should not match "Rust"
    assert normalizer.normalize_skill("Trust").is_recognized is False
    assert normalizer.normalize_skill("Crust").is_recognized is False

    # "Google" should not match "Go"
    assert normalizer.normalize_skill("Google").canonical_name != "Go"

    # "Script" alone should not match "JavaScript" or "TypeScript"
    assert normalizer.normalize_skill("Script").is_recognized is False


# ============================================================================
# 13. Runtime Rule Registration
# ============================================================================

def test_runtime_rule_registration(engine):
    """Engine supports registering custom rules dynamically at runtime."""
    custom_rule = EquivalenceRule(
        canonical_skill="CustomFrameworkX",
        equivalent_skill="CFX",
        relationship_type=SkillRelationshipType.EQUIVALENT,
        confidence=0.96,
        bidirectional=True,
        source="unit_test",
        rationale="Custom framework alias test",
        version="1.0.0",
    )
    engine.register_rule(custom_rule)

    eval_custom = engine.evaluate_equivalence("CustomFrameworkX", "CFX")
    assert eval_custom.is_equivalent is True
    assert eval_custom.relationship_type == SkillRelationshipType.EQUIVALENT
    assert eval_custom.similarity_score == 0.96


# ============================================================================
# 14. Skill Set Comparison (Candidate vs Job Requirements)
# ============================================================================

def test_compare_candidate_to_job_skills(engine):
    """SkillSetComparison correctly matches, detects missing, and calculates coverage."""
    candidate = ["Python", "Docker", "PostgreSQL", "Git", "Python"]  # Duplicate Python
    required = ["Python", "Kubernetes", "Postgres"]
    preferred = ["Django", "AWS"]

    comparison = engine.compare_skill_sets(candidate, required, preferred)

    # Candidate skills deduplicated
    assert len(comparison.candidate_skills) == 4

    # Matched required: Python (exact), Postgres (alias to PostgreSQL)
    assert len(comparison.matched_required) == 2
    matched_req_skills = {m.skill_b for m in comparison.matched_required}
    assert "Python" in matched_req_skills
    assert "Postgres" in matched_req_skills

    # Missing required: Kubernetes (candidate has Docker, which is related, not equivalent)
    assert comparison.missing_required == ["Kubernetes"]

    # Related matches: Docker relates to Kubernetes, Python is prerequisite for Django
    assert len(comparison.related_matches) >= 1

    # Missing preferred: AWS (and Django since candidate only has Python prerequisite)
    assert "AWS" in comparison.missing_preferred

    # Coverage calculations
    assert comparison.required_coverage_ratio == pytest.approx(0.667, rel=1e-2)
    assert 0.0 < comparison.overall_coverage_ratio < 1.0


# ============================================================================
# 15. Integration with SkillItem and JobSkillRequirement Models
# ============================================================================

def test_schema_object_integration(engine):
    """Engine directly accepts CandidateProfile SkillItem and JobSkillRequirement objects."""
    candidate_item = SkillItem(
        canonical_name="JavaScript",
        matched_alias="js",
        category="Programming Languages",
        confidence=1.0,
        source_section="skills",
        occurrences=2,
    )

    job_req = JobSkillRequirement(
        canonical_name="React",
        matched_alias="react",
        category="Frontend Development",
        is_required=True,
        confidence=1.0,
    )

    # JavaScript is prerequisite for React
    eval_res = engine.evaluate_equivalence(candidate_item, job_req)
    assert eval_res.is_equivalent is False
    assert eval_res.is_related is True
    assert eval_res.relationship_type == SkillRelationshipType.PREREQUISITE
    assert eval_res.similarity_score == 0.75
