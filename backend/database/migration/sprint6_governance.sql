-- Sprint 6: Human Governance, State Machines and Override Workflows
-- US-18: Automated scores are advisory only.
-- Only authorized human staff can change candidate placement states.

BEGIN;

-- 1. Store the current governance state for each candidate.
CREATE TABLE IF NOT EXISTS candidate_governance_state (
    candidate_user_id UUID PRIMARY KEY
        REFERENCES users(id) ON DELETE RESTRICT,

    current_state VARCHAR(50) NOT NULL DEFAULT 'PENDING_OFFICER_REVIEW'
        CHECK (
            current_state IN (
                'PENDING_OFFICER_REVIEW',
                'SHORTLISTED_BY_OFFICER',
                'REJECTED_BY_OFFICER',
                'REFERRED_FOR_MANUAL_EVALUATION'
            )
        ),

    latest_advisory_score NUMERIC(5,2)
        CHECK (
            latest_advisory_score IS NULL
            OR latest_advisory_score BETWEEN 0 AND 100
        ),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Preserve every automated advisory event and human decision.
CREATE TABLE IF NOT EXISTS candidate_governance_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    candidate_user_id UUID NOT NULL
        REFERENCES users(id) ON DELETE RESTRICT,

    actor_user_id UUID
        REFERENCES users(id) ON DELETE RESTRICT,

    event_type VARCHAR(30) NOT NULL
        CHECK (event_type IN ('advisory_score', 'human_decision')),

    previous_state VARCHAR(50)
        CHECK (
            previous_state IS NULL OR previous_state IN (
                'PENDING_OFFICER_REVIEW',
                'SHORTLISTED_BY_OFFICER',
                'REJECTED_BY_OFFICER',
                'REFERRED_FOR_MANUAL_EVALUATION'
            )
        ),

    new_state VARCHAR(50)
        CHECK (
            new_state IS NULL OR new_state IN (
                'PENDING_OFFICER_REVIEW',
                'SHORTLISTED_BY_OFFICER',
                'REJECTED_BY_OFFICER',
                'REFERRED_FOR_MANUAL_EVALUATION'
            )
        ),

    advisory_score NUMERIC(5,2)
        CHECK (
            advisory_score IS NULL
            OR advisory_score BETWEEN 0 AND 100
        ),

    rationale TEXT,

    is_human_override BOOLEAN NOT NULL DEFAULT FALSE,

    advisory_metadata JSONB NOT NULL DEFAULT
        '{
            "advisory_only": true,
            "autonomous_rejection_forbidden": true,
            "requires_human_signoff": true
        }'::jsonb,

    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Human decisions require an authenticated actor and valid rationale.
    -- Automated advisory events cannot change candidate state.
    CONSTRAINT candidate_governance_audit_event_rules CHECK (
        (
            event_type = 'human_decision'
            AND actor_user_id IS NOT NULL
            AND new_state IS NOT NULL
            AND rationale IS NOT NULL
            AND CHAR_LENGTH(BTRIM(rationale)) >= 15
        )
        OR
        (
            event_type = 'advisory_score'
            AND actor_user_id IS NULL
            AND previous_state IS NULL
            AND new_state IS NULL
            AND rationale IS NULL
            AND is_human_override = FALSE
            AND advisory_score IS NOT NULL
        )
    )
);

-- 3. Support efficient candidate history and officer audit queries.
CREATE INDEX IF NOT EXISTS idx_candidate_governance_audit_candidate
    ON candidate_governance_audit(candidate_user_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_candidate_governance_audit_actor
    ON candidate_governance_audit(actor_user_id, recorded_at DESC);

CREATE INDEX IF NOT EXISTS idx_candidate_governance_audit_event
    ON candidate_governance_audit(event_type, recorded_at DESC);

COMMIT;
