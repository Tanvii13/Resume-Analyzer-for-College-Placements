# NLP Sprint 3 – Verification Report (Modules E, F, G)

Resume Analyzer for College Placements · NLP layer · Sprint 3 (EPIC 3 – Feedback & Explainability: US-08, US-09, US-10)

## 1. Module completion status

| Module | Description | Status | Owner |
|---|---|---|---|
| A | Resume Scoring Engine | Done (earlier) | Atharv |
| B | Formatting Quality Analyzer | Done (earlier) | Atharv |
| C | Content Quality & Impact Analyzer | Done (earlier) | Atharv |
| D | Improvement Areas Detection | Done (earlier) | Atharv |
| **E** | **Rule-Based Recommendation Engine (US-09)** | **Done** | Tanishk |
| **F** | **Explainability & NLP Pipeline Integration (US-10)** | **Done** | Tanishk |
| **G** | **NLP Evaluation & Testing** | **Done** | Tanishk |

Scope kept to the NLP layer: no FastAPI routes, database code, frontend, LLM calls or Sprint 4 job matching.
Sprint 1/2 modules and Modules A–D were not modified (only `app/nlp/__init__.py` gained new exports).

## 2. Files created and modified

Created
- `backend/app/nlp/recommendations/` – `schemas.py`, `rules.py` (rule registry), `engine.py`, `__init__.py`
- `backend/app/nlp/analysis/` – `schemas.py` (`Sprint3AnalysisResult`), `explainability.py`, `pipeline.py`, `__init__.py`
- `backend/app/nlp/evaluation/` – `metrics.py`, `evaluator.py`, `__init__.py`
- `backend/scripts/evaluate_nlp_sprint3.py` – reproduces the metrics below
- `backend/tests/nlp/test_recommendations.py`, `test_analysis_pipeline.py`, `test_sprint3_evaluation.py`, `test_sprint3_invariants.py`
- `backend/tests/nlp/fixtures/sprint3/` – 13 synthetic resumes, `labels.json`, `labelled_bullets.json`
- `Documents/NLP_SPRINT_3_VERIFICATION_REPORT.md` (this file)

Modified
- `backend/app/nlp/__init__.py` – exports for Modules E and F

## 3. Architecture

```
CandidateProfile (Sprint 2) + raw text
  -> B  FormattingQualityAnalyzer      (run once, shared with A and D)
  -> A  ResumeScoringEngine
  -> C  ContentQualityAnalyzer
  -> D  ImprovementAreasDetector
  -> E  RecommendationEngine           issue -> rule -> recommendation, merge duplicates, prioritize
  -> F  ExplanationBuilder             score / issue / recommendation explanations + consistency checks
  -> Sprint3AnalysisResult
```

Key signatures
```python
ResumeAnalysisPipeline().analyze(profile: CandidateProfile, raw_text: str | None = None) -> Sprint3AnalysisResult
ResumeAnalysisPipeline().analyze_text(text: str, filename: str, resume_id: str | None = None) -> Sprint3AnalysisResult
RecommendationEngine().generate(improvement_report, scoring_result=None, content_report=None,
                                formatting_result=None, profile=None) -> RecommendationReport
run_evaluation(fixtures_dir: Path, timing_repeats: int = 3) -> dict
```

`Sprint3AnalysisResult` fields: `overall_score`, `score_label`, `component_scores`, `formatting_analysis`,
`content_quality_analysis`, `improvement_areas`, `recommendations`, `explanations`, `strengths`, `rule_version`,
`analyzer_version`, `analysis_metadata` (module status, per-module timings, structured errors, consistency checks).

Design points
- Every recommendation maps to a detected Module D issue (`related_issue_id(s)`); unknown issue ids fall back to a
  generic rule that is still tied to the issue and reported in `unmapped_issue_ids`.
- Duplicate advice is merged (e.g. "missing projects" from Modules A, B and D becomes one recommendation).
- Priority score = 0.50·severity factor + 0.20·component weight + 0.15·confidence + 0.15·actionability;
  high ≥ 0.78, medium ≥ 0.55; critical issues are always high. Documented in `recommendations/engine.py`.
- Advice is made specific only from detected evidence (named weak projects, quoted passive bullets, skills used in
  projects but missing from the skills list). No skills, certifications, achievements or numbers are invented;
  measurable-impact advice explicitly says to use only real numbers.
- `potential_score_gain` = points Module A actually deducted for that issue (an upper bound, never a promise).
- A module failure is recorded as a `ModuleError` (`validation_error` with Pydantic details, or `exception`) and the
  rest of the analysis still runs. A failed score is `None`, not 0.

## 4. Tests

| Command | Result |
|---|---|
| `pytest backend/tests/nlp/` | **525 passed, 1 xfailed** |
| `pytest backend/tests/` (whole backend, on `nlp` branch) | **582 passed, 1 xfailed** |
| Same changes applied on `main`, whole backend | **634 passed, 1 xfailed** |
| `ruff check` on all new files (CI config) | passed |

New tests: 171 (E: 30, F: 21, G evaluation: 10, G invariants: 110 + 1 xfail). Existing tests: 354, all still passing.

The 1 xfail is a known Module A issue (see §7); it is marked `strict=True`, so it starts failing as soon as the
issue is fixed, as a reminder to remove the marker.

Scoring invariants verified (`test_sprint3_invariants.py`)
- Scores within 0–100 for 19 fixtures and 7 damaged-input variants (shuffled, truncated, all caps, letters stripped…)
- Identical output for repeated runs and fresh pipeline instances
- Changing name, email, phone, college name or adding a gender line does not change any score or recommendation
- Every deduction has a reason and evidence; every issue and recommendation has an explanation
- Missing sections (`IMP_MISSING_*`) and an unreadable resume (`IMP_EXTRACTION_UNCERTAINTY`) are reported differently
- No contradictions (recommendations map to issues, no "missing X" when X was extracted, component scores sum to total)
- No duplicate deductions (except the known Module A case)

## 5. Evaluation metrics and methodology

Methodology
- 13 synthetic resumes covering every case in the Sprint 3 brief (strong, weak, missing sections, incomplete
  education, limited / detailed projects, no internships, no work experience, inconsistent formatting, repeated
  bullets, measurable / no measurable achievements, low-confidence extraction) plus 36 hand-labelled bullets.
- Labels were written from the resume text before running the system. Each case lists issues that should be
  detected and issues that must not be; anything unlisted is excluded from precision/recall and reported for review.
- All numbers come from `python scripts/evaluate_nlp_sprint3.py`. The set is small and synthetic; these figures
  describe behaviour on these cases only and are **not** a claim of real-world accuracy.

Labelled cases: 13 resumes, 36 bullets

| Area | Metric | Value |
|---|---|---|
| Improvement detection (Module D) | Precision | 1.000 |
| | Recall | 0.917 |
| | F1 | 0.957 |
| | TP / FP / FN / TN | 22 / 0 / 2 / 116 |
| Formatting detection (Module B) | Precision | 0.778 |
| | Recall | 1.000 |
| | False-positive rate | 0.067 |
| Content quality (Module C) | Band agreement with labels | 0.727 (11 cases) |
| | Action-verb detection accuracy | 0.917 |
| | Impact-metric detection accuracy | 0.889 |
| | Weak-opening detection accuracy | 1.000 |
| Recommendations (Module E) | Issue-to-recommendation mapping accuracy | 1.000 (49 checks) |
| | Duplicate recommendation rate | 0.000 (48 recs) |
| | Recall of manually expected recommendations | 0.882 |
| Scoring (Module A) | Strong > average > weak pairwise ordering | 1.000 (54 pairs) |

Errors found:
- Improvement false negatives:
  - s3_03_missing_sections:IMP_MISSING_SKILLS
  - s3_08_no_work_experience:IMP_MISSING_SOFT_SKILLS
- Improvement false positives: none
- Formatting false positives:
  - s3_01_strong:FMT_INCONSISTENT_DATE_FORMATS
  - s3_11_measurable_achievements:FMT_INCONSISTENT_DATE_FORMATS
- Formatting false negatives: none
- Content band disagreements:
  - predicted strong vs label moderate
  - predicted strong vs label moderate
  - predicted strong vs label moderate
- Bullet detector errors:
  - verb: predicted False, label True: "Wrote 120 unit tests, raising coverage from 54% to 91%."
  - metric: predicted False, label True: "Designed a REST API serving 1,200 daily orders."
  - verb: predicted False, label True: "Achieved 99.9% uptime over a 30-day deployment."
  - verb: predicted False, label True: "Trained a model on 18,000 course ratings."
  - metric: predicted False, label True: "Trained a model on 18,000 course ratings."
  - metric: predicted False, label True: "Responsible for handling 500 customer tickets per week."
  - metric: predicted True, label False: "Team of 3 students, 2023."
- Missing expected recommendations:
  - s3_03_missing_sections:REC_ADD_TECHNICAL_SKILLS_SECTION
  - s3_08_no_work_experience:REC_SHOW_SOFT_SKILLS

Timings (median / max ms):
- End to end incl. Sprint 2 extraction: 17.83 / 41.52 over 65 runs
- formatting: 1.44 / 5.3
- scoring: 0.24 / 1.31
- content: 0.25 / 0.75
- improvement: 0.08 / 0.16
- recommendations: 0.1 / 0.22
- explainability: 0.11 / 0.3

| Case | Score | Content band (pred / label) | Issues |
|---|---|---|---|
| Strong resume | 99.01 | strong / strong | IMP_INCONSISTENT_DATE_FORMATS |
| Weak resume | 35.47 | weak / weak | IMP_CONTACT_MISSING_DEV_PROFILES, IMP_CONTACT_MISSING_PHONE, IMP_EDU_MISSING_CGPA, IMP_EDU_MISSING_YEAR, IMP_GENERIC_RESUME_CLICHES, IMP_LACK_OF_MEASURABLE_IMPACT, IMP_MISSING_SKILLS, IMP_MISSING_SOFT_SKILLS, IMP_PASSIVE_PHRASING, IMP_WEAK_PROJECT_DESCRIPTION |
| Missing critical sections | 29.65 | weak / None | FMT_MISSING_SECTION_HEADING, IMP_LOW_SKILL_INVENTORY, IMP_MISSING_PRACTICAL_WORK, IMP_MISSING_PROJECTS, IMP_MISSING_SOFT_SKILLS |
| Incomplete education details | 85.58 | strong / moderate | IMP_EDU_MISSING_CGPA, IMP_EDU_MISSING_YEAR, IMP_LACK_OF_MEASURABLE_IMPACT, IMP_MISSING_SOFT_SKILLS, IMP_WEAK_PROJECT_DESCRIPTION |
| Limited project descriptions | 58.78 | weak / weak | IMP_LACK_OF_MEASURABLE_IMPACT, IMP_MISSING_SOFT_SKILLS, IMP_WEAK_PROJECT_DESCRIPTION |
| Detailed project descriptions | 98.69 | strong / strong | - |
| No internships (full-time job only) | 90.34 | strong / moderate | IMP_INCONSISTENT_DATE_FORMATS, IMP_MISSING_SOFT_SKILLS |
| No work experience (fresher) | 89.08 | strong / moderate | - |
| Inconsistent formatting | 80.31 | moderate / moderate | FMT_INCONSISTENT_BULLET_PUNCTUATION, IMP_EXCESSIVE_WHITESPACE, IMP_INCONSISTENT_BULLET_FORMATTING, IMP_INCONSISTENT_DATE_FORMATS, IMP_INCONSISTENT_HEADINGS, IMP_LACK_OF_MEASURABLE_IMPACT, IMP_MISSING_SOFT_SKILLS |
| Repeated bullet points | 79.12 | moderate / moderate | FMT_DUPLICATE_BULLET_CONTENT, IMP_DUPLICATE_BULLET_CONTENT, IMP_LACK_OF_MEASURABLE_IMPACT, IMP_MISSING_SOFT_SKILLS |
| Measurable achievements | 95.83 | strong / strong | IMP_INCONSISTENT_DATE_FORMATS |
| No measurable achievements | 80.29 | moderate / moderate | IMP_INCONSISTENT_DATE_FORMATS, IMP_LACK_OF_MEASURABLE_IMPACT, IMP_MISSING_SOFT_SKILLS |
| Low-confidence extraction (garbled layout) | 4.3 | weak / None | FMT_MISSING_SECTION_HEADING, IMP_CONTACT_MISSING_DEV_PROFILES, IMP_CONTACT_MISSING_EMAIL, IMP_CONTACT_MISSING_PHONE, IMP_EXTRACTION_UNCERTAINTY, IMP_MISSING_EDUCATION, IMP_MISSING_PRACTICAL_WORK, IMP_MISSING_PROJECTS, IMP_MISSING_SKILLS, IMP_MISSING_SOFT_SKILLS |


## 6. Performance

All modules are rule-based and fast (see timings above). One Sprint 3 analysis peaks well under 20 MB of
allocations (`test_peak_memory`). Repeated processing was removed: formatting analysis and scoring each run once per
resume and are passed into Module D instead of being recomputed (`test_formatting_and_scoring_run_once_per_analysis`).
No caching was introduced, so output stays deterministic.

## 7. Known limitations and issues found in earlier modules

Found by Module G; not changed in this PR so the module owners can review them:

1. **Module D – missing skills section not flagged** (`detector.py`): checks `profile.technical_skills` instead of
   `section_summary.missing_critical_sections`. A GitHub link in the header is extracted as a "skill", so a resume
   with no skills section gets "low skill inventory" instead of "add a skills section".
2. **Module D – no action-verb issue**: Module A deducts `CONTENT_FEW_ACTION_VERBS` (often the largest content
   deduction), but Module D only raises passive phrasing, so the student loses points with no advice. Module E
   already has a rule for `IMP_LACK_OF_ACTION_VERBS`; Module D only needs to emit it. Same for `SKILL_UNSUBSTANTIATED`
   → `IMP_UNSUBSTANTIATED_SKILLS`. Reported at runtime as consistency check
   `significant_deductions_have_improvement_area`.
3. **Module A – duplicate deduction**: with experience but no projects, `SEC_MISSING_PROJECTS` is deducted twice
   (missing critical section + practical-work check) — tracked by the strict xfail test.
4. **Module B – date false positive**: year-only education ranges ("2022 - 2026") next to month-year job ranges are
   flagged as inconsistent date formats on otherwise clean resumes.
5. **Module C – lexicon gaps**: "Wrote", "Achieved", "Trained" are not recognised as action verbs; "1,200 daily orders"
   is not recognised as a metric; "Team of 3 students, 2023" is wrongly treated as one.
6. **Module C – generous content bands**: 3 of 11 resumes labelled "moderate" content score as "strong".
7. **Sprint 2 skill extractor**: the branch name "Electronics and Communication Engineering" yields the soft skill
   "Communication", which hides the "no soft skills" issue.
8. Formatting analysis needs raw text; when only a `CandidateProfile` is available it is skipped (status `skipped`,
   with a warning), not failed.
9. Pre-existing `ruff check` findings in Modules A–D / Sprint 2 files (18 on `main`) make the CI lint step fail
   independently of this work.

`test_known_misses_are_still_present` and `KNOWN_UNCOVERED_DEDUCTIONS` list items 1, 2, 4 and 7, so when they are
fixed the tests point out exactly which thresholds and lists to update.

## 8. Sprint 1 & 2 regression status

All Sprint 1 and Sprint 2 tests pass unchanged. `CandidateProfile` is not modified, and a test confirms the Sprint 3
pipeline does not mutate the profile it analyses.

## 9. Remaining work / handover

- Backend: expose `ResumeAnalysisPipeline().analyze(profile, raw_text)` through the existing resume endpoints; the
  result is a plain Pydantic model (`result.model_dump()`).
- Frontend: `explanations.score_summary`, `explanations.score_breakdown`, and `recommendations.recommendations`
  (already sorted by priority) map directly onto a feedback dashboard.
- Module owners: items 1–7 in §7.
- Sprint 4: job-description alignment (weight currently redistributed, see `scoring/weights.py`).
