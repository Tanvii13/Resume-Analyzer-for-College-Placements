# Sprint 5 – Complete Testing Report

Resume Analyzer for College Placements · EPIC 5 Placement Staff Access and Reporting
(US-14 staff view, US-15 placement dashboard and reports, US-16 roles, US-17 privacy,
US-18 decision support)

Scope: complete testing of Sprint 5. That covers the NLP Modules A–E and the Sprint 5 backend
features (RBAC / admin roles, staff access and counsellor reviews, privacy masking, data
retention, placement dashboard), run on the latest `main` (ce5b88d) with the Sprint 5 NLP
changes applied.

## 1. Summary

| Area | Status |
|---|---|
| NLP Module A – Staff analysis insights | Done earlier; tested here through the workflow (passes; one wording issue, §5) |
| NLP Module B – Versioning | Done earlier; tested here (passes) |
| NLP Module C – Historical reprocessing | Done earlier; tested here (passes) |
| NLP Module D – Placement reports and insights (US-15) | **Done** (this PR) |
| NLP Module E – Integration, evaluation and testing | **Done** (this PR) |
| Backend RBAC, staff access, counsellor reviews | Works against a real PostgreSQL database |
| Backend placement dashboard (`/dashboard/*`) | **Broken**: returns 500 (§4.1) |
| Data retention / erasure | Code and tests sit in a root-level `app/` folder, not in `backend/` (§4.2) |
| Backend using the NLP placement report | **Not yet**; wiring is described in `NLP_SPRINT_5_INTEGRATION_GUIDE.md` |

## 2. What was built (NLP, `backend/app/nlp/placement_reports/`)

| File | Purpose |
|---|---|
| `schemas.py` | `StudentRecord` input and `PlacementReport` output (statistics, gaps, weaknesses, training, insights, limitations, privacy) |
| `training_catalog.py` | Editable list of workshops and bootcamps, each tied to the weaknesses or skill categories it addresses |
| `builder.py` | `build_placement_report()` – Module D aggregation with privacy checks |
| `workflow.py` | `Sprint5Workflow` – Module E integration of Sprint 2–4 with Modules A, B, C and D |
| `scripts/evaluate_nlp_sprint5.py` | Labelled evaluation of the report against the Sprint 3 and Sprint 4 hand labels |
| `tests/nlp/test_placement_reports.py` | 34 tests for Module D |
| `tests/nlp/test_sprint5_integration.py` | 24 tests for Module E |

## 3. Test results

| Suite | Result |
|---|---|
| NLP tests (`backend/tests/nlp`), Sprints 2–5 | **706 passed, 2 skipped** (648 before this PR; 58 new) |
| Whole backend, no database | 857 passed, 21 failed – all 21 need `DATABASE_URL` |
| Whole backend, with PostgreSQL 16 and all migrations applied | **873 passed, 5 failed** (§4.3) |
| Frontend (`frontend/tests`) | **35 passed** |
| Root-level `tests/test_data_retention.py` | 5 passed |
| `scripts/evaluate_nlp_sprint4.py` | Runs; same results as Sprint 4 (regression check) |
| `scripts/evaluate_nlp_sprint5.py` | See §3.2 |
| Lint (`ruff` 0.9.10, default rules and `main`'s `ruff.toml`) | Clean for all new files |

### 3.1 Module E checks

| Requirement | How it was tested | Result |
|---|---|---|
| Integrate Modules A, B, C, D | `Sprint5Workflow` runs profile → analysis → job fits → staff view (A), attaches version metadata (B), reprocesses stored results (C) and builds the report (D) | Pass |
| Compatible with existing data structures | Workflow outputs are the unchanged Sprint 2–4 types; scores and job relevance equal the stand-alone Sprint 3/4 results; report JSON stored in and reloaded from the existing `placement_reports` table gives an identical report | Pass |
| Individual student workflow | All stages "ok" for 13 labelled resumes; staff view score equals the analysis score | Pass |
| Aggregate analytics and report generation | Statistics recomputed independently in tests; every count checked per student | Pass |
| Regression | Full NLP suite, both evaluation scripts, frontend suite and full backend suite | Pass (failures in §4 are unrelated to NLP) |
| Missing data | Empty and unreadable resumes, empty job descriptions, records with no data, duplicates, profile-only and staff-analysis-only records, no job data, an empty batch, a failing stage | Pass – each case is counted in `coverage` and explained in `limitations` |
| Output consistency | Same input gives byte-identical JSON; input order does not change the report; inputs are not modified; JSON round-trip | Pass |
| Privacy safeguards | No name, email, phone, filename or id from 20 students appears in the report; a planted leak raises `PrivacyViolationError`; departments under 5 students are hidden | Pass |
| Historical versions | Reprocessing gives the same score; an unsupported old version or configuration is reported and the stored result is kept | Pass |

### 3.2 Labelled evaluation (`python scripts/evaluate_nlp_sprint5.py`)

| Check | Result |
|---|---|
| Weakness counts within the range implied by the Sprint 3 labels | 19 / 19 issues |
| Missing-skill counts within the range implied by the Sprint 4 gap labels | 13 / 13 skills |
| Personal data in the report | 0 leaks |
| Deterministic | Yes |
| Stage failures | 0 |
| Time for 13 students plus 6 resume–job pairs | about 0.6 s |

### 3.3 Backend API smoke test (FastAPI TestClient, real PostgreSQL)

| Request | Expected | Result |
|---|---|---|
| Register / login / `GET /auth/me` | 201 / 200 / 200 | Pass |
| `POST /resumes/upload` (sample DOCX) | 200 | Pass |
| `PUT /admin/users/{id}/role` as admin | 200 | Pass |
| Same as student / with invalid role | 403 / 400 | Pass |
| `GET /officer/students/{id}/resume-analysis` as officer / as student | 200 / 403 | Pass |
| `POST /officer/.../reviews` as counsellor / as officer | 200 / 403 | Pass |
| `GET /dashboard/overview`, `GET /dashboard/skill-deficits` as officer | 200 | **500** |
| `/dashboard/overview` as student / no token | 403 / 401 | Pass |

## 4. Issues found outside the NLP code (for the owners)

### 4.1 Placement dashboard returns 500 (backend, US-15)

`app/services/dashboard_service.py` reads the tables `resume_improvement_logs` and
`resume_jd_matches` (and writes batch statistics), but no migration in the repository creates
them. With every migration applied, `/dashboard/overview` and `/dashboard/skill-deficits`
fail with `UndefinedTable: relation "resume_improvement_logs" does not exist`. Fix: add a
migration for these tables, or read from the existing tables (`resume_analyses`,
`resume_jd_comparisons`). The NLP `PlacementReport` can also supply this data (see the
integration guide).

### 4.2 Files uploaded to the repository root

`main` has a second copy of the backend at the repository root (`app/`, `tests/`,
`database/`, `main.py`, `requirements.txt`). The Sprint 5 data-retention feature
(`app/services/retention_service.py`, `tests/test_data_retention.py`) exists only there, so it
is not part of the running backend in `backend/`. The base schema and the Sprint 1–5 SQL
migrations are also only at the root (`database/`), while `backend/database/migration/` has
only the Sprint 4 officer reviews and Sprint 5 RBAC files. Fix: move the retention service and
its tests into `backend/`, keep one `database/` folder, and remove the duplicate root copy.

### 4.3 Persistence service tests out of date

`tests/test_persistence_service.py` (5 tests) mocks `connection.cursor()`, but
`persistence_service.py` now calls `connection.execute()`. The tests fail with or without a
database. Fix: update the mocks to the current code.

### 4.4 Frontend staff dashboard not connected

The Flask staff dashboard computes its own figures from in-memory data and does not call the
backend dashboard or the NLP report.

## 5. NLP observations (not fixed in this PR)

- Sprint 3 strengths are generous for weak resumes. For the labelled weak resume (score 35,
  "Needs Improvement") the strengths include "Comprehensive portfolio of applied projects"
  (two projects, one untitled) and two near-identical "clear document structure" lines.
  Module A shows these strengths to staff as they are. The text comes from
  `app/nlp/scoring/section_scoring.py`; a minimum project count and de-duplication would fix it.
- `IMP_MISSING_SOFT_SKILLS` is reported for about 75% of the fixture resumes, so the soft-skills
  workshop appears in most reports. That matches the Sprint 3 rule, but the rule may be stricter
  than placement staff expect.
- The report recognises only skills in the taxonomy; skills outside it are not counted as gaps
  or strengths. The report states this in `limitations`.

## 6. How to reproduce

```bash
cd backend
export AUTH_SECRET_KEY=test-secret-key-for-testing-at-least-32-chars-long!
python -m pytest tests/nlp -q                 # NLP, Sprints 2-5
python scripts/evaluate_nlp_sprint5.py        # labelled evaluation
python -m pytest -q                           # whole backend (set DATABASE_URL for DB tests)
cd ../frontend && python -m pytest -q
```

For the database tests: create a PostgreSQL database, apply `database/schema.sql` and the files
in `database/migration/` (root) and `backend/database/migration/`, then set
`DATABASE_URL=postgresql://user@host:port/dbname`.
