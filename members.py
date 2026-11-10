
import re
import sqlite3
from datetime import date, datetime

from database import get_connection, close_connection, is_positive_integer


EMAIL_PATTERN = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"


# ---------- Small helper functions ----------

def is_valid_email(email):
    """True if the email looks like name@site.com."""
    return re.match(EMAIL_PATTERN, email) is not None


def is_valid_phone(phone):
    """True if phone has only digits and is 10 to 15 digits long."""
    return phone.isdigit() and 10 <= len(phone) <= 15


def is_valid_date(text):
    """True if text is a real date in YYYY-MM-DD format and not in the future."""
    try:
        d = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return False

    return d <= date.today()


def count_active_loans(cursor, member_id):
    """Count loans of this member that are not returned yet."""
    cursor.execute(
        "SELECT COUNT(*) FROM loans WHERE member_id = ? AND return_date IS NULL",
        (member_id,),
    )
    return cursor.fetchone()[0]


def get_member_by_id(cursor, member_id):
    """Return one member row, or None if not found."""
    cursor.execute(
        "SELECT member_id, name, email, phone, address, join_date "
        "FROM members WHERE member_id = ?",
        (member_id,),
    )
    return cursor.fetchone()


def show_member_details(member):
    labels = ["Member ID", "Name", "Email", "Phone", "Address", "Join Date"]

    for label, value in zip(labels, member):
        if value is None or value == "":
            value = "-"
        print(f"  {label:<10}: {value}")


def print_members_table(rows):
    line = "-" * 101

    print(line)
    print(
        f"{'ID':<5}{'Name':<20}{'Email':<28}{'Phone':<14}"
        f"{'Address':<22}{'Join Date':<12}"
    )
    print(line)

    for member_id, name, email, phone, address, join_date in rows:
        phone = phone if phone else "-"
        address = address if address else "-"
        join_date = join_date if join_date else "-"
        email = email if email else "-"

        print(
            f"{member_id:<5}{name[:18]:<20}{email[:26]:<28}{phone[:12]:<14}"
            f"{address[:20]:<22}{join_date:<12}"
        )

    print(line)


def ask_new_value(label, old_value):
    """Ask for a new value. If the user presses Enter, keep the old one."""
    shown = "" if old_value is None else old_value

    text = input(f"{label} [{shown}]: ").strip()

    if text == "":
        return "" if old_value is None else str(old_value)

    return text


# ---------- 1. Register a new member ----------

def register_member(name, email, phone, address, join_date):
    """Check the data, then save one member. Returns (True/False, message)."""

    name = name.strip()
    email = email.strip().lower()
    phone = phone.strip()
    address = address.strip()
    join_date = join_date.strip()

    if name == "":
        return False, "Name cannot be empty."

    if email == "":
        return False, "Email cannot be empty."

    if not is_valid_email(email):
        return False, "Email format is not valid. Example: name@gmail.com"

    if phone != "" and not is_valid_phone(phone):
        return False, "Phone must have 10 to 15 digits only."

    if join_date == "":
        join_date = date.today().isoformat()

    elif not is_valid_date(join_date):
        return False, "Join date must be a real date like 2026-11-04 (not in future)."

    connection = get_connection()

    if connection is None:
        return False, "Could not connect to the database."

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT member_id FROM members WHERE email = ?",
            (email,)
        )

        if cursor.fetchone() is not None:
            return False, "A member with this email already exists."

        cursor.execute(
            "INSERT INTO members (name, email, phone, address, join_date) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, email, phone, address, join_date),
        )

        connection.commit()

        return True, f"Member registered successfully. Member ID = {cursor.lastrowid}"

    except sqlite3.Error as error:
        return False, f"Database error: {error}"

    finally:
        close_connection(connection)


def register_member_from_user():
    print("\n--- Register New Member ---")

    name = input("Name: ")
    email = input("Email: ")
    phone = input("Phone (10-15 digits, Enter to skip): ")
    address = input("Address: ")
    join_date = input("Join date YYYY-MM-DD (Enter = today): ")

    success, message = register_member(
        name, email, phone, address, join_date
    )

    print(("SUCCESS: " if success else "ERROR: ") + message)


# ---------- 2. View all members ----------

def view_all_members():
    connection = get_connection()

    if connection is None:
        print("Could not connect to the database.")
        return

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT member_id, name, email, phone, address, join_date "
            "FROM members ORDER BY member_id"
        )

        rows = cursor.fetchall()

        if len(rows) == 0:
            print("No members found.")
        else:
            print_members_table(rows)
            print(f"Total members: {len(rows)}")

    except sqlite3.Error as error:
        print("Database error:", error)

    finally:
        close_connection(connection)


# ---------- 3. Search members ----------

def search_members(search_type, keyword):
    """Search by 'id', 'name', 'email' or 'phone'."""

    keyword = keyword.strip()

    if keyword == "":
        print("Search text cannot be empty.")
        return

    base = (
        "SELECT member_id, name, email, phone, address, join_date "
        "FROM members WHERE "
    )

    if search_type == "id":

        if not is_positive_integer(keyword):
            print("Member ID must be a positive integer.")
            return

        sql = base + "member_id = ?"
        value = int(keyword)

    elif search_type == "name":
        sql = base + "name LIKE ?"
        value = "%" + keyword + "%"

    elif search_type == "email":
        sql = base + "email LIKE ?"
        value = "%" + keyword + "%"

    elif search_type == "phone":
        sql = base + "phone LIKE ?"
        value = "%" + keyword + "%"

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
            print("No member found.")
        else:
            print_members_table(rows)
            print(f"Members found: {len(rows)}")

    except sqlite3.Error as error:
        print("Database error:", error)

    finally:
        close_connection(connection)


def search_member_from_user():
    print("\n--- Search Member ---")

    print("1. Search by Member ID")
    print("2. Search by Name")
    print("3. Search by Email")
    print("4. Search by Phone")

    choice = input("Enter choice (1-4): ").strip()

    if choice == "1":
        search_members("id", input("Enter Member ID: "))

    elif choice == "2":
        search_members("name", input("Enter name (or part of it): "))

    elif choice == "3":
        search_members("email", input("Enter email (or part of it): "))

    elif choice == "4":
        search_members("phone", input("Enter phone (or part of it): "))

    else:
        print("Invalid choice.")


# ---------- 4. Update member ----------

def update_member_from_user():
    print("\n--- Update Member ---")

    id_text = input("Enter Member ID: ").strip()

    if not is_positive_integer(id_text):
        print("ERROR: Member ID must be a positive integer.")
        return

    member_id = int(id_text)

    connection = get_connection()

    if connection is None:
        print("ERROR: Could not connect to the database.")
        return

    try:
        cursor = connection.cursor()

        member = get_member_by_id(cursor, member_id)

        if member is None:
            print("ERROR: No member found with this Member ID.")
            return

        print("\nCurrent details:")
        show_member_details(member)

        print("\nPress Enter to keep the old value.")

        name = ask_new_value("Name", member[1])
        email = ask_new_value("Email", member[2]).lower()
        phone = ask_new_value("Phone", member[3])
        address = ask_new_value("Address", member[4])

        if name == "":
            print("ERROR: Name cannot be empty.")
            return

        if email == "":
            print("ERROR: Email cannot be empty.")
            return

        if not is_valid_email(email):
            print("ERROR: Email format is not valid.")
            return

        if phone != "" and not is_valid_phone(phone):
            print("ERROR: Phone must have 10 to 15 digits only.")
            return

        cursor.execute(
            "SELECT member_id FROM members WHERE email = ? AND member_id != ?",
            (email, member_id),
        )

        if cursor.fetchone() is not None:
            print("ERROR: Another member already has this email.")
            return

        cursor.execute(
            "UPDATE members SET name = ?, email = ?, phone = ?, address = ? "
            "WHERE member_id = ?",
            (name, email, phone, address, member_id),
        )

        connection.commit()
        print("SUCCESS: Member updated successfully.")

    except sqlite3.Error as error:
        print("ERROR: Database error:", error)

    finally:
        close_connection(connection)


# ---------- 5. Delete member ----------

def delete_member_from_user():
    print("\n--- Delete Member ---")

    id_text = input("Enter Member ID: ").strip()

    if not is_positive_integer(id_text):
        print("ERROR: Member ID must be a positive integer.")
        return

    member_id = int(id_text)

    connection = get_connection()

    if connection is None:
        print("ERROR: Could not connect to the database.")
        return

    try:
        cursor = connection.cursor()

        member = get_member_by_id(cursor, member_id)

        if member is None:
            print("ERROR: No member found with this Member ID.")
            return

        print("\nMember to delete:")
        show_member_details(member)

        if count_active_loans(cursor, member_id) > 0:
            print("ERROR: This member has active loans. Cannot be deleted.")
            return

        answer = input(
            "\nAre you sure you want to delete this member? (yes/no): "
        )

        if answer.strip().lower() != "yes":
            print("Deletion cancelled.")
            return

        # Delete the member's login account first
        cursor.execute(
            "DELETE FROM users WHERE member_id = ?",
            (member_id,)
        )

        # Then delete the member
        cursor.execute(
            "DELETE FROM members WHERE member_id = ?",
            (member_id,)
        )

        connection.commit()
        print("SUCCESS: Member and associated login account deleted successfully.")

    except sqlite3.IntegrityError:
        print("ERROR: This member has loan history, so it cannot be deleted.")

    except sqlite3.Error as error:
        print("ERROR: Database error:", error)

    finally:
        close_connection(connection)


# ---------- Functions for the GUI (they return data, they do not print) ----------

def get_all_members_rows():
    """Return all members for the table, or None if there is an error."""

    connection = get_connection()

    if connection is None:
        return None

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT member_id, name, email, phone, address, join_date "
            "FROM members ORDER BY member_id"
        )

        return cursor.fetchall()

    except sqlite3.Error:
        return None

    finally:
        close_connection(connection)


def search_members_rows(search_type, keyword):
    """Search by 'id', 'name', 'email' or 'phone'. Returns rows, or None on error."""

    keyword = keyword.strip()

    base = (
        "SELECT member_id, name, email, phone, address, join_date "
        "FROM members WHERE "
    )

    if search_type == "id":
        if not is_positive_integer(keyword):
            return []

        sql, value = base + "member_id = ?", int(keyword)

    elif search_type == "name":
        sql, value = base + "name LIKE ?", "%" + keyword + "%"

    elif search_type == "email":
        sql, value = base + "email LIKE ?", "%" + keyword + "%"

    elif search_type == "phone":
        sql, value = base + "phone LIKE ?", "%" + keyword + "%"

    else:
        return []

    connection = get_connection()

    if connection is None:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute(sql, (value,))
        return cursor.fetchall()

    except sqlite3.Error:
        return None

    finally:
        close_connection(connection)


def get_member_full(member_id):
    """Return all 6 fields of one member (or None)."""

    connection = get_connection()

    if connection is None:
        return None

    try:
        return get_member_by_id(connection.cursor(), member_id)

    except sqlite3.Error:
        return None

    finally:
        close_connection(connection)


def update_member(member_id, name, email, phone, address):
    """Check the data, then update one member. Returns (True/False, message)."""

    name = name.strip()
    email = email.strip().lower()
    phone = phone.strip()
    address = address.strip()

    if name == "":
        return False, "Name cannot be empty."

    if email == "":
        return False, "Email cannot be empty."

    if not is_valid_email(email):
        return False, "Email format is not valid. Example: name@gmail.com"

    if phone != "" and not is_valid_phone(phone):
        return False, "Phone must have 10 to 15 digits only."

    connection = get_connection()

    if connection is None:
        return False, "Could not connect to the database."

    try:
        cursor = connection.cursor()

        if get_member_by_id(cursor, member_id) is None:
            return False, "No member found with this Member ID."

        cursor.execute(
            "SELECT member_id FROM members WHERE email = ? AND member_id != ?",
            (email, member_id),
        )

        if cursor.fetchone() is not None:
            return False, "Another member already has this email."

        cursor.execute(
            "UPDATE members SET name = ?, email = ?, phone = ?, address = ? "
            "WHERE member_id = ?",
            (name, email, phone, address, member_id),
        )

        connection.commit()
        return True, "Member updated successfully."

    except sqlite3.Error as error:
        return False, f"Database error: {error}"

    finally:
        close_connection(connection)


def delete_member(member_id):
    """Delete one member and their login if there are no active or historical loans."""

    connection = get_connection()

    if connection is None:
        return False, "Could not connect to the database."

    try:
        cursor = connection.cursor()

        if get_member_by_id(cursor, member_id) is None:
            return False, "No member found with this Member ID."

        if count_active_loans(cursor, member_id) > 0:
            return False, "This member has active loans. Cannot be deleted."

        # Delete the member's login account first
        cursor.execute(
            "DELETE FROM users WHERE member_id = ?",
            (member_id,)
        )

        # Then delete the member
        cursor.execute(
            "DELETE FROM members WHERE member_id = ?",
            (member_id,)
        )

        connection.commit()

        return True, "Member and associated login account deleted successfully."

    except sqlite3.IntegrityError:
        return False, "This member has loan history, so it cannot be deleted."

    except sqlite3.Error as error:
        return False, f"Database error: {error}"

    finally:
        close_connection(connection)
