"""auth.py - login, logout, sessions and access-control decorators."""
from functools import wraps
from flask import Blueprint, request, session, redirect, url_for, flash
from werkzeug.security import check_password_hash
from database import query

bp = Blueprint("auth", __name__)


def is_admin():
    return session.get("role") == "admin"


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login", next=request.path))
        if not is_admin():
            flash("Only administrators can do that.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapper


@bp.route("/login", methods=["GET", "POST"])
def login():
    import ui  # imported here to avoid a circular import
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    username = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = query("SELECT * FROM users WHERE username = ?", (username,), one=True)
        if user and check_password_hash(user["password"], password):
            session.clear()
            session.update(user_id=user["id"], username=user["username"], name=user["name"], role=user["role"])
            nxt = request.args.get("next", "")
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return ui.render_login(username)


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
