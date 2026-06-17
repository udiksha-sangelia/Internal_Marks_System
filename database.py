import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    ForeignKey,
    select,
    insert,
    update,
    and_,
)
from sqlalchemy.exc import IntegrityError

# Configuration
DEPARTMENT = os.environ.get("DEPARTMENT", "MCA")
DEFAULT_STUDENT_PASSWORD = os.environ.get("DEFAULT_STUDENT_PASSWORD", "student123")
DEFAULT_FACULTY_PASSWORD = os.environ.get("DEFAULT_FACULTY_PASSWORD", "faculty123")

# Determine DB URL: use `DATABASE_URL` environment variable for MySQL (or any SQLAlchemy URL).
# Examples:
#  mysql+pymysql://user:password@host:3306/dbname
#  sqlite:///ia_marks.db
BASE_DIR = Path(__file__).parent
sqlite_path = BASE_DIR / "ia_marks.db"
DEFAULT_SQLITE_URL = f"sqlite:///{sqlite_path.as_posix()}"
DB_URL = os.environ.get("DATABASE_URL", os.environ.get("MYSQL_URL", DEFAULT_SQLITE_URL))

engine = create_engine(DB_URL, future=True)
metadata = MetaData()

# Table definitions
students = Table(
    "students",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("usn", String(64), unique=True, nullable=False),
    Column("name", String(255), nullable=False),
    Column("email", String(255), nullable=False),
    Column("semester", Integer, nullable=False, default=1),
    Column("department", String(64), nullable=False, default=DEPARTMENT),
    Column("password", String(255), nullable=False),
    Column("created_at", DateTime, nullable=False),
)

faculties = Table(
    "faculties",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(255), nullable=False),
    Column("email", String(255), unique=True, nullable=False),
    Column("department", String(64), nullable=False, default=DEPARTMENT),
    Column("password", String(255), nullable=False),
    Column("created_at", DateTime, nullable=False),
)

subjects = Table(
    "subjects",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("code", String(64), unique=True, nullable=False),
    Column("name", String(255), nullable=False),
    Column("semester", Integer, nullable=False, default=1),
    Column("department", String(64), nullable=False, default=DEPARTMENT),
    Column("created_at", DateTime, nullable=False),
)

activities = Table(
    "activities",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("action", Text, nullable=False),
    Column("created_at", DateTime, nullable=False),
)

allocations = Table(
    "allocations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("faculty_id", Integer, ForeignKey("faculties.id", ondelete="CASCADE"), nullable=False),
    Column("subject_id", Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", DateTime, nullable=False),
)

marks = Table(
    "marks",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("student_id", Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
    Column("subject_id", Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False),
    Column("marks", Float),
    Column("assignment_marks", Float),
    Column("lab_marks", Float),
    Column("updated_at", DateTime, nullable=False),
)

# Create all tables if they don't exist
def init_db():
    metadata.create_all(engine)


# Utility helpers
def _now():
    return datetime.now()


def compute_subject_average(assignment_marks, lab_marks, theory_marks):
    values = [v for v in (assignment_marks, lab_marks, theory_marks) if v is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def time_ago(timestamp):
    try:
        if isinstance(timestamp, str):
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        else:
            dt = timestamp
        diff = datetime.now() - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "Just now"
        if seconds < 3600:
            return f"{seconds // 60} min ago"
        if seconds < 86400:
            return f"{seconds // 3600} hour ago"
        return f"{seconds // 86400} day ago"
    except Exception:
        return str(timestamp)


def log_activity(action):
    with engine.begin() as conn:
        conn.execute(insert(activities).values(action=action, created_at=_now()))


# ---------- Students ----------

def get_students(department=DEPARTMENT):
    stmt = select(students).where(students.c.department == department).order_by(students.c.name)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


def get_student_by_id(student_id):
    stmt = select(students).where(students.c.id == student_id)
    with engine.connect() as conn:
        row = conn.execute(stmt).mappings().first()
    return dict(row) if row else None


def get_student_by_usn(usn):
    stmt = select(students).where(students.c.usn == usn)
    with engine.connect() as conn:
        row = conn.execute(stmt).mappings().first()
    return dict(row) if row else None


def add_student(usn, name, email, semester, password=None):
    now = _now()
    try:
        with engine.begin() as conn:
            conn.execute(
                insert(students).values(
                    usn=usn,
                    name=name,
                    email=email,
                    semester=semester,
                    department=DEPARTMENT,
                    password=password or DEFAULT_STUDENT_PASSWORD,
                    created_at=now,
                )
            )
        log_activity(f"Added student {name} ({usn}) in {DEPARTMENT}")
    except IntegrityError:
        raise


def delete_student(student_id):
    student = get_student_by_id(student_id)
    if not student:
        return False
    with engine.begin() as conn:
        conn.execute(marks.delete().where(marks.c.student_id == student_id))
        conn.execute(students.delete().where(students.c.id == student_id))
    log_activity(f"Deleted student {student['name']} ({student['usn']})")
    return True


def student_count(department=DEPARTMENT):
    return len(get_students(department))


# ---------- Faculties ----------

def get_faculties(department=DEPARTMENT):
    stmt = select(faculties).where(faculties.c.department == department).order_by(faculties.c.name)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


def get_faculty_by_id(faculty_id):
    stmt = select(faculties).where(faculties.c.id == faculty_id)
    with engine.connect() as conn:
        row = conn.execute(stmt).mappings().first()
    return dict(row) if row else None


def get_faculty_by_email(email):
    stmt = select(faculties).where(faculties.c.email.ilike(email.strip()))
    with engine.connect() as conn:
        row = conn.execute(stmt).mappings().first()
    return dict(row) if row else None


def add_faculty(name, email, password=None):
    now = _now()
    try:
        with engine.begin() as conn:
            conn.execute(
                insert(faculties).values(
                    name=name,
                    email=email.strip().lower(),
                    department=DEPARTMENT,
                    password=password or DEFAULT_FACULTY_PASSWORD,
                    created_at=now,
                )
            )
        log_activity(f"Added faculty {name} in {DEPARTMENT}")
    except IntegrityError:
        raise


def delete_faculty(faculty_id):
    faculty = get_faculty_by_id(faculty_id)
    if not faculty:
        return False
    with engine.begin() as conn:
        conn.execute(allocations.delete().where(allocations.c.faculty_id == faculty_id))
        conn.execute(faculties.delete().where(faculties.c.id == faculty_id))
    log_activity(f"Deleted faculty {faculty['name']}")
    return True


def faculty_count(department=DEPARTMENT):
    return len(get_faculties(department))


def get_recent_faculties(limit=4, department=DEPARTMENT):
    stmt = select(faculties).where(faculties.c.department == department).order_by(faculties.c.created_at.desc()).limit(limit)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


# ---------- Subjects ----------

def get_subjects(department=DEPARTMENT):
    stmt = select(subjects).where(subjects.c.department == department).order_by(subjects.c.semester, subjects.c.name)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


def add_subject(code, name, semester):
    now = _now()
    try:
        with engine.begin() as conn:
            conn.execute(insert(subjects).values(code=code, name=name, semester=semester, department=DEPARTMENT, created_at=now))
        log_activity(f"Added subject {name} ({code})")
    except IntegrityError:
        raise


def delete_subject(subject_id):
    with engine.begin() as conn:
        row = conn.execute(select(subjects.c.name).where(subjects.c.id == subject_id)).mappings().first()
        conn.execute(marks.delete().where(marks.c.subject_id == subject_id))
        conn.execute(allocations.delete().where(allocations.c.subject_id == subject_id))
        conn.execute(subjects.delete().where(subjects.c.id == subject_id))
    if row:
        log_activity(f"Deleted subject {row['name']}")


def subject_count(department=DEPARTMENT):
    return len(get_subjects(department))


# ---------- Activities ----------

def get_recent_activities(limit=5):
    stmt = select(activities).order_by(activities.c.created_at.desc()).limit(limit)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    activities_list = []
    for r in rows:
        activities_list.append({"text": r["action"], "time": time_ago(r["created_at"])})
    return activities_list


# ---------- Allocations ----------

def get_allocations():
    stmt = select(
        allocations.c.id,
        allocations.c.faculty_id,
        allocations.c.subject_id,
        allocations.c.created_at,
        faculties.c.name.label("faculty_name"),
        faculties.c.email.label("faculty_email"),
        subjects.c.code.label("subject_code"),
        subjects.c.name.label("subject_name"),
        subjects.c.semester,
    ).join(faculties, faculties.c.id == allocations.c.faculty_id).join(subjects, subjects.c.id == allocations.c.subject_id).order_by(subjects.c.semester, subjects.c.name)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


def get_allocation_by_subject(subject_id):
    stmt = select(allocations).where(allocations.c.subject_id == subject_id)
    with engine.connect() as conn:
        row = conn.execute(stmt).mappings().first()
    return dict(row) if row else None


def add_allocation(faculty_id, subject_id):
    subject = None
    faculty = get_faculty_by_id(faculty_id)
    with engine.connect() as conn:
        subject = conn.execute(select(subjects.c.name, subjects.c.code).where(subjects.c.id == subject_id)).mappings().first()
    now = _now()
    with engine.begin() as conn:
        conn.execute(insert(allocations).values(faculty_id=faculty_id, subject_id=subject_id, created_at=now))
    if faculty and subject:
        log_activity(f"Allocated {subject['name']} ({subject['code']}) to {faculty['name']}")


def delete_allocation(allocation_id):
    stmt = select(allocations.c.id, faculties.c.name.label("faculty_name"), subjects.c.name.label("subject_name")).join(faculties, faculties.c.id == allocations.c.faculty_id).join(subjects, subjects.c.id == allocations.c.subject_id).where(allocations.c.id == allocation_id)
    with engine.begin() as conn:
        row = conn.execute(stmt).mappings().first()
        conn.execute(allocations.delete().where(allocations.c.id == allocation_id))
    if row:
        log_activity(f"Removed allocation of {row['subject_name']} from {row['faculty_name']}")


def get_faculty_subjects(faculty_id):
    stmt = select(subjects, allocations.c.id.label("allocation_id")).join(allocations, allocations.c.subject_id == subjects.c.id).where(allocations.c.faculty_id == faculty_id).order_by(subjects.c.semester, subjects.c.name)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


def faculty_owns_subject(faculty_id, subject_id):
    stmt = select(allocations.c.id).where(and_(allocations.c.faculty_id == faculty_id, allocations.c.subject_id == subject_id))
    with engine.connect() as conn:
        row = conn.execute(stmt).first()
    return row is not None


def get_subject_by_id(subject_id):
    stmt = select(subjects).where(subjects.c.id == subject_id)
    with engine.connect() as conn:
        row = conn.execute(stmt).mappings().first()
    return dict(row) if row else None


def get_students_for_subject(subject_id):
    subject = get_subject_by_id(subject_id)
    if not subject:
        return []
    stmt = select(
        students,
        marks.c.marks,
        marks.c.assignment_marks,
        marks.c.lab_marks,
        marks.c.updated_at.label("marks_updated_at"),
    ).select_from(students.outerjoin(marks, and_(marks.c.student_id == students.c.id, marks.c.subject_id == subject_id))).where(and_(students.c.department == subject["department"], students.c.semester == subject["semester"])).order_by(students.c.usn)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


def get_student_semester_marks(student_id, semester):
    stmt = select(
        subjects.c.id.label("subject_id"),
        subjects.c.code,
        subjects.c.name,
        subjects.c.semester,
        marks.c.marks.label("theory_marks"),
        marks.c.assignment_marks,
        marks.c.lab_marks,
        marks.c.updated_at,
    ).select_from(subjects.outerjoin(marks, and_(marks.c.subject_id == subjects.c.id, marks.c.student_id == student_id))).where(and_(subjects.c.department == DEPARTMENT, subjects.c.semester == semester)).order_by(subjects.c.name)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()

    subject_marks = []
    subject_averages = []
    for row in rows:
        r = dict(row)
        avg = compute_subject_average(r.get("assignment_marks"), r.get("lab_marks"), r.get("theory_marks"))
        r["average"] = avg
        subject_marks.append(r)
        if avg is not None:
            subject_averages.append(avg)

    overall_average = None
    if subject_averages:
        overall_average = round(sum(subject_averages) / len(subject_averages), 2)

    return subject_marks, overall_average


def upsert_mark(student_id, subject_id, theory_marks=None, assignment_marks=None, lab_marks=None):
    now = _now()
    with engine.begin() as conn:
        existing = conn.execute(select(marks).where(and_(marks.c.student_id == student_id, marks.c.subject_id == subject_id))).mappings().first()
        if existing:
            theory = theory_marks if theory_marks is not None else existing.get("marks")
            assignment = assignment_marks if assignment_marks is not None else existing.get("assignment_marks")
            lab = lab_marks if lab_marks is not None else existing.get("lab_marks")
            conn.execute(update(marks).where(and_(marks.c.student_id == student_id, marks.c.subject_id == subject_id)).values(marks=theory, assignment_marks=assignment, lab_marks=lab, updated_at=now))
        else:
            conn.execute(insert(marks).values(student_id=student_id, subject_id=subject_id, marks=theory_marks, assignment_marks=assignment_marks, lab_marks=lab_marks, updated_at=now))


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
    return len(get_allocations())


# ---------- Dashboard stats ----------

def get_dashboard_stats():
    return {"students": student_count(), "faculties": faculty_count(), "subjects": subject_count(), "departments": 1}
