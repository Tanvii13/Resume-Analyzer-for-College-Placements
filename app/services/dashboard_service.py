from psycopg.types.json import Jsonb
from collections import Counter

from app.database import get_connection


def calculate_batch_metrics(batch_year):
    if not isinstance(batch_year, int):
        raise ValueError("batch_year must be an integer")

    with get_connection() as conn:
        with conn.cursor() as cur:

            # Latest readiness score for each student's resume.
            cur.execute(
                """
                WITH latest_scores AS (
                    SELECT DISTINCT ON (r.user_id)
                        r.user_id,
                        u.department,
                        l.overall_score
                    FROM resume_improvement_logs l
                    JOIN resumes r ON r.id = l.resume_id
                    JOIN users u ON u.id = r.user_id
                    WHERE u.batch_year = %s
                      AND l.overall_score IS NOT NULL
                    ORDER BY r.user_id, l.created_at DESC
                )
                SELECT
                    department,
                    COUNT(DISTINCT user_id),
                    ROUND(AVG(overall_score), 2)
                FROM latest_scores
                GROUP BY department
                ORDER BY department
                """,
                (batch_year,),
            )

            department_rows = cur.fetchall()

            # Count students, not resumes, in the selected batch.
            cur.execute(
                """
                SELECT COUNT(DISTINCT r.user_id)
                FROM resume_improvement_logs l
                JOIN resumes r ON r.id = l.resume_id
                JOIN users u ON u.id = r.user_id
                WHERE u.batch_year = %s
                """,
                (batch_year,),
            )
            total_students = cur.fetchone()[0]

            # Latest match per student and job, then count missing skills.
            cur.execute(
                """
                WITH latest_matches AS (
                    SELECT DISTINCT ON (m.user_id, m.job_description_id)
                        m.user_id,
                        m.job_description_id,
                        m.missing_skills
                    FROM resume_jd_matches m
                    JOIN users u ON u.id = m.user_id
                    WHERE u.batch_year = %s
                    ORDER BY
                        m.user_id,
                        m.job_description_id,
                        m.created_at DESC
                )
                SELECT missing_skills
                FROM latest_matches
                """,
                (batch_year,),
            )

            missing_rows = cur.fetchall()

    skill_counts = Counter()

    for row in missing_rows:
        skills = row[0] or []
        for skill in skills:
            if isinstance(skill, str) and skill.strip():
                skill_counts[skill.strip()] += 1

    top_missing_skills = [
        {"skill": skill, "count": count}
        for skill, count in skill_counts.most_common(5)
    ]

    departments = [
        {
            "department": row[0] or "Unspecified",
            "students_analyzed": row[1],
            "average_readiness_score": float(row[2] or 0),
        }
        for row in department_rows
    ]

    return {
        "batch_year": batch_year,
        "total_students_analyzed": total_students,
        "department_metrics": departments,
        "top_missing_skills": top_missing_skills,
        "privacy_note": (
            "This report contains aggregated batch-level information "
            "and does not expose individual student resumes."
        ),
    }


def save_batch_statistics(batch_year, metrics):
    with get_connection() as conn:
        with conn.cursor() as cur:
            for department in metrics["department_metrics"]:
                cur.execute(
                    """
                    INSERT INTO placement_statistics (
                        batch_year,
                        department,
                        total_students_analyzed,
                        average_readiness_score,
                        top_missing_skills,
                        generated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (batch_year, department)
                    DO UPDATE SET
                        total_students_analyzed =
                            EXCLUDED.total_students_analyzed,
                        average_readiness_score =
                            EXCLUDED.average_readiness_score,
                        top_missing_skills =
                            EXCLUDED.top_missing_skills,
                        generated_at = NOW()
                    """,
                    (
                        batch_year,
                        department["department"],
                        department["students_analyzed"],
                        department["average_readiness_score"],
                        Jsonb(metrics["top_missing_skills"]).Jsonb(metrics["top_missing_skills"]),
                    ),
                )

    return {"message": "Placement statistics saved successfully"}
