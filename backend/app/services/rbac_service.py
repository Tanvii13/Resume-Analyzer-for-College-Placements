
from uuid import UUID

from app.database import get_connection
from app.services.audit_logger import log_role_change


# Roles supported by the application.
# career_counselor is retained for Sprint 4 compatibility.
ALLOWED_ROLES = {
    "student",
    "placement_officer",
    "admin",
    "career_counselor",
}


class RBACError(Exception):
    """Base exception for role-based access control operations."""


class InvalidRoleError(RBACError):
    """Raised when an unsupported role is requested."""


class UserNotFoundError(RBACError):
    """Raised when the requested user does not exist."""


class UnauthorizedActorError(RBACError):
    """Raised when the user performing the action is not an administrator."""


def validate_role(role: str) -> str:
    """Validate and normalize a role name."""

    if not isinstance(role, str):
        raise InvalidRoleError("Role must be a string.")

    normalized_role = role.strip().lower()

    if normalized_role not in ALLOWED_ROLES:
        raise InvalidRoleError(
            f"Unsupported role: {normalized_role}"
        )

    return normalized_role


def get_user_roles(user_id: str) -> list[str]:
    """Retrieve all roles assigned to an active user."""

    try:
        parsed_user_id = UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid user ID format.")

    with get_connection() as conn:
        user = conn.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s AND is_active = TRUE
            """,
            (parsed_user_id,),
        ).fetchone()

        if user is None:
            raise UserNotFoundError("User not found or inactive.")

        rows = conn.execute(
            """
            SELECT r.name
            FROM user_roles AS ur
            JOIN roles AS r ON r.id = ur.role_id
            WHERE ur.user_id = %s
            ORDER BY r.name
            """,
            (parsed_user_id,),
        ).fetchall()

    return [row[0] for row in rows]


def update_user_role(
    user_id: str,
    new_role: str,
    actor_email: str,
) -> dict:
    """
    Replace a user's role and record the change in the audit log.

    The administrator is verified using their authenticated email.
    The role update and audit entry execute in the same transaction.
    """

    # Validate the target user's UUID.
    try:
        parsed_user_id = UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid user ID format.")

    # Validate administrator identity.
    if not isinstance(actor_email, str) or not actor_email.strip():
        raise UnauthorizedActorError("Invalid administrator identity.")

    normalized_actor_email = actor_email.strip().lower()

    # Validate the requested role.
    normalized_role = validate_role(new_role)

    with get_connection() as conn:
        with conn.transaction():

            # Verify that the requesting user is an active administrator.
            actor = conn.execute(
                """
                SELECT u.id
                FROM users AS u
                JOIN user_roles AS ur ON ur.user_id = u.id
                JOIN roles AS r ON r.id = ur.role_id
                WHERE u.email = %s
                  AND u.is_active = TRUE
                  AND r.name = 'admin'
                """,
                (normalized_actor_email,),
            ).fetchone()

            if actor is None:
                raise UnauthorizedActorError(
                    "Only active administrators can change user roles."
                )

            parsed_actor_id = actor[0]

            # Find and lock the target user.
            user = conn.execute(
                """
                SELECT id, email
                FROM users
                WHERE id = %s
                  AND is_active = TRUE
                FOR UPDATE
                """,
                (parsed_user_id,),
            ).fetchone()

            if user is None:
                raise UserNotFoundError(
                    "User not found or inactive."
                )

            # Retrieve the target user's existing role.
            old_role_row = conn.execute(
                """
                SELECT r.name
                FROM user_roles AS ur
                JOIN roles AS r ON r.id = ur.role_id
                WHERE ur.user_id = %s
                """,
                (parsed_user_id,),
            ).fetchone()

            if old_role_row is None:
                raise UserNotFoundError(
                    "User has no assigned role."
                )

            old_role = old_role_row[0]

            # Verify that the requested role exists in the database.
            role = conn.execute(
                """
                SELECT id, name
                FROM roles
                WHERE name = %s
                """,
                (normalized_role,),
            ).fetchone()

            if role is None:
                raise InvalidRoleError(
                    f"Role '{normalized_role}' is not configured in the database."
                )

            # Replace the user's existing role.
            conn.execute(
                """
                DELETE FROM user_roles
                WHERE user_id = %s
                """,
                (parsed_user_id,),
            )

            conn.execute(
                """
                INSERT INTO user_roles (user_id, role_id)
                VALUES (%s, %s)
                """,
                (parsed_user_id, role[0]),
            )

            # Record the role change in the audit log.
            # This uses the same transaction as the role update.
            log_role_change(
                conn=conn,
                actor_user_id=parsed_actor_id,
                target_user_id=parsed_user_id,
                old_role=old_role,
                new_role=role[1],
            )

    return {
        "user_id": str(user[0]),
        "email": user[1],
        "old_role": old_role,
        "role": role[1],
        "message": "User role updated successfully.",
    }
