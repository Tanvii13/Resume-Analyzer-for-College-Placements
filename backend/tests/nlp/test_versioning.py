from datetime import datetime, timezone

from app.nlp.analysis import ResumeAnalysisPipeline
from app.nlp.job_matching import ResumeJobMatcher
from app.nlp.job_matching.schemas import ParsedJobDescription
from app.nlp.pipeline import ResumeNLPPipeline
from app.nlp.scoring import ScoringWeights
from app.nlp.schemas import CandidateProfile, PipelineMetadata
from app.nlp.versioning import build_version_metadata, configuration_fingerprint


def test_profile_metadata_has_versions_fingerprints_and_caller_timestamp():
    created = datetime(2026, 11, 21, tzinfo=timezone.utc)
    profile = ResumeNLPPipeline().process("Python\nSkills\nPython", "resume.pdf", created_at=created)
    meta = profile.metadata.version_metadata
    assert meta.created_at == created
    assert meta.component_versions["profile_extraction"] == profile.pipeline_version
    assert meta.taxonomy_fingerprint.startswith("sha256:")
    assert meta.skill_aliases_fingerprint.startswith("sha256:")


def test_analysis_metadata_fingerprints_actual_scoring_configuration():
    profile = CandidateProfile(filename="resume.pdf")
    default = ResumeAnalysisPipeline().analyze(profile).analysis_metadata.version_metadata
    changed = ResumeAnalysisPipeline(weights=ScoringWeights(content_quality=30.0)).analyze(profile).analysis_metadata.version_metadata
    assert default.scoring_configuration_version == "3.0.0"
    assert default.scoring_configuration_fingerprint != changed.scoring_configuration_fingerprint


def test_metadata_round_trips_and_old_results_without_metadata_still_validate():
    metadata = build_version_metadata(("scoring",))
    assert type(metadata).model_validate_json(metadata.model_dump_json()) == metadata
    assert PipelineMetadata.model_validate({}).version_metadata is None


def test_job_matching_carries_only_its_relevant_component_versions():
    match = ResumeJobMatcher().match(CandidateProfile(filename="r.pdf"), ParsedJobDescription(title="Intern"))
    assert match.version_metadata.component_versions["job_matching"] == match.matching_engine_version
    assert "scoring" not in match.version_metadata.component_versions


def test_fingerprint_is_stable_for_equivalent_mapping_order():
    assert configuration_fingerprint({"b": 2, "a": 1}) == configuration_fingerprint({"a": 1, "b": 2})
