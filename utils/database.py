"""
database.py
------------
Handles all SQLite database operations for the AI Classroom Attendance System.

Tables:
    students   -> stores registered student info + path to their face encoding
    attendance -> stores daily attendance records (one row per student per date)
"""

import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
DB_PATH = os.path.join(DB_DIR, "attendance.db")


def get_db_connection():
    """Return a new SQLite connection with row access by column name."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they do not already exist. Safe to call every startup."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            image_path TEXT NOT NULL,
            encoding_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
            UNIQUE(student_id, date),
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# STUDENT OPERATIONS
# ---------------------------------------------------------------------------

def add_student(student_id, name, image_path, encoding_path):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO students (student_id, name, image_path, encoding_path, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (student_id, name, image_path, encoding_path, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return True, "Student registered successfully."
    except sqlite3.IntegrityError:
        return False, f"Student ID '{student_id}' already exists."
    except sqlite3.Error as e:
        return False, f"Database error: {e}"
    finally:
        conn.close()


def get_all_students():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM students ORDER BY name ASC").fetchall()
    conn.close()
    return rows


def get_student_by_id(student_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    conn.close()
    return row


def search_students(query):
    conn = get_db_connection()
    like = f"%{query}%"
    rows = conn.execute(
        "SELECT * FROM students WHERE name LIKE ? OR student_id LIKE ? ORDER BY name ASC",
        (like, like),
    ).fetchall()
    conn.close()
    return rows


def delete_student(student_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
    conn.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
    conn.commit()
    conn.close()


def student_count():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) AS c FROM students").fetchone()["c"]
    conn.close()
    return count


# ---------------------------------------------------------------------------
# ATTENDANCE OPERATIONS
# ---------------------------------------------------------------------------

def mark_attendance(student_id, status="Present", date=None, time_str=None):
    """
    Insert or update an attendance record for a student on a given date.
    Prevents duplicate rows for the same student + date (UNIQUE constraint),
    and instead updates the existing row (e.g. Absent -> Present if recognized later).
    """
    date = date or datetime.now().strftime("%Y-%m-%d")
    time_str = time_str or datetime.now().strftime("%H:%M:%S")

    conn = get_db_connection()
    existing = conn.execute(
        "SELECT * FROM attendance WHERE student_id = ? AND date = ?", (student_id, date)
    ).fetchone()

    if existing:
        # Only "upgrade" Absent -> Present automatically; don't silently overwrite
        # a Present with a later Absent from the same auto-detection pass.
        if status == "Present" and existing["status"] == "Absent":
            conn.execute(
                "UPDATE attendance SET status = ?, time = ? WHERE student_id = ? AND date = ?",
                (status, time_str, student_id, date),
            )
            conn.commit()
    else:
        conn.execute(
            "INSERT INTO attendance (student_id, date, time, status) VALUES (?, ?, ?, ?)",
            (student_id, date, time_str, status),
        )
        conn.commit()
    conn.close()


def mark_absent_for_unmarked(date=None):
    """For a given date, any registered student without an attendance row is marked Absent."""
    date = date or datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    students = conn.execute("SELECT student_id FROM students").fetchall()
    existing_ids = {
        r["student_id"]
        for r in conn.execute("SELECT student_id FROM attendance WHERE date = ?", (date,)).fetchall()
    }
    time_str = datetime.now().strftime("%H:%M:%S")
    for s in students:
        if s["student_id"] not in existing_ids:
            conn.execute(
                "INSERT INTO attendance (student_id, date, time, status) VALUES (?, ?, ?, ?)",
                (s["student_id"], date, time_str, "Absent"),
            )
    conn.commit()
    conn.close()


def get_attendance_by_date(date=None):
    date = date or datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT a.id, a.student_id, s.name, a.date, a.time, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.date = ?
        ORDER BY s.name ASC
        """,
        (date,),
    ).fetchall()
    conn.close()
    return rows


def get_all_attendance():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT a.id, a.student_id, s.name, a.date, a.time, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        ORDER BY a.date DESC, s.name ASC
        """
    ).fetchall()
    conn.close()
    return rows


def get_attendance_record(record_id):
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT a.id, a.student_id, s.name, a.date, a.time, a.status
        FROM attendance a
        JOIN students s ON a.student_id = s.student_id
        WHERE a.id = ?
        """,
        (record_id,),
    ).fetchone()
    conn.close()
    return row


def update_attendance_status(record_id, new_status):
    conn = get_db_connection()
    conn.execute("UPDATE attendance SET status = ? WHERE id = ?", (new_status, record_id))
    conn.commit()
    conn.close()


def today_stats():
    """Return (total_students, present_count, absent_count, percentage) for today."""
    date = datetime.now().strftime("%Y-%m-%d")
    total = student_count()
    conn = get_db_connection()
    present = conn.execute(
        "SELECT COUNT(*) AS c FROM attendance WHERE date = ? AND status = 'Present'", (date,)
    ).fetchone()["c"]
    conn.close()
    absent = max(total - present, 0)
    pct = round((present / total) * 100, 1) if total > 0 else 0.0
    return total, present, absent, pct
