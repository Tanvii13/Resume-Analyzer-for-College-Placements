import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Create a connection to the Resume Analyzer PostgreSQL database."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Configure it in the backend .env file."
        )

    return psycopg.connect(database_url, connect_timeout=5)
