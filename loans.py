
import sqlite3
from datetime import date, datetime, timedelta

from database import (
    get_connection,
    close_connection,
    is_positive_integer
)


# ==================================================
# CONSTANTS
# ==================================================

LOAN_DAYS = 14
FINE_PER_DAY = 5


# ==================================================
# ISSUE BOOK
# ==================================================

def issue_book(book_id, member_id):
    """
    Issue one book to one member.

    Returns:
        (True, details_dictionary)
        (False, error_message)
    """

    connection = get_connection()

    if connection is None:
        return False, "Could not connect to the database."

    try:
        cursor = connection.cursor()

        # Check whether book exists
        cursor.execute("""
            SELECT title, available_copies
            FROM books
            WHERE book_id = ?
        """, (book_id,))

        book = cursor.fetchone()

        if book is None:
            return False, "No book found with this Book ID."

        title, available = book

        # Check whether member exists
        cursor.execute("""
            SELECT name
            FROM members
            WHERE member_id = ?
        """, (member_id,))

        member = cursor.fetchone()

        if member is None:
            return False, "No member found with this Member ID."

        member_name = member[0]

        # Check available copies
        if available <= 0:
            return False, "No copies available."

        # Calculate issue and due dates
        issue_date = date.today()
        due_date = issue_date + timedelta(days=LOAN_DAYS)

        issue_text = issue_date.strftime("%Y-%m-%d")
        due_text = due_date.strftime("%Y-%m-%d")

        # Insert loan record
        cursor.execute("""
            INSERT INTO loans (
                book_id,
                member_id,
                issue_date,
                due_date,
                return_date,
                fine_amount,
                status
            )
            VALUES (?, ?, ?, ?, NULL, 0, 'Issued')
        """, (book_id, member_id, issue_text, due_text))

        loan_id = cursor.lastrowid

        # Reduce available copies
        cursor.execute("""
            UPDATE books
            SET available_copies = available_copies - 1
            WHERE book_id = ?
            AND available_copies > 0
        """, (book_id,))

        if cursor.rowcount != 1:
            connection.rollback()
            return False, "Could not reduce available copies."

        # Save changes
        connection.commit()

        return True, {
            "loan_id": loan_id,
            "book_id": book_id,
            "title": title,
            "member_id": member_id,
            "member_name": member_name,
            "issue_date": issue_text,
            "due_date": due_text,
            "status": "Issued"
        }

    except sqlite3.Error as error:
        connection.rollback()
        return False, f"Database error: {error}"

    finally:
        close_connection(connection)


# ==================================================
# ISSUE BOOK FROM USER (CONSOLE)
# ==================================================

def issue_book_from_user():
    """Take input from the user and issue a book."""

    print("\n========== ISSUE BOOK ==========")

    book_text = input("Enter Book ID: ").strip()
    member_text = input("Enter Member ID: ").strip()

    if not is_positive_integer(book_text) or not is_positive_integer(member_text):
        print("ERROR: Book ID and Member ID must be positive integers.")
        return

    success, result = issue_book(
        int(book_text),
        int(member_text)
    )

    if not success:
        print("ERROR:", result)
        return

    print("\nSUCCESS: Book issued successfully.")

    print("\n--------- Issue Confirmation ---------")
    print(f"Loan ID     : {result['loan_id']}")
    print(f"Book ID     : {result['book_id']}")
    print(f"Book Title  : {result['title']}")
    print(f"Member ID   : {result['member_id']}")
    print(f"Member Name : {result['member_name']}")
    print(f"Issue Date  : {result['issue_date']}")
    print(f"Due Date    : {result['due_date']}")
    print(f"Status      : {result['status']}")
    print("--------------------------------------")


# ==================================================
# CALCULATE FINE
# ==================================================

def calculate_fine(due_date_text, return_date):
    """
    Calculate overdue days and fine.

    Fine = Overdue Days * Fine Per Day

    Returns:
        (overdue_days, fine)
    """

    due_date = datetime.strptime(
        due_date_text,
        "%Y-%m-%d"
    ).date()

    overdue_days = max(
        0,
        (return_date - due_date).days
    )

    fine = overdue_days * FINE_PER_DAY

    return overdue_days, fine


# ==================================================
# FIND ACTIVE LOAN
# ==================================================

def find_active_loan(loan_id):
    """
    Find a loan that has not been returned.

    Returns:
        (True, details_dictionary)
        (False, error_message)
    """

    connection = get_connection()

    if connection is None:
        return False, "Could not connect to the database."

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                l.loan_id,
                l.book_id,
                l.member_id,
                b.title,
                m.name,
                l.issue_date,
                l.due_date,
                l.return_date,
                l.status

            FROM loans l

            JOIN books b
                ON b.book_id = l.book_id

            JOIN members m
                ON m.member_id = l.member_id

            WHERE l.loan_id = ?
        """, (loan_id,))

        row = cursor.fetchone()

        if row is None:
            return False, "Loan not found. Please check the Loan ID."

        (
            loan_id,
            book_id,
            member_id,
            title,
            member_name,
            issue_date,
            due_date,
            return_date,
            status
        ) = row

        # Check whether book is already returned
        if return_date is not None or status != "Issued":
            return False, "This book is already returned."

        # Calculate expected fine
        overdue_days, fine = calculate_fine(
            due_date,
            date.today()
        )

        return True, {
            "loan_id": loan_id,
            "book_id": book_id,
            "member_id": member_id,
            "title": title,
            "member_name": member_name,
            "issue_date": issue_date,
            "due_date": due_date,
            "return_date": date.today().strftime("%Y-%m-%d"),
            "overdue_days": overdue_days,
            "fine": fine
        }

    except (sqlite3.Error, ValueError) as error:
        return False, f"Error: {error}"

    finally:
        close_connection(connection)


# ==================================================
# RETURN BOOK
# ==================================================

def return_book(loan_id):
    """
    Return one book.

    1. Find the loan.
    2. Check whether already returned.
    3. Calculate fine.
    4. Update loan information.
    5. Increase available copies.
    6. Save both changes together.

    Returns:
        (True, details_dictionary)
        (False, error_message)
    """

    connection = get_connection()

    if connection is None:
        return False, "Could not connect to the database."

    try:
        cursor = connection.cursor()

        # Find the loan
        cursor.execute("""
            SELECT book_id, due_date, return_date, status
            FROM loans
            WHERE loan_id = ?
        """, (loan_id,))

        row = cursor.fetchone()

        if row is None:
            return False, "Loan not found. Please check the Loan ID."

        book_id, due_date_text, return_date, status = row

        # Prevent duplicate return
        if return_date is not None or status != "Issued":
            return False, "This book is already returned."

        # Calculate fine
        today = date.today()

        overdue_days, fine = calculate_fine(
            due_date_text,
            today
        )

        today_text = today.strftime("%Y-%m-%d")

        # Update loan
        cursor.execute("""
            UPDATE loans
            SET
                return_date = ?,
                fine_amount = ?,
                status = 'Returned'
            WHERE loan_id = ?
            AND return_date IS NULL
            AND status = 'Issued'
        """, (today_text, fine, loan_id))

        if cursor.rowcount != 1:
            connection.rollback()
            return False, "This book is already returned."

        # Increase available book copies
        cursor.execute("""
            UPDATE books
            SET available_copies = MIN(
                available_copies + 1,
                total_copies
            )
            WHERE book_id = ?
        """, (book_id,))

        if cursor.rowcount != 1:
            connection.rollback()
            return False, "Could not update available book copies."

        # Save changes
        connection.commit()

        return True, {
            "loan_id": loan_id,
            "return_date": today_text,
            "overdue_days": overdue_days,
            "fine": fine
        }

    except (sqlite3.Error, ValueError) as error:
        connection.rollback()
        return False, f"Database error: {error}"

    finally:
        close_connection(connection)


# ==================================================
# RETURN BOOK FROM USER (CONSOLE)
# ==================================================

def return_book_from_user():
    """Take Loan ID from the user and return the book."""

    print("\n========== RETURN BOOK ==========")

    loan_text = input("Enter Loan ID: ").strip()

    # Validate Loan ID
    if not is_positive_integer(loan_text):
        print("ERROR: Loan ID must be a positive integer.")
        return

    loan_id = int(loan_text)

    # Find active loan
    success, loan_details = find_active_loan(loan_id)

    if not success:
        print("ERROR:", loan_details)
        return

    # Display loan information
    print("\n--------- Loan Details ---------")
    print(f"Loan ID       : {loan_details['loan_id']}")
    print(f"Book ID       : {loan_details['book_id']}")
    print(f"Book Title    : {loan_details['title']}")
    print(f"Member ID     : {loan_details['member_id']}")
    print(f"Member Name   : {loan_details['member_name']}")
    print(f"Issue Date    : {loan_details['issue_date']}")
    print(f"Due Date      : {loan_details['due_date']}")
    print(f"Return Date   : {loan_details['return_date']}")
    print(f"Overdue Days  : {loan_details['overdue_days']}")
    print(f"Expected Fine : Rs. {loan_details['fine']}")
    print("--------------------------------")

    # Ask for confirmation
    confirm = input(
        "\nConfirm book return? (yes/no): "
    ).strip().lower()

    if confirm not in ("yes", "y"):
        print("Book return cancelled.")
        return

    # Return book
    success, result = return_book(loan_id)

    if not success:
        print("ERROR:", result)
        return

    # Display confirmation
    print("\nSUCCESS: Book returned successfully.")

    print("\n--------- Return Confirmation ---------")
    print(f"Loan ID      : {result['loan_id']}")
    print(f"Return Date  : {result['return_date']}")
    print(f"Overdue Days : {result['overdue_days']}")
    print(f"Fine Amount  : Rs. {result['fine']}")
    print("---------------------------------------")
