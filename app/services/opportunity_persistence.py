
from uuid import UUID
from psycopg.types.json import Jsonb

from app.database import get_connection


class OpportunityNotFoundError(Exception):
    pass


def _validate_uuid(value):
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid opportunity ID") from exc


def _validate_skills(value, field):
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")

    cleaned = []
    for skill in value:
        if not isinstance(skill, str) or not skill.strip():
            raise ValueError(f"{field} must contain non-empty strings")
        cleaned.append(skill.strip())

    return cleaned


def create_opportunity(data):
    title = str(data.get("title", "")).strip()
    company = str(data.get("company", "")).strip()

    if not title or not company:
        raise ValueError("Title and company are required")

    required = _validate_skills(
        data.get("required_skills", []), "required_skills"
    )
    preferred = _validate_skills(
        data.get("preferred_skills", []), "preferred_skills"
    )

    min_cgpa = data.get("min_cgpa")
    if min_cgpa is not None and not 0 <= float(min_cgpa) <= 10:
        raise ValueError("min_cgpa must be between 0 and 10")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO opportunities (
                    title, company, description,
                    required_skills, preferred_skills,
                    min_cgpa, deadline
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, title, company, description,
                          required_skills, preferred_skills,
                          min_cgpa, deadline, is_active, created_at
                """,
                (
                    title,
                    company,
                    data.get("description"),
                    Jsonb(required),
                    Jsonb(preferred),
                    min_cgpa,
                    data.get("deadline"),
                ),
            )
            row = cur.fetchone()

    return _format_opportunity(row)


def _format_opportunity(row):
    return {
        "id": str(row[0]),
        "title": row[1],
        "company": row[2],
        "description": row[3],
        "required_skills": row[4],
        "preferred_skills": row[5],
        "min_cgpa": float(row[6]) if row[6] is not None else None,
        "deadline": row[7],
        "is_active": row[8],
        "created_at": row[9],
    }


def get_opportunities(active_only=True):
    query = """
        SELECT id, title, company, description,
               required_skills, preferred_skills,
               min_cgpa, deadline, is_active, created_at
        FROM opportunities
    """

    if active_only:
        query += " WHERE is_active = TRUE"

    query += " ORDER BY created_at DESC"

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

    return [_format_opportunity(row) for row in rows]


def update_opportunity_status(opportunity_id, is_active):
    opportunity_id = _validate_uuid(opportunity_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE opportunities
                SET is_active = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id
                """,
                (bool(is_active), opportunity_id),
            )
            row = cur.fetchone()

    if row is None:
        raise OpportunityNotFoundError("Opportunity not found")

    return {"id": str(row[0]), "is_active": bool(is_active)}
