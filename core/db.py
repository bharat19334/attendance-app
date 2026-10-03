"""SQLite database: students + attendance."""
from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager

from .config import DATA_DIR, DB_PATH


@contextmanager
def db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                roll_no    TEXT NOT NULL UNIQUE,
                branch     TEXT NOT NULL,
                year       TEXT NOT NULL,
                section    TEXT NOT NULL,
                embeddings TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                subject    TEXT NOT NULL,
                period     TEXT NOT NULL,
                date       TEXT NOT NULL,
                status     TEXT NOT NULL CHECK (status IN ('Present', 'Absent')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (student_id, date, period)
            );
            """
        )


def _roll_key(roll: str):
    """Roll numbers ko natural order mein sort karne ke liye (2 < 10)."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", roll) if t]


# ---------------------------------------------------------------- students
def add_student(name, roll_no, branch, year, section, embeddings) -> int:
    payload = json.dumps([[float(x) for x in e] for e in embeddings])
    with db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO students (name, roll_no, branch, year, section, embeddings) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (name, roll_no, branch, year, section, payload),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"Roll number {roll_no} pehle se registered hai.") from None
        return cur.lastrowid


def list_students(branch=None, year=None, section=None, with_embeddings=False) -> list[dict]:
    query = "SELECT * FROM students WHERE 1=1"
    params: list = []
    for column, value in (("branch", branch), ("year", year), ("section", section)):
        if value is not None:
            query += f" AND {column} = ?"
            params.append(value)
    with db() as conn:
        rows = [dict(r) for r in conn.execute(query, params)]
    for r in rows:
        emb = json.loads(r.pop("embeddings"))
        if with_embeddings:
            r["embeddings"] = emb
        else:
            r["photos"] = len(emb)
    rows.sort(key=lambda r: (r["branch"], r["year"], r["section"], _roll_key(r["roll_no"])))
    return rows


def delete_student(student_id: int) -> None:
    with db() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))


def student_counts() -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT branch, year, section, COUNT(*) AS students FROM students "
            "GROUP BY branch, year, section ORDER BY branch, year, section"
        ).fetchall()
    return [dict(r) for r in rows]


# -------------------------------------------------------------- attendance
_UPSERT = """
INSERT INTO attendance (student_id, subject, period, date, status)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(student_id, date, period) DO UPDATE SET
    subject = excluded.subject,
    status  = CASE WHEN ? = 1 AND attendance.status = 'Present'
                   THEN 'Present' ELSE excluded.status END
"""


def save_session(roster_ids, present_ids, subject, period, date, merge_present=True) -> None:
    """Class ke har student ka status save karo (jo present_ids mein hai wo Present, baaki Absent).

    merge_present=True: us period ki pehle se Present attendance Absent nahi hogi
    (agar ek hi period mein 2 photos li jaayein)."""
    present = set(present_ids)
    with db() as conn:
        for sid in roster_ids:
            status = "Present" if sid in present else "Absent"
            conn.execute(_UPSERT, (sid, subject, period, date, status, 1 if merge_present else 0))


def set_status(student_id, subject, period, date, status) -> None:
    """Manual correction: seedha overwrite."""
    with db() as conn:
        conn.execute(_UPSERT, (student_id, subject, period, date, status, 0))


def session_rows(branch, year, section, date, period) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT a.id, s.id AS student_id, s.roll_no, s.name, a.status, a.subject
            FROM attendance a JOIN students s ON s.id = a.student_id
            WHERE s.branch = ? AND s.year = ? AND s.section = ? AND a.date = ? AND a.period = ?
            """,
            (branch, year, section, date, period),
        ).fetchall()
    out = [dict(r) for r in rows]
    out.sort(key=lambda r: _roll_key(r["roll_no"]))
    return out


def month_records(branch, year, section, month) -> list[dict]:
    """month = 'YYYY-MM'"""
    with db() as conn:
        rows = conn.execute(
            """
            SELECT s.id AS student_id, s.roll_no, s.name, a.subject, a.period, a.date, a.status
            FROM attendance a JOIN students s ON s.id = a.student_id
            WHERE s.branch = ? AND s.year = ? AND s.section = ? AND a.date LIKE ?
            """,
            (branch, year, section, f"{month}-%"),
        ).fetchall()
    return [dict(r) for r in rows]


def today_stats(date: str) -> tuple[int, int]:
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS total, "
            "COALESCE(SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END), 0) AS present "
            "FROM attendance WHERE date = ?",
            (date,),
        ).fetchone()
    return row["total"], row["present"]
