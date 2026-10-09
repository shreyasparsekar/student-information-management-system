"""reports.py - five filterable reports with print and CSV export."""
import csv
import io
from flask import Blueprint, request, Response
from auth import login_required
from database import query
from ui import render, data_table, opt_courses, money, pct_badge, status_badge

bp = Blueprint("reports", __name__, url_prefix="/reports")

REPORTS = {
    "student": ("Student Report", """SELECT s.id, s.course_id, s.student_id AS sid, s.full_name AS name, s.gender, s.phone,
        s.email, c.name AS course, s.semester_no AS semester, s.admission_date FROM students s
        JOIN courses c ON c.id = s.course_id""",
        [("sid", "Student ID"), ("name", "Name"), ("gender", "Gender"), ("phone", "Phone"), ("email", "Email"),
         ("course", "Course"), ("semester", "Sem"), ("admission_date", "Admitted")]),
    "attendance": ("Attendance Report", """SELECT a.id, st.course_id, st.student_id AS sid, st.full_name AS name,
        sub.name AS subject, a.total_classes AS total, a.present, a.total_classes - a.present AS absent,
        ROUND(a.present * 100.0 / a.total_classes, 1) AS pct FROM attendance a
        JOIN students st ON st.id = a.student_id JOIN subjects sub ON sub.id = a.subject_id""",
        [("sid", "Student ID"), ("name", "Student"), ("subject", "Subject"), ("total", "Total"),
         ("present", "Present"), ("absent", "Absent"), ("pct", "Attendance", pct_badge)]),
    "marks": ("Marks / Result Report", """SELECT m.id, st.course_id, st.student_id AS sid, st.full_name AS name,
        sub.name AS subject, m.internal, m.external, m.total, m.percentage, m.grade, m.result FROM marks m
        JOIN students st ON st.id = m.student_id JOIN subjects sub ON sub.id = m.subject_id""",
        [("sid", "Student ID"), ("name", "Student"), ("subject", "Subject"), ("internal", "Internal"),
         ("external", "External"), ("total", "Total"), ("grade", "Grade"), ("result", "Result", status_badge)]),
    "fees": ("Fees Report", """SELECT f.id, f.course_id, st.student_id AS sid, st.full_name AS name, c.name AS course,
        f.total_fees, f.paid, f.pending, f.payment_date, f.status FROM fees f
        JOIN students st ON st.id = f.student_id JOIN courses c ON c.id = f.course_id""",
        [("sid", "Student ID"), ("name", "Student"), ("course", "Course"), ("total_fees", "Total", money),
         ("paid", "Paid", money), ("pending", "Pending", money), ("status", "Status", status_badge)]),
    "course": ("Course-wise Student Report", """SELECT c.id, c.id AS course_id, c.code, c.name AS course,
        (SELECT COUNT(*) FROM students WHERE course_id = c.id) AS students,
        (SELECT COUNT(*) FROM subjects WHERE course_id = c.id) AS subjects,
        (SELECT IFNULL(SUM(pending), 0) FROM fees WHERE course_id = c.id) AS pending,
        (SELECT IFNULL(GROUP_CONCAT(full_name, ', '), '-') FROM students WHERE course_id = c.id) AS names FROM courses c""",
        [("code", "Code"), ("course", "Course"), ("students", "Students"), ("subjects", "Subjects"),
         ("pending", "Pending Fees", money), ("names", "Student Names")]),
}
SEARCH = {"student": ["sid", "name", "email", "course"], "attendance": ["sid", "name", "subject"],
          "marks": ["sid", "name", "subject", "grade", "result"], "fees": ["sid", "name", "course", "status"],
          "course": ["code", "course", "names"]}


@bp.route("/")
@login_required
def index():
    kind = request.args.get("type", "student")
    if kind not in REPORTS:
        kind = "student"
    q, course = request.args.get("q", "").strip(), request.args.get("course", "")
    title, sql, columns = REPORTS[kind]
    where, args = [], []
    if q:
        where.append("(" + " OR ".join(f"CAST({c} AS TEXT) LIKE ?" for c in SEARCH[kind]) + ")")
        args += [f"%{q}%"] * len(SEARCH[kind])
    if course.isdigit():
        where.append("course_id = ?")
        args.append(int(course))
    rows = query(f"SELECT * FROM ({sql})" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id", args)
    if request.args.get("export") == "csv":
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow([c[1] for c in columns])
        w.writerows([[r[c[0]] for c in columns] for r in rows])
        return Response(out.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={kind}_report.csv"})
    tabs = [(k, v[0]) for k, v in REPORTS.items()]
    return render(REPORT_T, "Reports", tabs=tabs, kind=kind, rtitle=title, q=q, course=course,
                  courses=opt_courses(), table=data_table(columns, rows), count=len(rows))


REPORT_T = """
<div style="--c:#0891b2">
<div class="page-head"><h2>📑 Reports</h2></div>
<div class="tabs">{% for k, name in tabs %}<a class="{{ 'on' if k == kind }}" href="{{ url_for('reports.index', type=k) }}">{{ name }}</a>{% endfor %}</div>
<form class="filters" method="get"><input type="hidden" name="type" value="{{ kind }}">
 <input type="search" name="q" value="{{ q }}" placeholder="Search this report...">
 <select name="course"><option value="">All courses</option>
  {% for v, l in courses %}<option value="{{ v }}" {{ 'selected' if v|string == course }}>{{ l }}</option>{% endfor %}</select>
 <button class="btn btn-main" type="submit">🔍 Apply</button>
 <a class="btn btn-grey" href="{{ url_for('reports.index', type=kind) }}">✖ Reset</a>
 <a class="btn btn-green" href="{{ url_for('reports.index', type=kind, q=q, course=course, export='csv') }}">⬇ Export CSV</a>
 <button class="btn btn-blue" type="button" onclick="window.print()">🖨️ Print</button>
</form>
<h3 class="sec">{{ rtitle }} <span class="muted">({{ count }} rows)</span></h3>
{{ table }}
</div>
"""
