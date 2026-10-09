"""database.py - SQLite connection helpers, table creation and demo data."""
import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "students.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql, args=(), one=False):
    """Run a SELECT. Returns a list of rows (or a single row if one=True)."""
    conn = get_db()
    try:
        rows = conn.execute(sql, args).fetchall()
    finally:
        conn.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, args=()):
    """Run INSERT / UPDATE / DELETE. Returns the last inserted row id."""
    conn = get_db()
    try:
        cur = conn.execute(sql, args)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def calc_grade(percentage):
    for limit, grade in ((90, "A+"), (80, "A"), (70, "B+"), (60, "B"), (50, "C"), (40, "D")):
        if percentage >= limit:
            return grade
    return "F"


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin','user'))
);
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL UNIQUE,
    duration INTEGER NOT NULL DEFAULT 3,
    description TEXT
);
CREATE TABLE IF NOT EXISTS semesters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    number INTEGER NOT NULL CHECK (number BETWEEN 1 AND 8),
    academic_year TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    UNIQUE (course_id, number, academic_year)
);
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    dob TEXT NOT NULL,
    gender TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    address TEXT NOT NULL,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    semester_no INTEGER NOT NULL CHECK (semester_no BETWEEN 1 AND 8),
    admission_date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    semester_no INTEGER NOT NULL CHECK (semester_no BETWEEN 1 AND 8),
    credits INTEGER NOT NULL CHECK (credits BETWEEN 1 AND 10)
);
CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    semester_no INTEGER NOT NULL,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    enroll_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Active',
    UNIQUE (student_id, subject_id)
);
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    total_classes INTEGER NOT NULL CHECK (total_classes > 0),
    present INTEGER NOT NULL CHECK (present >= 0),
    UNIQUE (student_id, subject_id)
);
CREATE TABLE IF NOT EXISTS marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    internal REAL NOT NULL,
    external REAL NOT NULL,
    total REAL NOT NULL,
    percentage REAL NOT NULL,
    grade TEXT NOT NULL,
    result TEXT NOT NULL,
    UNIQUE (student_id, subject_id)
);
CREATE TABLE IF NOT EXISTS fees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    total_fees REAL NOT NULL,
    paid REAL NOT NULL DEFAULT 0,
    pending REAL NOT NULL,
    payment_date TEXT,
    status TEXT NOT NULL
);
"""


def init_db():
    """Create the database/tables if missing and add demo data on first run."""
    conn = get_db()
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        _seed(conn)
    conn.commit()
    conn.close()


def _seed(conn):
    conn.executemany("INSERT INTO users (name, username, password, email, role) VALUES (?,?,?,?,?)", [
        ("System Administrator", "admin", generate_password_hash("admin123"), "admin@college.edu", "admin"),
        ("Office Staff", "staff", generate_password_hash("staff123"), "staff@college.edu", "user"),
    ])
    conn.executemany("INSERT INTO courses (code, name, duration, description) VALUES (?,?,?,?)", [
        ("BCA", "BCA", 3, "Bachelor of Computer Applications"),
        ("BSCCS", "BSc Computer Science", 3, "Bachelor of Science in Computer Science"),
        ("BBA", "BBA", 3, "Bachelor of Business Administration"),
        ("BCOM", "B.Com", 3, "Bachelor of Commerce"),
        ("BECE", "BE Computer Engineering", 4, "Bachelor of Engineering in Computer Engineering"),
    ])
    conn.executemany("INSERT INTO semesters (course_id, number, academic_year, start_date, end_date) VALUES (?,?,?,?,?)", [
        (1, 1, "2025-2026", "2025-07-01", "2025-12-15"), (1, 2, "2025-2026", "2026-01-05", "2026-05-30"),
        (2, 1, "2025-2026", "2025-07-01", "2025-12-15"), (3, 1, "2025-2026", "2025-07-01", "2025-12-15"),
        (4, 1, "2025-2026", "2025-07-01", "2025-12-15"), (5, 1, "2025-2026", "2025-08-01", "2025-12-20"),
    ])
    # id order: 1 C, 2 Maths, 3 Digital, 4 DS, 5 DBMS, 6 Python, 7 Mgmt, 8 Economics, 9 Accounting, 10 Physics
    conn.executemany("INSERT INTO subjects (subject_code, name, course_id, semester_no, credits) VALUES (?,?,?,?,?)", [
        ("BCA101", "Programming in C", 1, 1, 4), ("BCA102", "Mathematics", 1, 1, 3),
        ("BCA103", "Digital Electronics", 1, 1, 3), ("BCA201", "Data Structures", 1, 2, 4),
        ("BCA202", "Database Management Systems", 1, 2, 4), ("CS101", "Python Programming", 2, 1, 4),
        ("BBA101", "Principles of Management", 3, 1, 4), ("BBA102", "Business Economics", 3, 1, 3),
        ("COM101", "Financial Accounting", 4, 1, 4), ("ENG101", "Engineering Physics", 5, 1, 3),
    ])
    students = [
        ("STU2025001", "Aarav Sharma", "2006-03-14", "Male", "9876543210", "aarav@example.com", "12 MG Road, Pune", 1, 1, "2025-07-01"),
        ("STU2025002", "Diya Patel", "2006-08-22", "Female", "9876543211", "diya@example.com", "45 Park Street, Mumbai", 1, 1, "2025-07-01"),
        ("STU2025003", "Rohan Mehta", "2005-11-02", "Male", "9876543212", "rohan@example.com", "7 Lake View, Nashik", 1, 2, "2024-07-01"),
        ("STU2025004", "Sneha Iyer", "2006-01-30", "Female", "9876543213", "sneha@example.com", "88 Anna Nagar, Chennai", 2, 1, "2025-07-02"),
        ("STU2025005", "Kabir Singh", "2006-05-19", "Male", "9876543214", "kabir@example.com", "23 Civil Lines, Delhi", 3, 1, "2025-07-03"),
        ("STU2025006", "Meera Nair", "2006-09-09", "Female", "9876543215", "meera@example.com", "5 Beach Road, Kochi", 4, 1, "2025-07-03"),
        ("STU2025007", "Arjun Reddy", "2006-12-12", "Male", "9876543216", "arjun@example.com", "19 Jubilee Hills, Hyderabad", 5, 1, "2025-08-01"),
    ]
    conn.executemany("""INSERT INTO students (student_id, full_name, dob, gender, phone, email, address,
                        course_id, semester_no, admission_date) VALUES (?,?,?,?,?,?,?,?,?,?)""", students)
    # (student pk, course, sem, subject pk)
    enroll = [(1, 1, 1, 1), (1, 1, 1, 2), (1, 1, 1, 3), (2, 1, 1, 1), (2, 1, 1, 2), (3, 1, 2, 4), (3, 1, 2, 5),
              (4, 2, 1, 6), (5, 3, 1, 7), (5, 3, 1, 8), (6, 4, 1, 9), (7, 5, 1, 10)]
    conn.executemany("""INSERT INTO enrollments (student_id, course_id, semester_no, subject_id, enroll_date, status)
                        VALUES (?,?,?,?,'2025-07-05','Active')""", enroll)
    conn.executemany("INSERT INTO attendance (student_id, subject_id, total_classes, present) VALUES (?,?,?,?)", [
        (1, 1, 40, 38), (1, 2, 40, 31), (1, 3, 40, 22), (2, 1, 40, 35), (2, 2, 40, 28), (3, 4, 36, 30),
        (3, 5, 36, 20), (4, 6, 38, 37), (5, 7, 35, 27), (6, 9, 35, 33), (7, 10, 30, 17),
    ])
    for sid, sub, internal, external in [(1, 1, 35, 52), (1, 2, 30, 41), (1, 3, 20, 18), (2, 1, 32, 45), (2, 2, 28, 39),
                                         (3, 4, 36, 55), (4, 6, 38, 57), (5, 7, 30, 44), (6, 9, 33, 50), (7, 10, 15, 20)]:
        total = internal + external
        conn.execute("INSERT INTO marks (student_id, subject_id, internal, external, total, percentage, grade, result) "
                     "VALUES (?,?,?,?,?,?,?,?)",
                     (sid, sub, internal, external, total, total, calc_grade(total), "Pass" if total >= 40 else "Fail"))
    for sid, course, total, paid, date in [(1, 1, 45000, 45000, "2025-07-10"), (2, 1, 45000, 20000, "2025-07-12"),
                                           (3, 1, 45000, 0, None), (4, 2, 48000, 48000, "2025-07-11"),
                                           (5, 3, 52000, 25000, "2025-07-15"), (6, 4, 30000, 0, None),
                                           (7, 5, 90000, 60000, "2025-08-05")]:
        pending = total - paid
        status = "Paid" if pending <= 0 else ("Partially Paid" if paid > 0 else "Pending")
        conn.execute("INSERT INTO fees (student_id, course_id, total_fees, paid, pending, payment_date, status) "
                     "VALUES (?,?,?,?,?,?,?)", (sid, course, total, paid, pending, date, status))
