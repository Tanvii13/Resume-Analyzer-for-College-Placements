# Sprint 4 – Testing & Debugging Report

Resume Analyzer for College Placements · EPIC 4 Job / Internship Matching (US-11, US-12, US-13)

Scope: complete testing of Sprint 4, covering the NLP Modules A–F and the backend Sprint 4
endpoints, to check that everything is integrated.

## 1. Summary

| Area | Status |
|---|---|
| NLP Modules A–C (job description parsing, skill normalization, matching) | Done earlier; tested here, issues listed in §5 |
| NLP Module D – Skill Gap Analysis | **Done** (this PR) |
| NLP Module E – Job/Internship Relevance Ranking | **Done** (this PR) |
| NLP Module F – Integration, Evaluation & Testing | **Done** (this PR) |
| Backend API on `main` | **Was not starting.** Fixed in a separate PR (`sprint4-integration-fixes`, §4) |
| Backend endpoints using the NLP engine | **Not yet.** The endpoints use separate keyword matchers; see `NLP_SPRINT_4_INTEGRATION_GUIDE.md` |

## 2. What was built (NLP, `backend/app/nlp/job_matching/`)

| File | Module | Purpose |
|---|---|---|
| `skill_gap_schemas.py`, `skill_gap_analyzer.py` | D | Matched / partial / missing skills, required vs preferred vs soft kept separate; "X or Y" requirements; skills only in responsibilities down-ranked; importance-ranked gaps with advice; eligibility checks (CGPA, batch, branch, degree, backlogs) |
| `ranking_schemas.py`, `opportunity_ranker.py` | E | Ranks openings (raw JD text, backend records or parsed JDs); eligible first, then relevance; reasons for each position; clear message when nothing fits; common gaps; preferences; converts to the backend `OpportunityRecommendationsResponse` |
| `workflow.py` | F | `JobMatchingWorkflow.compare()` / `.rank()`: one entry point, stage-isolated errors, adapters to the backend `JDMatchResponse` / `JDCompareResponse` |
| `evaluation.py`, `scripts/evaluate_nlp_sprint4.py` | F | Labelled evaluation of Modules A, B, D, E |
| `tests/nlp/fixtures/sprint4/` | F | 8 synthetic job descriptions, 2 new synthetic resumes, `labels.json` |

Relevance = 0.6 × Module C match score + 0.4 × alternative-aware required-skill coverage. A JD whose
skills cannot be read is capped below "Moderate Fit", and needing more full-time experience than the
resume shows costs 15 points. Fit tiers use the backend's names (High / Moderate / Developing Fit).

## 3. Test results

| Command | Result |
|---|---|
| `pytest backend/tests/nlp` on `main` | **634 passed** (542 existing + 92 new) |
| Same, on the `nlp` branch | 632 passed, 2 skipped (the 2 backend-schema checks need `app/schemas`, which is only on `main`) |
| `pytest backend/tests` on `main` before fixes | **7 collection errors** – the backend could not import |
| `pytest backend/tests` with the integration fixes | **727 passed** (incl. 8 new API smoke tests) |
| Both PRs combined, `pytest backend/tests` | **819 passed**; `ruff check backend` passes |
| `ruff check backend` (CI lint) on `main` | 5 errors (unused imports) – fixed in the fixes PR, now passes |

New NLP tests: Module D 29, Module E 35, Module F workflow 18, Sprint 4 evaluation 10.

## 4. Integration bugs found and fixed (PR `sprint4-integration-fixes` → `main`)

| # | Problem | Effect | Fix |
|---|---|---|---|
| 1 | `backend/app/routers/resumes.py` line 116 lost its indentation in merge `f97c1cc` | **Backend could not start**; every API test failed to import | Re-indented the line |
| 2 | Sprint 4 dashboard + opportunity persistence code was committed to the root `app/` folder, but `backend/main.py` imports it from `backend/app/` | **Backend could not start** (`No module named app.routers.dashboard`) | Moved `dashboard.py`, `dashboard_service.py`, `opportunity_persistence.py`, `opportunity_seed.py` and their 3 tests into `backend/` |
| 3 | `test_dashboard_service.py` imported `require_placement_officer`, removed in `a3d1be7` | Test collection error | Rewrote the test for the shared `require_staff_or_counselor` dependency (+ checks every dashboard route uses it) |
| 4 | Two test files named `test_improvement_detector.py` (`tests/` and `tests/nlp/`) | pytest "import file mismatch" – **CI test step fails** | Renamed the backend one to `test_improvement_detector_service.py` |
| 5 | `/opportunities` router existed but was never mounted in `backend/main.py` | Sprint 4 recommendation endpoints unreachable | Added `app.include_router(opportunities_router)` |
| 6 | 5 unused imports in Sprint 3/4 backend files | **CI lint step fails** | Removed them |
| 7 | No test that the app actually starts with all Sprint 4 routes | The problems above went unnoticed | Added `tests/test_sprint4_api_smoke.py` (app import, all Sprint 4 routes mounted, auth, response models) |

## 5. Issues found and reported (not changed – owners should review)

Backend (Sprint 4 endpoints)
1. **Endpoints don't use the NLP engine.** `/resumes/{id}/compare-jd`, `/resume-insights/match-job-description`
   and `/opportunities/*` use keyword matchers in `services/`. See the integration guide; the NLP output already
   converts to their response models.
2. **`/opportunities/recommended` invents skills.** With no extracted skills it falls back to
   `["Python", "FastAPI", "SQL", "Git"]`, so a student without a resume gets recommendations for skills they
   never claimed. It should tell them to upload a resume (US-12 AC 3).
3. `/opportunities/*` ranks a hard-coded `CAMPUS_OPPORTUNITIES_POOL`, not the `opportunities` table that
   `opportunity_persistence.get_opportunities()` manages.
4. The root-level `app/`, `main.py` and `tests/` are an older copy of the backend (their 20 tests fail with
   "DATABASE_URL is missing"; CI doesn't run them). Consider deleting them to avoid more misplaced commits.

NLP Module A – job description parser
5. A requirement bullet starting "Experience with…" (e.g. "Experience with React") is read as an EXPERIENCE
   section heading, so that line and the next ("Familiarity with Git") are lost.
6. "Python or Java" / "PostgreSQL or MySQL" are stored as separate required skills. (Module D now treats them
   as one either-or requirement.)
7. Skills mentioned only in responsibilities become required skills ("work with QA teams" → "Quality
   Assurance"). (Module D now flags and down-ranks these.)
8. A "Qualification" heading is not read, so degree/branch rules under it are missed (j07).
9. Skill words can land in `fields_of_study` ("Statistics"), which wrongly made CS students ineligible.
   (Module D now only checks real branch names.)

NLP Module B – skill taxonomy
10. Missing common campus skills: **Excel, Arduino, Microcontrollers, Embedded C, PCB design, AutoCAD,
    SolidWorks**. Data-analyst, ECE and mechanical JDs lose most of their requirements, and students who list
    these skills don't get credit (the resume extractor shares the taxonomy).

NLP Module C – matcher
11. Every profile skill is labelled `explicit_skills_section`, even ones extracted from projects. (Module D
    checks the profile's own source, so "list this in your Skills section" tips work.)
12. Empty dimensions score full marks: a JD with no readable skills still gets a 60–70 match. (Module E caps
    these below Moderate Fit.)
13. "ECE" is only a related match for "Electronics and Communication Engineering"; a missing field of study
    is scored as an exact match.
14. Graduating batch and backlog rules are parsed but not checked. (Module D checks batch; backlogs are reported
    as "confirm with placement cell".)
15. Broad skills inferred from responsibilities ("Deep Learning", "AI") weigh as hard requirements, which is
    why an ML student sees the ML internship 4th (see ranking errors below). Module D now credits broad skills
    shown by tools (PyTorch → Machine Learning) as *partial*.

`test_sprint4_evaluation.py` lists items 5, 7 and 10 as `KNOWN_*` misses, so when they are fixed the test
fails and points to the thresholds to raise.

## 6. Evaluation (Module F)

Method: 8 synthetic job descriptions × 7 synthetic student resumes. Relevance grades (0–3), expected JD
fields and skills, 24 labelled skill pairs and 6 labelled gap pairs were written from the documents
**before** running the system. Numbers come from `python scripts/evaluate_nlp_sprint4.py`. The set is
small and synthetic: these figures describe these cases only and are not real-world accuracy.

Labelled set: 8 job descriptions x 7 student resumes

| Module | Metric | Value |
|---|---|---|
| A – JD parsing | Skill precision / recall / F1 | 0.982 / 0.821 / 0.894 |
| | Required-vs-preferred level accuracy | 1.000 |
| | Field accuracy: title | 1.000 |
| | Field accuracy: company | 1.000 |
| | Field accuracy: job_type | 1.000 |
| | Field accuracy: min_cgpa | 1.000 |
| | Field accuracy: batches | 1.000 |
| | Field accuracy: experience | 0.875 |
| B – Skill equivalence | Pair accuracy (24 pairs) | 1.000 |
| | False-equivalence rate | 0.000 |
| | Missed-equivalence rate | 0.000 |
| D – Skill gaps | Recall of skills the student has | 0.750 |
| | Recall of skills the student lacks | 1.000 |
| | Skills the student has reported as missing | 0 |
| E – Ranking | NDCG@3 | 0.931 |
| | Precision@1 | 0.857 |
| | MRR (first reasonable fit) | 1.000 |
| | Pairwise order accuracy (125 pairs) | 0.952 |
| | Suitability precision / recall | 0.800 / 0.923 |

Errors found:
- JD skills missed:
  - j02_frontend_intern:git
  - j02_frontend_intern:react
  - j03_data_analyst:excel
  - j05_embedded_intern:arduino
  - j05_embedded_intern:digital electronics
  - j05_embedded_intern:embedded c
  - j05_embedded_intern:microcontrollers
  - j05_embedded_intern:pcb design
  - j08_mechanical_design:autocad
  - j08_mechanical_design:engineering drawing
  - j08_mechanical_design:solidworks
  - j08_mechanical_design:strength of materials
- JD skills wrongly added:
  - j01_backend_intern:quality assurance
- Level errors: none
- Equivalence errors: none
- Gap errors:
  - r_frontend|j02_frontend_intern: has React, reported not in JD skills
  - r_frontend|j02_frontend_intern: has Git, reported not in JD skills
  - r_data|j03_data_analyst: has Excel, reported not in JD skills
  - s3_12_no_measurable_achievements|j02_frontend_intern: has React, reported not in JD skills
  - s3_12_no_measurable_achievements|j02_frontend_intern: has Git, reported not in JD skills
- Ranking order errors:
  - s3_01_strong: j07_fullstack_sde (grade 1) ranked above j04_ml_intern (grade 2)
  - s3_06_detailed_projects: j01_backend_intern (grade 2) ranked above j04_ml_intern (grade 3)
  - s3_06_detailed_projects: j03_data_analyst (grade 1) ranked above j04_ml_intern (grade 3)
  - s3_06_detailed_projects: j06_devops_intern (grade 2) ranked above j04_ml_intern (grade 3)
  - s3_11_measurable_achievements: j02_frontend_intern (grade 0) ranked above j04_ml_intern (grade 1)
  - s3_11_measurable_achievements: j07_fullstack_sde (grade 0) ranked above j04_ml_intern (grade 1)

Timings (median / max ms):
- compare_ms: 18.9 / 35.74
- rank_8_jobs_ms: 98.6 / 178.64

| Student | Top opening | Grades in ranked order | Marked suitable |
|---|---|---|---|
| s3_01_strong | j01_backend_intern | [3, 2, 2, 1, 2, 1, 0, 0] | j01_backend_intern, j03_data_analyst, j06_devops_intern, j04_ml_intern |
| s3_06_detailed_projects | j01_backend_intern | [2, 2, 1, 3, 1, 0, 0, 0] | j01_backend_intern, j06_devops_intern, j03_data_analyst, j04_ml_intern |
| s3_08_no_work_experience | j05_embedded_intern | [3, 1, 0, 0, 0, 0, 0, 0] | j05_embedded_intern |
| s3_11_measurable_achievements | j06_devops_intern | [3, 2, 1, 0, 0, 1, 0, 0] | j06_devops_intern, j01_backend_intern, j03_data_analyst |
| s3_12_no_measurable_achievements | j02_frontend_intern | [2, 1, 1, 1, 1, 0, 0, 0] | - |
| r_frontend | j02_frontend_intern | [3, 1, 0, 0, 0, 0, 0, 0] | j02_frontend_intern |
| r_data | j03_data_analyst | [3, 1, 0, 0, 0, 0, 0, 0] | j03_data_analyst, j01_backend_intern |

## 7. Acceptance criteria check

| Criterion | Where it is met | Tested by |
|---|---|---|
| US-11 AC1 compare resume with JD requirements | `JobMatchingWorkflow.compare()` | `test_job_matching_workflow.py` |
| US-11 AC2 related / equivalent skills considered | Module B equivalence + Module D partial / either-or | `test_skill_gap_analyzer.py`, skill-pair eval (24/24) |
| US-11 AC3 matching and missing shown clearly | `SkillGapReport` matched / partial / missing lists | `test_matching_and_missing_separate` |
| US-12 AC1 relevant opportunities shown | `OpportunityRanker.rank()` | `test_opportunity_ranker.py`, ranking eval |
| US-12 AC2 organised by relevance | eligible first, then relevance; reasons per position | `test_eligible_before_not_eligible_then_by_relevance` |
| US-12 AC3 tell the user when nothing fits | `guidance_message`, `has_suitable_matches` | `test_no_suitable_match_message`, `test_empty_input` |
| US-13 AC1 matching and missing shown separately | separate lists per status | `test_required_preferred_and_soft_are_separate` |
| US-13 AC2 required vs preferred distinguished | separate required / preferred lists | same, + JD level accuracy 1.0 |
| US-13 AC3 related skills handled appropriately | `partial` status, related skills you have, no false equivalence | `test_related_skill_is_partial_not_missing`, false-equivalence rate 0.0 |

## 8. How to re-run

```
cd backend
python -m pytest tests/nlp -q                      # NLP layer
python -m pytest tests -q                          # whole backend (after the fixes PR)
python scripts/evaluate_nlp_sprint4.py             # Sprint 4 metrics
ruff check backend                                 # CI lint (from repo root)
```
