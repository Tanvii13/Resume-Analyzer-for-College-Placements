-- ============================================================
-- Sprint 2 Migration: Resume Analysis & Scoring
-- Run AFTER sprint1_schema.sql (or schema.sql from Sprint 1)
--
-- Depends on Sprint 1 tables:
--   users, roles, user_roles, resumes, resume_sections
-- ============================================================

-- ============================================================
-- 1. SKILLS
-- ============================================================

CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name VARCHAR(100) NOT NULL UNIQUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 2. RESUME_SKILLS
-- ============================================================

CREATE TABLE IF NOT EXISTS resume_skills (
    resume_id UUID NOT NULL
        REFERENCES resumes(id)
        ON DELETE CASCADE,

    skill_id UUID NOT NULL
        REFERENCES skills(id)
        ON DELETE RESTRICT,

    source VARCHAR(20) NOT NULL DEFAULT 'extracted'
        CHECK (source IN ('extracted', 'manual')),

    confidence NUMERIC(5,4)
        CHECK (
            confidence IS NULL OR
            (confidence >= 0 AND confidence <= 1)
        ),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (resume_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_resume_skills_skill
    ON resume_skills(skill_id);

-- ============================================================
-- 3. RESUME_ANALYSES
-- ============================================================

CREATE TABLE IF NOT EXISTS resume_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    resume_id UUID NOT NULL
        REFERENCES resumes(id)
        ON DELETE CASCADE,

    status VARCHAR(20) NOT NULL DEFAULT 'processing'
        CHECK (
            status IN ('processing', 'completed', 'failed')
        ),

    overall_score NUMERIC(5,2)
        CHECK (
            overall_score IS NULL OR
            (overall_score >= 0 AND overall_score <= 100)
        ),

    skills_score NUMERIC(5,2)
        CHECK (
            skills_score IS NULL OR
            (skills_score >= 0 AND skills_score <= 100)
        ),

    projects_score NUMERIC(5,2)
        CHECK (
            projects_score IS NULL OR
            (projects_score >= 0 AND projects_score <= 100)
        ),

    education_score NUMERIC(5,2)
        CHECK (
            education_score IS NULL OR
            (education_score >= 0 AND education_score <= 100)
        ),

    experience_score NUMERIC(5,2)
        CHECK (
            experience_score IS NULL OR
            (experience_score >= 0 AND experience_score <= 100)
        ),

    formatting_score NUMERIC(5,2)
        CHECK (
            formatting_score IS NULL OR
            (formatting_score >= 0 AND formatting_score <= 100)
        ),

    placement_readiness_score NUMERIC(5,2)
        CHECK (
            placement_readiness_score IS NULL OR
            (
                placement_readiness_score >= 0
                AND placement_readiness_score <= 100
            )
        ),

    strengths      TEXT,
    weaknesses     TEXT,
    recommendations TEXT,
    error_message  TEXT,

    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_resume_analyses_resume
    ON resume_analyses(resume_id, started_at DESC);

-- ============================================================
-- INITIAL SKILLS SEED DATA
-- ============================================================

INSERT INTO skills (name)
VALUES
    ('C++'),
    ('C'),
    ('Python'),
    ('Java'),
    ('JavaScript'),
    ('TypeScript'),
    ('SQL'),
    ('PostgreSQL'),
    ('MySQL'),
    ('MongoDB'),
    ('DBMS'),
    ('Data Structures'),
    ('Algorithms'),
    ('Git'),
    ('GitHub'),
    ('Linux'),
    ('Docker'),
    ('React'),
    ('Node.js'),
    ('FastAPI'),
    ('Spring Boot'),
    ('Machine Learning'),
    ('Deep Learning'),
    ('Computer Networks'),
    ('Operating Systems')
ON CONFLICT (name) DO NOTHING;
