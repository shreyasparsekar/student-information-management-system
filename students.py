"""students.py - student CRUD, search and individual student profile page."""
from datetime import date
from flask import Blueprint, flash, redirect, url_for
from auth import login_required
from database import query
from ui import (make_crud, F, opt_courses, SEMESTERS, render, data_table, money, pct_badge, status_badge)

bp = Blueprint("students", __name__, url_prefix="/students")


def validate(v, row_id):
    v["student_id"] = v["student_id"].upper()
    if not (v["phone"].isdigit() and len(v["phone"]) == 10):
        return "Phone number must contain exactly 10 digits."
    if v["dob"] >= date.today().isoformat():
        return "Date of birth must be in the past."
    if v["admission_date"] <= v["dob"]:
        return "Admission date must be after the date of birth."


make_crud(
    bp, table="students", title="Students", singular="Student", icon="🧑‍🎓", colour="#2563eb",
    fields=[F("student_id", "Student ID", placeholder="e.g. STU2025008"), F("full_name", "Full Name"),
            F("dob", "Date of Birth", "date"),
            F("gender", "Gender", "select", options=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")]),
            F("phone", "Phone Number", "tel", placeholder="10 digits"), F("email", "Email", "email"),
            F("course_id", "Course", "select", options=opt_courses),
            F("semester_no", "Semester", "select", options=SEMESTERS),
            F("admission_date", "Admission Date", "date", default="today"),
            F("address", "Address", "textarea")],
    list_sql="""SELECT s.id, s.student_id, s.full_name, s.gender, s.phone, s.email, c.name AS course,
                s.semester_no AS semester, s.admission_date
                FROM students s JOIN courses c ON c.id = s.course_id""",
    columns=[("student_id", "Student ID"), ("full_name", "Name"), ("gender", "Gender"), ("phone", "Phone"),
             ("email", "Email"), ("course", "Course"), ("semester", "Sem"), ("admission_date", "Admitted")],
    search_cols=["student_id", "full_name", "phone", "email", "course"],
    validate=validate,
    row_links=[("👁️ View", "students.view", "btn-green")],
)


@bp.route("/view/<int:row_id>")
@login_required
def view(row_id):
    s = query("""SELECT s.*, c.name AS course FROM students s JOIN courses c ON c.id = s.course_id
                 WHERE s.id = ?""", (row_id,), one=True)
    if not s:
        flash("Student not found.", "error")
        return redirect(url_for("students.index"))
    sections = [
        ("📝 Enrolled Subjects", data_table(
            [("subject", "Subject"), ("semester_no", "Semester"), ("enroll_date", "Enrolled On"),
             ("status", "Status", status_badge)],
            query("""SELECT sub.name AS subject, e.semester_no, e.enroll_date, e.status FROM enrollments e
                     JOIN subjects sub ON sub.id = e.subject_id WHERE e.student_id = ?""", (row_id,)))),
        ("📅 Attendance", data_table(
            [("subject", "Subject"), ("total_classes", "Total"), ("present", "Present"), ("absent", "Absent"),
             ("pct", "Attendance", pct_badge)],
            query("""SELECT sub.name AS subject, a.total_classes, a.present, a.total_classes - a.present AS absent,
                     a.present * 100.0 / a.total_classes AS pct FROM attendance a
                     JOIN subjects sub ON sub.id = a.subject_id WHERE a.student_id = ?""", (row_id,)))),
        ("📊 Marks & Results", data_table(
            [("subject", "Subject"), ("internal", "Internal"), ("external", "External"), ("total", "Total"),
             ("percentage", "%"), ("grade", "Grade"), ("result", "Result", status_badge)],
            query("""SELECT sub.name AS subject, m.* FROM marks m JOIN subjects sub ON sub.id = m.subject_id
                     WHERE m.student_id = ?""", (row_id,)))),
        ("💰 Fees", data_table(
            [("total_fees", "Total", money), ("paid", "Paid", money), ("pending", "Pending", money),
             ("payment_date", "Payment Date"), ("status", "Status", status_badge)],
            query("SELECT * FROM fees WHERE student_id = ?", (row_id,)))),
    ]
    return render(VIEW_T, "Student Profile", s=s, sections=sections)


VIEW_T = """
<div style="--c:#2563eb">
<div class="page-head"><h2>🧑‍🎓 Student Profile</h2><a class="btn btn-grey" href="{{ url_for('students.index') }}">⬅ Back</a></div>
<div class="panel"><div class="profile-top"><div class="big-avatar">{{ s.full_name[:1] }}</div>
 <div><h3 style="margin:0">{{ s.full_name }}</h3><span class="muted">{{ s.student_id }} · {{ s.course }} · Semester {{ s.semester_no }}</span></div></div>
 <div class="kv">
  <div><b>Date of Birth</b>{{ s.dob }}</div><div><b>Gender</b>{{ s.gender }}</div><div><b>Phone</b>{{ s.phone }}</div>
  <div><b>Email</b>{{ s.email }}</div><div><b>Admission Date</b>{{ s.admission_date }}</div><div><b>Address</b>{{ s.address }}</div>
 </div></div>
{% for name, table in sections %}<h3 class="sec">{{ name }}</h3>{{ table }}{% endfor %}
</div>
"""
