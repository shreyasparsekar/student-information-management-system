"""ui.py - shared page layout (sidebar, header, CSS) and the generic CRUD engine
used by students, courses, subjects, semesters, enrollment, attendance, marks, fees and admin."""
import re
import sqlite3
from datetime import date, datetime
from flask import render_template_string, request, session, redirect, url_for, flash
from markupsafe import Markup, escape
from auth import login_required, admin_required, is_admin
from database import query, execute

# (icon, title, short description, endpoint, colour)
MODULES = [
    ("🧑‍🎓", "Students", "Add, search and manage student records", "students.index", "#2563eb"),
    ("📚", "Courses", "Manage the courses offered by the college", "courses.index", "#7c3aed"),
    ("📖", "Subjects", "Subjects, credits and semester mapping", "subjects.index", "#0d9488"),
    ("🎓", "Semesters", "Academic years and semester dates", "semesters.index", "#ea580c"),
    ("📝", "Enrollment", "Enrol students into courses and subjects", "enrollment.index", "#db2777"),
    ("📅", "Attendance", "Track classes attended with colour alerts", "attendance.index", "#16a34a"),
    ("📊", "Marks & Results", "Marks, grades and pass/fail results", "marks.index", "#4f46e5"),
    ("💰", "Fees", "Fees paid, pending and payment status", "fees.index", "#d97706"),
    ("📑", "Reports", "Filter, print and export reports", "reports.index", "#0891b2"),
    ("👤", "Profile", "View and update your own account", "profile.index", "#475569"),
    ("⚙️", "Admin Panel", "Users, roles and system information", "admin.index", "#dc2626"),
    ("🚪", "Logout", "Sign out of the system safely", "auth.logout", "#64748b"),
]

SEMESTERS = [(i, f"Semester {i}") for i in range(1, 9)]


# ---------- dropdown option helpers ----------
def opt_courses():
    return [(r["id"], r["name"]) for r in query("SELECT id, name FROM courses ORDER BY name")]


def opt_students():
    return [(r["id"], f'{r["student_id"]} - {r["full_name"]}')
            for r in query("SELECT id, student_id, full_name FROM students ORDER BY student_id")]


def opt_subjects():
    return [(r["id"], f'{r["subject_code"]} - {r["name"]} (Sem {r["semester_no"]})')
            for r in query("SELECT id, subject_code, name, semester_no FROM subjects ORDER BY subject_code")]


# ---------- small HTML helpers ----------
def badge(text, colour):
    return Markup(f'<span class="badge {colour}">{escape(text)}</span>')


def money(value, row=None):
    return f"₹{float(value or 0):,.2f}"


def pct_badge(value, row=None):
    v = float(value)
    return badge(f"{v:.1f}%", "green" if v >= 75 else "yellow" if v >= 60 else "red")


STATUS_COLOURS = {"Paid": "green", "Partially Paid": "yellow", "Pending": "red", "Pass": "green", "Fail": "red",
                  "Active": "green", "Completed": "blue", "Dropped": "red", "admin": "red", "user": "blue"}


def status_badge(value, row=None):
    return badge(value, STATUS_COLOURS.get(value, "blue"))


def data_table(columns, rows):
    """Plain read-only table (used by reports and the student profile page)."""
    head = "".join(f"<th>{escape(c[1])}</th>" for c in columns)
    body = ""
    for r in rows:
        cells = ""
        for c in columns:
            val = c[2](r[c[0]], r) if len(c) > 2 else ("" if r[c[0]] is None else r[c[0]])
            cells += f'<td data-label="{escape(c[1])}">{escape(val)}</td>'
        body += f"<tr>{cells}</tr>"
    if not rows:
        body = f'<tr><td colspan="{len(columns)}" class="empty">No records found.</td></tr>'
    return Markup(f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')


# ---------- page rendering ----------
def render(inner, title, **ctx):
    body = render_template_string(inner, title=title, admin=is_admin(), **ctx)
    ep = (request.endpoint or "").split(".")[0]
    return render_template_string(BASE, title=title, body=Markup(body), modules=MODULES, active=ep, admin=is_admin())


def render_login(username=""):
    return render_template_string(LOGIN_T, username=username)


# ---------- generic CRUD engine ----------
def F(name, label, type="text", required=True, options=None, **kw):
    return dict(name=name, label=label, type=type, required=required, options=options, **kw)


def make_crud(bp, *, table, title, singular, icon, colour, fields, list_sql, columns, search_cols,
              validate=None, can_delete=None, extra_buttons=(), row_links=(), admin_only=False):
    read_guard = admin_required if admin_only else login_required
    ep = bp.name

    def check(values, row_id):
        for f in fields:
            v = values[f["name"]]
            if not v:
                if f["required"] and not (f["type"] == "password" and row_id):
                    return f'{f["label"]} is required.'
                continue
            if f["type"] == "number":
                try:
                    n = float(v)
                except ValueError:
                    return f'{f["label"]} must be a number.'
                if "min" in f and n < f["min"]:
                    return f'{f["label"]} must be at least {f["min"]}.'
                if "max" in f and n > f["max"]:
                    return f'{f["label"]} must not be more than {f["max"]}.'
            elif f["type"] == "date":
                try:
                    datetime.strptime(v, "%Y-%m-%d")
                except ValueError:
                    return f'{f["label"]} must be a valid date.'
            elif f["type"] == "email" and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
                return "Please enter a valid email address."
        return validate(values, row_id) if validate else None

    def index():
        q = request.args.get("q", "").strip()
        sql, args = f"SELECT * FROM ({list_sql})", []
        if q:
            sql += " WHERE " + " OR ".join(f"CAST({c} AS TEXT) LIKE ?" for c in search_cols)
            args = [f"%{q}%"] * len(search_cols)
        try:
            rows = query(sql + " ORDER BY id DESC", args)
        except sqlite3.Error:
            flash("Could not read data from the database.", "error")
            rows = []

        def cell(row, col):
            return col[2](row[col[0]], row) if len(col) > 2 else ("" if row[col[0]] is None else row[col[0]])
        return render(LIST_T, title, icon=icon, colour=colour, columns=columns, rows=rows, q=q, cell=cell, ep=ep,
                      singular=singular, extra_buttons=extra_buttons, row_links=row_links)

    def form(row_id=None):
        values = {}
        if row_id:
            rec = query(f"SELECT * FROM {table} WHERE id = ?", (row_id,), one=True)
            if not rec:
                flash("Record not found.", "error")
                return redirect(url_for(f"{ep}.index"))
            values = dict(rec)
        if request.method == "POST":
            values = {f["name"]: request.form.get(f["name"], "").strip() for f in fields}
            error = check(values, row_id)
            if not error:
                data = {k: (v if v != "" else None) for k, v in values.items()}
                cols = list(data)
                try:
                    if row_id:
                        execute(f"UPDATE {table} SET {', '.join(c + '=?' for c in cols)} WHERE id = ?",
                                [*data.values(), row_id])
                        flash(f"{singular} updated successfully.", "success")
                    else:
                        execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                                list(data.values()))
                        flash(f"{singular} added successfully.", "success")
                    return redirect(url_for(f"{ep}.index"))
                except sqlite3.IntegrityError as e:
                    msg = str(e)
                    error = ("A record with the same unique value already exists." if "UNIQUE" in msg else
                             "One of the selected items does not exist." if "FOREIGN KEY" in msg else
                             "The data breaks a database rule. Please check the values.")
                except sqlite3.Error:
                    error = "Database error. Please try again."
            flash(error, "error")
        shown = []
        for f in fields:
            opts = f["options"]() if callable(f["options"]) else f["options"]
            val = values.get(f["name"], "")
            if val in ("", None) and not row_id and f.get("default") == "today":
                val = date.today().isoformat()
            shown.append({**f, "opts": opts, "value": "" if f["type"] == "password" or val is None else val})
        return render(FORM_T, title, icon=icon, colour=colour, fields=shown, editing=bool(row_id),
                      singular=singular, back=url_for(f"{ep}.index"))

    def delete(row_id):
        err = can_delete(row_id) if can_delete else None
        if err:
            flash(err, "error")
        else:
            try:
                execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
                flash(f"{singular} deleted.", "success")
            except sqlite3.IntegrityError:
                flash(f"Cannot delete this {singular.lower()} because other records depend on it. "
                      "Remove those records first.", "error")
            except sqlite3.Error:
                flash("Database error. Please try again.", "error")
        return redirect(url_for(f"{ep}.index"))

    bp.add_url_rule("/", endpoint="index", view_func=read_guard(index))
    bp.add_url_rule("/add", endpoint="add", view_func=admin_required(lambda: form(None)), methods=["GET", "POST"])
    bp.add_url_rule("/edit/<int:row_id>", endpoint="edit", view_func=admin_required(form), methods=["GET", "POST"])
    bp.add_url_rule("/delete/<int:row_id>", endpoint="delete", view_func=admin_required(delete), methods=["POST"])


LIST_T = """
<div style="--c:{{ colour }}">
<div class="page-head"><h2><span class="ico">{{ icon }}</span> {{ title }}</h2>
 <div class="btn-row">
  {% for label, endpoint, css in extra_buttons %}<a class="btn {{ css }}" href="{{ url_for(endpoint) }}">{{ label }}</a>{% endfor %}
  {% if admin %}<a class="btn btn-main" href="{{ url_for(ep + '.add') }}">➕ Add {{ singular }}</a>{% endif %}
 </div></div>
<form class="searchbar" method="get">
 <input type="search" name="q" value="{{ q }}" placeholder="Search {{ title|lower }}...">
 <button class="btn btn-main" type="submit">🔍 Search</button>
 {% if q %}<a class="btn btn-grey" href="{{ url_for(ep + '.index') }}">✖ Clear</a>{% endif %}
</form>
<div class="table-wrap"><table>
 <thead><tr>{% for c in columns %}<th>{{ c[1] }}</th>{% endfor %}<th>Actions</th></tr></thead>
 <tbody>
 {% for r in rows %}<tr>
  {% for c in columns %}<td data-label="{{ c[1] }}">{{ cell(r, c) }}</td>{% endfor %}
  <td data-label="Actions" class="actions">
   {% for label, endpoint, css in row_links %}<a class="btn btn-sm {{ css }}" href="{{ url_for(endpoint, row_id=r['id']) }}">{{ label }}</a>{% endfor %}
   {% if admin %}<a class="btn btn-sm btn-blue" href="{{ url_for(ep + '.edit', row_id=r['id']) }}">✏️ Edit</a>
   <form method="post" action="{{ url_for(ep + '.delete', row_id=r['id']) }}" onsubmit="return confirm('Delete this record permanently?')">
    <button class="btn btn-sm btn-red" type="submit">🗑️ Delete</button></form>
   {% elif not row_links %}<span class="muted">View only</span>{% endif %}
  </td></tr>
 {% else %}<tr><td colspan="{{ columns|length + 1 }}" class="empty">No records found.{% if admin %} Use “Add {{ singular }}” to create one.{% endif %}</td></tr>
 {% endfor %}
 </tbody></table></div>
<p class="muted">{{ rows|length }} record(s) shown.</p>
</div>
"""

FORM_T = """
<div style="--c:{{ colour }}">
<div class="page-head"><h2><span class="ico">{{ icon }}</span> {{ 'Edit' if editing else 'Add' }} {{ singular }}</h2>
 <a class="btn btn-grey" href="{{ back }}">⬅ Back</a></div>
<form method="post" class="panel form-grid" autocomplete="off">
 {% for f in fields %}
 <div class="field {{ 'full' if f.type == 'textarea' }}">
  <label for="{{ f.name }}">{{ f.label }}{% if f.required and not (f.type == 'password' and editing) %} <span class="req">*</span>{% endif %}</label>
  {% if f.type == 'select' %}
   <select id="{{ f.name }}" name="{{ f.name }}"><option value="">-- Select --</option>
    {% for v, l in f.opts %}<option value="{{ v }}" {{ 'selected' if v|string == f.value|string }}>{{ l }}</option>{% endfor %}</select>
  {% elif f.type == 'textarea' %}
   <textarea id="{{ f.name }}" name="{{ f.name }}" rows="3">{{ f.value }}</textarea>
  {% else %}
   <input id="{{ f.name }}" name="{{ f.name }}" type="{{ f.type }}" value="{{ f.value }}"
    {% if f.type == 'number' %}step="{{ f.step or 'any' }}" {% if f.min is defined %}min="{{ f.min }}"{% endif %} {% if f.max is defined %}max="{{ f.max }}"{% endif %}{% endif %}
    {% if f.placeholder %}placeholder="{{ f.placeholder }}"{% endif %}>
   {% if f.type == 'password' and editing %}<small class="muted">Leave blank to keep the current password.</small>{% endif %}
  {% endif %}
  {% if f.hint %}<small class="muted">{{ f.hint }}</small>{% endif %}
 </div>
 {% endfor %}
 <div class="full btn-row"><button class="btn btn-main" type="submit">💾 Save {{ singular }}</button>
  <a class="btn btn-grey" href="{{ back }}">Cancel</a></div>
</form></div>
"""

CSS = """
:root{--bg:#eef2f7;--ink:#1e293b;--muted:#64748b;--side:#0f172a}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--ink);line-height:1.5}
a{color:inherit}
.topbar{position:fixed;top:0;left:0;right:0;height:60px;background:linear-gradient(90deg,#4f46e5,#2563eb 55%,#0ea5e9);color:#fff;display:flex;align-items:center;gap:12px;padding:0 18px;z-index:30;box-shadow:0 2px 12px rgba(15,23,42,.25)}
.topbar h1{font-size:1.05rem;margin:0;flex:1;letter-spacing:.4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.menu-btn{display:none;background:rgba(255,255,255,.2);border:0;color:#fff;font-size:1.4rem;border-radius:8px;padding:2px 10px;cursor:pointer}
.user-chip{display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.18);padding:4px 14px 4px 5px;border-radius:30px;font-size:.85rem;text-decoration:none}
.avatar{width:30px;height:30px;border-radius:50%;background:#fff;color:#4f46e5;display:grid;place-items:center;font-weight:700}
.top-logout{background:#ef4444;color:#fff;text-decoration:none;padding:7px 14px;border-radius:8px;font-size:.85rem;font-weight:600}
.top-logout:hover{background:#dc2626}
.sidebar{position:fixed;top:60px;bottom:0;left:0;width:240px;background:var(--side);padding:12px 10px;overflow-y:auto;z-index:20;transition:transform .25s}
.sidebar a{display:flex;align-items:center;gap:12px;color:#cbd5e1;text-decoration:none;padding:9px 12px;border-radius:10px;margin-bottom:4px;border-left:4px solid var(--c);font-size:.93rem;transition:.2s}
.sidebar a:hover,.sidebar a.active{background:var(--c);color:#fff;transform:translateX(3px)}
.main{margin:60px 0 0 240px;padding:24px;min-height:calc(100vh - 60px)}
.page-head{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:18px;padding-left:14px;border-left:6px solid var(--c,#2563eb)}
.page-head h2{margin:0;font-size:1.5rem}.ico{margin-right:4px}
.btn-row{display:flex;gap:8px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:6px;border:0;border-radius:9px;padding:9px 16px;font-size:.9rem;font-weight:600;color:#fff;cursor:pointer;text-decoration:none;background:#64748b;transition:.2s;font-family:inherit}
.btn:hover{filter:brightness(1.1);transform:translateY(-2px);box-shadow:0 4px 10px rgba(0,0,0,.18)}
.btn-main{background:var(--c,#2563eb)}.btn-blue{background:#2563eb}.btn-green{background:#16a34a}.btn-red{background:#dc2626}.btn-grey{background:#64748b}.btn-purple{background:#7c3aed}.btn-orange{background:#ea580c}
.btn-sm{padding:5px 10px;font-size:.8rem}
.searchbar{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.searchbar input,.filters input,.filters select{flex:1;min-width:180px}
input,select,textarea{width:100%;padding:10px 12px;border:2px solid #cbd5e1;border-radius:9px;font-size:.95rem;font-family:inherit;background:#fff}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--c,#2563eb);box-shadow:0 0 0 3px rgba(37,99,235,.15)}
.table-wrap{overflow-x:auto;background:#fff;border-radius:12px;box-shadow:0 2px 10px rgba(15,23,42,.08)}
table{width:100%;border-collapse:collapse;font-size:.9rem}
th{background:var(--c,#2563eb);color:#fff;text-align:left;padding:12px;white-space:nowrap}
td{padding:10px 12px;border-bottom:1px solid #e2e8f0;vertical-align:middle}
tbody tr:nth-child(even){background:#f8fafc}tbody tr:hover{background:#eef6ff}
td.actions{display:flex;gap:6px;flex-wrap:wrap;align-items:center}td.actions form{margin:0}
.empty{text-align:center;color:var(--muted);padding:28px}.muted{color:var(--muted);font-size:.85rem}
.badge{display:inline-block;padding:3px 11px;border-radius:20px;font-size:.8rem;font-weight:700}
.badge.green{background:#dcfce7;color:#166534}.badge.yellow{background:#fef3c7;color:#92400e}.badge.red{background:#fee2e2;color:#991b1b}.badge.blue{background:#dbeafe;color:#1e40af}
.panel{background:#fff;border-radius:14px;padding:22px;box-shadow:0 2px 10px rgba(15,23,42,.08);margin-bottom:20px}
.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}
.field label{display:block;font-weight:600;margin-bottom:5px;font-size:.88rem}.req{color:#dc2626}.full{grid-column:1/-1}
.alert{padding:12px 16px;border-radius:10px;margin-bottom:16px;font-weight:600}
.alert.success{background:#dcfce7;color:#166534;border-left:5px solid #16a34a}.alert.error{background:#fee2e2;color:#991b1b;border-left:5px solid #dc2626}
.stats,.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:16px;margin-bottom:26px}
.stat,.card{background:var(--c);background-image:linear-gradient(135deg,rgba(255,255,255,.2),rgba(0,0,0,.14));color:#fff;border-radius:16px;padding:18px;box-shadow:0 4px 14px rgba(15,23,42,.18)}
.stat .n{font-size:1.8rem;font-weight:800}.stat .l{opacity:.92;font-size:.9rem}.stat .i{float:right;font-size:2rem}
.card{text-decoration:none;display:block;transition:.2s;min-height:130px}.card:hover{transform:translateY(-6px);box-shadow:0 10px 22px rgba(15,23,42,.28)}
.card .i{font-size:2.2rem}.card h3{margin:6px 0 2px}.card p{margin:0;font-size:.85rem;opacity:.92}
h3.sec{margin:6px 0 14px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.tabs a{text-decoration:none;padding:8px 14px;border-radius:30px;background:#fff;border:2px solid var(--c);color:var(--c);font-weight:600;font-size:.88rem}
.tabs a.on,.tabs a:hover{background:var(--c);color:#fff}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.profile-top{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.big-avatar{width:80px;height:80px;border-radius:50%;background:var(--c);color:#fff;display:grid;place-items:center;font-size:2.2rem;font-weight:700}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:16px}
.kv div{background:#f8fafc;border-radius:10px;padding:10px 14px;border-left:4px solid var(--c)}.kv b{display:block;font-size:.78rem;color:var(--muted);font-weight:600}
@media(max-width:850px){
 .menu-btn{display:block}.sidebar{transform:translateX(-100%)}.sidebar.open{transform:none;box-shadow:6px 0 20px rgba(0,0,0,.35)}
 .main{margin-left:0;padding:14px}.user-chip .nm{display:none}.topbar h1{font-size:.8rem}
}
@media print{.topbar,.sidebar,.filters,.tabs,.btn-row,.page-head .btn{display:none!important}.main{margin:0}}
"""

BASE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} | STUDENT INFORMATION MANAGEMENT SYSTEM</title>
<style>""" + CSS + """</style></head><body>
<header class="topbar">
 <button class="menu-btn" onclick="document.getElementById('sb').classList.toggle('open')" aria-label="Menu">☰</button>
 <h1>🎓 STUDENT INFORMATION MANAGEMENT SYSTEM</h1>
 <a class="user-chip" href="{{ url_for('profile.index') }}"><span class="avatar">{{ session.name[:1]|upper }}</span>
  <span class="nm">{{ session.name }} ({{ session.role|capitalize }})</span></a>
 <a class="top-logout" href="{{ url_for('auth.logout') }}">🚪 Logout</a>
</header>
<nav class="sidebar" id="sb">
 <a href="{{ url_for('dashboard') }}" style="--c:#2563eb" class="{{ 'active' if active == 'dashboard' }}">🏠 Dashboard</a>
 {% for icon, name, desc, endpoint, colour in modules %}
 <a href="{{ url_for(endpoint) }}" style="--c:{{ colour }}" class="{{ 'active' if endpoint.split('.')[0] == active }}">{{ '👨‍🎓' if endpoint == 'students.index' else icon }} {{ name }}</a>
 {% endfor %}
</nav>
<main class="main">
 {% with msgs = get_flashed_messages(with_categories=true) %}{% for cat, m in msgs %}<div class="alert {{ cat }}">{{ m }}</div>{% endfor %}{% endwith %}
 {{ body }}
</main></body></html>"""

LOGIN_T = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Login | STUDENT INFORMATION MANAGEMENT SYSTEM</title>
<style>""" + CSS + """
body{min-height:100vh;display:grid;place-items:center;background:linear-gradient(135deg,#4f46e5,#0ea5e9 55%,#14b8a6);padding:16px}
.login{background:#fff;border-radius:18px;padding:32px;width:100%;max-width:410px;box-shadow:0 20px 50px rgba(0,0,0,.3)}
.login h1{font-size:1.2rem;text-align:center;margin:0 0 4px;color:#3730a3}.login .logo{font-size:3rem;text-align:center}
.login p{text-align:center;margin:0 0 20px}.login .field{margin-bottom:14px}.login .btn{width:100%;justify-content:center;padding:12px}
.demo{background:#f1f5f9;border-radius:10px;padding:10px 14px;margin-top:16px;font-size:.82rem}
</style></head><body>
<div class="login" style="--c:#4f46e5">
 <div class="logo">🎓</div><h1>STUDENT INFORMATION MANAGEMENT SYSTEM</h1><p class="muted">Sign in to continue</p>
 {% with msgs = get_flashed_messages(with_categories=true) %}{% for cat, m in msgs %}<div class="alert {{ cat }}">{{ m }}</div>{% endfor %}{% endwith %}
 <form method="post">
  <div class="field"><label for="username">👤 Username</label><input id="username" name="username" value="{{ username }}" required autofocus></div>
  <div class="field"><label for="password">🔒 Password</label><input id="password" name="password" type="password" required></div>
  <button class="btn btn-main" type="submit">Login</button>
 </form>
 <div class="demo"><b>Demo accounts</b><br>Admin: <code>admin</code> / <code>admin123</code><br>Staff (view only): <code>staff</code> / <code>staff123</code></div>
</div></body></html>"""
