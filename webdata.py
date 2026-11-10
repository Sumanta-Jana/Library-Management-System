"""Data helpers for the web site and the REST API.

Everything here returns plain dictionaries / lists so that the same
functions can feed both HTML pages and JSON responses.
"""

import math
import sqlite3
from datetime import date, datetime, timedelta

import books as books_module
import loans as loans_module
import members as members_module
from database import close_connection, get_connection

LOAN_DAYS = loans_module.LOAN_DAYS
FINE_PER_DAY = loans_module.FINE_PER_DAY
MAX_ACTIVE_LOANS = 5
RENEW_DAYS = 7
MAX_RENEWALS = 2


# ----------------------------------------------------------
# Low-level helpers
# ----------------------------------------------------------

def query(sql, params=()):
    """Run a SELECT and return a list of dictionaries."""
    connection = get_connection(dict_rows=True)
    if connection is None:
        raise sqlite3.OperationalError("Could not connect to the database.")
    try:
        return [dict(row) for row in connection.execute(sql, params)]
    finally:
        close_connection(connection)


def query_one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None


def scalar(sql, params=()):
    connection = get_connection()
    if connection is None:
        raise sqlite3.OperationalError("Could not connect to the database.")
    try:
        row = connection.execute(sql, params).fetchone()
        return (row[0] or 0) if row else 0
    finally:
        close_connection(connection)


def execute(sql, params=()):
    connection = get_connection()
    if connection is None:
        raise sqlite3.OperationalError("Could not connect to the database.")
    try:
        cursor = connection.execute(sql, params)
        connection.commit()
        return cursor.rowcount
    finally:
        close_connection(connection)


def today_text():
    return date.today().strftime("%Y-%m-%d")


def paginate(total, page, per_page):
    pages = max(1, math.ceil(total / per_page))
    page = min(max(1, page), pages)
    return page, pages


def like(text):
    """Escape LIKE wildcards so a search for 50% really searches for 50%."""
    safe = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{safe}%"


# ----------------------------------------------------------
# Books
# ----------------------------------------------------------

BOOK_SORTS = {
    "title": "b.title COLLATE NOCASE ASC",
    "author": "b.author COLLATE NOCASE ASC",
    "newest": "b.book_id DESC",
    "year": "b.publication_year DESC",
    "popular": "loan_count DESC, b.title COLLATE NOCASE ASC",
}

BOOK_COLUMNS = """
    b.book_id, b.title, b.author, b.isbn, b.category, b.publisher,
    b.publication_year, b.total_copies, b.available_copies,
    b.cover_image, b.description,
    (SELECT COUNT(*) FROM loans l WHERE l.book_id = b.book_id) AS loan_count
"""


def list_books(search="", category="", availability="", sort="title",
               page=1, per_page=12):
    where, params = [], []

    if search:
        pattern = like(search)
        where.append(
            "(b.title LIKE ? ESCAPE '\\' OR b.author LIKE ? ESCAPE '\\' "
            "OR b.isbn LIKE ? ESCAPE '\\' OR b.category LIKE ? ESCAPE '\\')"
        )
        params += [pattern] * 4

    if category:
        where.append("b.category = ?")
        params.append(category)

    if availability == "available":
        where.append("b.available_copies > 0")
    elif availability == "out":
        where.append("b.available_copies = 0")

    clause = (" WHERE " + " AND ".join(where)) if where else ""
    order = BOOK_SORTS.get(sort, BOOK_SORTS["title"])

    total = scalar(f"SELECT COUNT(*) FROM books b{clause}", params)
    page, pages = paginate(total, page, per_page)

    items = query(
        f"SELECT {BOOK_COLUMNS} FROM books b{clause} "
        f"ORDER BY {order} LIMIT ? OFFSET ?",
        params + [per_page, (page - 1) * per_page],
    )

    return {"items": items, "total": total, "page": page,
            "pages": pages, "per_page": per_page}


def list_categories():
    rows = query(
        "SELECT category, COUNT(*) AS n FROM books "
        "WHERE category IS NOT NULL AND TRIM(category) != '' "
        "GROUP BY category ORDER BY category COLLATE NOCASE"
    )
    return rows


def get_book(book_id):
    return query_one(
        f"SELECT {BOOK_COLUMNS} FROM books b WHERE b.book_id = ?",
        (book_id,),
    )


def book_loan_history(book_id, limit=8):
    return query(
        """
        SELECT l.loan_id, m.name AS member_name, l.issue_date, l.due_date,
               l.return_date, l.status
        FROM loans l JOIN members m ON m.member_id = l.member_id
        WHERE l.book_id = ? ORDER BY l.loan_id DESC LIMIT ?
        """,
        (book_id, limit),
    )


def save_book_extras(book_id, description=None, cover_image=None,
                     clear_cover=False):
    """Description and cover image are stored apart from the core fields."""
    if description is not None:
        execute("UPDATE books SET description = ? WHERE book_id = ?",
                ((description.strip() or None), book_id))
    if clear_cover:
        execute("UPDATE books SET cover_image = NULL WHERE book_id = ?",
                (book_id,))
    elif cover_image:
        execute("UPDATE books SET cover_image = ? WHERE book_id = ?",
                (cover_image, book_id))


def create_book(title, author, isbn, category, publisher, year, copies,
                description="", cover_image=None):
    ok, message = books_module.add_book(
        title, author, isbn, category, publisher, year, copies, copies
    )
    if not ok:
        return False, message, None

    row = query_one("SELECT book_id FROM books WHERE isbn = ?",
                    (books_module.clean_isbn(isbn.strip()),))
    book_id = row["book_id"] if row else None

    if book_id:
        save_book_extras(book_id, description, cover_image)

    return True, "Book added to the library.", book_id


def edit_book(book_id, title, author, isbn, category, publisher, year,
              copies, description="", cover_image=None, clear_cover=False):
    ok, message = books_module.update_book(
        book_id, title, author, isbn, category, publisher, year, copies, ""
    )
    if not ok:
        return False, message

    save_book_extras(book_id, description, cover_image, clear_cover)
    return True, "Book updated successfully."


# ----------------------------------------------------------
# Members
# ----------------------------------------------------------

def list_members(search="", page=1, per_page=15):
    where, params = "", []

    if search:
        pattern = like(search)
        where = (
            " WHERE (m.name LIKE ? ESCAPE '\\' OR m.email LIKE ? ESCAPE '\\' "
            "OR m.phone LIKE ? ESCAPE '\\' OR CAST(m.member_id AS TEXT) = ?)"
        )
        params = [pattern, pattern, pattern, search.strip()]

    total = scalar(f"SELECT COUNT(*) FROM members m{where}", params)
    page, pages = paginate(total, page, per_page)

    items = query(
        f"""
        SELECT m.member_id, m.name, m.email, m.phone, m.address, m.join_date,
               (SELECT COUNT(*) FROM loans l
                 WHERE l.member_id = m.member_id
                   AND l.return_date IS NULL) AS active_loans,
               (SELECT u.username FROM users u
                 WHERE u.member_id = m.member_id) AS username
        FROM members m{where}
        ORDER BY m.member_id DESC LIMIT ? OFFSET ?
        """,
        params + [per_page, (page - 1) * per_page],
    )

    return {"items": items, "total": total, "page": page,
            "pages": pages, "per_page": per_page}


def get_member(member_id):
    return query_one(
        """
        SELECT m.member_id, m.name, m.email, m.phone, m.address, m.join_date,
               (SELECT u.username FROM users u
                 WHERE u.member_id = m.member_id) AS username
        FROM members m WHERE m.member_id = ?
        """,
        (member_id,),
    )


def member_summary(member_id):
    today = today_text()
    return {
        "borrowed": scalar(
            "SELECT COUNT(*) FROM loans WHERE member_id = ? "
            "AND return_date IS NULL", (member_id,)),
        "overdue": scalar(
            "SELECT COUNT(*) FROM loans WHERE member_id = ? "
            "AND return_date IS NULL AND due_date < ?", (member_id, today)),
        "total_read": scalar(
            "SELECT COUNT(*) FROM loans WHERE member_id = ?", (member_id,)),
        "pending_fine": scalar(
            "SELECT COALESCE(SUM(MAX(CAST(julianday(?) - julianday(due_date) "
            "AS INTEGER), 0)), 0) FROM loans WHERE member_id = ? "
            "AND return_date IS NULL", (today, member_id)) * FINE_PER_DAY,
        "paid_fine": scalar(
            "SELECT COALESCE(SUM(fine_amount), 0) FROM loans "
            "WHERE member_id = ? AND status = 'Returned'", (member_id,)),
    }


# ----------------------------------------------------------
# Loans
# ----------------------------------------------------------

LOAN_SELECT = """
    SELECT l.loan_id, l.book_id, b.title, b.author, b.cover_image,
           l.member_id, m.name AS member_name, m.phone AS member_phone,
           l.issue_date, l.due_date, l.return_date, l.fine_amount,
           l.status, l.renewals,
           CASE WHEN l.return_date IS NULL
                THEN MAX(CAST(julianday(:today) - julianday(l.due_date)
                              AS INTEGER), 0)
                ELSE MAX(CAST(julianday(l.return_date)
                              - julianday(l.due_date) AS INTEGER), 0)
           END AS overdue_days
    FROM loans l
    JOIN books b ON b.book_id = l.book_id
    JOIN members m ON m.member_id = l.member_id
"""


def _decorate_loan(row):
    active = row["return_date"] is None
    row["is_active"] = active
    row["is_overdue"] = active and row["overdue_days"] > 0
    row["current_fine"] = (
        row["overdue_days"] * FINE_PER_DAY if active else row["fine_amount"]
    )
    row["can_renew"] = (
        active and not row["is_overdue"] and row["renewals"] < MAX_RENEWALS
    )
    if active:
        try:
            due = datetime.strptime(row["due_date"], "%Y-%m-%d").date()
            row["days_left"] = (due - date.today()).days
        except ValueError:
            row["days_left"] = None
    else:
        row["days_left"] = None
    return row


def list_loans(status="active", search="", member_id=None,
               page=1, per_page=15):
    where, params = [], {"today": today_text()}

    if status == "active":
        where.append("l.return_date IS NULL")
    elif status == "overdue":
        where.append("l.return_date IS NULL AND l.due_date < :today")
    elif status == "returned":
        where.append("l.return_date IS NOT NULL")

    if member_id is not None:
        where.append("l.member_id = :member_id")
        params["member_id"] = member_id

    if search:
        where.append(
            "(b.title LIKE :s ESCAPE '\\' OR m.name LIKE :s ESCAPE '\\' "
            "OR CAST(l.loan_id AS TEXT) = :raw)"
        )
        params["s"] = like(search)
        params["raw"] = search.strip()

    clause = (" WHERE " + " AND ".join(where)) if where else ""

    connection = get_connection()
    try:
        total = connection.execute(
            "SELECT COUNT(*) FROM loans l JOIN books b ON b.book_id = l.book_id "
            "JOIN members m ON m.member_id = l.member_id" + clause,
            params,
        ).fetchone()[0]
    finally:
        close_connection(connection)

    page, pages = paginate(total, page, per_page)
    params.update(limit=per_page, offset=(page - 1) * per_page)

    rows = query(
        LOAN_SELECT + clause + " ORDER BY l.loan_id DESC LIMIT :limit OFFSET :offset",
        params,
    )

    return {"items": [_decorate_loan(r) for r in rows], "total": total,
            "page": page, "pages": pages, "per_page": per_page}


def get_loan(loan_id):
    rows = query(LOAN_SELECT + " WHERE l.loan_id = :id",
                 {"today": today_text(), "id": loan_id})
    return _decorate_loan(rows[0]) if rows else None


def issue_checked(book_id, member_id):
    """Issue a book after the library rules have been checked."""

    if get_book(book_id) is None:
        return False, "No book found with this Book ID."

    if get_member(member_id) is None:
        return False, "No member found with this Member ID."

    active = scalar(
        "SELECT COUNT(*) FROM loans WHERE member_id = ? AND return_date IS NULL",
        (member_id,))

    if active >= MAX_ACTIVE_LOANS:
        return False, (f"This member already has {MAX_ACTIVE_LOANS} books "
                       "issued, which is the limit.")

    already = scalar(
        "SELECT COUNT(*) FROM loans WHERE member_id = ? AND book_id = ? "
        "AND return_date IS NULL", (member_id, book_id))

    if already:
        return False, "This member already has a copy of this book."

    return loans_module.issue_book(book_id, member_id)


def renew_loan(loan_id, member_id=None):
    """Extend a loan by 7 days (maximum 2 renewals, never when overdue)."""
    loan = get_loan(loan_id)

    if loan is None:
        return False, "Loan not found."

    if member_id is not None and loan["member_id"] != member_id:
        return False, "Loan not found."

    if not loan["is_active"]:
        return False, "This book has already been returned."

    if loan["is_overdue"]:
        return False, "Overdue books cannot be renewed. Please return it first."

    if loan["renewals"] >= MAX_RENEWALS:
        return False, f"A loan can be renewed only {MAX_RENEWALS} times."

    new_due = (datetime.strptime(loan["due_date"], "%Y-%m-%d").date()
               + timedelta(days=RENEW_DAYS)).strftime("%Y-%m-%d")

    execute(
        "UPDATE loans SET due_date = ?, renewals = renewals + 1 "
        "WHERE loan_id = ? AND return_date IS NULL",
        (new_due, loan_id),
    )
    return True, f"Renewed. New due date is {new_due}."


# ----------------------------------------------------------
# Statistics for dashboards
# ----------------------------------------------------------

def overview_stats():
    today = today_text()
    overdue_days_sql = (
        "SELECT COALESCE(SUM(MAX(CAST(julianday(?) - julianday(due_date) "
        "AS INTEGER), 0)), 0) FROM loans WHERE return_date IS NULL"
    )
    return {
        "total_books": scalar("SELECT COUNT(*) FROM books"),
        "total_copies": scalar("SELECT SUM(total_copies) FROM books"),
        "available_copies": scalar("SELECT SUM(available_copies) FROM books"),
        "total_members": scalar("SELECT COUNT(*) FROM members"),
        "issued_books": scalar(
            "SELECT COUNT(*) FROM loans WHERE return_date IS NULL"),
        "overdue_books": scalar(
            "SELECT COUNT(*) FROM loans WHERE return_date IS NULL "
            "AND due_date < ?", (today,)),
        "fines_collected": scalar(
            "SELECT SUM(fine_amount) FROM loans WHERE status = 'Returned'"),
        "fines_pending": scalar(overdue_days_sql, (today,)) * FINE_PER_DAY,
        "total_loans": scalar("SELECT COUNT(*) FROM loans"),
    }


def category_breakdown(limit=6):
    return query(
        "SELECT COALESCE(NULLIF(TRIM(category), ''), 'Uncategorised') AS name, "
        "COUNT(*) AS n FROM books GROUP BY name ORDER BY n DESC, name LIMIT ?",
        (limit,),
    )


def loans_last_days(days=7):
    """Number of books issued on each of the last N days."""
    result = []
    for offset in range(days - 1, -1, -1):
        day = date.today() - timedelta(days=offset)
        n = scalar("SELECT COUNT(*) FROM loans WHERE issue_date = ?",
                   (day.strftime("%Y-%m-%d"),))
        result.append({"label": day.strftime("%a"), "date": day.isoformat(),
                       "n": n})
    return result


def top_books(limit=5):
    return query(
        """
        SELECT b.book_id, b.title, b.author, b.cover_image,
               COUNT(l.loan_id) AS n
        FROM books b JOIN loans l ON l.book_id = b.book_id
        GROUP BY b.book_id ORDER BY n DESC, b.title LIMIT ?
        """,
        (limit,),
    )


def fine_rows():
    return query(
        """
        SELECT l.loan_id, b.title, m.name AS member_name, l.due_date,
               l.return_date, l.fine_amount
        FROM loans l JOIN books b ON b.book_id = l.book_id
        JOIN members m ON m.member_id = l.member_id
        WHERE l.status = 'Returned' AND l.fine_amount > 0
        ORDER BY l.return_date DESC
        """
    )


def available_rows():
    return query(
        "SELECT book_id, title, author, category, total_copies, "
        "available_copies FROM books WHERE available_copies > 0 "
        "ORDER BY title COLLATE NOCASE"
    )
