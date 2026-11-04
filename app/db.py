"""The app's SQLite database, <data folder>/bsg.sqlite (PLAN-app.md §7).

The schema is versioned with PRAGMA user_version: each step adds its tables in a new numbered migration, and opening
the database applies the missing ones. Step 2 (users and login): users, sessions, login_attempts. Step 3 (storage):
jobs, runs, approvals, flags, escalations, ai_calls, audit.

Jobs and runs are keyed by their folder name and run number, not by row ids, and the history tables (approvals,
flags, escalations, ai_calls, audit) refer to them that way. So `python -m app.storage rebuild-index` can rebuild
the jobs and runs tables from the folders without breaking the history. audit is append-only: triggers in the
database refuse every UPDATE and DELETE, whoever runs them.

WAL mode: a page can read while a run writes (PLAN-app.md §7)."""
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
    # 2: storage (§11 step 3)
    """
    CREATE TABLE jobs (
        folder TEXT PRIMARY KEY COLLATE NOCASE,   -- jobs/<folder>/, the job's prefix; unique ignoring case (Windows)
        prefix TEXT NOT NULL,
        title TEXT NOT NULL,
        site TEXT NOT NULL DEFAULT '',
        kind TEXT NOT NULL,                       -- standard / corner / U / fire door
        created_at REAL NOT NULL,
        updated_at REAL NOT NULL
    );
    CREATE TABLE runs (
        job TEXT NOT NULL REFERENCES jobs(folder) ON DELETE CASCADE,
        number INTEGER NOT NULL,                  -- runs/0001, ...; never reused
        status TEXT NOT NULL CHECK (status IN ('running', 'done', 'failed', 'interrupted')),
        started_at REAL NOT NULL,
        started_by INTEGER REFERENCES users(id),
        finished_at REAL,
        error TEXT,
        PRIMARY KEY (job, number)
    );
    CREATE TABLE approvals (
        id INTEGER PRIMARY KEY,
        job TEXT NOT NULL,
        run INTEGER NOT NULL,
        user_id INTEGER NOT NULL REFERENCES users(id),
        at REAL NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        UNIQUE (job, run)
    );
    CREATE TABLE ai_calls (                       -- empty until the AI reviewer (§11 steps 9-12)
        id INTEGER PRIMARY KEY,
        job TEXT NOT NULL,
        run INTEGER,
        kind TEXT NOT NULL CHECK (kind IN ('input_review', 'output_review', 'explain')),
        model TEXT NOT NULL,
        served_model TEXT,
        input_tokens INTEGER,
        output_tokens INTEGER,
        cost_usd REAL,
        stop_reason TEXT,
        ok INTEGER NOT NULL,
        error TEXT,
        review_file TEXT,                         -- reviews/<file> in the job folder
        user_id INTEGER REFERENCES users(id),
        created_at REAL NOT NULL
    );
    CREATE TABLE flags (                          -- empty until the AI reviewer
        id INTEGER PRIMARY KEY,
        job TEXT NOT NULL,
        run INTEGER,                              -- NULL for the input review
        stage TEXT NOT NULL CHECK (stage IN ('input', 'output')),
        category TEXT NOT NULL,
        level TEXT NOT NULL CHECK (level IN ('safety', 'normal')),
        title TEXT NOT NULL,
        what_i_saw TEXT NOT NULL,
        rule_ref TEXT NOT NULL DEFAULT '',
        evidence TEXT,
        suggestion TEXT,                          -- JSON: [{field, value, reason}]
        ai_call_id INTEGER REFERENCES ai_calls(id),
        created_at REAL NOT NULL,
        answer TEXT CHECK (answer IN ('yes', 'no', 'not_sure')),
        answered_by INTEGER REFERENCES users(id),
        answered_at REAL,
        comment TEXT
    );
    CREATE TABLE escalations (                    -- empty until the AI reviewer
        id INTEGER PRIMARY KEY,
        job TEXT NOT NULL,
        run INTEGER,
        flag_id INTEGER REFERENCES flags(id),
        to_user INTEGER REFERENCES users(id),     -- NULL = either Gus or his boss
        reason TEXT NOT NULL,
        question TEXT NOT NULL,
        created_by INTEGER REFERENCES users(id),
        created_at REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'answered')),
        answer TEXT,
        answered_by INTEGER REFERENCES users(id),
        answered_at REAL
    );
    CREATE TABLE audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        at REAL NOT NULL,
        user_id INTEGER REFERENCES users(id),     -- NULL for the app itself (e.g. the scheduled backup)
        action TEXT NOT NULL,                     -- e.g. job.created, run.started, run.finished, backup.done
        job TEXT,
        run INTEGER,
        detail TEXT NOT NULL DEFAULT '{}'         -- JSON
    );
    CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END;
    CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT, 'audit is append-only'); END;
    CREATE INDEX audit_job ON audit(job, run);
    CREATE INDEX flags_job ON flags(job, run);
    CREATE INDEX ai_calls_created ON ai_calls(created_at);
    """,
]


def connect(settings):
    """An open connection with the schema up to date. Use as a context manager (commits on success)."""
    conn = sqlite3.connect(settings.data_dir / "bsg.sqlite", timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")      # stored in the file; readers don't wait for a writer
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA foreign_keys = ON")
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for n, sql in enumerate(MIGRATIONS[version:], start=version + 1):
        with conn:
            conn.executescript(sql)
            conn.execute(f"PRAGMA user_version = {n}")
    return conn
