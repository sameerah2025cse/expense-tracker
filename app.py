"""Expense Tracker
A small web app built with Flask and SQLite.
Add expenses, see category-wise totals, filter by month and export to CSV.
"""

import csv
import io
import sqlite3
from datetime import date

from flask import Flask, Response, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = "change-this-secret-key"  # needed for flash messages

DB_NAME = "expenses.db"
CATEGORIES = ["Food", "Travel", "Shopping", "Bills", "Education", "Other"]


def get_db():
    """Open a connection to the database. Rows can be read by column name."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the expenses table if it does not exist yet."""
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL CHECK (amount > 0),
            category TEXT NOT NULL,
            date TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    month = request.args.get("month", "")  # example: 2026-11
    conn = get_db()

    expenses = conn.execute(
        """
        SELECT * FROM expenses
        WHERE (? = '' OR substr(date, 1, 7) = ?)
        ORDER BY date DESC, id DESC
        """,
        (month, month),
    ).fetchall()

    summary = conn.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE (? = '' OR substr(date, 1, 7) = ?)
        GROUP BY category
        ORDER BY total DESC
        """,
        (month, month),
    ).fetchall()

    months = conn.execute(
        "SELECT DISTINCT substr(date, 1, 7) AS m FROM expenses ORDER BY m DESC"
    ).fetchall()
    conn.close()

    grand_total = sum(row["total"] for row in summary)
    return render_template(
        "index.html",
        expenses=expenses,
        summary=summary,
        months=months,
        selected_month=month,
        grand_total=grand_total,
        categories=CATEGORIES,
        today=date.today().isoformat(),
    )


@app.route("/add", methods=["POST"])
def add_expense():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "")
    expense_date = request.form.get("date", "")
    try:
        amount = float(request.form.get("amount", ""))
    except ValueError:
        amount = 0

    if not title or amount <= 0 or category not in CATEGORIES or not expense_date:
        flash("Please fill all fields correctly. Amount must be more than 0.")
        return redirect(url_for("index"))

    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (title, amount, category, date) VALUES (?, ?, ?, ?)",
        (title, amount, category, expense_date),
    )
    conn.commit()
    conn.close()
    flash("Expense added.")
    return redirect(url_for("index"))


@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()
    flash("Expense deleted.")
    return redirect(url_for("index"))


@app.route("/export")
def export_csv():
    conn = get_db()
    rows = conn.execute(
        "SELECT date, title, category, amount FROM expenses ORDER BY date DESC"
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Title", "Category", "Amount"])
    for row in rows:
        writer.writerow([row["date"], row["title"], row["category"], row["amount"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses.csv"},
    )


init_db()

if __name__ == "__main__":
    app.run(debug=True)
