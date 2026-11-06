"""
End-to-end tests for Sprint 2 – Module F: Structured Profile Aggregator (NLP-10).

Each synthetic resume in fixtures/resumes/*.txt has a matching
*.golden.json file listing the fields the pipeline must produce. Golden files
check exact values for contact, education, experience and projects, and use
"_include" / "_exclude" lists for skills so that taxonomy growth in Module E
does not break these tests.

Covers (plan §13 and §16):
- Pipeline runs without exceptions and returns a valid CandidateProfile
- Fixture set: standard table format, fresher with no experience,
  non-standard section order, Diploma + B.E. with full-time job,
  Jake's-template style, sparse resume with empty sections
- Experience vs. internship routing
- Missing fields returned as None / [], never invented
- Serialization to dict and JSON, round-trip validation
- Module failure isolation (one extractor failing gives a partial profile + warning)
- Empty / whitespace input
- Latency target: <= 150 ms per resume after warm-up
"""

from datetime import date
import json
from pathlib import Path
import time

import pytest

from app.nlp import CandidateProfile, NLPProcessingRequest, ResumeNLPPipeline, analyze_resume

FIXTURES = Path(__file__).parent / "fixtures" / "resumes"
RESUME_FILES = sorted(FIXTURES.glob("*.txt"))


@pytest.fixture(scope="module")
def pipeline():
    return ResumeNLPPipeline(today=date(2026, 11, 6))


def load_case(path: Path):
    text = path.read_text(encoding="utf-8")
    golden = json.loads(path.with_suffix(".golden.json").read_text(encoding="utf-8"))
    return text, golden


def assert_subset(actual: dict, expected: dict, where: str):
    for key, value in expected.items():
        assert actual.get(key) == value, f"{where}.{key}: expected {value!r}, got {actual.get(key)!r}"


def test_fixture_set_present():
    assert len(RESUME_FILES) >= 6
    for path in RESUME_FILES:
        assert path.with_suffix(".golden.json").exists(), f"missing golden file for {path.name}"


@pytest.mark.parametrize("path", RESUME_FILES, ids=lambda p: p.stem)
def test_golden_profiles(pipeline, path):
    text, golden = load_case(path)
    profile = pipeline.process(text, path.name)
    data = profile.model_dump()

    assert_subset(data["contact"], golden["contact"], "contact")

    for section in ("education", "experience", "internships"):
        assert len(data[section]) == len(golden[section]), f"{section} count"
        for i, (actual, expected) in enumerate(zip(data[section], golden[section])):
            assert_subset(actual, expected, f"{section}[{i}]")

    assert len(data["projects"]) == len(golden["projects"]), "projects count"
    for i, (actual, expected) in enumerate(zip(data["projects"], golden["projects"])):
        expected = dict(expected)
        tech = expected.pop("technologies_include", [])
        assert_subset(actual, expected, f"projects[{i}]")
        assert set(tech) <= set(actual["technologies"]), f"projects[{i}] technologies"

    tech_names = {s["canonical_name"] for s in data["technical_skills"]}
    soft_names = {s["canonical_name"] for s in data["soft_skills"]}
    assert set(golden["technical_skills_include"]) <= tech_names, tech_names
    assert set(golden.get("soft_skills_include", [])) <= soft_names, soft_names
    for bad in golden["skills_exclude"]:
        assert bad not in tech_names, f"false-positive skill {bad!r}"

    assert data["certifications"] == golden["certifications"]
    assert data["achievements"] == golden["achievements"]
    assert data["section_summary"]["missing_critical_sections"] == golden["missing_critical_sections"]
    assert set(profile.metadata.module_status.values()) == {"ok"}


@pytest.mark.parametrize("path", RESUME_FILES, ids=lambda p: p.stem)
def test_serialization_round_trip(pipeline, path):
    profile = pipeline.process(path.read_text(encoding="utf-8"), path.name)
    as_json = profile.model_dump_json()
    as_dict = json.loads(as_json)
    assert as_dict["pipeline_version"] == "2.0.0"
    assert as_dict["filename"] == path.name
    rebuilt = CandidateProfile.model_validate(as_dict)
    assert rebuilt == profile


def test_internships_and_experience_are_routed(pipeline):
    text, _ = load_case(FIXTURES / "04_diploma_fulltime.txt")
    profile = pipeline.process(text, "x.txt")
    assert all(not e.is_internship for e in profile.experience)
    assert all(e.is_internship for e in profile.internships)
    assert profile.experience[0].duration_months == 42  # Jun 2023 -> Nov 2026, inclusive


def test_sparse_resume_reports_gaps_without_inventing(pipeline):
    text, _ = load_case(FIXTURES / "06_minimal_sparse.txt")
    profile = pipeline.process(text, "sparse.txt")
    assert profile.contact.email is None and profile.contact.phone is None
    assert profile.experience == [] and profile.internships == [] and profile.projects == []
    warnings = " ".join(profile.metadata.warnings)
    assert "No email" in warnings and "No phone" in warnings and "projects" in warnings
    assert profile.metadata.confidence_level.value in {"low", "medium"}


@pytest.mark.parametrize("text", ["", "   \n\t  ", None])
def test_empty_input_returns_valid_empty_profile(pipeline, text):
    profile = pipeline.process(text, "empty.pdf")
    assert isinstance(profile, CandidateProfile)
    assert profile.education == [] and profile.technical_skills == []
    assert profile.metadata.warnings
    assert profile.metadata.overall_confidence == 0.0


def test_module_failure_gives_partial_profile(sample_resume_text):
    pipeline = ResumeNLPPipeline()

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    pipeline.education_extractor.extract = boom
    profile = pipeline.process(sample_resume_text, "x.pdf")
    assert profile.education == []
    assert profile.metadata.module_status["education"] == "failed"
    assert any("education extraction failed" in w for w in profile.metadata.warnings)
    # Everything else still extracted
    assert profile.contact.email == "aarav.sharma@dau.ac.in"
    assert profile.internships and profile.projects and profile.technical_skills


def test_process_request_and_analyze_resume(sample_resume_text):
    req = NLPProcessingRequest(resume_id="r-42", filename="a.pdf", text=sample_resume_text)
    profile = ResumeNLPPipeline().process_request(req)
    assert profile.metadata.resume_id == "r-42"
    assert analyze_resume(sample_resume_text, "a.pdf").contact.full_name == "Aarav Sharma"


def test_latency_under_150ms(pipeline):
    texts = [p.read_text(encoding="utf-8") for p in RESUME_FILES]
    pipeline.process(texts[0], "warmup")  # compile caches
    for text in texts:
        start = time.perf_counter()
        pipeline.process(text, "timing")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms <= 150, f"pipeline took {elapsed_ms:.1f} ms"


def test_pipeline_has_no_http_coupling():
    import app.nlp.pipeline as module
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "fastapi" not in source.lower()
    assert "Request" not in source.replace("NLPProcessingRequest", "")
