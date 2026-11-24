"""Sprint 6 Module A privacy-boundary tests for the NLP layer."""

import logging

from app.nlp import ResumeNLPPipeline
from app.nlp.analysis import ResumeAnalysisPipeline


def test_pipeline_failure_does_not_log_or_return_resume_text(caplog):
    raw_resume = "Aarav Sharma\naarav.sharma@example.edu\nPython"
    pipeline = ResumeNLPPipeline()

    def fail(*args, **kwargs):
        raise RuntimeError(raw_resume)

    pipeline.education_extractor.extract = fail
    with caplog.at_level(logging.ERROR):
        profile = pipeline.process(raw_resume, "Aarav-Sharma.pdf")

    diagnostics = " ".join(profile.metadata.warnings + [record.getMessage() for record in caplog.records])
    assert raw_resume not in diagnostics
    assert "aarav.sharma@example.edu" not in diagnostics
    assert profile.education == []
    assert profile.metadata.module_status["education"] == "failed"


def test_analysis_failure_does_not_return_raw_exception_data(caplog):
    raw_resume = "Aarav Sharma\naarav.sharma@example.edu\nPython"
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
    assert result.analysis_metadata.module_status["content"] == "failed"
