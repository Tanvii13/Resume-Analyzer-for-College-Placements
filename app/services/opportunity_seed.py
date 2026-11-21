
from app.database import get_connection
from app.services.opportunity_persistence import create_opportunity


SAMPLE_OPPORTUNITIES = [
    {
        "title": "Python Backend Developer",
        "company": "Example Technologies",
        "description": "Entry-level backend development opportunity.",
        "required_skills": ["Python", "SQL", "REST API"],
        "preferred_skills": ["FastAPI", "PostgreSQL", "Git"],
        "min_cgpa": 6.0,
        "deadline": None,
    },
    {
        "title": "Frontend Developer Intern",
        "company": "Example Software",
        "description": "Frontend internship for college students.",
        "required_skills": ["HTML", "CSS", "JavaScript"],
        "preferred_skills": ["React", "Git"],
        "min_cgpa": 6.5,
        "deadline": None,
    },
    {
        "title": "Data Analyst",
        "company": "Example Analytics",
        "description": "Entry-level data analysis opportunity.",
        "required_skills": ["Python", "SQL", "Excel"],
        "preferred_skills": ["Power BI", "Pandas"],
        "min_cgpa": 6.0,
        "deadline": None,
    },
]


def seed_opportunities():
    inserted = 0
    skipped = 0

    for opportunity in SAMPLE_OPPORTUNITIES:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id
                    FROM opportunities
                    WHERE LOWER(title) = LOWER(%s)
                      AND LOWER(company) = LOWER(%s)
                    LIMIT 1
                    """,
                    (opportunity["title"], opportunity["company"]),
                )
                exists = cur.fetchone()

        if exists:
            skipped += 1
            continue

        create_opportunity(opportunity)
        inserted += 1

    return {
        "inserted": inserted,
        "skipped": skipped,
        "message": "Opportunity seeding completed",
    }


if __name__ == "__main__":
    print(seed_opportunities())
