"""subjects.py - manage subjects (code, name, course, semester, credits)."""
from flask import Blueprint
from ui import make_crud, F, opt_courses, SEMESTERS

bp = Blueprint("subjects", __name__, url_prefix="/subjects")

make_crud(
    bp, table="subjects", title="Subjects", singular="Subject", icon="📖", colour="#0d9488",
    fields=[F("subject_code", "Subject ID", placeholder="e.g. BCA101"), F("name", "Subject Name"),
            F("course_id", "Course", "select", options=opt_courses),
            F("semester_no", "Semester", "select", options=SEMESTERS),
            F("credits", "Credits", "number", min=1, max=10, step=1)],
    list_sql="""SELECT s.id, s.subject_code, s.name, c.name AS course, s.semester_no AS semester, s.credits
                FROM subjects s JOIN courses c ON c.id = s.course_id""",
    columns=[("subject_code", "Subject ID"), ("name", "Subject Name"), ("course", "Course"),
             ("semester", "Semester"), ("credits", "Credits")],
    search_cols=["subject_code", "name", "course", "semester"],
)
