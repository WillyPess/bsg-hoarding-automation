"""The app's SQLite database, <data folder>/bsg.sqlite (PLAN-app.md §7).

The schema is versioned with PRAGMA user_version: each step adds its tables in a new numbered migration, and opening
the database applies the missing ones. Step 2 (users and login): users, sessions, login_attempts. The jobs, runs,
flags and audit tables come in step 3."""
import sqlite3

MIGRATIONS = [
    # 1: users and login (§11 step 2)
    """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE COLLATE NOCASE,
        role TEXT NOT NULL CHECK (role IN ('estimator', 'manager')),
        password_hash TEXT NOT NULL,
        created_at REAL NOT NULL,
        active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE sessions (
        id_hash TEXT PRIMARY KEY,          -- sha256 of the cookie value: a copy of the database gives no live session
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        csrf TEXT NOT NULL,
        created_at REAL NOT NULL,
        last_seen REAL NOT NULL
    );
    CREATE TABLE login_attempts (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,                -- as typed, lower case
        ip TEXT NOT NULL,
        ok INTEGER NOT NULL,
        at REAL NOT NULL
    );
    CREATE INDEX login_attempts_at ON login_attempts(at);
    """,
]


def connect(settings):
    """An open connection with the schema up to date. Use as a context manager (commits on success)."""
    conn = sqlite3.connect(settings.data_dir / "bsg.sqlite", timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for n, sql in enumerate(MIGRATIONS[version:], start=version + 1):
        with conn:
            conn.executescript(sql)
            conn.execute(f"PRAGMA user_version = {n}")
    return conn
