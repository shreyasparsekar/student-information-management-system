"""marks.py - internal + external marks; total, percentage, grade and result are automatic."""
from flask import Blueprint
from database import calc_grade
from ui import make_crud, F, opt_students, opt_subjects, status_badge, badge

bp = Blueprint("marks", __name__, url_prefix="/marks")
MAX_TOTAL = 100  # internal (40) + external (60)


def validate(v, row_id):
    internal, external = float(v["internal"]), float(v["external"])
    total = internal + external
    pct = round(total * 100 / MAX_TOTAL, 2)
    v.update(internal=internal, external=external, total=total, percentage=pct,
             grade=calc_grade(pct), result="Pass" if pct >= 40 else "Fail")


make_crud(
    bp, table="marks", title="Marks & Results", singular="Marks", icon="📊", colour="#4f46e5",
    fields=[F("student_id", "Student", "select", options=opt_students),
            F("subject_id", "Subject", "select", options=opt_subjects),
            F("internal", "Internal Marks (out of 40)", "number", min=0, max=40),
            F("external", "External Marks (out of 60)", "number", min=0, max=60)],
    list_sql="""SELECT m.id, st.student_id AS sid, st.full_name AS name, sub.name AS subject, m.internal, m.external,
                m.total, m.percentage, m.grade, m.result FROM marks m
                JOIN students st ON st.id = m.student_id JOIN subjects sub ON sub.id = m.subject_id""",
    columns=[("sid", "Student ID"), ("name", "Student"), ("subject", "Subject"), ("internal", "Internal"),
             ("external", "External"), ("total", "Total"), ("percentage", "%", lambda v, r: f"{v:.1f}%"),
             ("grade", "Grade", lambda v, r: badge(v, "green" if v in ("A+", "A", "B+") else "yellow" if v in ("B", "C", "D") else "red")),
             ("result", "Result", status_badge)],
    search_cols=["sid", "name", "subject", "grade", "result"],
    validate=validate,
)
