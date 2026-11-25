"""Sprint 6 Module A privacy-boundary tests for the NLP layer."""

import logging

from app.nlp import ProjectEntry, ResumeNLPPipeline
from app.nlp.analysis import ResumeAnalysisPipeline
from app.nlp.job_matching import JobMatchingWorkflow


def test_pipeline_failure_does_not_log_or_return_resume_text(caplog):
    raw_resume = "Aarav Sharma\naarav.sharma@example.edu\n+91 9876543210\nPython"
    pipeline = ResumeNLPPipeline()

    def fail(*args, **kwargs):
        raise RuntimeError(raw_resume)

    pipeline.education_extractor.extract = fail
    with caplog.at_level(logging.ERROR):
        profile = pipeline.process(raw_resume, "Aarav-Sharma.pdf")

    diagnostics = " ".join(profile.metadata.warnings + [record.getMessage() for record in caplog.records])
    assert raw_resume not in diagnostics
    assert "aarav.sharma@example.edu" not in diagnostics
    assert "9876543210" not in diagnostics
    assert profile.education == []
    assert profile.metadata.module_status["education"] == "failed"


def test_analysis_failure_does_not_return_raw_exception_data(caplog):
    raw_resume = "Aarav Sharma\naarav.sharma@example.edu\n+91 9876543210\nPython"
    profile = ResumeNLPPipeline().process(raw_resume, "Aarav-Sharma.pdf")
    pipeline = ResumeAnalysisPipeline()

    def fail(*args, **kwargs):
        raise RuntimeError(raw_resume)

    pipeline.content_analyzer.analyze = fail
    with caplog.at_level(logging.ERROR):
        result = pipeline.analyze(profile)

    diagnostics = " ".join([error.message for error in result.analysis_metadata.errors] + [record.getMessage() for record in caplog.records])
    assert raw_resume not in diagnostics
    assert "aarav.sharma@example.edu" not in diagnostics
    assert "9876543210" not in diagnostics
    assert result.analysis_metadata.module_status["content"] == "failed"


def test_job_matching_output_and_failure_do_not_expose_candidate_data():
    raw_resume = "Aarav Sharma\naarav.sharma@example.edu\n+91 9876543210\nPython"
    workflow = JobMatchingWorkflow()

    def fail(*args, **kwargs):
        raise RuntimeError(raw_resume)

    workflow.matcher.match = fail
    report = workflow.compare(raw_resume, "Backend intern requiring Python and Docker.", "Aarav-Sharma.pdf")
    serialized = report.model_dump_json().lower()

    assert "aarav sharma" not in serialized
    assert "aarav.sharma@example.edu" not in serialized
    assert "9876543210" not in serialized
    assert "candidate_name" not in serialized
    assert report.metadata.stage_status["matching"] == "failed"


def test_sensitive_models_are_safe_to_debug_print_without_changing_serialization():
    raw_resume = "Aarav Sharma\naarav.sharma@example.edu\n+91 9876543210\nPython"
    profile = ResumeNLPPipeline().process(raw_resume, "Aarav-Sharma.pdf")

    profile.projects.append(ProjectEntry(description="Contact aarav.sharma@example.edu for details."))
    debug_text = repr(profile) + repr(profile.contact)
    assert "Aarav Sharma" not in debug_text
    assert "aarav.sharma@example.edu" not in debug_text
    assert "9876543210" not in debug_text
    # The backend's authorised model serialization remains unchanged.
    assert profile.contact.email == "aarav.sharma@example.edu"
