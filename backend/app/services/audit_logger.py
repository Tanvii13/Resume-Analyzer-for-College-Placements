
from uuid import UUID

from psycopg import Connection


def log_role_change(
    conn: Connection,
    actor_user_id: UUID,
    target_user_id: UUID,
    old_role: str,
    new_role: str,
) -> None:
    """
    Record a user role change in the audit log.

    Uses the caller's database connection so the audit record
    participates in the same transaction as the role update.
    """

    conn.execute(
        """
        INSERT INTO role_change_audit_log (
            actor_user_id,
            target_user_id,
            old_role,
            new_role,
            action
        )
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            actor_user_id,
            target_user_id,
            old_role,
            new_role,
            "role_updated",
        ),
    )
