
import sqlite3
from datetime import date
from database import get_connection, close_connection, is_positive_integer


# ---------- ISBN Validation ----------

def clean_isbn(isbn):
    """Remove spaces and hyphens, and make X a capital letter."""
    return isbn.replace("-", "").replace(" ", "").upper()


def is_valid_isbn(isbn):
    """ISBN-10: 9 digits + (digit or X). ISBN-13: 13 digits."""
    if len(isbn) == 10:
        return isbn[:9].isdigit() and (isbn[9].isdigit() or isbn[9] == "X")
    if len(isbn) == 13:
        return isbn.isdigit()
    return False


# ---------- Add Book ----------

def add_book(title, author, isbn, category, publisher,
             publication_year, total_copies, available_copies):
    """Check the data, then save one book. Returns (True/False, message)."""

    # 1. Clean the text
    title = title.strip()
    author = author.strip()
    isbn = clean_isbn(isbn.strip())
    category = category.strip()
    publisher = publisher.strip()

    # 2. Required fields must not be empty
    if title == "" or author == "" or isbn == "":
        return False, "Title, author and ISBN cannot be empty."

    # 3. Validate ISBN
    if not is_valid_isbn(isbn):
        return False, "ISBN must be 10 or 13 digits (ISBN-10 can end with X)."

    # 4. Copies must be whole numbers
    try:
        total_copies = int(total_copies)
        available_copies = int(available_copies)
    except ValueError:
        return False, "Copies must be whole numbers."

    if total_copies < 1:
        return False, "Total copies must be at least 1."

    if available_copies < 0 or available_copies > total_copies:
        return False, "Available copies must be from 0 to total copies."

    # 5. Publication year is optional, but if given it must be valid
    year_text = str(publication_year).strip()

    if year_text == "":
        publication_year = None
    else:
        try:
            publication_year = int(year_text)
        except ValueError:
            return False, "Publication year must be a number."

        if publication_year < 1000 or publication_year > date.today().year:
            return False, "Publication year is not valid."

    # 6. Save in the database
    connection = get_connection()

    if connection is None:
        return False, "Could not connect to the database."

    try:
        cursor = connection.cursor()

        # Prevent duplicate ISBN
        cursor.execute(
            "SELECT book_id FROM books WHERE isbn = ?",
            (isbn,)
        )

        if cursor.fetchone() is not None:
            return False, "A book with this ISBN already exists."

        cursor.execute(
            """
            INSERT INTO books (
                title, author, isbn, category, publisher,
                publication_year, total_copies, available_copies
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title, author, isbn, category, publisher,
                publication_year, total_copies, available_copies
            )
        )

        connection.commit()

        return True, f"Book added successfully. Book ID = {cursor.lastrowid}"

    except Exception as error:
        return False, f"Database error: {error}"

    finally:
        close_connection(connection)


# ---------- Display Books ----------

def print_books_table(rows):
    """Show a list of books as a table in the terminal."""

    line = "-" * 88

    print(line)
    print(f"{'ID':<5}{'Title':<30}{'Author':<22}{'Genre':<18}{'Available':<10}")
    print(line)

    for book_id, title, author, category, available in rows:
        category = category if category else "-"

        print(
            f"{book_id:<5}{title[:28]:<30}{author[:20]:<22}"
            f"{category[:16]:<18}{available:<10}"
        )

    print(line)


def view_all_books():
    """Display all books."""

    connection = get_connection()

    if connection is None:
        print("Could not connect to the database.")
        return

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT book_id, title, author, category, available_copies "
            "FROM books ORDER BY book_id"
        )

        rows = cursor.fetchall()

        if len(rows) == 0:
            print("No books found in the library.")
        else:
            print_books_table(rows)
            print(f"Total books: {len(rows)}")

    except Exception as error:
        print("Database error:", error)

    finally:
        close_connection(connection)


# ---------- Search Books ----------

def search_books(search_type, keyword):
    """Search by 'title', 'author' or 'isbn'."""

    keyword = keyword.strip()

    if keyword == "":
        print("Search text cannot be empty.")
        return

    # Only these 3 fixed SQL texts are used.
    if search_type == "title":
        sql = (
            "SELECT book_id, title, author, category, available_copies "
            "FROM books WHERE title LIKE ?"
        )
        value = "%" + keyword + "%"

    elif search_type == "author":
        sql = (
            "SELECT book_id, title, author, category, available_copies "
            "FROM books WHERE author LIKE ?"
        )
        value = "%" + keyword + "%"

    elif search_type == "isbn":
        sql = (
            "SELECT book_id, title, author, category, available_copies "
            "FROM books WHERE isbn = ?"
        )
        value = clean_isbn(keyword)

    else:
        print("Invalid search type.")
        return

    connection = get_connection()

    if connection is None:
        print("Could not connect to the database.")
        return

    try:
        cursor = connection.cursor()
        cursor.execute(sql, (value,))
        rows = cursor.fetchall()

        if len(rows) == 0:
            print("No book found.")
        else:
            print_books_table(rows)
            print(f"Books found: {len(rows)}")

    except Exception as error:
        print("Database error:", error)

    finally:
        close_connection(connection)


# ---------- Functions That Ask the User for Input ----------

def add_book_from_user():
    print("\n--- Add New Book ---")

    title = input("Title: ")
    author = input("Author: ")
    isbn = input("ISBN: ")
    category = input("Genre / Category: ")
    publisher = input("Publisher: ")
    year = input("Publication year (press Enter to skip): ")
    total = input("Total copies: ")
    available = input("Available copies: ")

    success, message = add_book(
        title, author, isbn, category,
        publisher, year, total, available
    )

    print(("SUCCESS: " if success else "ERROR: ") + message)


def search_book_from_user():
    print("\n--- Search Book ---")
    print("1. Search by Title")
    print("2. Search by Author")
    print("3. Search by ISBN")

    choice = input("Enter choice (1-3): ").strip()

    if choice == "1":
        search_books("title", input("Enter title (or part of it): "))

    elif choice == "2":
        search_books("author", input("Enter author (or part of name): "))

    elif choice == "3":
        search_books("isbn", input("Enter exact ISBN: "))

    else:
        print("Invalid choice.")


# ---------- Helper Functions for Update and Delete ----------

def get_book_by_id(cursor, book_id):
    """Return one book row, or None if the book does not exist."""

    cursor.execute(
        "SELECT book_id, title, author, isbn, category, publisher, "
        "publication_year, total_copies, available_copies "
        "FROM books WHERE book_id = ?",
        (book_id,)
    )

    return cursor.fetchone()


def count_active_loans(cursor, book_id):
    """Count loans of this book that are not returned yet."""

    cursor.execute(
        "SELECT COUNT(*) FROM loans WHERE book_id = ? AND return_date IS NULL",
        (book_id,)
    )

    return cursor.fetchone()[0]


def show_book_details(book):
    """Print all details of one book."""

    labels = [
        "Book ID", "Title", "Author", "ISBN", "Category",
        "Publisher", "Publication Year", "Total Copies",
        "Available Copies"
    ]

    for label, value in zip(labels, book):
        if value is None or value == "":
            value = "-"

        print(f"  {label:<18}: {value}")


def ask_new_value(label, old_value):
    """Ask for a new value. Enter keeps the old value."""

    shown = "" if old_value is None else old_value
    text = input(f"{label} [{shown}]: ").strip()

    if text == "":
        return "" if old_value is None else str(old_value)

    return text


# ---------- Update Book ----------

def update_book_from_user():
    print("\n--- Update Book ---")

    id_text = input("Enter Book ID: ").strip()

    if not is_positive_integer(id_text):
        print("ERROR: Book ID must be a positive integer.")
        return

    book_id = int(id_text)

    connection = get_connection()

    if connection is None:
        print("ERROR: Could not connect to the database.")
        return

    try:
        cursor = connection.cursor()

        # 1. Check that the book exists
        book = get_book_by_id(cursor, book_id)

        if book is None:
            print("ERROR: No book found with this Book ID.")
            return

        # 2. Show the old details
        issued = count_active_loans(cursor, book_id)

        print("\nCurrent details:")
        show_book_details(book)
        print(f"  Currently issued  : {issued}")
        print("\nPress Enter to keep the old value.")

        # 3. Ask for new values
        title = ask_new_value("Title", book[1])
        author = ask_new_value("Author", book[2])
        isbn = clean_isbn(ask_new_value("ISBN", book[3]))
        category = ask_new_value("Category", book[4])
        publisher = ask_new_value("Publisher", book[5])
        year_text = ask_new_value("Publication year", book[6])
        total_text = ask_new_value("Total copies", book[7])

        # 4. Validate required fields
        if title == "" or author == "" or isbn == "":
            print("ERROR: Title, author and ISBN cannot be empty.")
            return

        # 5. Validate ISBN
        if not is_valid_isbn(isbn):
            print("ERROR: ISBN must be 10 or 13 digits (ISBN-10 can end with X).")
            return

        # 6. Validate year (optional)
        if year_text == "":
            year = None
        else:
            try:
                year = int(year_text)
            except ValueError:
                print("ERROR: Publication year must be a number.")
                return

            if year < 1000 or year > date.today().year:
                print("ERROR: Publication year is not valid.")
                return

        # 7. Validate total copies
        try:
            total = int(total_text)
        except ValueError:
            print("ERROR: Total copies must be a whole number.")
            return

        if total < 1:
            print("ERROR: Total copies must be at least 1.")
            return

        if total < issued:
            print(f"ERROR: Total copies cannot be less than issued copies ({issued}).")
            return

        # 8. Available copies must always be total - issued
        correct_available = total - issued

        avail_text = input(
            f"Available copies (press Enter = {correct_available}): "
        ).strip()

        if avail_text == "":
            available = correct_available
        else:
            try:
                available = int(avail_text)
            except ValueError:
                print("ERROR: Available copies must be a whole number.")
                return

            if available != correct_available:
                print(
                    f"ERROR: Available copies must be {correct_available} "
                    f"(total {total} - issued {issued})."
                )
                return

        # 9. Prevent duplicate ISBN (ignore this same book)
        cursor.execute(
            "SELECT book_id FROM books WHERE isbn = ? AND book_id != ?",
            (isbn, book_id)
        )

        if cursor.fetchone() is not None:
            print("ERROR: Another book already has this ISBN.")
            return

        # 10. Save the changes
        cursor.execute(
            """
            UPDATE books
            SET title = ?, author = ?, isbn = ?, category = ?, publisher = ?,
                publication_year = ?, total_copies = ?, available_copies = ?
            WHERE book_id = ?
            """,
            (
                title, author, isbn, category, publisher,
                year, total, available, book_id
            )
        )

        connection.commit()
        print("SUCCESS: Book updated successfully.")

    except sqlite3.Error as error:
        print("ERROR: Database error:", error)

    finally:
        close_connection(connection)


# ---------- Delete Book ----------

def delete_book_from_user():
    print("\n--- Delete Book ---")

    id_text = input("Enter Book ID: ").strip()

    if not is_positive_integer(id_text):
        print("ERROR: Book ID must be a positive integer.")
        return

    book_id = int(id_text)

    connection = get_connection()

    if connection is None:
        print("ERROR: Could not connect to the database.")
        return

    try:
        cursor = connection.cursor()

        # 1. Check that the book exists
        book = get_book_by_id(cursor, book_id)

        if book is None:
            print("ERROR: No book found with this Book ID.")
            return

        # 2. Show the book
        print("\nBook to delete:")
        show_book_details(book)

        # 3. Stop if the book has active loans
        if count_active_loans(cursor, book_id) > 0:
            print("ERROR: This book has active loans. It cannot be deleted.")
            return

        # 4. Ask for confirmation
        answer = input(
            "\nAre you sure you want to delete this book? (yes/no): "
        )

        if answer.strip().lower() != "yes":
            print("Deletion cancelled.")
            return

        # 5. Delete
        cursor.execute(
            "DELETE FROM books WHERE book_id = ?",
            (book_id,)
        )

        connection.commit()
        print("SUCCESS: Book deleted successfully.")

    except sqlite3.IntegrityError:
        # Happens if old (returned) loans still point to this book
        print("ERROR: This book has loan history, so it cannot be deleted.")

    except sqlite3.Error as error:
        print("ERROR: Database error:", error)

    finally:
        close_connection(connection)
    # ---------- Functions for the GUI (they return data, they do not print) ----------

def parse_year(year_text):
    """Returns (True, year or None) or (False, error message)."""
    year_text = str(year_text).strip()
    if year_text == "":
        return True, None
    try:
        year = int(year_text)
    except ValueError:
        return False, "Publication year must be a number."
    if year < 1000 or year > date.today().year:
        return False, "Publication year is not valid."
    return True, year


def get_all_books_rows():
    """Return all books for the table, or None if there is an error."""
    connection = get_connection()
    if connection is None:
        return None
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT book_id, title, author, isbn, category, "
            "total_copies, available_copies FROM books ORDER BY book_id"
        )
        return cursor.fetchall()
    except sqlite3.Error:
        return None
    finally:
        close_connection(connection)


def search_books_rows(search_type, keyword):
    """Search by 'title', 'author' or 'isbn'. Returns rows, or None on error."""
    keyword = keyword.strip()
    base = ("SELECT book_id, title, author, isbn, category, "
            "total_copies, available_copies FROM books WHERE ")

    if search_type == "title":
        sql, params = base + "title LIKE ?", ("%" + keyword + "%",)
    elif search_type == "author":
        sql, params = base + "author LIKE ?", ("%" + keyword + "%",)
    elif search_type == "isbn":
        sql, params = base + "isbn = ? OR isbn = ?", (keyword, clean_isbn(keyword))
    else:
        return []

    connection = get_connection()
    if connection is None:
        return None
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()
    except sqlite3.Error:
        return None
    finally:
        close_connection(connection)


def get_book_full(book_id):
    """Return all 9 fields of one book (or None)."""
    connection = get_connection()
    if connection is None:
        return None
    try:
        return get_book_by_id(connection.cursor(), book_id)
    except sqlite3.Error:
        return None
    finally:
        close_connection(connection)


def update_book(book_id, title, author, isbn, category, publisher,
                publication_year, total_copies, available_copies):
    """Check the data, then update one book. Returns (True/False, message)."""
    title = title.strip()
    author = author.strip()
    isbn = clean_isbn(isbn.strip())
    category = category.strip()
    publisher = publisher.strip()

    if title == "" or author == "" or isbn == "":
        return False, "Title, author and ISBN cannot be empty."
    if not is_valid_isbn(isbn):
        return False, "ISBN must be 10 or 13 digits (ISBN-10 can end with X)."

    ok, year = parse_year(publication_year)
    if not ok:
        return False, year   # 'year' holds the error message here

    try:
        total = int(total_copies)
    except ValueError:
        return False, "Total copies must be a whole number."
    if total < 1:
        return False, "Total copies must be at least 1."

    connection = get_connection()
    if connection is None:
        return False, "Could not connect to the database."

    try:
        cursor = connection.cursor()

        if get_book_by_id(cursor, book_id) is None:
            return False, "No book found with this Book ID."

        issued = count_active_loans(cursor, book_id)
        if total < issued:
            return False, f"Total copies cannot be less than issued copies ({issued})."

        # Available copies must always be: total - issued
        correct_available = total - issued
        available_text = str(available_copies).strip()
        if available_text == "":
            available = correct_available
        else:
            try:
                available = int(available_text)
            except ValueError:
                return False, "Available copies must be a whole number."
            if available != correct_available:
                return False, (f"Available copies must be {correct_available} "
                               f"(total {total} - issued {issued}).")

        cursor.execute("SELECT book_id FROM books WHERE isbn = ? AND book_id != ?",
                       (isbn, book_id))
        if cursor.fetchone() is not None:
            return False, "Another book already has this ISBN."

        cursor.execute(
            """
            UPDATE books
            SET title = ?, author = ?, isbn = ?, category = ?, publisher = ?,
                publication_year = ?, total_copies = ?, available_copies = ?
            WHERE book_id = ?
            """,
            (title, author, isbn, category, publisher,
             year, total, available, book_id),
        )
        connection.commit()
        return True, "Book updated successfully."
    except sqlite3.Error as error:
        return False, f"Database error: {error}"
    finally:
        close_connection(connection)


def delete_book(book_id):
    """Delete one book if it has no active loans. Returns (True/False, message)."""
    connection = get_connection()
    if connection is None:
        return False, "Could not connect to the database."

    try:
        cursor = connection.cursor()

        if get_book_by_id(cursor, book_id) is None:
            return False, "No book found with this Book ID."
        if count_active_loans(cursor, book_id) > 0:
            return False, "This book has active loans. It cannot be deleted."

        cursor.execute("DELETE FROM books WHERE book_id = ?", (book_id,))
        connection.commit()
        return True, "Book deleted successfully."
    except sqlite3.IntegrityError:
        return False, "This book has loan history, so it cannot be deleted."
    except sqlite3.Error as error:
        return False, f"Database error: {error}"
    finally:
        close_connection(connection)