"""admin.py - admin panel: manage users, roles and view system information."""
import platform
import os
import sys
from datetime import datetime
import flask
from flask import Blueprint, session
from werkzeug.security import generate_password_hash
from auth import admin_required
from database import query, DB_PATH
from ui import make_crud, F, render, status_badge

bp = Blueprint("admin", __name__, url_prefix="/admin")


def validate(v, row_id):
    if len(v["username"]) < 3 or " " in v["username"]:
        return "Username must be at least 3 characters with no spaces."
    pw = v.get("password")
    if pw:
        if len(pw) < 6:
            return "Password must be at least 6 characters."
        v["password"] = generate_password_hash(pw)
    else:
        v.pop("password", None)
    if row_id and int(row_id) == session["user_id"] and v["role"] != "admin":
        return "You cannot remove your own admin role."


def can_delete(row_id):
    if row_id == session["user_id"]:
        return "You cannot delete your own account."
    target = query("SELECT role FROM users WHERE id = ?", (row_id,), one=True)
    if target and target["role"] == "admin" and query("SELECT COUNT(*) c FROM users WHERE role='admin'", one=True)["c"] <= 1:
        return "The last administrator cannot be deleted."


make_crud(
    bp, table="users", title="Admin Panel - Users", singular="User", icon="⚙️", colour="#dc2626", admin_only=True,
    fields=[F("name", "Full Name"), F("username", "Username"),
            F("password", "Password", "password", hint="Minimum 6 characters."), F("email", "Email", "email"),
            F("role", "Role", "select", options=[("admin", "Admin"), ("user", "User (view only)")])],
    list_sql="SELECT id, name, username, email, role FROM users",
    columns=[("name", "Name"), ("username", "Username"), ("email", "Email"), ("role", "Role", status_badge)],
    search_cols=["name", "username", "email", "role"],
    validate=validate, can_delete=can_delete,
    extra_buttons=[("🖥️ System Information", "admin.system", "btn-purple")],
)


@bp.route("/system")
@admin_required
def system():
    tables = ["users", "students", "courses", "subjects", "semesters", "enrollments", "attendance", "marks", "fees"]
    counts = [(t, query(f"SELECT COUNT(*) c FROM {t}", one=True)["c"]) for t in tables]
    info = [("Python version", sys.version.split()[0]), ("Flask version", flask.__version__ if hasattr(flask, "__version__") else "3.x"),
            ("Operating system", platform.platform()), ("Database file", DB_PATH),
            ("Database size", f"{os.path.getsize(DB_PATH) / 1024:.1f} KB"),
            ("Server time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))]
    return render(SYSTEM_T, "System Information", counts=counts, info=info)


SYSTEM_T = """
<div style="--c:#dc2626">
<div class="page-head"><h2>🖥️ System Information</h2><a class="btn btn-grey" href="{{ url_for('admin.index') }}">⬅ Back to Users</a></div>
<div class="panel"><div class="kv">{% for k, v in info %}<div><b>{{ k }}</b>{{ v }}</div>{% endfor %}</div></div>
<h3 class="sec">Database records</h3>
<div class="table-wrap"><table><thead><tr><th>Table</th><th>Records</th></tr></thead><tbody>
{% for t, c in counts %}<tr><td>{{ t }}</td><td><span class="badge blue">{{ c }}</span></td></tr>{% endfor %}</tbody></table></div>
</div>
"""
