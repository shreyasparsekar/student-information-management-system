"""courses.py - add / view / edit / delete / search courses."""
from flask import Blueprint
from ui import make_crud, F

bp = Blueprint("courses", __name__, url_prefix="/courses")

make_crud(
    bp, table="courses", title="Courses", singular="Course", icon="📚", colour="#7c3aed",
    fields=[F("code", "Course Code", placeholder="e.g. BCA"), F("name", "Course Name"),
            F("duration", "Duration (years)", "number", min=1, max=6, step=1),
            F("description", "Description", "textarea", required=False)],
    list_sql="SELECT id, code, name, duration, description FROM courses",
    columns=[("code", "Code"), ("name", "Course Name"), ("duration", "Years"), ("description", "Description")],
    search_cols=["code", "name", "description"],
)
