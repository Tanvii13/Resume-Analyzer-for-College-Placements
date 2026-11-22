# NLP Sprint 5 Integration Guide (Modules D and E)

This guide covers the Sprint 5 NLP code that the backend and frontend can call. Modules A
(staff insights), B (versioning) and C (historical reprocessing) are documented in their own
files. Modules D and E are new in this sprint and are explained here.

All code lives in `backend/app/nlp/placement_reports/`. It is pure Python: no database, no file
or network access, no LLM. For the same input it always gives the same output.

## Module D: placement reports and insights (US-15)

`build_placement_report(records)` turns many students' existing NLP results into one
`PlacementReport`. It does not analyse resumes again. Each `StudentRecord` holds what is already
stored for one student:

| Field | Source | Required |
|---|---|---|
| `student_ref` | any internal id, used only to drop duplicates; never copied into the report | yes |
| `department`, `batch_year` | user / resume record | no |
| `profile` | Sprint 2 `CandidateProfile` | no |
| `analysis` | Sprint 3 `Sprint3AnalysisResult` | no (needed for scores and weaknesses) |
| `job_fits` | Sprint 4 `JobFitReport` list | no (needed for skill gaps) |
| `ranking` | Sprint 4 `OpportunityRankingReport` | no |
| `staff_analysis` | Sprint 5 Module A `StaffAnalysisResult` | no (used when `analysis` is missing) |

The report contains:

- `coverage`: how many students were supplied, analysed, compared with jobs, had low
  extraction confidence, module errors, duplicates or no usable data.
- `readiness`: mean, median, minimum, maximum and standard deviation of overall scores, the
  score-label distribution and the average of each score component (weakest first).
- `department_breakdown`: per-department average score and most common weakness. Groups with
  fewer than 5 students are hidden (`suppressed: true`).
- `resume_weaknesses`: the 10 most frequent Sprint 3 improvement issues, counted once per student.
- `common_skill_gaps`: the 10 most frequent missing required / preferred job skills, counted once
  per student, with the job titles that ask for them.
- `common_skills`: the most frequently demonstrated technical skills.
- `training_recommendations`: workshops / bootcamps from `training_catalog.py`. A program is
  recommended only when at least 2 students and at least 20% of the relevant group need it.
  Priority is high at 50% or more (30% if a critical issue is involved), medium at 30% or more,
  low otherwise. Each recommendation lists its evidence as counts.
- `insights`: short statements, each with evidence, metrics and a confidence level
  (high needs 30 or more students and good coverage, medium needs 10 or more).
- `limitations`: computed from the data supplied (small sample, partial job coverage, unreadable
  resumes, failed modules, suppressed groups, mixed versions, and what the system cannot know).
- `privacy`, `decision_support_note`, `source_versions`, `configuration`, `report_version`.

Counting rules: percentages of weaknesses use students with a resume analysis as the
denominator. Skill-gap percentages use students who were compared with at least one job.

### Privacy safeguards

- Only counts and percentages are produced. Names, emails, phone numbers, profile links,
  student ids, filenames and resume text are never copied.
- Before returning, the builder searches the serialised report for every student's name, email,
  phone, links, filename and reference. If any is found it raises `PrivacyViolationError`
  instead of returning the report.
- Departments under `min_group_size` (default 5) are suppressed, and a whole cohort under that
  size sets `privacy.small_cohort_warning`.

## Module E: integrated workflow

`Sprint5Workflow` joins Sprint 2-4 with Modules A-D:

```python
from app.nlp import Sprint5Workflow

wf = Sprint5Workflow()

# One student, fresh analysis: profile -> Sprint 3 analysis -> job fits -> staff view (A)
student = wf.analyze_student(raw_text, "resume.pdf", job_descriptions=[jd_text],
                             student_ref=str(resume_id), department="CSE", batch_year=2026)
student.record.staff_analysis     # Module A result for the staff page
student.version_metadata          # Module B snapshot, store it next to the result
student.stage_status, student.errors

# Results already in the database; optionally regenerate them (Module C)
stored = wf.from_stored(profile, analysis=old_analysis, job_fits=old_fits, reprocess=True,
                        jobs=[parsed_job, ...])

# Batch report for the placement dashboard (Module D)
report = wf.build_report([student, stored, ...], generated_at=now.isoformat())
report.model_dump(mode="json")    # ready for an API response
```

- A failing stage is recorded in `stage_status` ("failed") and `errors`; the other stages still
  run, so one bad resume never stops a batch.
- `from_stored` never edits the stored objects. If a stored result's version cannot be
  reprocessed (`UnsupportedHistoricalVersionError`), the stored result is kept and the error is
  reported.
- `analyze_batch(resumes, job_descriptions)` parses each job description once and analyses a
  list of `{"raw_text", "filename", "student_ref", "department", "batch_year"}` dicts.

## Suggested backend wiring (owned by the backend team)

1. A staff-only endpoint, for example `GET /dashboard/report?batch_year=2026`, protected with the
   existing `require_staff_or_counselor` dependency.
2. Load each student's latest stored profile / analysis / job comparisons, wrap them with
   `wf.from_stored(...)`, call `wf.build_report(...)` and return `report.model_dump(mode="json")`.
3. The Sprint 5 migration already has a `placement_reports` table. A report can be stored as
   `report_type='overall_summary'`, `title=report.title`, `report_data=report.model_dump_json()`.
   This was tested: the stored JSON loads back into an identical `PlacementReport`.

## Evaluation

Run from `backend/`:

```bash
python scripts/evaluate_nlp_sprint5.py
```

It runs the workflow on the labelled fixture resumes and checks that the report's weakness and
skill-gap counts fall within the ranges implied by the hand-written Sprint 3 and Sprint 4 labels,
that no personal data appears in the report and that the output is deterministic.
