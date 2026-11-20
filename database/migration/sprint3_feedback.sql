
-- ============================================================
-- Sprint 3 Migration: Feedback & Explainability
-- Run AFTER sprint2_schema.sql
--
-- Covers:
-- US-08: Identify Areas That Need Improvement
-- US-09: Get Resume Improvement Suggestions
-- US-10: Understand the Score and Recommendations
--
-- Requirements:
-- FR-06, FR-07, FR-11
-- ============================================================

BEGIN;

-- ============================================================
-- 1. ANALYSIS_FEEDBACK
-- Stores specific areas that need improvement in a resume.
-- ============================================================

CREATE TABLE IF NOT EXISTS analysis_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    analysis_id UUID NOT NULL
        REFERENCES resume_analyses(id)
        ON DELETE CASCADE,

    category VARCHAR(30) NOT NULL
        CHECK (
            category IN (
                'skills',
                'projects',
                'education',
                'experience',
                'formatting',
                'general'
            )
        ),

    severity VARCHAR(10) NOT NULL DEFAULT 'medium'
        CHECK (
            severity IN ('low', 'medium', 'high')
        ),

    title VARCHAR(200) NOT NULL,

    description TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_feedback_analysis
    ON analysis_feedback(analysis_id);

CREATE INDEX IF NOT EXISTS idx_analysis_feedback_category
    ON analysis_feedback(analysis_id, category);


-- ============================================================
-- 2. IMPROVEMENT_SUGGESTIONS
-- Stores actionable suggestions linked to feedback.
-- ============================================================

CREATE TABLE IF NOT EXISTS improvement_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    feedback_id UUID NOT NULL
        REFERENCES analysis_feedback(id)
        ON DELETE CASCADE,

    suggestion_text TEXT NOT NULL,

    priority VARCHAR(10) NOT NULL DEFAULT 'medium'
        CHECK (
            priority IN ('low', 'medium', 'high')
        ),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_improvement_suggestions_feedback
    ON improvement_suggestions(feedback_id);


-- ============================================================
-- 3. SCORE_EXPLANATIONS
-- Stores explanations for individual analysis scores.
-- ============================================================

CREATE TABLE IF NOT EXISTS score_explanations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    analysis_id UUID NOT NULL
        REFERENCES resume_analyses(id)
        ON DELETE CASCADE,

    score_category VARCHAR(30) NOT NULL
        CHECK (
            score_category IN (
                'overall',
                'skills',
                'projects',
                'education',
                'experience',
                'formatting',
                'placement_readiness'
            )
        ),

    score NUMERIC(5,2) NOT NULL
        CHECK (score >= 0 AND score <= 100),

    explanation TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (analysis_id, score_category)
);

CREATE INDEX IF NOT EXISTS idx_score_explanations_analysis
    ON score_explanations(analysis_id);


COMMIT;

