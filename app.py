import csv
import io
import os
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash

import database as db

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

db.init_db()


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
            else:
                try:
                    db.add_student(usn, name, email, int(semester))
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
                        semester = int(row.get("semester", 1) or 1)
                        db.add_student(usn, row["name"], row["email"], semester)
                        added += 1
                    db.log_activity(f"Uploaded {added} students via CSV")
                    flash(f"CSV upload complete: {added} added, {skipped} skipped.", "success")
                except Exception as e:
                    flash(f"CSV upload failed: {e}", "error")

        return redirect(url_for("students"))

    return render_template(
        "students.html",
        admin_name=session.get("admin_name", "Admin"),
        students=db.get_students(),
        active_page="students",
    )


@app.route("/students/delete/<int:student_id>", methods=["POST"])
@admin_required
def delete_student(student_id):
    if db.delete_student(student_id):
        flash("Student deleted successfully.", "success")
    else:
        flash("Student not found.", "error")
    return redirect(url_for("students"))


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
    return redirect(url_for("students"))


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
        code = (request.form.get("code") or "").strip().upper()
        name = (request.form.get("name") or "").strip()
        semester = request.form.get("semester", "1")

        if not code or not name:
            flash("Subject code and name are required.", "error")
        else:
            try:
                db.add_subject(code, name, int(semester))
                flash(f"Subject {name} added successfully.", "success")
            except Exception:
                flash("Failed to add subject. Code may already exist.", "error")
        return redirect(url_for("subjects"))

    return render_template(
        "subjects.html",
        admin_name=session.get("admin_name", "Admin"),
        subjects=db.get_subjects(),
        active_page="subjects",
    )


@app.route("/subjects/delete/<int:subject_id>", methods=["POST"])
@admin_required
def delete_subject(subject_id):
    db.delete_subject(subject_id)
    flash("Subject deleted successfully.", "success")
    return redirect(url_for("subjects"))


# ---------- Other Admin Pages ----------

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


@app.route("/reports")
@admin_required
def reports():
    return render_template(
        "reports.html",
        admin_name=session.get("admin_name", "Admin"),
        stats=db.get_dashboard_stats(),
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
    subject_marks, overall_average = db.get_student_semester_marks(
        student["id"], student["semester"]
    )
    return render_template(
        "student_dashboard.html",
        student=student,
        subject_marks=subject_marks,
        overall_average=overall_average,
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


@app.route("/faculty/dashboard")
@faculty_required
def faculty_dashboard():
    faculty = db.get_faculty_by_id(session["user_id"])
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
            "marks_entered": sum(
                1 for s in students
                if s.get("marks") is not None
                or s.get("assignment_marks") is not None
                or s.get("lab_marks") is not None
            ),
        })
    return render_template(
        "faculty_dashboard.html",
        faculty=faculty,
        subjects=subject_details,
        subject_count=len(subject_details),
        total_students=len(student_ids),
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
                assignment_raw = request.form.get(f"assignment_{sid}", "").strip()
                lab_raw = request.form.get(f"lab_{sid}", "").strip()
                theory_raw = request.form.get(f"theory_{sid}", "").strip()

                if not assignment_raw and not lab_raw and not theory_raw:
                    continue

                try:
                    assignment = float(assignment_raw) if assignment_raw else None
                    lab = float(lab_raw) if lab_raw else None
                    theory = float(theory_raw) if theory_raw else None

                    if assignment is not None and (assignment < 0 or assignment > 10):
                        flash(f"Assignment marks for {student['usn']} must be 0-10.", "error")
                        return redirect(url_for("faculty_subject_marks", subject_id=subject_id))
                    if lab is not None and (lab < 0 or lab > 10):
                        flash(f"Lab marks for {student['usn']} must be 0-10.", "error")
                        return redirect(url_for("faculty_subject_marks", subject_id=subject_id))
                    if theory is not None and (theory < 0 or theory > 20):
                        flash(f"Theory marks for {student['usn']} must be 0-20.", "error")
                        return redirect(url_for("faculty_subject_marks", subject_id=subject_id))

                    db.upsert_mark(
                        sid, subject_id,
                        theory_marks=theory,
                        assignment_marks=assignment,
                        lab_marks=lab,
                    )
                    updated += 1
                except ValueError:
                    flash(f"Invalid marks for {student['usn']}.", "error")
                    return redirect(url_for("faculty_subject_marks", subject_id=subject_id))

            db.log_activity(
                f"{session.get('user_name')} updated marks for {updated} students in {subject['name']}"
            )
            flash(f"Marks saved for {updated} student(s).", "success")

        elif action == "csv_upload":
            file = request.files.get("csv_file")
            if not file or not file.filename:
                flash("Please select a CSV file.", "error")
            else:
                try:
                    rows = parse_csv_upload(file, ["usn"])
                    entries = []
                    for row in rows:
                        try:
                            assignment = float(row["assignment_marks"]) if row.get("assignment_marks") else None
                            lab = float(row["lab_marks"]) if row.get("lab_marks") else None
                            theory_val = row.get("theory_marks") or row.get("marks")
                            theory = float(theory_val) if theory_val else None

                            if assignment is not None and (assignment < 0 or assignment > 10):
                                raise ValueError("assignment out of range")
                            if lab is not None and (lab < 0 or lab > 10):
                                raise ValueError("lab out of range")
                            if theory is not None and (theory < 0 or theory > 20):
                                raise ValueError("theory out of range")

                            if assignment is None and lab is None and theory is None:
                                continue

                            entries.append((row["usn"], theory, assignment, lab))
                        except ValueError:
                            flash(f"Invalid marks for USN {row['usn']}. Check ranges.", "error")
                            return redirect(url_for("faculty_subject_marks", subject_id=subject_id))

                    updated, skipped = db.bulk_upsert_marks_by_usn(subject_id, entries)
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


@app.route("/faculty/logout")
def faculty_logout():
    session.clear()
    return redirect(url_for("faculty_login"))


if __name__ == "__main__":
    app.run(debug=True)
