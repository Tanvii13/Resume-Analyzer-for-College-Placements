# NLP Sprint 4 – Backend Integration Guide

Resume Analyzer for College Placements · EPIC 4 Job / Internship Matching (US-11, US-12, US-13)

This explains how the backend can use the Sprint 4 NLP job-matching workflow. Everything lives
in `backend/app/nlp/job_matching/`, has no HTTP / database / LLM dependencies, and returns
Pydantic v2 models.

## 1. Current state (as of this PR)

The Sprint 4 API endpoints do **not** use the NLP engine yet. They use separate backend services:

| Endpoint | Uses today | Should use |
|---|---|---|
| `POST /resumes/{resume_id}/compare-jd` | `services/jd_parser.py` + `jd_matcher.py` (keyword matching) | `JobMatchingWorkflow.compare()` |
| `POST /resume-insights/match-job-description` | `services/jd_matcher.py` | `JobMatchingWorkflow.compare()` |
| `GET /opportunities/recommended` | `services/opportunity_matcher.py` on a hard-coded pool | `JobMatchingWorkflow.rank()` on the `opportunities` table |
| `POST /opportunities/evaluate-match` | `services/opportunity_matcher.py` | `JobMatchingWorkflow.compare()` |

The NLP results convert directly into the backend's **existing** response models, so these
endpoints can switch engines without changing their API contract or the frontend.

## 2. The two calls

```python
from app.nlp.job_matching import get_job_matching_workflow, RankingPreferences

workflow = get_job_matching_workflow()          # shared instance; build once, reuse

# US-11 / US-13: one resume vs one job description
report = workflow.compare(resume, job)          # -> JobFitReport

# US-12: rank many openings for one student
ranking = workflow.rank(resume, opportunities,  # -> OpportunityRankingReport
                        preferences=RankingPreferences(job_types=["internship"]))
```

`resume` can be the resume **text** (the Sprint 2 pipeline runs inside) or an existing
`CandidateProfile`. Prefer the profile when you already have one stored: it skips re-parsing.

`job` / each opportunity can be:
- raw JD text (`str`)
- a backend opportunity row / `OpportunityBase` dict (`id`, `title`, `company`, `location`,
  `opportunity_type`, `description`, `required_skills`, `preferred_skills`, `min_cgpa`)
- a `JobOpportunity` or `ParsedJobDescription`

When a record has both a `description` and skill lists, they are merged; skills the employer
listed explicitly are always treated as required/preferred as listed.

## 3. Drop-in endpoint changes

### `/resume-insights/match-job-description` and `/resumes/{id}/compare-jd`

```python
report = get_job_matching_workflow().compare(profile_or_text, request.jd_text)
if report.metadata.errors:
    raise HTTPException(status_code=422, detail=[e.model_dump() for e in report.metadata.errors])

return JDMatchResponse(**report.to_backend_jd_match())
# or
return JDCompareResponse(resume_id=resume_id, target_role=request.target_role,
                         **report.to_backend_jd_compare())
```

### `/opportunities/recommended`

```python
rows = get_opportunities(active_only=True)        # from services/opportunity_persistence.py
ranking = get_job_matching_workflow().rank(profile, rows)
return OpportunityRecommendationsResponse(**ranking.to_backend_response())
```

`to_backend_response()` already produces `total_opportunities_evaluated`,
`matched_opportunities_count`, `has_suitable_matches`, `guidance_message` and
`recommended_opportunities` (each an `OpportunityMatchCard` with the same
`skills_breakdown` keys the frontend uses today). These shapes are checked against the real
backend schemas in `tests/nlp/test_job_matching_workflow.py` and `test_opportunity_ranker.py`.

**Do not fall back to made-up skills when a student has no resume.** Return
`has_suitable_matches=False` with a message asking them to upload a resume (US-12 AC 3).

## 4. What the student gets (richer than the current response)

`JobFitReport`
- `relevance_score` (0–100), `fit_tier` (High / Moderate / Developing Fit), `is_suitable`, `summary`
- `skill_gap.matched_required / partial_required / missing_required` and the same for preferred,
  plus `soft_skills` (US-13 AC 1 and AC 2). Each item has resume evidence, the JD line, importance and advice.
- `skill_gap.alternative_groups`: "Python **or** Java" is one requirement, so a Python-only student is not
  told Java is missing.
- `skill_gap.priority_gaps`: what to work on first, with advice that never claims a skill the student lacks.
- `skill_gap.eligibility_checks`: CGPA, graduating batch, branch, degree and backlogs, each
  `met` / `not_met` / `unknown`.
- `match`: Module C component scores and per-requirement rationale.

`OpportunityRankingReport`
- `ranked_opportunities` (eligible first, then by relevance) with `ranking_reasons`, including why each is
  below the one above it.
- `guidance_message`: always present; says clearly when nothing is a good match (US-12 AC 3).
- `common_gaps`: required skills missing across several openings ("learn Docker: needed by 3 openings").
- `filtered_out` (with reasons) and `errors` (one bad record never stops the ranking).

## 5. Errors and robustness

- `compare()` never raises for bad input. Each stage (`resume`, `job_description`, `matching`, `skill_gap`,
  `relevance`) is reported in `report.metadata.stage_status`, and failures appear in `report.metadata.errors`
  as `{stage, error_type, message, details}`.
- An empty JD gives `job_description: failed` with a clear message, not a 500.
- A JD with no readable technical skills (e.g. a mechanical role) is never shown as a good fit.

## 6. Performance

Measured on the evaluation set (see the verification report): about **19 ms** per `compare()` with an
existing profile and about **100 ms** to rank 8 openings. Create the workflow once (`get_job_matching_workflow()`)
and reuse it.

## 7. Configuration

- `RankingPreferences`: `job_types`, `locations` (remote always allowed), `include_ineligible`,
  `min_relevance`, `top_k`.
- Relevance formula and thresholds are constants at the top of `opportunity_ranker.py`
  (`MATCH_WEIGHT`, `COVERAGE_WEIGHT`, `HIGH_FIT`, `MODERATE_FIT`, `EXPERIENCE_GAP_PENALTY`).
- Module C weights: `MatchingWeights` in `matcher_schemas.py`.
