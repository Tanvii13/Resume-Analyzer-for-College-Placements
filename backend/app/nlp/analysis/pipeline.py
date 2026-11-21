"""
Sprint 3 NLP analysis orchestrator (Module F).

    CandidateProfile (+ raw text, optional)
      -> Module B  Formatting Quality Analyzer     (needs raw text; skipped without it)
      -> Module A  Resume Scoring Engine           (reuses the Module B result)
      -> Module C  Content Quality Analyzer
      -> Module D  Improvement Areas Detection     (reuses A, B, C)
      -> Module E  Recommendation Engine
      -> Explainability Builder
      -> Sprint3AnalysisResult

Formatting runs before scoring so its result is computed once and shared (Modules A and D
would otherwise each re-run it).

Each module runs in isolation: a failure is recorded as a structured ModuleError and later
modules still run with whatever is available. The Sprint 2 pipeline is untouched; this is a
separate service that consumes its CandidateProfile.

No HTTP, database or LLM dependencies.

Usage:
    from app.nlp.analysis import ResumeAnalysisPipeline
    result = ResumeAnalysisPipeline().analyze(profile, raw_text=text)
    # or, from raw text (runs the Sprint 2 pipeline first):
    result = ResumeAnalysisPipeline().analyze_text(text, "resume.pdf")
    result.model_dump()   # dict for the API layer
"""

import logging
import time
from datetime import datetime
from typing import Any, Callable, Optional, TypeVar

from pydantic import ValidationError

from app.nlp.analysis.explainability import ExplanationBuilder
from app.nlp.analysis.schemas import (
    SPRINT3_ANALYZER_VERSION,
    AnalysisExplanations,
    AnalysisMetadata,
    ModuleError,
    Sprint3AnalysisResult,
)
from app.nlp.content import CONTENT_ANALYZER_VERSION, ContentQualityAnalyzer
from app.nlp.formatting import FORMATTING_ANALYZER_VERSION, FormattingQualityAnalyzer
from app.nlp.improvement import IMPROVEMENT_ENGINE_VERSION, ImprovementAreasDetector
from app.nlp.pipeline import ResumeNLPPipeline
from app.nlp.recommendations import RECOMMENDATION_ENGINE_VERSION, RecommendationEngine
from app.nlp.schemas import CandidateProfile
from app.nlp.scoring import ResumeScoringEngine, ScoringWeights
from app.nlp.scoring.weights import SCORING_RULE_VERSION
from app.nlp.versioning import build_version_metadata

logger = logging.getLogger(__name__)

T = TypeVar("T")

MODULES = ("formatting", "scoring", "content", "improvement", "recommendations", "explainability")


class ResumeAnalysisPipeline:
    """Runs Sprint 3 Modules A-E on a CandidateProfile and builds an explainable result."""

    def __init__(
        self,
        weights: Optional[ScoringWeights] = None,
        nlp_pipeline: Optional[ResumeNLPPipeline] = None,
    ):
        self.formatting_analyzer = FormattingQualityAnalyzer()
        self.scoring_engine = ResumeScoringEngine(weights=weights)
        self.content_analyzer = ContentQualityAnalyzer()
        self.improvement_detector = ImprovementAreasDetector()
        self.recommendation_engine = RecommendationEngine()
        self.explanation_builder = ExplanationBuilder()
        self._nlp_pipeline = nlp_pipeline

    # ------------------------------------------------------------------ API

    def analyze_text(
        self, text: Optional[str], filename: str, resume_id: Optional[str] = None
    ) -> Sprint3AnalysisResult:
        """Run the Sprint 2 extraction pipeline, then the Sprint 3 analysis."""
        if self._nlp_pipeline is None:
            self._nlp_pipeline = ResumeNLPPipeline()
        profile = self._nlp_pipeline.process(text, filename, resume_id=resume_id)
        return self.analyze(profile, raw_text=text)

    def analyze(
        self, profile: CandidateProfile, raw_text: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> Sprint3AnalysisResult:
        """Analyze an existing CandidateProfile. `raw_text` enables formatting analysis."""
        started = time.perf_counter()
        meta = AnalysisMetadata(
            raw_text_available=bool(raw_text and raw_text.strip()),
            extraction_confidence=profile.metadata.overall_confidence if profile.metadata else None,
            module_versions={
                "scoring": SCORING_RULE_VERSION,
                "formatting": FORMATTING_ANALYZER_VERSION,
                "content": CONTENT_ANALYZER_VERSION,
                "improvement": IMPROVEMENT_ENGINE_VERSION,
                "recommendations": RECOMMENDATION_ENGINE_VERSION,
                "analysis": SPRINT3_ANALYZER_VERSION,
            },
            version_metadata=build_version_metadata(
                ("profile_extraction", "scoring", "formatting", "content", "improvement", "recommendations", "analysis"),
                created_at=created_at, scoring_weights=self.scoring_engine.weights,
            ),
        )

        if meta.raw_text_available:
            formatting = self._run(
                "formatting",
                meta,
                lambda: self.formatting_analyzer.analyze(raw_text, profile=profile),
            )
        else:
            formatting = None
            meta.module_status["formatting"] = "skipped"
            meta.warnings.append("Formatting analysis skipped: raw resume text was not provided.")

        scoring = self._run(
            "scoring",
            meta,
            lambda: self.scoring_engine.evaluate(
                profile, raw_text=raw_text, formatting_result=formatting
            ),
        )
        content = self._run("content", meta, lambda: self.content_analyzer.analyze(profile))
        improvement = self._run(
            "improvement",
            meta,
            lambda: self.improvement_detector.detect(
                profile,
                scoring_result=scoring,
                formatting_result=formatting,
                content_report=content,
                raw_text=None,
            ),
        )
        recommendations = self._run(
            "recommendations",
            meta,
            lambda: (
                self.recommendation_engine.generate(
                    improvement,
                    scoring_result=scoring,
                    content_report=content,
                    formatting_result=formatting,
                    profile=profile,
                )
                if improvement is not None
                else _raise(RuntimeError("no improvement report to build recommendations from"))
            ),
        )
        explanations = self._run(
            "explainability",
            meta,
            lambda: self.explanation_builder.build(scoring, improvement, recommendations),
        )
        if explanations is None:
            explanations = AnalysisExplanations(
                score_summary="Explanations could not be generated for this analysis."
            )

        checks, check_warnings = self.explanation_builder.consistency_checks(
            profile, scoring, improvement, recommendations, explanations
        )
        meta.consistency_checks = checks
        meta.warnings.extend(check_warnings)

        strengths = []
        for source in (
            scoring.strengths if scoring else [],
            improvement.strong_areas if improvement else [],
            formatting.strengths if formatting else [],
        ):
            for s in source:
                if s not in strengths:
                    strengths.append(s)

        meta.processing_time_ms = round((time.perf_counter() - started) * 1000, 2)
        return Sprint3AnalysisResult(
            filename=profile.filename,
            overall_score=scoring.overall_score if scoring else None,
            score_label=scoring.score_label if scoring else None,
            component_scores=dict(scoring.component_scores) if scoring else {},
            formatting_analysis=formatting,
            content_quality_analysis=content,
            improvement_areas=improvement,
            recommendations=recommendations,
            explanations=explanations,
            strengths=strengths,
            rule_version=scoring.rule_version if scoring else None,
            analyzer_version=SPRINT3_ANALYZER_VERSION,
            analysis_metadata=meta,
        )

    # ------------------------------------------------------------ internals

    @staticmethod
    def _run(module: str, meta: AnalysisMetadata, fn: Callable[[], T]) -> Optional[T]:
        start = time.perf_counter()
        try:
            result = fn()
            meta.module_status[module] = "ok"
            return result
        except ValidationError as exc:
            logger.warning("Sprint 3 module '%s' produced invalid output", module, exc_info=True)
            meta.module_status[module] = "failed"
            meta.errors.append(
                ModuleError(
                    module=module,
                    error_type="validation_error",
                    message=str(exc).splitlines()[0],
                    details=[
                        {k: v for k, v in e.items() if k in ("loc", "msg", "type")}
                        for e in exc.errors()
                    ],
                )
            )
            return None
        except Exception as exc:  # noqa: BLE001 - isolate module failures
            logger.exception("Sprint 3 module '%s' failed", module)
            meta.module_status[module] = "failed"
            meta.errors.append(
                ModuleError(
                    module=module, error_type="exception", message=f"{type(exc).__name__}: {exc}"
                )
            )
            return None
        finally:
            meta.module_timings_ms[module] = round((time.perf_counter() - start) * 1000, 2)


def _raise(exc: Exception) -> Any:
    raise exc


_default: Optional[ResumeAnalysisPipeline] = None


def run_sprint3_analysis(
    profile: CandidateProfile, raw_text: Optional[str] = None
) -> Sprint3AnalysisResult:
    """Analyze a profile with a shared default pipeline instance."""
    global _default
    if _default is None:
        _default = ResumeAnalysisPipeline()
    return _default.analyze(profile, raw_text=raw_text)


__all__ = ["MODULES", "ResumeAnalysisPipeline", "run_sprint3_analysis"]
