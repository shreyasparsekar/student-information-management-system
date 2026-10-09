"""profile.py - view and update the logged-in user's own account."""
import sqlite3
from flask import Blueprint, request, session, flash, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from auth import login_required
from database import query, execute
from ui import render

bp = Blueprint("profile", __name__, url_prefix="/profile")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    user = query("SELECT * FROM users WHERE id = ?", (session["user_id"],), one=True)
    if not user:
        session.clear()
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "info":
                name, email = request.form.get("name", "").strip(), request.form.get("email", "").strip()
                if not name or "@" not in email:
                    flash("Enter your name and a valid email address.", "error")
                else:
                    execute("UPDATE users SET name = ?, email = ? WHERE id = ?", (name, email, user["id"]))
                    session["name"] = name
                    flash("Profile updated successfully.", "success")
                    return redirect(url_for("profile.index"))
            elif action == "password":
                old, new, again = (request.form.get(k, "") for k in ("old", "new", "again"))
                if not check_password_hash(user["password"], old):
                    flash("Current password is incorrect.", "error")
                elif len(new) < 6:
                    flash("New password must be at least 6 characters.", "error")
                elif new != again:
                    flash("New passwords do not match.", "error")
                else:
                    execute("UPDATE users SET password = ? WHERE id = ?", (generate_password_hash(new), user["id"]))
                    flash("Password changed successfully.", "success")
                    return redirect(url_for("profile.index"))
        except sqlite3.Error:
            flash("Database error. Please try again.", "error")
    return render(PROFILE_T, "Profile", u=user)


PROFILE_T = """
<div style="--c:#475569">
<div class="page-head"><h2>👤 My Profile</h2></div>
<div class="panel"><div class="profile-top"><div class="big-avatar">{{ u.name[:1]|upper }}</div>
 <div><h3 style="margin:0">{{ u.name }}</h3><span class="badge {{ 'red' if u.role == 'admin' else 'blue' }}">{{ u.role|capitalize }}</span></div></div>
 <div class="kv"><div><b>Name</b>{{ u.name }}</div><div><b>Username</b>{{ u.username }}</div>
  <div><b>Role</b>{{ u.role|capitalize }}</div><div><b>Email</b>{{ u.email }}</div></div></div>
<form method="post" class="panel form-grid"><input type="hidden" name="action" value="info">
 <h3 class="full" style="margin:0">✏️ Update Profile</h3>
 <div class="field"><label>Full Name</label><input name="name" value="{{ u.name }}" required></div>
 <div class="field"><label>Email</label><input name="email" type="email" value="{{ u.email }}" required></div>
 <div class="full"><button class="btn btn-main" type="submit">💾 Save Profile</button></div></form>
<form method="post" class="panel form-grid"><input type="hidden" name="action" value="password">
 <h3 class="full" style="margin:0">🔒 Change Password</h3>
 <div class="field"><label>Current Password</label><input name="old" type="password" required></div>
 <div class="field"><label>New Password</label><input name="new" type="password" required></div>
 <div class="field"><label>Confirm New Password</label><input name="again" type="password" required></div>
 <div class="full"><button class="btn btn-main" type="submit">🔑 Change Password</button></div></form>
</div>
"""
