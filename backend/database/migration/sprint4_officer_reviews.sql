-- Sprint 4: Placement staff and counselor resume reviews
-- Apply after the core users, roles, and resumes tables exist.

BEGIN;

-- Ensure the counselor role can be assigned to staff accounts.
INSERT INTO roles (name)
VALUES ('career_counselor')
ON CONFLICT (name) DO NOTHING;

-- Record every authorized staff access to student resume data.
CREATE TABLE IF NOT EXISTS staff_resume_access_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    student_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    access_type VARCHAR(30) NOT NULL DEFAULT 'view_analysis'
        CHECK (access_type IN ('view_analysis', 'view_resume', 'view_skills', 'view_feedback')),
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_staff_access_log_staff
    ON staff_resume_access_log(staff_user_id, accessed_at DESC);

CREATE INDEX IF NOT EXISTS idx_staff_access_log_student
    ON staff_resume_access_log(student_user_id, accessed_at DESC);

-- Keep every review as a separate record so review history is preserved.
CREATE TABLE IF NOT EXISTS counselor_resume_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    reviewer_user_id UUID NOT NULL
        REFERENCES users(id) ON DELETE RESTRICT,

    student_user_id UUID NOT NULL
        REFERENCES users(id) ON DELETE CASCADE,

    resume_id UUID NOT NULL
        REFERENCES resumes(id) ON DELETE CASCADE,

    status VARCHAR(40) NOT NULL DEFAULT 'Pending Review'
        CHECK (
            status IN (
                'Pending Review',
                'Approved for Placement',
                'Revision Needed'
            )
        ),

    notes TEXT,

    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_counselor_reviews_resume
    ON counselor_resume_reviews(resume_id, reviewed_at DESC);

CREATE INDEX IF NOT EXISTS idx_counselor_reviews_reviewer
    ON counselor_resume_reviews(reviewer_user_id, reviewed_at DESC);

COMMIT;
