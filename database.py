import sqlite3
from datetime import datetime

DB_PATH = "companies.db"


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
                careers_url  TEXT    NOT NULL,
                position     TEXT    NOT NULL,
                applied_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def save_company(name, careers_url, job_titles="", location=""):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO companies (name, careers_url, job_titles, location, added_at)
            VALUES (?, ?, ?, ?, ?)
            """,
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


def mark_applied(company_name, careers_url, position):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO applications (company_name, careers_url, position, applied_at) VALUES (?, ?, ?, ?)",
            (company_name, careers_url, position, datetime.utcnow()),
        )
        conn.commit()


def get_application(careers_url):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM applications WHERE careers_url = ? ORDER BY applied_at DESC LIMIT 1",
            (careers_url,),
        ).fetchone()
    return dict(row) if row else None


def all_applications():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM applications ORDER BY applied_at DESC"
        ).fetchall()]
