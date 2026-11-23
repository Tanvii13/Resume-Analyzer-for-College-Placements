import unittest
from unittest.mock import MagicMock

from app.schemas.pipeline_schemas import (
    ExtractedProfileDTO,
    FullPipelineResult,
    ScoringResultDTO,
    StageExecutionMetric,
)
from app.services.pipeline_orchestrator import ResumePipelineOrchestrator
from app.evaluation.pilot_benchmark import PilotBenchmarkRunner, PILOT_RESUME_CORPUS


class TestSprint7Member2Pipeline(unittest.TestCase):
    def test_pipeline_schemas_serialization(self):
        metric = StageExecutionMetric(
            stage_name="extraction",
            duration_ms=45.2,
            success=True,
        )
        self.assertEqual(metric.stage_name, "extraction")
        self.assertTrue(metric.success)

        profile = ExtractedProfileDTO(
            skills=["Python", "FastAPI", "Docker"],
            sections={"Skills": "Python, FastAPI", "Experience": "Backend Intern"},
        )
        self.assertEqual(len(profile.skills), 3)

        scoring = ScoringResultDTO(
            composite_score=85.0,
            bullet_feedback_count=2,
            section_grades={"Skills": "Good"},
            is_advisory=True,
        )
        self.assertEqual(scoring.composite_score, 85.0)
        self.assertTrue(scoring.is_advisory)

        full_res = FullPipelineResult(
            profile=profile,
            scoring=scoring,
            execution_metrics=[metric],
            is_advisory=True,
        )
        serialized = full_res.model_dump()
        self.assertEqual(serialized["scoring"]["composite_score"], 85.0)
        self.assertTrue(serialized["is_advisory"])

    def test_orchestrator_stage_isolation(self):
        mock_extractor = MagicMock()
        mock_extractor.extract_skills.return_value = ["Python", "PostgreSQL", "Git"]

        orchestrator = ResumePipelineOrchestrator(skill_extractor=mock_extractor)

        # 1. Independent extraction
        profile = orchestrator.extract_profile("Experienced Python developer with PostgreSQL and Git.")
        self.assertIn("Python", profile.skills)
        self.assertIn("PostgreSQL", profile.skills)

        # 2. Independent scoring on existing profile
        scoring = orchestrator.score_profile(profile)
        self.assertGreaterEqual(scoring.composite_score, 25.0)
        self.assertTrue(scoring.is_advisory)

        # 3. Independent matching on existing profile
        jd_text = "Looking for a Python backend engineer with PostgreSQL experience."
        matching = orchestrator.match_profile(profile, jd_text, target_role="Backend Engineer")
        self.assertEqual(matching.target_role, "Backend Engineer")
        self.assertIn("Python", matching.matched_skills)

        # 4. Independent fairness audit
        fairness = orchestrator.audit_fairness(profile, scoring.composite_score)
        self.assertTrue(fairness.is_fair)

    def test_orchestrator_full_pipeline_execution(self):
        orchestrator = ResumePipelineOrchestrator()
        sample_text = "Junior Developer with skills: Python, FastAPI, Docker, SQL."
        sample_sections = {"Skills": "Python, FastAPI, Docker, SQL"}
        sample_jd = "Requirements: Python, SQL, Docker, FastAPI."

        result = orchestrator.execute_full_pipeline(
            raw_text=sample_text,
            sections=sample_sections,
            jd_text=sample_jd,
            target_role="Junior Developer",
        )

        self.assertIsInstance(result, FullPipelineResult)
        self.assertGreater(result.scoring.composite_score, 0)
        self.assertTrue(result.is_advisory)
        self.assertGreaterEqual(len(result.execution_metrics), 3)

        stage_names = [m.stage_name for m in result.execution_metrics]
        self.assertIn("extraction", stage_names)
        self.assertIn("scoring", stage_names)
        self.assertIn("matching", stage_names)
        self.assertIn("fairness", stage_names)

    def test_pilot_benchmark_runner_20_resumes(self):
        self.assertEqual(len(PILOT_RESUME_CORPUS), 20)

        orchestrator = ResumePipelineOrchestrator()
        runner = PilotBenchmarkRunner(orchestrator=orchestrator)
        benchmark_res = runner.run_benchmark()

        self.assertEqual(benchmark_res["status"], "COMPLETED")
        self.assertEqual(benchmark_res["individual_evaluations_count"], 20)

        summary = benchmark_res["summary"]
        self.assertEqual(summary["total_resumes_tested"], 20)
        self.assertTrue(summary["fairness_parity_maintained"])
        self.assertGreater(summary["average_composite_score"], 0)
        self.assertIn("extraction", summary["stage_latency_breakdown"])

    def test_orchestrator_error_resilience(self):
        bad_extractor = MagicMock()
        bad_extractor.extract_skills.side_effect = RuntimeError("Parser process timed out")

        orchestrator = ResumePipelineOrchestrator(skill_extractor=bad_extractor)
        result = orchestrator.execute_full_pipeline(raw_text="Test raw text")

        extraction_metric = next(m for m in result.execution_metrics if m.stage_name == "extraction")
        self.assertFalse(extraction_metric.success)
        self.assertIn("timed out", extraction_metric.error_message)
        self.assertTrue(result.is_advisory)


if __name__ == "__main__":
    unittest.main()
