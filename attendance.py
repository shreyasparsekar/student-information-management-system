"""attendance.py - add / update / view / search attendance with colour indicators."""
from flask import Blueprint
from ui import make_crud, F, opt_students, opt_subjects, pct_badge

bp = Blueprint("attendance", __name__, url_prefix="/attendance")


def validate(v, row_id):
    if int(float(v["present"])) > int(float(v["total_classes"])):
        return "Present classes cannot be more than total classes."


make_crud(
    bp, table="attendance", title="Attendance", singular="Attendance", icon="📅", colour="#16a34a",
    fields=[F("student_id", "Student", "select", options=opt_students),
            F("subject_id", "Subject", "select", options=opt_subjects),
            F("total_classes", "Total Classes", "number", min=1, step=1),
            F("present", "Classes Present", "number", min=0, step=1)],
    list_sql="""SELECT a.id, st.full_name AS name, st.student_id AS sid, sub.name AS subject,
                a.total_classes AS total, a.present, a.total_classes - a.present AS absent,
                ROUND(a.present * 100.0 / a.total_classes, 1) AS pct
                FROM attendance a JOIN students st ON st.id = a.student_id JOIN subjects sub ON sub.id = a.subject_id""",
    columns=[("name", "Student"), ("sid", "Student ID"), ("subject", "Subject"), ("total", "Total"),
             ("present", "Present"), ("absent", "Absent"), ("pct", "Attendance", pct_badge)],
    search_cols=["name", "sid", "subject"],
    validate=validate,
)
