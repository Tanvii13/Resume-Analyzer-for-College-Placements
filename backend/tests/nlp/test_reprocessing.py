from copy import deepcopy
from datetime import datetime, timezone

import pytest

from app.nlp.analysis import ResumeAnalysisPipeline
from app.nlp.job_matching.schemas import JobSkillRequirement, ParsedJobDescription
from app.nlp.reprocessing import (
    UnsupportedHistoricalVersionError,
    reprocess_job_matching,
    reprocess_resume_analysis,
)
from app.nlp.schemas import CandidateProfile, ProjectEntry, SkillItem


def profile():
    return CandidateProfile(filename="student.pdf", technical_skills=[SkillItem(canonical_name="Python", matched_alias="python", category="Programming Languages")], projects=[ProjectEntry(title="API", technologies=["Python"])])


def job():
    return ParsedJobDescription(title="Python Intern", required_technical_skills=[JobSkillRequirement(canonical_name="Python", matched_alias="python", category="Programming Languages", is_required=True)])


def test_identical_configuration_is_deterministic_and_marks_new_generation():
    first = reprocess_resume_analysis(profile())
    second = reprocess_resume_analysis(profile())
    assert first.generation_kind == "reprocessed"
    assert first.result.overall_score == second.result.overall_score
    assert first.result.analysis_metadata.version_metadata.scoring_configuration_fingerprint == second.result.analysis_metadata.version_metadata.scoring_configuration_fingerprint


def test_selected_supported_configuration_and_metadata_are_preserved():
    created = datetime(2026, 11, 21, tzinfo=timezone.utc)
    result = reprocess_resume_analysis(profile(), configuration="sprint3-audit-reference-v3", created_at=created)
    assert result.configuration_id == "sprint3-audit-reference-v3"
    assert result.result.analysis_metadata.version_metadata.created_at == created


def test_missing_profile_invalid_config_and_unsupported_history_fail_safely():
    with pytest.raises(TypeError):
        reprocess_resume_analysis(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Unsupported resume"):
        reprocess_resume_analysis(profile(), configuration="unknown")
    old = ResumeAnalysisPipeline().analyze(profile())
    old.analyzer_version = "2.0.0"
    with pytest.raises(UnsupportedHistoricalVersionError):
        reprocess_resume_analysis(profile(), historical_result=old)


def test_job_reprocessing_regenerates_match_and_skill_gap_without_mutating_inputs():
    candidate, target = profile(), job()
    before_candidate, before_job = deepcopy(candidate), deepcopy(target)
    result = reprocess_job_matching(candidate, target)
    assert result.result.match is not None
    assert result.result.skill_gap is not None
    assert result.result.match.version_metadata.component_versions["job_matching"] == "4.0.0"
    assert candidate == before_candidate and target == before_job


def test_historical_result_remains_unchanged():
    candidate = profile()
    old = ResumeAnalysisPipeline().analyze(candidate)
    before = old.model_dump(mode="json")
    rebuilt = reprocess_resume_analysis(candidate, historical_result=old)
    assert rebuilt.historical_result_supplied is True
    assert old.model_dump(mode="json") == before
