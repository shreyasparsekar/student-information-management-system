"""enrollment.py - enrol students into a course, semester and subject."""
from flask import Blueprint
from database import query
from ui import make_crud, F, opt_students, opt_courses, opt_subjects, SEMESTERS, status_badge

bp = Blueprint("enrollment", __name__, url_prefix="/enrollment")


def validate(v, row_id):
    sub = query("SELECT course_id, semester_no FROM subjects WHERE id = ?", (v["subject_id"],), one=True)
    if not sub:
        return "Selected subject does not exist."
    if str(sub["course_id"]) != v["course_id"] or str(sub["semester_no"]) != v["semester_no"]:
        return "The selected subject does not belong to the chosen course and semester."


make_crud(
    bp, table="enrollments", title="Enrollment", singular="Enrollment", icon="📝", colour="#db2777",
    fields=[F("student_id", "Student", "select", options=opt_students),
            F("course_id", "Course", "select", options=opt_courses),
            F("semester_no", "Semester", "select", options=SEMESTERS),
            F("subject_id", "Subject", "select", options=opt_subjects),
            F("enroll_date", "Enrollment Date", "date", default="today"),
            F("status", "Status", "select", options=[("Active", "Active"), ("Completed", "Completed"), ("Dropped", "Dropped")])],
    list_sql="""SELECT e.id, st.student_id AS sid, st.full_name AS name, c.name AS course, e.semester_no AS semester,
                sub.name AS subject, e.enroll_date, e.status FROM enrollments e
                JOIN students st ON st.id = e.student_id JOIN courses c ON c.id = e.course_id
                JOIN subjects sub ON sub.id = e.subject_id""",
    columns=[("sid", "Student ID"), ("name", "Student"), ("course", "Course"), ("semester", "Sem"),
             ("subject", "Subject"), ("enroll_date", "Enrolled On"), ("status", "Status", status_badge)],
    search_cols=["sid", "name", "course", "subject", "status"],
    validate=validate,
)
