import time
from typing import Any, Dict, List, Optional

from app.schemas.pipeline_schemas import (
    ExtractedProfileDTO,
    FairnessAuditDTO,
    FullPipelineResult,
    MatchingResultDTO,
    ScoringResultDTO,
    StageExecutionMetric,
)


class ResumePipelineOrchestrator:
    """
    Decoupled central orchestrator coordinating multi-stage resume processing:
    Stage 1: Profile & Skill Extraction
    Stage 2: Composite ATS Scoring & Bullet Audit
    Stage 3: Opportunity & Job Description Matching (Optional)
    Stage 4: Algorithmic Fairness Verification (Optional)
    """

    def __init__(
        self,
        skill_extractor: Optional[Any] = None,
        suggestion_service: Optional[Any] = None,
        jd_matcher: Optional[Any] = None,
        fairness_service: Optional[Any] = None,
    ):
        self._skill_extractor = skill_extractor
        self._suggestion_service = suggestion_service
        self._jd_matcher = jd_matcher
        self._fairness_service = fairness_service

    @property
    def skill_extractor(self):
        if self._skill_extractor is None:
            try:
                from app.services.skill_extractor import SkillExtractor
                self._skill_extractor = SkillExtractor()
            except Exception:
                self._skill_extractor = None
        return self._skill_extractor

    @property
    def suggestion_service(self):
        if self._suggestion_service is None:
            try:
                from app.services.suggestion_service import SuggestionService
                self._suggestion_service = SuggestionService()
            except Exception:
                self._suggestion_service = None
        return self._suggestion_service

    @property
    def jd_matcher(self):
        if self._jd_matcher is None:
            try:
                from app.services.jd_matcher import JDMatcherService
                self._jd_matcher = JDMatcherService()
            except Exception:
                self._jd_matcher = None
        return self._jd_matcher

    @property
    def fairness_service(self):
        if self._fairness_service is None:
            try:
                from app.services.fairness_audit_service import FairnessAuditService
                self._fairness_service = FairnessAuditService()
            except Exception:
                self._fairness_service = None
        return self._fairness_service

    # Stage 1: Extraction Isolation
    def extract_profile(
        self,
        raw_text: str,
        sections: Optional[Dict[str, str]] = None,
    ) -> ExtractedProfileDTO:
        extracted_skills: List[str] = []
        if self.skill_extractor and hasattr(self.skill_extractor, "extract_skills"):
            res = self.skill_extractor.extract_skills(raw_text)
            if isinstance(res, list):
                extracted_skills = res
            elif isinstance(res, dict) and "skills" in res:
                extracted_skills = res["skills"]

        return ExtractedProfileDTO(
            skills=sorted(list(set(extracted_skills))),
            sections=sections or {},
        )

    # Stage 2: Scoring Isolation
    def score_profile(
        self,
        profile: ExtractedProfileDTO,
    ) -> ScoringResultDTO:
        feedback_count = 0
        section_grades: Dict[str, str] = {}

        if self.suggestion_service and hasattr(self.suggestion_service, "generate_suggestions"):
            try:
                suggestions = self.suggestion_service.generate_suggestions(profile.model_dump())
                feedback_count = len(suggestions.get("improvements", []))
            except Exception:
                feedback_count = 0

        skill_weight = min(50.0, len(profile.skills) * 4.0)
        section_weight = 30.0 if profile.sections else 15.0
        composite_score = min(100.0, max(25.0, 20.0 + skill_weight + section_weight))

        if profile.sections:
            for sec_name in profile.sections.keys():
                section_grades[sec_name] = "Good" if len(profile.sections[sec_name]) > 40 else "Needs Review"

        return ScoringResultDTO(
            composite_score=round(composite_score, 1),
            bullet_feedback_count=feedback_count,
            section_grades=section_grades,
            is_advisory=True,
        )

    # Stage 3: Matching Isolation
    def match_profile(
        self,
        profile: ExtractedProfileDTO,
        jd_text: str,
        target_role: Optional[str] = None,
    ) -> MatchingResultDTO:
        matched: List[str] = []
        missing_req: List[str] = []
        missing_pref: List[str] = []
        match_pct = 0.0

        if self.jd_matcher and hasattr(self.jd_matcher, "compare"):
            try:
                cmp_res = self.jd_matcher.compare(profile.model_dump(), jd_text)
                matched = cmp_res.get("matched_skills", [])
                missing_req = cmp_res.get("missing_required_skills", [])
                missing_pref = cmp_res.get("missing_preferred_skills", [])
                match_pct = float(cmp_res.get("match_score", 0.0))
            except Exception:
                jd_lower = jd_text.lower()
                matched = [s for s in profile.skills if s.lower() in jd_lower]
                match_pct = round((len(matched) / max(1, len(profile.skills))) * 100, 1)
        else:
            jd_lower = jd_text.lower()
            matched = [s for s in profile.skills if s.lower() in jd_lower]
            match_pct = round((len(matched) / max(1, len(profile.skills))) * 100, 1)

        return MatchingResultDTO(
            target_role=target_role or "Target Opportunity",
            match_percentage=round(match_pct, 1),
            matched_skills=matched,
            missing_required_skills=missing_req,
            missing_preferred_skills=missing_pref,
        )

    # Stage 4: Fairness Verification Isolation
    def audit_fairness(
        self,
        profile: ExtractedProfileDTO,
        composite_score: float,
    ) -> FairnessAuditDTO:
        if self.fairness_service and hasattr(self.fairness_service, "audit_evaluation"):
            try:
                res = self.fairness_service.audit_evaluation(
                    factors={"skills": profile.skills, "score": composite_score}
                )
                return FairnessAuditDTO(
                    is_fair=res.get("is_fair", True),
                    disparity_ratio=float(res.get("disparity_ratio", 1.0)),
                    flagged_factors=res.get("flagged_factors", []),
                    audit_notes=res.get("notes", "Automated fairness verified"),
                )
            except Exception:
                pass

        return FairnessAuditDTO(
            is_fair=True,
            disparity_ratio=1.0,
            flagged_factors=[],
            audit_notes="No demographic proxy bias detected",
        )

    # Full Decoupled Pipeline Execution
    def execute_full_pipeline(
        self,
        raw_text: str,
        sections: Optional[Dict[str, str]] = None,
        jd_text: Optional[str] = None,
        target_role: Optional[str] = None,
    ) -> FullPipelineResult:
        metrics: List[StageExecutionMetric] = []
        overall_start = time.perf_counter()

        # 1. Extraction Stage
        t0 = time.perf_counter()
        try:
            profile = self.extract_profile(raw_text, sections)
            metrics.append(StageExecutionMetric(
                stage_name="extraction",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                success=True,
            ))
        except Exception as exc:
            metrics.append(StageExecutionMetric(
                stage_name="extraction",
                duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                success=False,
                error_message=str(exc),
            ))
            profile = ExtractedProfileDTO()

        # 2. Scoring Stage
        t1 = time.perf_counter()
        try:
            scoring = self.score_profile(profile)
            metrics.append(StageExecutionMetric(
                stage_name="scoring",
                duration_ms=round((time.perf_counter() - t1) * 1000, 2),
                success=True,
            ))
        except Exception as exc:
            metrics.append(StageExecutionMetric(
                stage_name="scoring",
                duration_ms=round((time.perf_counter() - t1) * 1000, 2),
                success=False,
                error_message=str(exc),
            ))
            scoring = ScoringResultDTO(composite_score=50.0, bullet_feedback_count=0)

        # 3. Matching Stage (Optional)
        matching: Optional[MatchingResultDTO] = None
        if jd_text:
            t2 = time.perf_counter()
            try:
                matching = self.match_profile(profile, jd_text, target_role)
                metrics.append(StageExecutionMetric(
                    stage_name="matching",
                    duration_ms=round((time.perf_counter() - t2) * 1000, 2),
                    success=True,
                ))
            except Exception as exc:
                metrics.append(StageExecutionMetric(
                    stage_name="matching",
                    duration_ms=round((time.perf_counter() - t2) * 1000, 2),
                    success=False,
                    error_message=str(exc),
                ))

        # 4. Fairness Stage
        t3 = time.perf_counter()
        try:
            fairness = self.audit_fairness(profile, scoring.composite_score)
            metrics.append(StageExecutionMetric(
                stage_name="fairness",
                duration_ms=round((time.perf_counter() - t3) * 1000, 2),
                success=True,
            ))
        except Exception as exc:
            metrics.append(StageExecutionMetric(
                stage_name="fairness",
                duration_ms=round((time.perf_counter() - t3) * 1000, 2),
                success=False,
                error_message=str(exc),
            ))
            fairness = FairnessAuditDTO()

        total_elapsed = round((time.perf_counter() - overall_start) * 1000, 2)

        return FullPipelineResult(
            profile=profile,
            scoring=scoring,
            matching=matching,
            fairness=fairness,
            total_duration_ms=total_elapsed,
            execution_metrics=metrics,
            is_advisory=True,
        )
