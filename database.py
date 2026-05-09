import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "companies.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                careers_url TEXT    NOT NULL,
                job_titles  TEXT,
                location    TEXT,
                added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(careers_url)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT    NOT NULL,
                careers_url  TEXT    NOT NULL DEFAULT '',
                position     TEXT    NOT NULL,
                applied_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id      INTEGER REFERENCES users(id)
            )
        """)
        # Migrate: add user_id to applications if missing
        try:
            conn.execute("ALTER TABLE applications ADD COLUMN user_id INTEGER REFERENCES users(id)")
        except Exception:
            pass

        # Migrate users table: rebuild without NOT NULL on email if needed
        existing = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        if existing:
            schema = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
            ).fetchone()[0]
            if "email" in schema and "NOT NULL" in schema.split("email")[1].split("\n")[0]:
                conn.execute("ALTER TABLE users RENAME TO users_old")
                conn.execute("""
                    CREATE TABLE users (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        first_name    TEXT NOT NULL,
                        last_name     TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    INSERT INTO users (id, first_name, last_name, password_hash, created_at)
                    SELECT id, first_name, last_name, password_hash, created_at FROM users_old
                """)
                conn.execute("DROP TABLE users_old")
        else:
            conn.execute("""
                CREATE TABLE users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name    TEXT NOT NULL,
                    last_name     TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        conn.commit()


# ── User functions ──────────────────────────────────────────────

def create_user(first_name, last_name, password_hash):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (first_name, last_name, password_hash) VALUES (?, ?, ?)",
            (first_name, last_name, password_hash),
        )
        conn.commit()
        return cur.lastrowid


def get_user_by_name(first_name, last_name):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE LOWER(first_name)=LOWER(?) AND LOWER(last_name)=LOWER(?)",
            (first_name, last_name),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


# ── Company cache ────────────────────────────────────────────────

def save_company(name, careers_url, job_titles="", location=""):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO companies (name, careers_url, job_titles, location, added_at) VALUES (?, ?, ?, ?, ?)",
            (name, careers_url, job_titles, location, datetime.utcnow()),
        )
        conn.commit()


def search_cached(job_title, location):
    phrase = job_title.strip().lower()
    loc = location.strip().lower()
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM companies").fetchall()
    results = []
    for row in rows:
        row_titles = (row["job_titles"] or "").lower()
        row_loc = (row["location"] or "").lower()
        title_match = phrase in row_titles
        loc_match = not loc or loc in row_loc or row_loc in loc
        if title_match and loc_match:
            results.append(dict(row))
    return results


def all_companies():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM companies ORDER BY added_at DESC"
        ).fetchall()]


# ── Application tracking ─────────────────────────────────────────

def mark_applied(company_name, careers_url, position, user_id=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO applications (company_name, careers_url, position, applied_at, user_id) VALUES (?, ?, ?, ?, ?)",
            (company_name, careers_url, position, datetime.utcnow(), user_id),
        )
        conn.commit()


def get_application(careers_url, user_id=None):
    with get_conn() as conn:
        if user_id:
            row = conn.execute(
                "SELECT * FROM applications WHERE careers_url=? AND user_id=? ORDER BY applied_at DESC LIMIT 1",
                (careers_url, user_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM applications WHERE careers_url=? ORDER BY applied_at DESC LIMIT 1",
                (careers_url,),
            ).fetchone()
    return dict(row) if row else None


def get_application_by_company(company_name, user_id=None):
    with get_conn() as conn:
        if user_id:
            row = conn.execute(
                "SELECT * FROM applications WHERE LOWER(company_name)=LOWER(?) AND user_id=? ORDER BY applied_at DESC LIMIT 1",
                (company_name, user_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM applications WHERE LOWER(company_name)=LOWER(?) ORDER BY applied_at DESC LIMIT 1",
                (company_name,),
            ).fetchone()
    return dict(row) if row else None


def all_applications(user_id=None):
    with get_conn() as conn:
        if user_id:
            rows = conn.execute(
                "SELECT * FROM applications WHERE user_id=? ORDER BY applied_at DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM applications ORDER BY applied_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]
