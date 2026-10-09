"""semesters.py - semester number, academic year, course, start and end dates."""
import re
from flask import Blueprint
from ui import make_crud, F, opt_courses, SEMESTERS

bp = Blueprint("semesters", __name__, url_prefix="/semesters")


def validate(v, row_id):
    m = re.fullmatch(r"(\d{4})-(\d{4})", v["academic_year"])
    if not m or int(m.group(2)) != int(m.group(1)) + 1:
        return "Academic year must look like 2025-2026."
    if v["end_date"] <= v["start_date"]:
        return "End date must be after the start date."


make_crud(
    bp, table="semesters", title="Semesters", singular="Semester", icon="🎓", colour="#ea580c",
    fields=[F("course_id", "Course", "select", options=opt_courses),
            F("number", "Semester Number", "select", options=SEMESTERS),
            F("academic_year", "Academic Year", placeholder="2025-2026"),
            F("start_date", "Start Date", "date"), F("end_date", "End Date", "date")],
    list_sql="""SELECT s.id, c.name AS course, s.number AS semester, s.academic_year, s.start_date, s.end_date
                FROM semesters s JOIN courses c ON c.id = s.course_id""",
    columns=[("course", "Course"), ("semester", "Semester"), ("academic_year", "Academic Year"),
             ("start_date", "Start Date"), ("end_date", "End Date")],
    search_cols=["course", "semester", "academic_year"],
    validate=validate,
)
