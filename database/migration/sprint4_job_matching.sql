
-- ============================================================
-- Sprint 4 Migration: Job / Internship Matching
-- Run AFTER sprint3_feedback.sql
--
-- Covers:
--   US-11: Compare Resume with a Job Description
--   US-12: Find Relevant Job or Internship Opportunities
--   US-13: View Matching and Missing Skills
--
-- Requirements:
--   FR-08, FR-09, FR-10, DR-02, DR-03, DR-04
--
-- Depends on Sprint 1-3 tables:
--   resumes, skills, resume_skills, resume_analyses
-- ============================================================

BEGIN;

-- ============================================================
-- 1. JOB_OPPORTUNITIES
-- Stores job/internship listings that students can be matched
-- against. Covers US-12 (Find Relevant Job or Internship
-- Opportunities).
-- ============================================================

CREATE TABLE IF NOT EXISTS job_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    title VARCHAR(200) NOT NULL,

    company VARCHAR(200),

    type VARCHAR(20) NOT NULL DEFAULT 'job'
        CHECK (type IN ('job', 'internship')),

    -- Raw job description text provided by placement cell or scraped
    description_text TEXT NOT NULL,

    -- Optional structured fields parsed from the description
    location VARCHAR(200),

    -- e.g. 'entry', 'mid', 'senior'
    experience_level VARCHAR(20)
        CHECK (
            experience_level IS NULL OR
            experience_level IN ('entry', 'mid', 'senior')
        ),

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    posted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_job_opportunities_active_posted
    ON job_opportunities(is_active, posted_at DESC);

CREATE INDEX IF NOT EXISTS idx_job_opportunities_type
    ON job_opportunities(type);


-- ============================================================
-- 2. JOB_DESCRIPTION_SKILLS
-- Skills required or preferred by a job opportunity.
-- Supports US-11 and US-13 (matching and missing skills).
-- ============================================================

CREATE TABLE IF NOT EXISTS job_description_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    job_id UUID NOT NULL
        REFERENCES job_opportunities(id)
        ON DELETE CASCADE,

    skill_id UUID NOT NULL
        REFERENCES skills(id)
        ON DELETE RESTRICT,

    -- 'required' vs 'preferred' distinction per US-13 AC-2
    importance VARCHAR(10) NOT NULL DEFAULT 'required'
        CHECK (importance IN ('required', 'preferred')),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (job_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_jd_skills_job
    ON job_description_skills(job_id);

CREATE INDEX IF NOT EXISTS idx_jd_skills_skill
    ON job_description_skills(skill_id);


-- ============================================================
-- 3. RESUME_JD_COMPARISONS
-- Records each time a student compares their resume to a job.
-- Covers US-11 (Compare Resume with a Job Description).
-- Stores overall match score and status of the comparison.
-- ============================================================

CREATE TABLE IF NOT EXISTS resume_jd_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    resume_id UUID NOT NULL
        REFERENCES resumes(id)
        ON DELETE CASCADE,

    job_id UUID NOT NULL
        REFERENCES job_opportunities(id)
        ON DELETE CASCADE,

    -- Overall percentage match (0-100)
    overall_match_score NUMERIC(5,2)
        CHECK (
            overall_match_score IS NULL OR
            (overall_match_score >= 0 AND overall_match_score <= 100)
        ),

    -- Required-skills-only match score
    required_skills_match_score NUMERIC(5,2)
        CHECK (
            required_skills_match_score IS NULL OR
            (required_skills_match_score >= 0 AND required_skills_match_score <= 100)
        ),

    status VARCHAR(20) NOT NULL DEFAULT 'processing'
        CHECK (status IN ('processing', 'completed', 'failed')),

    error_message TEXT,

    compared_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_resume_jd_comparisons_resume
    ON resume_jd_comparisons(resume_id, compared_at DESC);

CREATE INDEX IF NOT EXISTS idx_resume_jd_comparisons_job
    ON resume_jd_comparisons(job_id);


-- ============================================================
-- 4. JD_SKILL_MATCHES
-- Per-skill breakdown of a resume-vs-job comparison.
-- Covers US-13 (View Matching and Missing Skills).
-- Each row is one skill from the job description and whether
-- the student's resume matched it or not.
-- ============================================================

CREATE TABLE IF NOT EXISTS jd_skill_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    comparison_id UUID NOT NULL
        REFERENCES resume_jd_comparisons(id)
        ON DELETE CASCADE,

    skill_id UUID NOT NULL
        REFERENCES skills(id)
        ON DELETE RESTRICT,

    -- Whether the resume contained this skill (matched) or not (missing)
    -- Covers US-13 AC-1: matching and missing skills shown separately
    is_matched BOOLEAN NOT NULL,

    -- Mirrors job_description_skills.importance
    -- Covers US-13 AC-2: required vs preferred distinguished
    importance VARCHAR(10) NOT NULL DEFAULT 'required'
        CHECK (importance IN ('required', 'preferred')),

    -- Confidence that this is a genuine match (from NLP layer)
    -- Covers US-11 AC-2: related/equivalent skills considered
    match_confidence NUMERIC(5,4)
        CHECK (
            match_confidence IS NULL OR
            (match_confidence >= 0 AND match_confidence <= 1)
        ),

    -- Optional note e.g. "matched via related skill: NumPy → Python"
    -- Covers US-11 AC-2 and US-13 AC-3
    match_note VARCHAR(300),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (comparison_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_jd_skill_matches_comparison
    ON jd_skill_matches(comparison_id);

CREATE INDEX IF NOT EXISTS idx_jd_skill_matches_matched
    ON jd_skill_matches(comparison_id, is_matched);


-- ============================================================
-- 5. RESUME_JOB_RECOMMENDATIONS
-- Stores ranked job recommendations for a resume.
-- Covers US-12 AC-2: opportunities organised by relevance.
-- Generated by the backend matching engine and cached here.
-- ============================================================

CREATE TABLE IF NOT EXISTS resume_job_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    resume_id UUID NOT NULL
        REFERENCES resumes(id)
        ON DELETE CASCADE,

    job_id UUID NOT NULL
        REFERENCES job_opportunities(id)
        ON DELETE CASCADE,

    -- Relevance rank (1 = most relevant)
    rank SMALLINT NOT NULL
        CHECK (rank >= 1),

    -- Computed relevance score used for ranking
    relevance_score NUMERIC(5,2) NOT NULL
        CHECK (relevance_score >= 0 AND relevance_score <= 100),

    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (resume_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_resume_job_recommendations_resume
    ON resume_job_recommendations(resume_id, rank ASC);


COMMIT;
