
import sqlite3
from datetime import date

from database import get_connection, close_connection, is_positive_integer
from loans import FINE_PER_DAY


# ==========================================================
# REUSABLE HELPER FUNCTIONS
# ==========================================================

def run_query(sql, params=()):
    """
    Run one SELECT query.
    Returns the rows, or None if there is an error.
    """

    connection = get_connection()

    if connection is None:
        print("ERROR: Could not connect to the database.")
        return None

    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()

    except sqlite3.Error as error:
        print("ERROR: Database error:", error)
        return None

    finally:
        close_connection(connection)


def print_table(headers, widths, rows):
    """
    Print rows as a table.
    Each column has a fixed width.
    """

    line = "-" * sum(widths)

    print(line)
    print("".join(
        f"{header:<{width}}"
        for header, width in zip(headers, widths)
    ))
    print(line)

    for row in rows:
        cells = []

        for value, width in zip(row, widths):
            text = "-" if value is None or value == "" else str(value)
            cells.append(f"{text[:width - 2]:<{width}}")

        print("".join(cells))

    print(line)


# ==========================================================
# 1. AVAILABLE BOOKS REPORT
# ==========================================================

def available_books_report():

    print("\n--- Available Books Report ---")

    rows = run_query(
        """
        SELECT book_id, title, author, category,
               total_copies, available_copies
        FROM books
        WHERE available_copies > 0
        ORDER BY book_id
        """
    )

    if rows is None:
        return

    if len(rows) == 0:
        print("No books are available right now.")
        return

    print_table(
        ["ID", "Title", "Author", "Category", "Total", "Available"],
        [5, 30, 22, 18, 8, 10],
        rows
    )

    print(f"Available books: {len(rows)}")


# ==========================================================
# 2. ISSUED BOOKS REPORT
# ==========================================================

def issued_books_report():

    print("\n--- Issued Books Report ---")

    rows = run_query(
        """
        SELECT l.loan_id, b.book_id, b.title,
               m.member_id, m.name,
               l.issue_date, l.due_date, l.status
        FROM loans l
        JOIN books b ON b.book_id = l.book_id
        JOIN members m ON m.member_id = l.member_id
        WHERE l.status = 'Issued'
        ORDER BY l.loan_id
        """
    )

    if rows is None:
        return

    if len(rows) == 0:
        print("No books are issued right now.")
        return

    print_table(
        [
            "Loan ID", "Book ID", "Title", "Member ID",
            "Member", "Issue Date", "Due Date", "Status"
        ],
        [9, 9, 26, 11, 18, 12, 12, 8],
        rows
    )

    print(f"Issued books: {len(rows)}")


# ==========================================================
# 3. OVERDUE BOOKS REPORT
# ==========================================================

def overdue_books_report():

    print("\n--- Overdue Books Report ---")

    today = date.today().strftime("%Y-%m-%d")

    rows = run_query(
        """
        SELECT l.loan_id, b.title, m.name, m.phone,
               l.issue_date, l.due_date,
               CAST(julianday(?) - julianday(l.due_date) AS INTEGER)
        FROM loans l
        JOIN books b ON b.book_id = l.book_id
        JOIN members m ON m.member_id = l.member_id
        WHERE l.status = 'Issued'
          AND l.return_date IS NULL
          AND l.due_date < ?
        ORDER BY l.due_date
        """,
        (today, today)
    )

    if rows is None:
        return

    if len(rows) == 0:
        print("No overdue books. Great!")
        return

    print_table(
        [
            "Loan ID", "Title", "Member", "Phone",
            "Issue Date", "Due Date", "Days"
        ],
        [9, 26, 18, 14, 12, 12, 6],
        rows
    )

    print(f"Overdue books: {len(rows)}")


# ==========================================================
# 4. MEMBER BORROWING HISTORY
# ==========================================================

def member_history_report():

    print("\n--- Member Borrowing History ---")

    id_text = input("Enter Member ID: ").strip()

    if not is_positive_integer(id_text):
        print("ERROR: Member ID must be a positive whole number.")
        return

    member_id = int(id_text)

    # Check whether the member exists
    member = run_query(
        "SELECT name FROM members WHERE member_id = ?",
        (member_id,)
    )

    if member is None:
        return

    if len(member) == 0:
        print("ERROR: No member found with this Member ID.")
        return

    print(f"Member: {member[0][0]} (ID {member_id})")

    rows = run_query(
        """
        SELECT l.loan_id, b.title, b.author,
               l.issue_date, l.due_date,
               l.return_date, l.fine_amount, l.status
        FROM loans l
        JOIN books b ON b.book_id = l.book_id
        WHERE l.member_id = ?
        ORDER BY l.loan_id
        """,
        (member_id,)
    )

    if rows is None:
        return

    if len(rows) == 0:
        print("This member has not borrowed any books yet.")
        return

    print_table(
        [
            "Loan ID", "Title", "Author", "Issue Date",
            "Due Date", "Return Date", "Fine", "Status"
        ],
        [9, 24, 18, 12, 12, 13, 7, 10],
        rows
    )

    print(f"Total loans: {len(rows)}")


# ==========================================================
# GUI FUNCTIONS
# These functions return data instead of printing it.
# ==========================================================


# ==========================================================
# 5. AVAILABLE BOOKS ROWS
# ==========================================================

def available_books_rows():

    return run_query(
        """
        SELECT book_id, title, author, category,
               total_copies, available_copies
        FROM books
        WHERE available_copies > 0
        ORDER BY book_id
        """
    )


# ==========================================================
# 6. ISSUED BOOKS ROWS
# ==========================================================

def issued_books_rows():

    return run_query(
        """
        SELECT l.loan_id, b.book_id, b.title,
               m.member_id, m.name,
               l.issue_date, l.due_date, l.status
        FROM loans l
        JOIN books b ON b.book_id = l.book_id
        JOIN members m ON m.member_id = l.member_id
        WHERE l.status = 'Issued'
        ORDER BY l.loan_id
        """
    )


# ==========================================================
# 7. OVERDUE BOOKS ROWS
# ==========================================================

def overdue_books_rows():

    today = date.today().strftime("%Y-%m-%d")

    return run_query(
        """
        SELECT l.loan_id, b.title, m.name, m.phone,
               l.issue_date, l.due_date,
               CAST(julianday(?) - julianday(l.due_date) AS INTEGER)
        FROM loans l
        JOIN books b ON b.book_id = l.book_id
        JOIN members m ON m.member_id = l.member_id
        WHERE l.status = 'Issued'
          AND l.return_date IS NULL
          AND l.due_date < ?
        ORDER BY l.due_date
        """,
        (today, today)
    )


# ==========================================================
# 8. MEMBER HISTORY ROWS
# ==========================================================

def member_history_rows(member_id):
    """
    Returns:
    (True, member_name, rows)
    or
    (False, error_message, [])
    """

    member = run_query(
        "SELECT name FROM members WHERE member_id = ?",
        (member_id,)
    )

    if member is None:
        return False, "Database error.", []

    if len(member) == 0:
        return False, "No member found with this Member ID.", []

    rows = run_query(
        """
        SELECT l.loan_id, b.title, b.author,
               l.issue_date, l.due_date,
               l.return_date, l.fine_amount, l.status
        FROM loans l
        JOIN books b ON b.book_id = l.book_id
        WHERE l.member_id = ?
        ORDER BY l.loan_id
        """,
        (member_id,)
    )

    if rows is None:
        return False, "Database error.", []

    return True, member[0][0], rows


# ==========================================================
# 9. ADMIN DASHBOARD STATISTICS
# ==========================================================

def dashboard_stats():
    """
    Return a dictionary of numbers for the admin dashboard.
    Returns None if a database error occurs.
    """

    today = date.today().strftime("%Y-%m-%d")

    queries = [

        ("total_books",
         "SELECT COUNT(*) FROM books",
         ()),

        ("total_copies",
         "SELECT SUM(total_copies) FROM books",
         ()),

        ("available_copies",
         "SELECT SUM(available_copies) FROM books",
         ()),

        ("total_members",
         "SELECT COUNT(*) FROM members",
         ()),

        # Total fines collected from returned books
        ("total_fine",
         "SELECT SUM(fine_amount) FROM loans WHERE status = 'Returned'",
         ()),

        ("issued_books",
         "SELECT COUNT(*) FROM loans WHERE status = 'Issued'",
         ()),

        ("overdue_books",
         """
         SELECT COUNT(*)
         FROM loans
         WHERE status = 'Issued'
           AND return_date IS NULL
           AND due_date < ?
         """,
         (today,)),

    ]

    stats = {}

    for key, sql, params in queries:

        rows = run_query(sql, params)

        if rows is None:
            return None

        # SUM returns None when there is no data.
        # Convert None to 0.
        stats[key] = rows[0][0] or 0

    return stats


# ==========================================================
# 10. FINE COLLECTION REPORT
# ==========================================================

def fine_collection_rows():
    """
    Return all returned loans that had a fine.
    """

    return run_query(
        """
        SELECT l.loan_id, b.title, m.name,
               l.due_date, l.return_date, l.fine_amount
        FROM loans l
        JOIN books b ON b.book_id = l.book_id
        JOIN members m ON m.member_id = l.member_id
        WHERE l.status = 'Returned'
          AND l.fine_amount > 0
        ORDER BY l.return_date DESC
        """
    )


# ==========================================================
# 11. MEMBER CURRENTLY ISSUED BOOKS
# ==========================================================

def member_issued_rows(member_id):
    """
    Return this member's issued books with:
    - Book details
    - Issue date
    - Due date
    - Overdue days
    - Current fine
    """

    today = date.today().strftime("%Y-%m-%d")

    rows = run_query(
        """
        SELECT l.loan_id, b.title, b.author,
               l.issue_date, l.due_date,
               MAX(
                   CAST(julianday(?) - julianday(l.due_date) AS INTEGER),
                   0
               )
        FROM loans l
        JOIN books b ON b.book_id = l.book_id
        WHERE l.member_id = ?
          AND l.status = 'Issued'
          AND l.return_date IS NULL
        ORDER BY l.due_date
        """,
        (today, member_id)
    )

    if rows is None:
        return None

    # Add the current fine amount to every row.
    return [
        row + (f"₹{row[5] * FINE_PER_DAY:.2f}",)
        for row in rows
    ]


# ==========================================================
# 12. MEMBER DASHBOARD DATA
# ==========================================================

def member_dashboard_data(member_id):
    """
    Returns:
    (stats_dictionary, issued_rows)

    Returns None if a database error occurs.
    """

    rows = member_issued_rows(member_id)

    if rows is None:
        return None

    stats = {

        # Number of books currently borrowed
        "borrowed": len(rows),

        # Number of currently overdue books
        "overdue": sum(
            1 for row in rows if row[5] > 0
        ),

        # Total pending fine
        "pending_fine": sum(
            row[5] for row in rows
        ) * FINE_PER_DAY,

    }

    return stats, rows


# ==========================================================
# 13. RECENT ISSUES
# ==========================================================

def recent_issues_rows(limit=5):
    """
    Return the latest book issues.
    """

    return run_query(
        """
        SELECT l.loan_id, b.title, m.name,
               l.issue_date, l.due_date, l.status
        FROM loans l
        JOIN books b ON b.book_id = l.book_id
        JOIN members m ON m.member_id = l.member_id
        ORDER BY l.loan_id DESC
        LIMIT ?
        """,
        (limit,)
    )


# ==========================================================
# 14. RECENT MEMBERS
# ==========================================================

def recent_members_rows(limit=5):
    """
    Return the latest registered members.
    """

    return run_query(
        """
        SELECT member_id, name, email, join_date
        FROM members
        ORDER BY member_id DESC
        LIMIT ?
        """,
        (limit,)
    )
