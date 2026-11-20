
-- Sprint 5: Role-Based Access Control audit trail
-- Records administrator role changes.

BEGIN;

CREATE TABLE IF NOT EXISTS role_change_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    actor_user_id UUID NOT NULL
        REFERENCES users(id) ON DELETE RESTRICT,

    target_user_id UUID NOT NULL
        REFERENCES users(id) ON DELETE RESTRICT,

    old_role VARCHAR(40) NOT NULL,
    new_role VARCHAR(40) NOT NULL,

    action VARCHAR(40) NOT NULL DEFAULT 'role_updated'
        CHECK (action = 'role_updated'),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_role_audit_actor
    ON role_change_audit_log(actor_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_role_audit_target
    ON role_change_audit_log(target_user_id, created_at DESC);

COMMIT;
