import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "ia_marks.db"
DEPARTMENT = "MCA"
DEFAULT_STUDENT_PASSWORD = "student123"
DEFAULT_FACULTY_PASSWORD = "faculty123"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usn TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            semester INTEGER NOT NULL DEFAULT 1,
            department TEXT NOT NULL DEFAULT 'MCA',
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS faculties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL DEFAULT 'MCA',
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            semester INTEGER NOT NULL DEFAULT 1,
            department TEXT NOT NULL DEFAULT 'MCA',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faculty_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(subject_id),
            FOREIGN KEY (faculty_id) REFERENCES faculties(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL,
            marks REAL,
            assignment_marks REAL,
            lab_marks REAL,
            updated_at TEXT NOT NULL,
            UNIQUE(student_id, subject_id),
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
        );
        """
    )
    _migrate_marks_columns(conn)
    conn.commit()
    conn.close()


def _migrate_marks_columns(conn):
    columns = {row[1] for row in conn.execute("PRAGMA table_info(marks)")}
    if "assignment_marks" not in columns:
        conn.execute("ALTER TABLE marks ADD COLUMN assignment_marks REAL")
    if "lab_marks" not in columns:
        conn.execute("ALTER TABLE marks ADD COLUMN lab_marks REAL")


def compute_subject_average(assignment_marks, lab_marks, theory_marks):
    values = [v for v in (assignment_marks, lab_marks, theory_marks) if v is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def log_activity(action):
    conn = get_db()
    conn.execute(
        "INSERT INTO activities (action, created_at) VALUES (?, ?)",
        (action, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def time_ago(timestamp_str):
    try:
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        diff = datetime.now() - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "Just now"
        if seconds < 3600:
            return f"{seconds // 60} min ago"
        if seconds < 86400:
            return f"{seconds // 3600} hour ago"
        return f"{seconds // 86400} day ago"
    except ValueError:
        return timestamp_str


# ---------- Students ----------

def get_students(department=DEPARTMENT):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM students WHERE department = ? ORDER BY name",
        (department,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student_by_id(student_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_student_by_usn(usn):
    conn = get_db()
    row = conn.execute("SELECT * FROM students WHERE usn = ?", (usn,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_student(usn, name, email, semester, password=None):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """INSERT INTO students (usn, name, email, semester, department, password, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (usn, name, email, semester, DEPARTMENT, password or DEFAULT_STUDENT_PASSWORD, now),
    )
    conn.commit()
    conn.close()
    log_activity(f"Added student {name} ({usn}) in {DEPARTMENT}")


def delete_student(student_id):
    student = get_student_by_id(student_id)
    if not student:
        return False
    conn = get_db()
    conn.execute("DELETE FROM marks WHERE student_id = ?", (student_id,))
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    log_activity(f"Deleted student {student['name']} ({student['usn']})")
    return True


def student_count(department=DEPARTMENT):
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM students WHERE department = ?", (department,)
    ).fetchone()[0]
    conn.close()
    return count


# ---------- Faculties ----------

def get_faculties(department=DEPARTMENT):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM faculties WHERE department = ? ORDER BY name",
        (department,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_faculty_by_id(faculty_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM faculties WHERE id = ?", (faculty_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_faculty_by_email(email):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM faculties WHERE LOWER(email) = LOWER(?)",
        (email.strip(),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def add_faculty(name, email, password=None):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """INSERT INTO faculties (name, email, department, password, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (name, email.strip().lower(), DEPARTMENT, password or DEFAULT_FACULTY_PASSWORD, now),
    )
    conn.commit()
    conn.close()
    log_activity(f"Added faculty {name} in {DEPARTMENT}")


def delete_faculty(faculty_id):
    faculty = get_faculty_by_id(faculty_id)
    if not faculty:
        return False
    conn = get_db()
    conn.execute("DELETE FROM allocations WHERE faculty_id = ?", (faculty_id,))
    conn.execute("DELETE FROM faculties WHERE id = ?", (faculty_id,))
    conn.commit()
    conn.close()
    log_activity(f"Deleted faculty {faculty['name']}")
    return True


def faculty_count(department=DEPARTMENT):
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM faculties WHERE department = ?", (department,)
    ).fetchone()[0]
    conn.close()
    return count


def get_recent_faculties(limit=4, department=DEPARTMENT):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM faculties WHERE department = ? ORDER BY created_at DESC LIMIT ?",
        (department, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- Subjects ----------

def get_subjects(department=DEPARTMENT):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM subjects WHERE department = ? ORDER BY semester, name",
        (department,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_subject(code, name, semester):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """INSERT INTO subjects (code, name, semester, department, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (code, name, semester, DEPARTMENT, now),
    )
    conn.commit()
    conn.close()
    log_activity(f"Added subject {name} ({code})")


def delete_subject(subject_id):
    conn = get_db()
    row = conn.execute("SELECT name FROM subjects WHERE id = ?", (subject_id,)).fetchone()
    conn.execute("DELETE FROM marks WHERE subject_id = ?", (subject_id,))
    conn.execute("DELETE FROM allocations WHERE subject_id = ?", (subject_id,))
    conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    conn.commit()
    conn.close()
    if row:
        log_activity(f"Deleted subject {row['name']}")


def subject_count(department=DEPARTMENT):
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) FROM subjects WHERE department = ?", (department,)
    ).fetchone()[0]
    conn.close()
    return count


# ---------- Activities ----------

def get_recent_activities(limit=5):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM activities ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    activities = []
    for r in rows:
        activities.append({
            "text": r["action"],
            "time": time_ago(r["created_at"]),
        })
    return activities


# ---------- Allocations ----------

def get_allocations():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT a.id, a.faculty_id, a.subject_id, a.created_at,
               f.name AS faculty_name, f.email AS faculty_email,
               s.code AS subject_code, s.name AS subject_name, s.semester
        FROM allocations a
        JOIN faculties f ON f.id = a.faculty_id
        JOIN subjects s ON s.id = a.subject_id
        ORDER BY s.semester, s.name
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_allocation_by_subject(subject_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM allocations WHERE subject_id = ?", (subject_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def add_allocation(faculty_id, subject_id):
    faculty = get_faculty_by_id(faculty_id)
    conn = get_db()
    subject = conn.execute("SELECT name, code FROM subjects WHERE id = ?", (subject_id,)).fetchone()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO allocations (faculty_id, subject_id, created_at) VALUES (?, ?, ?)",
        (faculty_id, subject_id, now),
    )
    conn.commit()
    conn.close()
    if faculty and subject:
        log_activity(
            f"Allocated {subject['name']} ({subject['code']}) to {faculty['name']}"
        )


def delete_allocation(allocation_id):
    conn = get_db()
    row = conn.execute(
        """
        SELECT a.id, f.name AS faculty_name, s.name AS subject_name
        FROM allocations a
        JOIN faculties f ON f.id = a.faculty_id
        JOIN subjects s ON s.id = a.subject_id
        WHERE a.id = ?
        """,
        (allocation_id,),
    ).fetchone()
    conn.execute("DELETE FROM allocations WHERE id = ?", (allocation_id,))
    conn.commit()
    conn.close()
    if row:
        log_activity(f"Removed allocation of {row['subject_name']} from {row['faculty_name']}")


def get_faculty_subjects(faculty_id):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT s.*, a.id AS allocation_id
        FROM allocations a
        JOIN subjects s ON s.id = a.subject_id
        WHERE a.faculty_id = ?
        ORDER BY s.semester, s.name
        """,
        (faculty_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def faculty_owns_subject(faculty_id, subject_id):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM allocations WHERE faculty_id = ? AND subject_id = ?",
        (faculty_id, subject_id),
    ).fetchone()
    conn.close()
    return row is not None


def get_subject_by_id(subject_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_students_for_subject(subject_id):
    subject = get_subject_by_id(subject_id)
    if not subject:
        return []
    conn = get_db()
    rows = conn.execute(
        """
        SELECT s.*, m.marks, m.assignment_marks, m.lab_marks, m.updated_at AS marks_updated_at
        FROM students s
        LEFT JOIN marks m ON m.student_id = s.id AND m.subject_id = ?
        WHERE s.department = ? AND s.semester = ?
        ORDER BY s.usn
        """,
        (subject_id, subject["department"], subject["semester"]),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_student_semester_marks(student_id, semester):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT s.id AS subject_id, s.code, s.name, s.semester,
               m.marks AS theory_marks, m.assignment_marks, m.lab_marks, m.updated_at
        FROM subjects s
        LEFT JOIN marks m ON m.subject_id = s.id AND m.student_id = ?
        WHERE s.department = ? AND s.semester = ?
        ORDER BY s.name
        """,
        (student_id, DEPARTMENT, semester),
    ).fetchall()
    conn.close()

    subject_marks = []
    subject_averages = []
    for row in rows:
        r = dict(row)
        avg = compute_subject_average(
            r.get("assignment_marks"),
            r.get("lab_marks"),
            r.get("theory_marks"),
        )
        r["average"] = avg
        subject_marks.append(r)
        if avg is not None:
            subject_averages.append(avg)

    overall_average = None
    if subject_averages:
        overall_average = round(sum(subject_averages) / len(subject_averages), 2)

    return subject_marks, overall_average


def upsert_mark(student_id, subject_id, theory_marks=None, assignment_marks=None, lab_marks=None):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing = conn.execute(
        "SELECT marks, assignment_marks, lab_marks FROM marks WHERE student_id = ? AND subject_id = ?",
        (student_id, subject_id),
    ).fetchone()

    if existing:
        theory = theory_marks if theory_marks is not None else existing["marks"]
        assignment = assignment_marks if assignment_marks is not None else existing["assignment_marks"]
        lab = lab_marks if lab_marks is not None else existing["lab_marks"]
        conn.execute(
            """
            UPDATE marks
            SET marks = ?, assignment_marks = ?, lab_marks = ?, updated_at = ?
            WHERE student_id = ? AND subject_id = ?
            """,
            (theory, assignment, lab, now, student_id, subject_id),
        )
    else:
        conn.execute(
            """
            INSERT INTO marks (student_id, subject_id, marks, assignment_marks, lab_marks, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (student_id, subject_id, theory_marks, assignment_marks, lab_marks, now),
        )
    conn.commit()
    conn.close()


def bulk_upsert_marks_by_usn(subject_id, entries):
    updated = 0
    skipped = 0
    for entry in entries:
        usn = entry[0].upper()
        student = get_student_by_usn(usn)
        if not student:
            skipped += 1
            continue
        upsert_mark(
            student["id"],
            subject_id,
            theory_marks=entry[1] if len(entry) > 1 else None,
            assignment_marks=entry[2] if len(entry) > 2 else None,
            lab_marks=entry[3] if len(entry) > 3 else None,
        )
        updated += 1
    return updated, skipped


def allocation_count():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM allocations").fetchone()[0]
    conn.close()
    return count


# ---------- Dashboard stats ----------

def get_dashboard_stats():
    return {
        "students": student_count(),
        "faculties": faculty_count(),
        "subjects": subject_count(),
        "departments": 1,
    }
