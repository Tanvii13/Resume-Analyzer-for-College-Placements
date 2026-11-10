import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()


class SQLiteConnection:
    """Lightweight SQLite compatibility wrapper for local/test usage."""

    def __init__(self, database_path: str | Path):
        self._connection = sqlite3.connect(str(database_path))
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._initialize_schema()

    def _initialize_schema(self):
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS user_roles (
                user_id TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, role_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT
            )
            """
        )
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS resumes (
                id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
                user_id TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                storage_key TEXT NOT NULL UNIQUE,
                file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx')),
                file_size_bytes INTEGER NOT NULL CHECK (file_size_bytes > 0 AND file_size_bytes <= 5242880),
                status TEXT NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'processing', 'processed', 'failed')),
                error_message TEXT,
                uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        self.execute(
            """
            INSERT OR IGNORE INTO roles (name) VALUES ('student'), ('placement_officer'), ('admin')
            """
        )
        self._connection.commit()

    @staticmethod
    def _normalize_sql(sql: str) -> str:
        return sql.replace("%s", "?")

    def execute(self, sql: str, params=None):
        params = () if params is None else params
        return self._connection.execute(self._normalize_sql(sql), params)

    @contextmanager
    def transaction(self):
        try:
            self._connection.execute("BEGIN")
            yield self
        except Exception:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        self._connection.close()
        return False


def get_connection():
    """Create a connection to the configured database or a local SQLite fallback."""
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return psycopg.connect(database_url, connect_timeout=5)

    db_path = Path(__file__).resolve().parents[1] / "resume_analyzer.db"
    return SQLiteConnection(db_path)
