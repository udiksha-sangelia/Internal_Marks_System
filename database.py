import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

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
    inspect,
    text,
)
from sqlalchemy.exc import IntegrityError

# Configuration
DEPARTMENT = os.environ.get("DEPARTMENT", "MCA")
MCA_SEMESTERS = 4
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
UPLOAD_DIR = BASE_DIR / "uploads" / "syllabus"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MARK_TYPES = ("assignments", "skill_development")
THEORY_FIELDS = {"theory_1": 25, "theory_2": 25}
ASSIGNMENT_FIELDS = {"assignment_1": 25, "assignment_2": 25}
SKILL_FIELDS = {"skill_development": 50}
LAB_RAW_FIELDS = {"lab_1": 100, "lab_2": 100}
MARK_FIELD_LIMITS = {**THEORY_FIELDS, **ASSIGNMENT_FIELDS, **SKILL_FIELDS, **LAB_RAW_FIELDS}
INPUT_MARK_FIELDS = list(THEORY_FIELDS) + list(ASSIGNMENT_FIELDS) + list(SKILL_FIELDS) + list(LAB_RAW_FIELDS)
PASS_THRESHOLD = 25
FINAL_MAX = 50


engine = create_engine(
    DB_URL,
    future=True,
    connect_args={
        "ssl": {}
    },
    pool_pre_ping=True,
)
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
    Column("mark_type", String(32), nullable=False, default="assignments"),
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
    Column("assignment_1", Float),
    Column("assignment_2", Float),
    Column("lab_1", Float),
    Column("lab_2", Float),
    Column("internal_1", Float),
    Column("internal_2", Float),
    Column("project_marks", Float),
    Column("theory_1", Float),
    Column("theory_2", Float),
    Column("skill_development", Float),
    Column("lab_final", Float),
    Column("final_marks", Float),
    Column("result", String(8)),
    Column("mark_type", String(32), nullable=False, default="assignments"),
    Column("updated_at", DateTime, nullable=False),
)

syllabi = Table(
    "syllabi",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("semester", Integer, unique=True, nullable=False),
    Column("filename", String(255), nullable=False),
    Column("original_name", String(255), nullable=False),
    Column("uploaded_at", DateTime, nullable=False),
)


def _migrate_schema():
    insp = inspect(engine)
    with engine.begin() as conn:
        if "subjects" in insp.get_table_names():
            subject_cols = {col["name"] for col in insp.get_columns("subjects")}
            if "mark_type" not in subject_cols:
                conn.execute(text("ALTER TABLE subjects ADD COLUMN mark_type VARCHAR(32) DEFAULT 'assignments'"))

        if "marks" not in insp.get_table_names():
            return

        existing = {col["name"] for col in insp.get_columns("marks")}
        new_cols = {
            "assignment_1": "FLOAT",
            "assignment_2": "FLOAT",
            "lab_1": "FLOAT",
            "lab_2": "FLOAT",
            "internal_1": "FLOAT",
            "internal_2": "FLOAT",
            "project_marks": "FLOAT",
            "theory_1": "FLOAT",
            "theory_2": "FLOAT",
            "skill_development": "FLOAT",
            "lab_final": "FLOAT",
            "final_marks": "FLOAT",
            "result": "VARCHAR(8)",
            "mark_type": "VARCHAR(32)",
        }
        for col, col_type in new_cols.items():
            if col not in existing:
                default = " DEFAULT 'assignments'" if col == "mark_type" else ""
                conn.execute(text(f"ALTER TABLE marks ADD COLUMN {col} {col_type}{default}"))

        mark_type_exists = "mark_type" in existing or "mark_type" in new_cols
        dialect = engine.dialect.name
        if mark_type_exists:
            if dialect == "mysql":
                conn.execute(
                    text(
                        """
                        UPDATE marks m
                        INNER JOIN subjects s ON m.subject_id = s.id
                        SET m.mark_type = COALESCE(NULLIF(m.mark_type, ''), s.mark_type, 'assignments')
                        WHERE m.mark_type IS NULL OR m.mark_type = ''
                        """
                    )
                )
            else:
                conn.execute(
                    text(
                        """
                        UPDATE marks
                        SET mark_type = COALESCE(
                            NULLIF(mark_type, ''),
                            (SELECT mark_type FROM subjects WHERE subjects.id = marks.subject_id),
                            'assignments'
                        )
                        WHERE mark_type IS NULL OR mark_type = ''
                        """
                    )
                )

        legacy_cols = {"internal_1", "internal_2", "project_marks", "assignment_marks"} & existing
        if legacy_cols:
            conn.execute(
                text(
                    """
                    UPDATE marks SET
                        theory_1 = COALESCE(theory_1, internal_1),
                        theory_2 = COALESCE(theory_2, internal_2),
                        skill_development = COALESCE(skill_development, project_marks),
                        assignment_1 = COALESCE(assignment_1, assignment_marks)
                    WHERE internal_1 IS NOT NULL
                       OR internal_2 IS NOT NULL
                       OR project_marks IS NOT NULL
                       OR assignment_marks IS NOT NULL
                    """
                )
            )


# Create all tables if they don't exist
def init_db():
    metadata.create_all(engine)
    _migrate_schema()


# Utility helpers
def _now():
    return datetime.now()


def normalize_mark_row(row):
    return {
        "theory_1": row.get("theory_1") if row.get("theory_1") is not None else row.get("internal_1"),
        "theory_2": row.get("theory_2") if row.get("theory_2") is not None else row.get("internal_2"),
        "assignment_1": row.get("assignment_1"),
        "assignment_2": row.get("assignment_2"),
        "skill_development": row.get("skill_development") if row.get("skill_development") is not None else row.get("project_marks"),
        "lab_1": row.get("lab_1"),
        "lab_2": row.get("lab_2"),
    }


def calculate_lab_final(lab_1, lab_2):
    if lab_1 is None or lab_2 is None:
        return None
    return round(((lab_1 + lab_2) / 2 / 100) * 50, 2)


def calculate_theory_total(theory_1, theory_2):
    if theory_1 is None and theory_2 is None:
        return None
    return round((theory_1 or 0) + (theory_2 or 0), 2)


def calculate_component_total(mark_type, assignment_1, assignment_2, skill_development):
    if mark_type == "skill_development":
        return skill_development
    if assignment_1 is None and assignment_2 is None:
        return None
    return round((assignment_1 or 0) + (assignment_2 or 0), 2)


def calculate_final_marks(theory_total, component_total, lab_final):
    sections = [value for value in (theory_total, component_total, lab_final) if value is not None]
    if not sections:
        return None
    return round(sum(sections) / len(sections), 2)


def determine_result(final_marks):
    if final_marks is None:
        return None
    return "PASS" if final_marks >= PASS_THRESHOLD else "FAIL"


def compute_calculated_marks(mark_type, components):
    theory_total = calculate_theory_total(components.get("theory_1"), components.get("theory_2"))
    lab_final = calculate_lab_final(components.get("lab_1"), components.get("lab_2"))
    component_total = calculate_component_total(
        mark_type,
        components.get("assignment_1"),
        components.get("assignment_2"),
        components.get("skill_development"),
    )
    final_marks = calculate_final_marks(theory_total, component_total, lab_final)
    return {
        "theory_total": theory_total,
        "component_total": component_total,
        "lab_final": lab_final,
        "final_marks": final_marks,
        "result": determine_result(final_marks),
    }


def enrich_mark_record(row, mark_type="assignments"):
    mark_type = row.get("mark_type") or mark_type or "assignments"
    if mark_type not in MARK_TYPES:
        mark_type = "assignments"
    data = dict(row)
    normalized = normalize_mark_row(row)
    calculated = compute_calculated_marks(mark_type, normalized)
    data.update(normalized)
    data.update(calculated)
    data["mark_type"] = mark_type
    return data


def row_has_marks(row):
    data = normalize_mark_row(row)
    return any(data.get(key) is not None for key in data)


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

def get_students(department=DEPARTMENT, semester=None):
    stmt = select(students).where(students.c.department == department)
    if semester is not None:
        stmt = stmt.where(students.c.semester == semester)
    stmt = stmt.order_by(students.c.semester, students.c.usn)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


def get_student_semester_counts(department=DEPARTMENT):
    all_students = get_students(department)
    counts = {sem: 0 for sem in range(1, MCA_SEMESTERS + 1)}
    for student in all_students:
        sem = student.get("semester")
        if sem in counts:
            counts[sem] += 1
    counts["all"] = len(all_students)
    return counts


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

def get_subjects(department=DEPARTMENT, semester=None):
    stmt = select(subjects).where(subjects.c.department == department)
    if semester is not None:
        stmt = stmt.where(subjects.c.semester == semester)
    stmt = stmt.order_by(subjects.c.semester, subjects.c.name)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


def get_subject_semester_counts(department=DEPARTMENT):
    all_subjects = get_subjects(department)
    counts = {sem: 0 for sem in range(1, MCA_SEMESTERS + 1)}
    for subject in all_subjects:
        sem = subject.get("semester")
        if sem in counts:
            counts[sem] += 1
    counts["all"] = len(all_subjects)
    return counts


def add_subject(code, name, semester, mark_type="assignments"):
    now = _now()

    with engine.begin() as conn:
        conn.execute(
            insert(subjects).values(
                code=code,
                name=name,
                semester=semester,
                department=DEPARTMENT,
                mark_type=mark_type,
                created_at=now,
            )
        )


def get_subject_by_code(code):
    stmt = select(subjects).where(subjects.c.code == code.upper())
    with engine.connect() as conn:
        row = conn.execute(stmt).mappings().first()
    return dict(row) if row else None


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
    if not row:
        return None
    data = dict(row)
    if not data.get("mark_type"):
        data["mark_type"] = "assignments"
    return data


def update_subject_mark_type(subject_id, mark_type):
    if mark_type not in MARK_TYPES:
        return False
    with engine.begin() as conn:
        conn.execute(update(subjects).where(subjects.c.id == subject_id).values(mark_type=mark_type))
    return True


def get_students_for_subject(subject_id):
    subject = get_subject_by_id(subject_id)
    if not subject:
        return []
    default_mark_type = subject.get("mark_type") or "assignments"
    input_cols = [marks.c[key] for key in INPUT_MARK_FIELDS]
    stmt = select(
        students,
        *input_cols,
        marks.c.mark_type,
        marks.c.lab_final,
        marks.c.final_marks,
        marks.c.result,
        marks.c.updated_at.label("marks_updated_at"),
    ).select_from(
        students.outerjoin(marks, and_(marks.c.student_id == students.c.id, marks.c.subject_id == subject_id))
    ).where(
        and_(students.c.department == subject["department"], students.c.semester == subject["semester"])
    ).order_by(students.c.usn)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [
        enrich_mark_record(dict(r), r.get("mark_type") or default_mark_type)
        for r in rows
    ]


def get_student_semester_marks(student_id, semester):
    stmt = select(
        subjects.c.id.label("subject_id"),
        subjects.c.code,
        subjects.c.name,
        subjects.c.semester,
        marks.c.mark_type,
        marks.c.theory_1,
        marks.c.theory_2,
        marks.c.assignment_1,
        marks.c.assignment_2,
        marks.c.skill_development,
        marks.c.lab_1,
        marks.c.lab_2,
        marks.c.internal_1,
        marks.c.internal_2,
        marks.c.project_marks,
        marks.c.lab_final,
        marks.c.final_marks,
        marks.c.result,
        marks.c.updated_at,
    ).select_from(
        subjects.outerjoin(marks, and_(marks.c.subject_id == subjects.c.id, marks.c.student_id == student_id))
    ).where(and_(subjects.c.department == DEPARTMENT, subjects.c.semester == semester)).order_by(subjects.c.name)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()

    subject_marks = []
    final_scores = []
    for row in rows:
        enriched = enrich_mark_record(dict(row), row.get("mark_type") or "assignments")
        subject_marks.append(enriched)
        if enriched.get("final_marks") is not None:
            final_scores.append(enriched["final_marks"])

    overall_average = round(sum(final_scores) / len(final_scores), 2) if final_scores else None
    return subject_marks, overall_average


def upsert_mark(student_id, subject_id, mark_type, **components):
    now = _now()
    mark_type = mark_type if mark_type in MARK_TYPES else "assignments"
    with engine.begin() as conn:
        existing = conn.execute(
            select(marks).where(and_(marks.c.student_id == student_id, marks.c.subject_id == subject_id))
        ).mappings().first()

        merged = normalize_mark_row(existing or {})
        for key in INPUT_MARK_FIELDS:
            if key in components:
                merged[key] = components[key]

        calculated = compute_calculated_marks(mark_type, merged)
        values = {**merged, **calculated, "updated_at": now}

        if existing:
            conn.execute(
                update(marks)
                .where(and_(marks.c.student_id == student_id, marks.c.subject_id == subject_id))
                .values(
                    **{k: values[k] for k in INPUT_MARK_FIELDS + ["lab_final", "final_marks", "result"]},
                    mark_type=mark_type,
                    updated_at=now,
                )
            )
        else:
            conn.execute(
                insert(marks).values(
                    student_id=student_id,
                    subject_id=subject_id,
                    **{k: values.get(k) for k in INPUT_MARK_FIELDS + ["lab_final", "final_marks", "result"]},
                    mark_type=mark_type,
                    updated_at=now,
                )
            )


def bulk_upsert_marks_by_usn(subject_id, mark_type, entries):
    updated = 0
    skipped = 0
    for entry in entries:
        usn = entry["usn"].upper()

        student = get_student_by_usn(usn)

        if not student:
            skipped += 1
            continue

        row_mark_type = entry.get("mark_type", mark_type)

        if row_mark_type not in MARK_TYPES:
            row_mark_type = mark_type

        components = {
            key: entry.get(key)
            for key in INPUT_MARK_FIELDS
            if key in entry
        }

        if not components:
            skipped += 1
            continue

        upsert_mark(
            student["id"],
            subject_id,
            row_mark_type,
            **components,
        )

        updated += 1
        return updated, skipped


def allocation_count():
    return len(get_allocations())


# ---------- Syllabus ----------

def get_syllabi():
    stmt = select(syllabi).order_by(syllabi.c.semester)
    with engine.connect() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(r) for r in rows]


def get_syllabus_by_semester(semester):
    stmt = select(syllabi).where(syllabi.c.semester == semester)
    with engine.connect() as conn:
        row = conn.execute(stmt).mappings().first()
    return dict(row) if row else None


def upsert_syllabus(semester, filename, original_name):
    now = _now()
    existing = get_syllabus_by_semester(semester)
    with engine.begin() as conn:
        if existing:
            conn.execute(
                update(syllabi)
                .where(syllabi.c.semester == semester)
                .values(filename=filename, original_name=original_name, uploaded_at=now)
            )
        else:
            conn.execute(
                insert(syllabi).values(
                    semester=semester,
                    filename=filename,
                    original_name=original_name,
                    uploaded_at=now,
                )
            )
    log_activity(f"Uploaded syllabus for Semester {semester}")


# ---------- Faculty reports ----------

def get_subject_statistics(subject_id):
    subject = get_subject_by_id(subject_id)
    if not subject:
        return None

    mark_type = subject.get("mark_type") or "assignments"
    students = get_students_for_subject(subject_id)
    student_count = len(students)
    marks_entered = sum(1 for s in students if row_has_marks(s))
    final_scores = []
    component_totals = {key: [] for key in INPUT_MARK_FIELDS}
    top_student = None
    top_score = -1

    for student in students:
        if student.get("final_marks") is not None:
            final_scores.append(student["final_marks"])
            if student["final_marks"] > top_score:
                top_score = student["final_marks"]
                top_student = {
                    "name": student["name"],
                    "usn": student["usn"],
                    "average": student["final_marks"],
                }
        for key in INPUT_MARK_FIELDS:
            if student.get(key) is not None:
                component_totals[key].append(student[key])

    class_average = round(sum(final_scores) / len(final_scores), 2) if final_scores else None
    component_averages = {
        key: round(sum(values) / len(values), 2) if values else None
        for key, values in component_totals.items()
    }
    pass_count = sum(1 for score in final_scores if score >= PASS_THRESHOLD)
    fail_count = len(final_scores) - pass_count if final_scores else 0

    return {
        "subject_id": subject_id,
        "code": subject["code"],
        "name": subject["name"],
        "semester": subject["semester"],
        "mark_type": mark_type,
        "student_count": student_count,
        "marks_entered": marks_entered,
        "class_average": class_average,
        "component_averages": component_averages,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "top_student": top_student,
    }


def get_faculty_reports(faculty_id):
    subjects = get_faculty_subjects(faculty_id)
    reports = []
    total_students = 0
    total_marks_entered = 0
    for sub in subjects:
        stats = get_subject_statistics(sub["id"])
        if stats:
            reports.append(stats)
            total_students += stats["student_count"]
            total_marks_entered += stats["marks_entered"]
    return {
        "subjects": reports,
        "subject_count": len(reports),
        "total_students": total_students,
        "total_marks_entered": total_marks_entered,
    }


# ---------- Dashboard stats ----------

def get_dashboard_stats():
    return {"students": student_count(), "faculties": faculty_count(), "subjects": subject_count(), "departments": 1}
