# Resume Analyzer — Database

PostgreSQL 18 database schema covering Sprint 1 through Sprint 5.

---

## Sprint 1 — User Accounts & Resume Upload

Covers user stories **US-01 to US-04**.

| User Story | Description |
|---|---|
| US-01 | Account data, authentication support, and role mapping |
| US-02 | Uploaded resume metadata |
| US-03 | Parsed resume sections |
| US-04 | Resume processing status and readable error messages |

### Tables

| Table | Purpose |
|---|---|
| `users` | Student and officer accounts |
| `roles` | Role catalog (`student`, `placement_officer`, `admin`) |
| `user_roles` | Many-to-many user ↔ role mapping |
| `resumes` | Resume file metadata and processing status |
| `resume_sections` | Parsed resume content (education, skills, experience, etc.) |

---

## Sprint 2 — Resume Analysis & Scoring

Covers user stories **US-05 to US-07** and analysis-related functionality of US-08.

| User Story | Description |
|---|---|
| US-05 | Skill extraction and tagging from resume content |
| US-06 | Section-wise scoring (skills, projects, education, experience, formatting) |
| US-07 | Placement readiness score calculation |
| US-08 | AI-generated strengths, weaknesses, and recommendations |

### Tables

| Table | Purpose |
|---|---|
| `skills` | Master catalog of placement-relevant skills (25 pre-seeded) |
| `resume_skills` | Links resumes to extracted/manual skills with confidence scores |
| `resume_analyses` | Full analysis result with sub-scores, strengths, weaknesses, and recommendations |

---

## Sprint 3 — Feedback & Explainability

Covers user stories **US-08 to US-10**.

| User Story | Description |
|---|---|
| US-08 | Identify areas that need improvement |
| US-09 | Get resume improvement suggestions |
| US-10 | Understand the score and recommendations |

### Requirements

- FR-06: Identify important areas for improvement.
- FR-07: Provide improvement suggestions.
- FR-11: Provide explanations for important results.
- NFR-05: Recommendations and important results should be understandable.
- NFR-08: Interface should be readable and accessible.

### Tables

| Table | Purpose |
|---|---|
| `analysis_feedback` | Stores resume analysis feedback, improvement areas, category, and severity |
| `improvement_suggestions` | Stores actionable improvement suggestions linked to feedback |
| `score_explanations` | Stores explanations for overall and category-wise scores |

### Feedback Categories

`skills`, `projects`, `education`, `experience`, `formatting`, `general`

### Feedback Severity & Suggestion Priority

`low`, `medium`, `high`

### Score Categories

`overall`, `skills`, `projects`, `education`, `experience`, `formatting`, `placement_readiness`

Scores are constrained to the range 0–100.

---

## Sprint 4 — Job & Internship Matching

Covers user stories **US-11 to US-13**.

| User Story | Description |
|---|---|
| US-11 | Store job and internship opportunities with required skills |
| US-12 | Compare a resume against a job description and track skill matches |
| US-13 | Rank and recommend job/internship opportunities for a resume |

### Requirements

- FR-08: Store job/internship opportunities and required skills.
- FR-09: Compare resume skills against job description skills.
- FR-10: Recommend and rank job/internship opportunities.
- DR-02: Job opportunity data storage standards.
- DR-03: Resume–JD comparison data standards.
- DR-04: Skill match tracking standards.

### Tables

| Table | Purpose |
|---|---|
| `job_opportunities` | Job and internship listings with metadata |
| `job_description_skills` | Skills required by a job, with importance (required / preferred) |
| `resume_jd_comparisons` | Match scores between a resume and a job description |
| `jd_skill_matches` | Per-skill match breakdown for each comparison |
| `resume_job_recommendations` | Ranked job recommendations generated for a resume |

### Match Scores

`overall_match_score` and `required_skills_match_score` are `NUMERIC(5,2)` constrained to 0–100.  
`match_confidence` on `jd_skill_matches` is `NUMERIC(5,4)` constrained to 0–1.

### Skill Importance

`required` — must-have skills for the role.  
`preferred` — nice-to-have skills.

---

## Sprint 5 — Placement Staff Access & Reporting

Covers user stories **US-14 to US-15**.

| User Story | Description |
|---|---|
| US-14 | Placement officers and counselors view student resume analysis |
| US-15 | Placement officers view dashboard summaries and reports |

### Requirements

- FR-12: Placement staff view of student resume analysis.
- FR-13: Placement dashboard and report generation.
- DR-05: Placement data aggregation standards (aggregated stats, no individual PII in reports).
- DR-07: Data governance — all staff access to student data is audited.

### Tables

| Table | Purpose |
|---|---|
| `staff_resume_access_log` | Audit trail — records every staff access to student resume/analysis data |
| `placement_reports` | Stores generated placement summary reports with aggregated statistics |

### Access Types (`staff_resume_access_log`)

`view_analysis` · `view_resume` · `view_skills` · `view_feedback`

### Report Types (`placement_reports`)

`overall_summary` · `skills_gap` · `readiness_distribution` · `job_match_summary`

### Design Notes

- `report_data` stores aggregated cohort statistics only — no individual student PII is stored in a report row (satisfies DR-05, US-15 AC-2).
- `is_archived` is a soft-delete flag. Reports are never hard-deleted, supporting institutional data retention requirements (US-15 AC-3).
- `generated_by` uses `ON DELETE RESTRICT` — a placement officer account cannot be deleted while they own reports, preserving the audit chain.

---

## Database Setup

Make sure PostgreSQL 18 is running and the `resume_analyzer` database exists.

Open the pgAdmin Query Tool for `resume_analyzer`, or use `psql`.

### Fresh Setup (All Sprints)

Applies all tables and seed data in one shot:

```bash
psql -U postgres -d resume_analyzer -f database/schema.sql
```

### Incremental Migrations (Sprint by Sprint)

Run migration files in order on an existing database:

```bash
# Sprint 1 — run first
psql -U postgres -d resume_analyzer -f database/migration/sprint1_schema.sql

# Sprint 2 — run after Sprint 1
psql -U postgres -d resume_analyzer -f database/migration/sprint2_schema.sql

# Sprint 3 — run after Sprint 2
psql -U postgres -d resume_analyzer -f database/migration/sprint3_feedback.sql

# Sprint 4 — run after Sprint 3
psql -U postgres -d resume_analyzer -f database/migration/sprint4_job_matching.sql

# Sprint 5 — run after Sprint 4
psql -U postgres -d resume_analyzer -f database/migration/sprint5_placement_staff.sql
```

Replace `postgres` with your PostgreSQL username if different.

**Note:** Schema and migration files use `CREATE TABLE IF NOT EXISTS` and conflict-safe inserts where applicable. However, migrations must be executed in dependency order because foreign keys reference tables created in earlier sprints. `CREATE TABLE IF NOT EXISTS` does not modify existing tables.

---

## Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    USERS ||--o{ USER_ROLES : has
    ROLES ||--o{ USER_ROLES : assigned
    USERS ||--o{ RESUMES : uploads
    RESUMES ||--o{ RESUME_SECTIONS : contains
    RESUMES ||--o{ RESUME_SKILLS : has
    RESUMES ||--o{ RESUME_ANALYSES : analyzed_by
    SKILLS ||--o{ RESUME_SKILLS : tagged_in
    RESUME_ANALYSES ||--o{ ANALYSIS_FEEDBACK : produces
    ANALYSIS_FEEDBACK ||--o{ IMPROVEMENT_SUGGESTIONS : contains
    RESUME_ANALYSES ||--o{ SCORE_EXPLANATIONS : explains
    RESUMES ||--o{ RESUME_JD_COMPARISONS : compared_in
    RESUMES ||--o{ RESUME_JOB_RECOMMENDATIONS : recommended
    JOB_OPPORTUNITIES ||--o{ JOB_DESCRIPTION_SKILLS : requires
    JOB_OPPORTUNITIES ||--o{ RESUME_JD_COMPARISONS : compared_against
    JOB_OPPORTUNITIES ||--o{ RESUME_JOB_RECOMMENDATIONS : recommended_as
    SKILLS ||--o{ JOB_DESCRIPTION_SKILLS : listed_in
    RESUME_JD_COMPARISONS ||--o{ JD_SKILL_MATCHES : breaks_down_to
    SKILLS ||--o{ JD_SKILL_MATCHES : matched_as
    USERS ||--o{ STAFF_RESUME_ACCESS_LOG : "accesses as staff"
    USERS ||--o{ STAFF_RESUME_ACCESS_LOG : "accessed as student"
    RESUMES ||--o{ STAFF_RESUME_ACCESS_LOG : accessed_via
    RESUME_ANALYSES ||--o{ STAFF_RESUME_ACCESS_LOG : logged_in
    USERS ||--o{ PLACEMENT_REPORTS : generates

    USERS {
        uuid id PK
        varchar full_name
        varchar email UK
        text password_hash
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }

    ROLES {
        smallint id PK
        varchar name UK
    }

    USER_ROLES {
        uuid user_id PK, FK
        smallint role_id PK, FK
    }

    RESUMES {
        uuid id PK
        uuid user_id FK
        varchar original_filename
        text storage_key UK
        varchar file_type
        bigint file_size_bytes
        varchar status
        text error_message
        timestamptz uploaded_at
        timestamptz processed_at
    }

    RESUME_SECTIONS {
        uuid id PK
        uuid resume_id FK
        varchar section_name
        text content
        timestamptz created_at
    }

    SKILLS {
        uuid id PK
        varchar name UK
        timestamptz created_at
    }

    RESUME_SKILLS {
        uuid resume_id PK, FK
        uuid skill_id PK, FK
        varchar source
        numeric confidence
        timestamptz created_at
    }

    RESUME_ANALYSES {
        uuid id PK
        uuid resume_id FK
        varchar status
        numeric overall_score
        numeric skills_score
        numeric projects_score
        numeric education_score
        numeric experience_score
        numeric formatting_score
        numeric placement_readiness_score
        text strengths
        text weaknesses
        text recommendations
        text error_message
        timestamptz started_at
        timestamptz completed_at
    }

    ANALYSIS_FEEDBACK {
        uuid id PK
        uuid analysis_id FK
        varchar category
        varchar severity
        varchar title
        text description
        timestamptz created_at
    }

    IMPROVEMENT_SUGGESTIONS {
        uuid id PK
        uuid feedback_id FK
        text suggestion_text
        varchar priority
        timestamptz created_at
    }

    SCORE_EXPLANATIONS {
        uuid id PK
        uuid analysis_id FK
        varchar score_category
        numeric score
        text explanation
        timestamptz created_at
    }

    JOB_OPPORTUNITIES {
        uuid id PK
        varchar title
        varchar company
        varchar type
        text description_text
        varchar location
        varchar experience_level
        boolean is_active
        timestamptz posted_at
        timestamptz expires_at
    }

    JOB_DESCRIPTION_SKILLS {
        uuid id PK
        uuid job_id FK
        uuid skill_id FK
        varchar importance
        timestamptz created_at
    }

    RESUME_JD_COMPARISONS {
        uuid id PK
        uuid resume_id FK
        uuid job_id FK
        numeric overall_match_score
        numeric required_skills_match_score
        varchar status
        text error_message
        timestamptz compared_at
        timestamptz completed_at
    }

    JD_SKILL_MATCHES {
        uuid id PK
        uuid comparison_id FK
        uuid skill_id FK
        boolean is_matched
        varchar importance
        numeric match_confidence
        varchar match_note
        timestamptz created_at
    }

    RESUME_JOB_RECOMMENDATIONS {
        uuid id PK
        uuid resume_id FK
        uuid job_id FK
        smallint rank
        numeric relevance_score
        timestamptz generated_at
    }

    STAFF_RESUME_ACCESS_LOG {
        uuid id PK
        uuid staff_user_id FK
        uuid student_user_id FK
        uuid resume_id FK
        uuid analysis_id FK
        varchar access_type
        timestamptz accessed_at
    }

    PLACEMENT_REPORTS {
        uuid id PK
        uuid generated_by FK
        varchar report_type
        varchar title
        jsonb filter_parameters
        jsonb report_data
        timestamptz generated_at
        boolean is_archived
    }
```

The editable Mermaid source is also available in [`erd.mmd`](erd.mmd).

---

## Important Design Decisions

- **Private file storage:** PDF and DOCX files are stored in private file storage, not directly in PostgreSQL. The `storage_key` column references the stored file. Coordinate the storage-key format with the backend team.
- **Password security:** Never store plain-text passwords. `password_hash` must contain a secure hash generated by the authentication/backend layer.
- **Parsed content:** `resume_sections` stores extracted sections such as education, skills, projects, and experience.
- **Processing errors:** `resumes.status` and `error_message` allow the application to track processing outcomes and report invalid or unreadable files.
- **Skill confidence:** `resume_skills.confidence` (0.0–1.0) reflects how certain the AI is that a skill was found. `source` distinguishes AI-extracted skills from manually added ones.
- **Analysis scores:** All score columns in `resume_analyses` are `NUMERIC(5,2)` constrained to 0–100. A `NULL` score means the analysis has not yet completed.
- **Feedback:** `analysis_feedback` records improvement areas by category and severity. Each feedback entry belongs to an analysis.
- **Improvement suggestions:** `improvement_suggestions` stores actionable suggestions linked to feedback entries.
- **Score explanations:** `score_explanations` stores explanations for individual score categories. Each analysis can have only one explanation per score category.
- **Data integrity:** UUID identifiers, foreign keys, constraints, indexes, and timezone-aware `TIMESTAMPTZ` columns are used throughout.
- **Safe reruns:** `CREATE TABLE IF NOT EXISTS` and conflict-safe inserts support rerunning compatible schema scripts. They do not update existing table definitions.
- **File size:** Resume files must be greater than 0 bytes and no larger than 5 MiB (5,242,880 bytes), enforced by a database constraint.
- **Job matching scores:** `overall_match_score` and `required_skills_match_score` are `NUMERIC(5,2)` constrained to 0–100. `match_confidence` on `jd_skill_matches` is `NUMERIC(5,4)` constrained to 0–1.
- **Soft delete for reports:** `placement_reports` uses `is_archived` instead of hard deletion to satisfy institutional data retention requirements.
- **Audit log cascade:** When a user or resume is deleted, associated `staff_resume_access_log` rows are deleted too (consistent with right-to-erasure). If only an analysis is deleted, the log row's `analysis_id` is set to NULL — the access event is preserved.

---

## Backend Integration Notes

- Store uploaded files outside the database in private storage; save the reference in `resumes.storage_key`.
- Use `resume_sections` for parsed resume content.
- Update `resumes.status` and `error_message` when processing succeeds or fails.
- Populate `resume_skills` with extracted skills and their confidence scores after parsing.
- Insert a row into `resume_analyses` with `status = 'processing'` when analysis starts; update scores and analysis feedback fields and set `status = 'completed'` (or `'failed'`) when done.
- Store individual improvement areas in `analysis_feedback`.
- Store actionable suggestions in `improvement_suggestions`, linked to their feedback entry.
- Store score explanations in `score_explanations`, linked to the corresponding analysis and score category.
- Keep authentication and role assignment consistent with `users`, `roles`, and `user_roles`.
- Populate `job_opportunities` and `job_description_skills` when job listings are created or imported.
- Insert a row into `resume_jd_comparisons` when a comparison is started; update match scores and `status` when it completes.
- Write per-skill results into `jd_skill_matches` for each comparison.
- Insert into `resume_job_recommendations` with a rank and relevance score after generating recommendations for a resume.
- Insert a row into `staff_resume_access_log` every time a placement officer or counselor views student resume or analysis data.
- Insert into `placement_reports` when a placement officer generates a summary report; store only aggregated statistics in `report_data`, never individual student records.
- Set `placement_reports.is_archived = TRUE` to hide a report from the UI; do not hard-delete report rows.
