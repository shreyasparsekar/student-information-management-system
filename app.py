"""app.py - main file. Run with:  python app.py   (opens http://127.0.0.1:5000 in Chrome)"""
import os
import threading
import webbrowser
from flask import Flask, redirect, session, url_for
from auth import bp as auth_bp, login_required
from database import init_db, query
from ui import render, MODULES, money
import students, courses, subjects, semesters, enrollment, attendance, marks, fees, reports, profile, admin

HOST, PORT = "127.0.0.1", 5000

app = Flask(__name__)
app.secret_key = "sims-college-project-secret-key"  # needed for sessions; change for real deployments
for module in (students, courses, subjects, semesters, enrollment, attendance, marks, fees, reports, profile, admin):
    app.register_blueprint(module.bp)
app.register_blueprint(auth_bp)


@app.route("/")
def home():
    return redirect(url_for("dashboard" if "user_id" in session else "auth.login"))


@app.route("/dashboard")
@login_required
def dashboard():
    one = lambda sql: query(sql, one=True)[0]
    avg_att = one("SELECT IFNULL(SUM(present) * 100.0 / SUM(total_classes), 0) FROM attendance")
    stats = [("🧑‍🎓", "Total Students", one("SELECT COUNT(*) FROM students"), "#2563eb"),
             ("📚", "Total Courses", one("SELECT COUNT(*) FROM courses"), "#7c3aed"),
             ("📖", "Total Subjects", one("SELECT COUNT(*) FROM subjects"), "#0d9488"),
             ("📝", "Total Enrollments", one("SELECT COUNT(*) FROM enrollments"), "#db2777"),
             ("📅", "Average Attendance", f"{avg_att:.1f}%", "#16a34a"),
             ("💰", "Pending Fees", money(one("SELECT IFNULL(SUM(pending), 0) FROM fees")), "#d97706")]
    return render(DASH_T, "Dashboard", stats=stats, modules=MODULES)


DASH_T = """
<div class="page-head" style="--c:#2563eb"><h2>🏠 Welcome, {{ session.name }}!</h2></div>
<div class="stats">{% for icon, label, value, colour in stats %}
 <div class="stat" style="--c:{{ colour }}"><span class="i">{{ icon }}</span><div class="n">{{ value }}</div><div class="l">{{ label }}</div></div>{% endfor %}</div>
<h3 class="sec">Modules</h3>
<div class="cards">{% for icon, name, desc, endpoint, colour in modules %}
 <a class="card" href="{{ url_for(endpoint) }}" style="--c:{{ colour }}"><div class="i">{{ icon }}</div><h3>{{ name }}</h3><p>{{ desc }}</p></a>{% endfor %}</div>
"""


@app.errorhandler(404)
def not_found(e):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render("<div class='panel'><h2>404 - Page not found</h2><p>The page you asked for does not exist.</p>"
                  "<a class='btn btn-blue' href='/dashboard'>🏠 Back to Dashboard</a></div>", "Not Found"), 404


@app.errorhandler(500)
def server_error(e):
    return render("<div class='panel'><h2>Something went wrong</h2><p>Please go back and try again.</p>"
                  "<a class='btn btn-blue' href='/dashboard'>🏠 Back to Dashboard</a></div>", "Error"), 500


def open_chrome():
    url = f"http://{HOST}:{PORT}"
    paths = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             "/usr/bin/google-chrome", "/usr/bin/chromium-browser"]
    for p in paths:
        if os.path.exists(p):
            webbrowser.register("chrome-app", None, webbrowser.BackgroundBrowser(p))
            webbrowser.get("chrome-app").open(url)
            return
    webbrowser.open(url)


if __name__ == "__main__":
    init_db()
    threading.Timer(1.2, open_chrome).start()
    print(f"\nStudent Information Management System running at http://{HOST}:{PORT}")
    print("Login: admin / admin123   (press CTRL+C to stop)\n")
    app.run(host=HOST, port=PORT, debug=False)
