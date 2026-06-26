import csv
import io
import os
import uuid
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, Response
from werkzeug.utils import secure_filename

import database as db

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
required = {
    "FLASK_SECRET_KEY": app.secret_key,
    "ADMIN_USERNAME": ADMIN_USERNAME,
    "ADMIN_PASSWORD": ADMIN_PASSWORD,
}

missing = [name for name, value in required.items() if not value]
if missing:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing)}"
    )
db.init_db()


@app.context_processor
def inject_mca_config():
    return {
        "mca_semesters": db.MCA_SEMESTERS,
        "mark_field_limits": db.MARK_FIELD_LIMITS,
        "mark_types": db.MARK_TYPES,
        "pass_threshold": db.PASS_THRESHOLD,
        "final_max": db.FINAL_MAX,
    }


def parse_semester(value, default=1):
    try:
        semester = int(value)
    except (TypeError, ValueError):
        return default
    if 1 <= semester <= db.MCA_SEMESTERS:
        return semester
    return None


def get_list_semester_filter():
    sem = request.args.get("sem")
    if sem in (None, "", "all"):
        return None
    return parse_semester(sem)


def redirect_preserve_sem(endpoint, **kwargs):
    sem = request.args.get("sem")
    if sem:
        kwargs["sem"] = sem
    return redirect(url_for(endpoint, **kwargs))


# ---------- Auth helpers ----------

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in") or session.get("role") != "admin":
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in") or session.get("role") != "student":
            return redirect(url_for("student_login"))
        return f(*args, **kwargs)
    return decorated


def faculty_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in") or session.get("role") != "faculty":
            return redirect(url_for("faculty_login"))
        return f(*args, **kwargs)
    return decorated


def parse_csv_upload(file, required_fields):
    content = file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for row in reader:
        cleaned = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
        if all(cleaned.get(f) for f in required_fields):
            rows.append(cleaned)
    return rows


def parse_mark_field(raw, field_name):
    if raw is None or str(raw).strip() == "":
        return None
    value = float(raw)
    max_val = db.MARK_FIELD_LIMITS[field_name]
    if value < 0 or value > max_val:
        raise ValueError(f"{field_name} out of range")
    return value


def parse_mark_row(row, mark_type="assignments"):
    components = {}
    legacy_map = {
        "internal_1": "theory_1",
        "internal_2": "theory_2",
        "theory": "theory_1",
        "theory_marks": "theory_1",
        "marks": "theory_1",
        "assignment_marks": "assignment_1",
        "assignment": "assignment_1",
        "project_marks": "skill_development",
        "project": "skill_development",
        "skill": "skill_development",
    }
    allowed = set(db.INPUT_MARK_FIELDS)
    if mark_type == "assignments":
        allowed -= set(db.SKILL_FIELDS)
    else:
        allowed -= set(db.ASSIGNMENT_FIELDS)

    for key in allowed:
        if row.get(key) not in (None, ""):
            components[key] = parse_mark_field(row[key], key)
    for legacy, target in legacy_map.items():
        if legacy in row and row[legacy] not in (None, "") and target in allowed and target not in components:
            components[target] = parse_mark_field(row[legacy], target)
    return components


def input_fields_for_mark_type(mark_type):
    fields = list(db.THEORY_FIELDS) + list(db.LAB_RAW_FIELDS)
    if mark_type == "skill_development":
        fields += list(db.SKILL_FIELDS)
    else:
        fields += list(db.ASSIGNMENT_FIELDS)
    return fields


# ---------- Home & Admin Login ----------

@app.route("/")
def home():
    role = session.get("role")
    if session.get("logged_in"):
        if role == "admin":
            return redirect(url_for("dashboard"))
        if role == "student":
            return redirect(url_for("student_dashboard"))
        if role == "faculty":
            return redirect(url_for("faculty_dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in") and session.get("role") == "admin":
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session["logged_in"] = True
            session["role"] = "admin"
            session["admin_name"] = "Admin"
            return redirect(url_for("dashboard"))

        flash("Invalid username or password", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- Admin Dashboard ----------

@app.route("/dashboard")
@admin_required
def dashboard():
    return render_template(
        "dashboard.html",
        admin_name=session.get("admin_name", "Admin"),
        stats=db.get_dashboard_stats(),
        recent_faculties=db.get_recent_faculties(),
        recent_activities=db.get_recent_activities(),
        active_page="dashboard",
    )


# ---------- Departments (MCA only) ----------

@app.route("/departments")
@admin_required
def departments():
    return render_template(
        "departments.html",
        admin_name=session.get("admin_name", "Admin"),
        student_count=db.student_count(),
        faculty_count=db.faculty_count(),
        subject_count=db.subject_count(),
        active_page="departments",
    )


@app.route("/departments/mca")
@admin_required
def department_mca():
    return render_template(
        "department_mca.html",
        admin_name=session.get("admin_name", "Admin"),
        student_count=db.student_count(),
        faculty_count=db.faculty_count(),
        active_page="departments",
    )


# ---------- Students Management ----------

@app.route("/students", methods=["GET", "POST"])
@admin_required
def students():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            usn = (request.form.get("usn") or "").strip().upper()
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").strip()
            semester = request.form.get("semester", "1")

            if not usn or not name or not email:
                flash("USN, name and email are required.", "error")
            elif db.get_student_by_usn(usn):
                flash(f"Student with USN {usn} already exists.", "error")
            elif parse_semester(semester) is None:
                flash(f"Semester must be between 1 and {db.MCA_SEMESTERS}.", "error")
            else:
                try:
                    db.add_student(usn, name, email, parse_semester(semester))
                    flash(f"Student {name} added successfully.", "success")
                except Exception:
                    flash("Failed to add student.", "error")

        elif action == "csv_upload":
            file = request.files.get("csv_file")
            if not file or not file.filename:
                flash("Please select a CSV file.", "error")
            else:
                try:
                    rows = parse_csv_upload(file, ["usn", "name", "email"])
                    added = 0
                    skipped = 0
                    for row in rows:
                        usn = row["usn"].upper()
                        if db.get_student_by_usn(usn):
                            skipped += 1
                            continue
                        semester = parse_semester(row.get("semester", 1), default=1)
                        db.add_student(usn, row["name"], row["email"], semester)
                        added += 1
                    db.log_activity(f"Uploaded {added} students via CSV")
                    flash(f"CSV upload complete: {added} added, {skipped} skipped.", "success")
                except Exception as e:
                    flash(f"CSV upload failed: {e}", "error")

        return redirect(url_for("students", **({"sem": request.args.get("sem")} if request.args.get("sem") else {})))

    filter_sem = get_list_semester_filter()
    student_list = db.get_students(semester=filter_sem)
    sem_counts = db.get_student_semester_counts()
    return render_template(
        "students.html",
        admin_name=session.get("admin_name", "Admin"),
        students=student_list,
        filter_sem=filter_sem,
        sem_counts=sem_counts,
        active_page="students",
    )


@app.route("/students/delete/<int:student_id>", methods=["POST"])
@admin_required
def delete_student(student_id):
    result = db.delete_student(student_id)
    if result:
        flash("Student deleted successfully.", "success")
    else:
        flash("Student not found or could not be deleted.", "error")
    return redirect(url_for("students", sem=request.args.get("sem")))


@app.route("/students/bulk-delete", methods=["POST"])
@admin_required
def bulk_delete_students():
    student_ids = request.form.getlist("student_ids")
    if not student_ids:
        flash("No students selected.", "error")
    else:
        deleted_count = 0
        for student_id in student_ids:
            try:
                if db.delete_student(int(student_id)):
                    deleted_count += 1
            except Exception:
                pass
        flash(f"{deleted_count} student(s) deleted successfully.", "success")
    return redirect(url_for("students", sem=request.args.get("sem")))


# ---------- Faculties Management ----------

@app.route("/faculties", methods=["GET", "POST"])
@admin_required
def faculties():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").strip()

            if not name or not email:
                flash("Name and email are required.", "error")
            elif db.get_faculty_by_email(email):
                flash(f"Faculty with email {email} already exists.", "error")
            else:
                try:
                    db.add_faculty(name, email)
                    flash(f"Faculty {name} added successfully.", "success")
                except Exception:
                    flash("Failed to add faculty.", "error")

        elif action == "csv_upload":
            file = request.files.get("csv_file")
            if not file or not file.filename:
                flash("Please select a CSV file.", "error")
            else:
                try:
                    rows = parse_csv_upload(file, ["name", "email"])
                    added = 0
                    skipped = 0
                    for row in rows:
                        if db.get_faculty_by_email(row["email"]):
                            skipped += 1
                            continue
                        db.add_faculty(row["name"], row["email"])
                        added += 1
                    db.log_activity(f"Uploaded {added} faculties via CSV")
                    flash(f"CSV upload complete: {added} added, {skipped} skipped.", "success")
                except Exception as e:
                    flash(f"CSV upload failed: {e}", "error")

        elif action == "bulk_delete":
            faculty_ids = request.form.getlist("faculty_ids")
            if not faculty_ids:
                flash("No faculties selected.", "error")
            else:
                deleted_count = 0
                for fid in faculty_ids:
                    try:
                        if db.delete_faculty(int(fid)):
                            deleted_count += 1
                    except Exception:
                        pass
                flash(f"{deleted_count} faculty member(s) deleted successfully.", "success")

        return redirect(url_for("faculties"))

    return render_template(
        "faculties.html",
        admin_name=session.get("admin_name", "Admin"),
        faculties=db.get_faculties(),
        active_page="faculties",
    )


@app.route("/faculties/delete/<int:faculty_id>", methods=["POST"])
@admin_required
def delete_faculty(faculty_id):
    if db.delete_faculty(faculty_id):
        flash("Faculty deleted successfully.", "success")
    else:
        flash("Faculty not found.", "error")
    return redirect(url_for("faculties"))


# ---------- Subjects ----------

@app.route("/subjects", methods=["GET", "POST"])
@admin_required
def subjects():
    if request.method == "POST":
        action = request.form.get("action", "add")

        if action == "csv_upload":
            file = request.files.get("csv_file")
            if not file or not file.filename:
                flash("Please select a CSV file.", "error")
            else:
                try:
                    rows = parse_csv_upload(file, ["code", "name"])
                    added = 0
                    skipped = 0
                    for row in rows:
                        code = row["code"].upper()
                        if db.get_subject_by_code(code):
                            skipped += 1
                            continue
                        semester = parse_semester(row.get("semester", 1), default=1)
                        db.add_subject(code, row["name"], semester)
                        added += 1
                    db.log_activity(f"Uploaded {added} subjects via CSV")
                    flash(f"CSV upload complete: {added} added, {skipped} skipped.", "success")
                except Exception as e:
                    flash(f"CSV upload failed: {e}", "error")
            return redirect(url_for("subjects", **({"sem": request.args.get("sem")} if request.args.get("sem") else {})))

        elif action == "bulk_delete":
            subject_ids = request.form.getlist("subject_ids")
            if not subject_ids:
                flash("No subjects selected.", "error")
            else:
                deleted_count = 0
                for sid in subject_ids:
                    try:
                        db.delete_subject(int(sid))
                        deleted_count += 1
                    except Exception:
                        pass
                flash(f"{deleted_count} subject(s) deleted successfully.", "success")
            return redirect(url_for("subjects", **({"sem": request.args.get("sem")} if request.args.get("sem") else {})))

        code = (request.form.get("code") or "").strip().upper()
        name = (request.form.get("name") or "").strip()
        semester = request.form.get("semester", "1")

        if not code or not name:
            flash("Subject code and name are required.", "error")
        elif parse_semester(semester) is None:
            flash(f"Semester must be between 1 and {db.MCA_SEMESTERS}.", "error")
        else:
            try:
                db.add_subject(code, name, parse_semester(semester))
                flash(f"Subject {name} added successfully.", "success")
            except Exception:
                flash("Failed to add subject. Code may already exist.", "error")
        return redirect(url_for("subjects", **({"sem": request.args.get("sem")} if request.args.get("sem") else {})))

    filter_sem = get_list_semester_filter()
    subject_list = db.get_subjects(semester=filter_sem)
    sem_counts = db.get_subject_semester_counts()
    return render_template(
        "subjects.html",
        admin_name=session.get("admin_name", "Admin"),
        subjects=subject_list,
        filter_sem=filter_sem,
        sem_counts=sem_counts,
        active_page="subjects",
    )


@app.route("/subjects/delete/<int:subject_id>", methods=["POST"])
@admin_required
def delete_subject(subject_id):
    db.delete_subject(subject_id)
    flash("Subject deleted successfully.", "success")
    return redirect(url_for("subjects", sem=request.args.get("sem")))


@app.route("/syllabus", methods=["GET", "POST"])
@admin_required
def admin_syllabus():
    if request.method == "POST":
        semester = request.form.get("semester", "1")
        file = request.files.get("pdf_file")
        sem = parse_semester(semester)
        if sem is None:
            flash(f"Semester must be between 1 and {db.MCA_SEMESTERS}.", "error")
        elif not file or not file.filename:
            flash("Please select a PDF file.", "error")
        elif not file.filename.lower().endswith(".pdf"):
            flash("Only PDF files are allowed.", "error")
        else:
            original_name = secure_filename(file.filename)
            stored_name = f"sem{sem}_{uuid.uuid4().hex[:8]}_{original_name}"
            file.save(db.UPLOAD_DIR / stored_name)
            existing = db.get_syllabus_by_semester(sem)
            if existing:
                old_path = db.UPLOAD_DIR / existing["filename"]
                if old_path.exists():
                    old_path.unlink()
            db.upsert_syllabus(sem, stored_name, original_name)
            flash(f"Syllabus uploaded for Semester {sem}.", "success")
        return redirect(url_for("admin_syllabus"))

    syllabi = {s["semester"]: s for s in db.get_syllabi()}
    return render_template(
        "admin_syllabus.html",
        admin_name=session.get("admin_name", "Admin"),
        syllabi=syllabi,
        active_page="syllabus",
    )


@app.route("/syllabus/file/<int:semester>")
def syllabus_file(semester):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    if session.get("role") not in ("faculty", "admin"):
        flash("Access denied.", "error")
        return redirect(url_for("home"))

    record = db.get_syllabus_by_semester(semester)
    if not record:
        flash("Syllabus not found for this semester.", "error")
        if session.get("role") == "faculty":
            return redirect(url_for("faculty_dashboard"))
        return redirect(url_for("admin_syllabus"))

    return send_from_directory(db.UPLOAD_DIR, record["filename"], as_attachment=False)


# ---------- Allocations ----------

@app.route("/allocations", methods=["GET", "POST"])
@admin_required
def allocations():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            faculty_id = request.form.get("faculty_id")
            subject_id = request.form.get("subject_id")

            if not faculty_id or not subject_id:
                flash("Select both faculty and subject.", "error")
            elif db.get_allocation_by_subject(int(subject_id)):
                flash("This subject is already allocated to a faculty.", "error")
            else:
                try:
                    db.add_allocation(int(faculty_id), int(subject_id))
                    flash("Subject allocated successfully.", "success")
                except Exception:
                    flash("Failed to allocate subject.", "error")

        elif action == "bulk_delete":
            allocation_ids = request.form.getlist("allocation_ids")
            if not allocation_ids:
                flash("No allocations selected.", "error")
            else:
                deleted_count = 0
                for aid in allocation_ids:
                    try:
                        db.delete_allocation(int(aid))
                        deleted_count += 1
                    except Exception:
                        pass
                flash(f"{deleted_count} allocation(s) removed successfully.", "success")

        return redirect(url_for("allocations"))

    return render_template(
        "allocations.html",
        admin_name=session.get("admin_name", "Admin"),
        allocations=db.get_allocations(),
        faculties=db.get_faculties(),
        subjects=db.get_subjects(),
        active_page="allocations",
    )


@app.route("/allocations/delete/<int:allocation_id>", methods=["POST"])
@admin_required
def delete_allocation(allocation_id):
    db.delete_allocation(allocation_id)
    flash("Allocation removed successfully.", "success")
    return redirect(url_for("allocations"))


# ---------- Reports ----------

@app.route("/reports")
@admin_required
def reports():
    all_subjects = db.get_subjects()
    subject_reports = []
    for sub in all_subjects:
        stats = db.get_subject_statistics(sub["id"])
        if stats:
            subject_reports.append(stats)

    sem_reports = {}
    for stat in subject_reports:
        sem = stat["semester"]
        if sem not in sem_reports:
            sem_reports[sem] = []
        sem_reports[sem].append(stat)

    return render_template(
        "reports.html",
        admin_name=session.get("admin_name", "Admin"),
        stats=db.get_dashboard_stats(),
        subject_reports=subject_reports,
        sem_reports=sem_reports,
        active_page="reports",
    )


@app.route("/reports/download/csv")
@admin_required
def reports_download_csv():
    all_subjects = db.get_subjects()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Subject Code", "Subject Name", "Semester", "Mark Type", "Total Students",
                     "Marks Entered", "Class Average", "Pass Count", "Fail Count", "Top Student", "Top Score"])
    for sub in all_subjects:
        stats = db.get_subject_statistics(sub["id"])
        if stats:
            top = stats.get("top_student") or {}
            writer.writerow([
                stats["code"], stats["name"], stats["semester"], stats["mark_type"],
                stats["student_count"], stats["marks_entered"], stats["class_average"] or "—",
                stats["pass_count"], stats["fail_count"],
                top.get("name", "—"), top.get("average", "—")
            ])
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=marks_report.csv"})


@app.route("/reports/marksheet/<int:student_id>")
@admin_required
def student_marksheet(student_id):
    student = db.get_student_by_id(student_id)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("reports"))
    all_sem_marks = {}
    for sem in range(1, student["semester"] + 1):
        marks, avg = db.get_student_semester_marks(student_id, sem)
        all_sem_marks[sem] = {"marks": marks, "average": avg}
    return render_template(
        "marksheet.html",
        admin_name=session.get("admin_name", "Admin"),
        student=student,
        all_sem_marks=all_sem_marks,
        active_page="reports",
    )


@app.route("/profile")
@admin_required
def profile():
    return render_template(
        "profile.html",
        admin_name=session.get("admin_name", "Admin"),
        active_page="profile",
    )


# ---------- Student Login & Dashboard ----------

@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    if session.get("logged_in") and session.get("role") == "student":
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        usn = (request.form.get("usn") or "").strip().upper()
        password = request.form.get("password") or ""

        student = db.get_student_by_usn(usn)
        if student and student["password"] == password:
            session.clear()
            session["logged_in"] = True
            session["role"] = "student"
            session["user_id"] = student["id"]
            session["user_name"] = student["name"]
            return redirect(url_for("student_dashboard"))

        flash("Invalid USN or password", "error")

    return render_template("student_login.html")


@app.route("/student/dashboard")
@student_required
def student_dashboard():
    student = db.get_student_by_id(session["user_id"])
    view_sem = request.args.get("sem", type=int) or student["semester"]
    if view_sem < 1 or view_sem > student["semester"]:
        view_sem = student["semester"]
    subject_marks, overall_average = db.get_student_semester_marks(student["id"], view_sem)
    available_sems = list(range(1, student["semester"] + 1))
    return render_template(
        "student_dashboard.html",
        student=student,
        subject_marks=subject_marks,
        overall_average=overall_average,
        view_sem=view_sem,
        available_sems=available_sems,
    )


@app.route("/student/logout")
def student_logout():
    session.clear()
    return redirect(url_for("student_login"))


# ---------- Faculty Login & Dashboard ----------

@app.route("/faculty/login", methods=["GET", "POST"])
def faculty_login():
    if session.get("logged_in") and session.get("role") == "faculty":
        return redirect(url_for("faculty_dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        faculty = db.get_faculty_by_email(email)
        if not faculty:
            flash("Email not found. Use the email uploaded by admin.", "error")
        elif faculty["password"] == password:
            session.clear()
            session["logged_in"] = True
            session["role"] = "faculty"
            session["user_id"] = faculty["id"]
            session["user_name"] = faculty["name"]
            return redirect(url_for("faculty_dashboard"))
        elif faculty:
            flash("Invalid password.", "error")

    return render_template("faculty_login.html")


@app.route("/faculty/dashboard", methods=["GET", "POST"])
@faculty_required
def faculty_dashboard():
    faculty = db.get_faculty_by_id(session["user_id"])

    if request.method == "POST" and request.form.get("action") == "upload_syllabus":
        semester = request.form.get("semester", "1")
        file = request.files.get("pdf_file")
        sem = parse_semester(semester)
        if sem is None:
            flash(f"Semester must be between 1 and {db.MCA_SEMESTERS}.", "error")
        elif not file or not file.filename:
            flash("Please select a PDF file.", "error")
        elif not file.filename.lower().endswith(".pdf"):
            flash("Only PDF files are allowed.", "error")
        else:
            original_name = secure_filename(file.filename)
            stored_name = f"sem{sem}_{uuid.uuid4().hex[:8]}_{original_name}"
            file.save(db.UPLOAD_DIR / stored_name)
            existing = db.get_syllabus_by_semester(sem)
            if existing:
                old_path = db.UPLOAD_DIR / existing["filename"]
                if old_path.exists():
                    old_path.unlink()
            db.upsert_syllabus(sem, stored_name, original_name)
            db.log_activity(f"{faculty['name']} uploaded syllabus for Semester {sem}")
            flash(f"Syllabus uploaded for Semester {sem}.", "success")
        return redirect(url_for("faculty_dashboard"))

    subjects = db.get_faculty_subjects(session["user_id"])
    subject_details = []
    student_ids = set()
    for sub in subjects:
        students = db.get_students_for_subject(sub["id"])
        for s in students:
            student_ids.add(s["id"])
        subject_details.append({
            **sub,
            "student_count": len(students),
            "marks_entered": sum(1 for s in students if db.row_has_marks(s)),
        })
    syllabi = {s["semester"]: s for s in db.get_syllabi()}
    return render_template(
        "faculty_dashboard.html",
        faculty=faculty,
        subjects=subject_details,
        subject_count=len(subject_details),
        total_students=len(student_ids),
        syllabi=syllabi,
    )


@app.route("/faculty/subject/<int:subject_id>/marks", methods=["GET", "POST"])
@faculty_required
def faculty_subject_marks(subject_id):
    faculty_id = session["user_id"]
    if not db.faculty_owns_subject(faculty_id, subject_id):
        flash("You are not allocated to this subject.", "error")
        return redirect(url_for("faculty_dashboard"))

    subject = db.get_subject_by_id(subject_id)
    if not subject:
        flash("Subject not found.", "error")
        return redirect(url_for("faculty_dashboard"))

    if request.method == "POST":
        action = request.form.get("action")

        if action == "save_marks":
            students = db.get_students_for_subject(subject_id)
            updated = 0
            for student in students:
                sid = student["id"]
                mark_type = request.form.get(f"mark_type_{sid}", "assignments")
                if mark_type not in db.MARK_TYPES:
                    mark_type = "assignments"
                components = {}
                try:
                    for field in input_fields_for_mark_type(mark_type):
                        raw = request.form.get(f"{field}_{sid}", "").strip()
                        if raw:
                            components[field] = parse_mark_field(raw, field)
                    db.upsert_mark(sid, subject_id, mark_type, **components)
                    updated += 1
                except ValueError:
                    flash(f"Invalid marks for {student['usn']}. Check component ranges.", "error")
                    return redirect(url_for("faculty_subject_marks", subject_id=subject_id))

            db.log_activity(
                f"{session.get('user_name')} updated marks for {updated} students in {subject['name']}"
            )
            flash(f"Marks saved for {updated} student(s). Lab totals and final results calculated.", "success")

        elif action == "csv_upload":
            file = request.files.get("csv_file")
            if not file or not file.filename:
                flash("Please select a CSV file.", "error")
            else:
                try:
                    rows = parse_csv_upload(file, ["usn"])
                    entries = []
                    default_type = "assignments"
                    for row in rows:
                        try:
                            row_type = row.get("mark_type", default_type)
                            if row_type not in db.MARK_TYPES:
                                row_type = default_type
                            components = parse_mark_row(row, row_type)
                            if not components and not row.get("mark_type"):
                                continue
                            entries.append({"usn": row["usn"], "mark_type": row_type, **components})
                        except ValueError:
                            flash(f"Invalid marks for USN {row['usn']}. Check ranges.", "error")
                            return redirect(url_for("faculty_subject_marks", subject_id=subject_id))

                    updated, skipped = db.bulk_upsert_marks_by_usn(subject_id, default_type, entries)
                    db.log_activity(
                        f"{session.get('user_name')} uploaded marks for {updated} students in {subject['name']}"
                    )
                    flash(f"CSV upload complete: {updated} updated, {skipped} skipped.", "success")
                except Exception as e:
                    flash(f"CSV upload failed: {e}", "error")

        return redirect(url_for("faculty_subject_marks", subject_id=subject_id))

    students = db.get_students_for_subject(subject_id)
    return render_template(
        "faculty_subject_marks.html",
        faculty=db.get_faculty_by_id(faculty_id),
        subject=subject,
        students=students,
    )


@app.route("/faculty/reports")
@faculty_required
def faculty_reports():
    faculty = db.get_faculty_by_id(session["user_id"])
    report = db.get_faculty_reports(session["user_id"])
    return render_template(
        "faculty_reports.html",
        faculty=faculty,
        report=report,
    )


@app.route("/faculty/logout")
def faculty_logout():
    session.clear()
    return redirect(url_for("faculty_login"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
