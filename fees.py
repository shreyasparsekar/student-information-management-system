"""fees.py - fees management; pending amount and payment status are automatic."""
from datetime import date
from flask import Blueprint
from database import query
from ui import make_crud, F, opt_students, money, status_badge

bp = Blueprint("fees", __name__, url_prefix="/fees")


def validate(v, row_id):
    total, paid = float(v["total_fees"]), float(v["paid"])
    if paid > total:
        return "Paid amount cannot be more than the total fees."
    st = query("SELECT course_id FROM students WHERE id = ?", (v["student_id"],), one=True)
    if not st:
        return "Selected student does not exist."
    pending = total - paid
    if paid > 0 and not v["payment_date"]:
        v["payment_date"] = date.today().isoformat()
    v.update(course_id=st["course_id"], total_fees=total, paid=paid, pending=pending,
             status="Paid" if pending <= 0 else "Partially Paid" if paid > 0 else "Pending")


make_crud(
    bp, table="fees", title="Fees", singular="Fee Record", icon="💰", colour="#d97706",
    fields=[F("student_id", "Student", "select", options=opt_students, hint="The course is taken from the student's record."),
            F("total_fees", "Total Fees (₹)", "number", min=1), F("paid", "Paid Amount (₹)", "number", min=0),
            F("payment_date", "Payment Date", "date", required=False)],
    list_sql="""SELECT f.id, st.student_id AS sid, st.full_name AS name, c.name AS course, f.total_fees, f.paid,
                f.pending, f.payment_date, f.status FROM fees f
                JOIN students st ON st.id = f.student_id JOIN courses c ON c.id = f.course_id""",
    columns=[("sid", "Student ID"), ("name", "Student"), ("course", "Course"), ("total_fees", "Total", money),
             ("paid", "Paid", money), ("pending", "Pending", money), ("payment_date", "Payment Date"),
             ("status", "Status", status_badge)],
    search_cols=["sid", "name", "course", "status"],
    validate=validate,
)
