
import members
import hashlib
import hmac
import os
import re
import sqlite3
from datetime import datetime
from database import get_connection, close_connection


ITERATIONS = 200_000
USERNAME_PATTERN = r"^[A-Za-z0-9_]{3,20}$"
MIN_PASSWORD_LENGTH = 6


# ---------- Password hashing ----------

def hash_password(password):
    """Create a secure salted password hash."""
    salt = os.urandom(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS
    )

    return f"{ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    """Verify the entered password."""
    try:
        rounds, salt_hex, hash_hex = stored_hash.split("$")

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(rounds)
        )

        return hmac.compare_digest(digest.hex(), hash_hex)

    except (ValueError, AttributeError):
        return False


# ---------- Credential validation ----------

def check_new_credentials(username, password):

    if not re.match(USERNAME_PATTERN, username):
        return "Username must be 3 to 20 letters, numbers or underscore."

    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

    return None


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------- Admin account ----------

def admin_exists():
    """Check whether an admin account already exists."""

    connection = get_connection()

    if connection is None:
        return True

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'Admin'"
        )

        return cursor.fetchone()[0] > 0

    except sqlite3.Error:
        return True

    finally:
        close_connection(connection)


def create_admin(username, password):
    """Create the first admin account."""

    username = username.strip().lower()

    error = check_new_credentials(username, password)

    if error:
        return False, error

    if admin_exists():
        return False, "An admin account already exists."

    connection = get_connection()

    if connection is None:
        return False, "Could not connect to the database."

    try:
        connection.execute(
            """
            INSERT INTO users
            (username, password_hash, role, member_id, created_at)
            VALUES (?, ?, 'Admin', NULL, ?)
            """,
            (
                username,
                hash_password(password),
                now_text()
            )
        )

        connection.commit()

        return True, "Admin account created. You can log in now."

    except sqlite3.IntegrityError:
        return False, "This username is already taken."

    except sqlite3.Error as error:
        return False, f"Database error: {error}"

    finally:
        close_connection(connection)


# ---------- Member account registration ----------

def register_member_account(member_id, email, username, password):

    username = username.strip().lower()
    email = email.strip().lower()

    error = check_new_credentials(username, password)

    if error:
        return False, error

    connection = get_connection()

    if connection is None:
        return False, "Could not connect to the database."

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT email FROM members WHERE member_id = ?",
            (member_id,)
        )

        row = cursor.fetchone()

        if row is None:
            return False, (
                "No member found with this Member ID. "
                "Ask the admin to register you first."
            )

        if row[0] is None or row[0].lower() != email:
            return False, (
                "This email does not match the registered email "
                "of the member."
            )

        cursor.execute(
            "SELECT user_id FROM users WHERE member_id = ?",
            (member_id,)
        )

        if cursor.fetchone() is not None:
            return False, "This member already has a login account."

        cursor.execute(
            """
            INSERT INTO users
            (username, password_hash, role, member_id, created_at)
            VALUES (?, ?, 'Member', ?, ?)
            """,
            (
                username,
                hash_password(password),
                member_id,
                now_text()
            )
        )

        connection.commit()

        return True, "Account created. You can log in now."

    except sqlite3.IntegrityError:
        return False, "This username is already taken."

    except sqlite3.Error as error:
        return False, f"Database error: {error}"

    finally:
        close_connection(connection)


# ---------- Login ----------

def login(username, password):
    """Authenticate a user."""

    username = username.strip().lower()

    if username == "" or password == "":
        return False, "Please enter username and password."

    connection = get_connection()

    if connection is None:
        return False, "Could not connect to the database."

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT user_id, username, password_hash, role, member_id
            FROM users
            WHERE username = ?
            """,
            (username,)
        )

        row = cursor.fetchone()

        if row is None or not verify_password(password, row[2]):
            return False, "Incorrect username or password."

        return True, {
            "user_id": row[0],
            "username": row[1],
            "role": row[3],
            "member_id": row[4]
        }

    except sqlite3.Error as error:
        return False, f"Database error: {error}"

    finally:
        close_connection(connection)


# ---------- Get user by ID ----------

def get_user_by_id(user_id):
    """Get user details without returning the password hash."""

    connection = get_connection()

    if connection is None:
        return None

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT user_id, username, role, member_id
            FROM users
            WHERE user_id = ?
            """,
            (user_id,)
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "user_id": row[0],
            "username": row[1],
            "role": row[2],
            "member_id": row[3]
        }

    except sqlite3.Error:
        return None

    finally:
        close_connection(connection)


# ---------- Public member registration ----------

def register_new_member(name, username, email, phone, address, password):
    """
    Create a member record and login account together.
    Public registration always creates a Member account.
    """

    name = name.strip()
    username = username.strip().lower()
    email = email.strip().lower()
    phone = phone.strip()
    address = address.strip()

    if name == "":
        return False, "Full name cannot be empty."

    if not members.is_valid_email(email):
        return False, "Email format is not valid. Example: name@gmail.com"

    if phone != "" and not members.is_valid_phone(phone):
        return False, "Phone must have 10 to 15 digits only."

    error = check_new_credentials(username, password)

    if error:
        return False, error

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
            return False, (
                "This email is already registered. "
                "Please contact the library admin."
            )

        cursor.execute(
            "SELECT user_id FROM users WHERE username = ?",
            (username,)
        )

        if cursor.fetchone() is not None:
            return False, "This username is already taken."

        join_date = datetime.now().strftime("%Y-%m-%d")

        cursor.execute(
            """
            INSERT INTO members
            (name, email, phone, address, join_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, email, phone, address, join_date)
        )

        member_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO users
            (username, password_hash, role, member_id, created_at)
            VALUES (?, ?, 'Member', ?, ?)
            """,
            (
                username,
                hash_password(password),
                member_id,
                now_text()
            )
        )

        connection.commit()

        return True, "Registration successful. You can log in now."

    except sqlite3.IntegrityError:
        connection.rollback()
        return False, "This username or email is already registered."

    except sqlite3.Error as error:
        connection.rollback()
        return False, f"Database error: {error}"

    finally:
        close_connection(connection)


# ---------- Change / reset password ----------

def change_password(user_id, old_password, new_password):
    """Let a logged-in user change their own password."""

    if len(new_password) < MIN_PASSWORD_LENGTH:
        return False, f"New password must be at least {MIN_PASSWORD_LENGTH} characters."

    connection = get_connection()

    if connection is None:
        return False, "Could not connect to the database."

    try:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        if row is None or not verify_password(old_password, row[0]):
            return False, "Your current password is not correct."

        connection.execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (hash_password(new_password), user_id)
        )
        connection.commit()

        return True, "Password changed successfully."

    except sqlite3.Error as error:
        return False, f"Database error: {error}"

    finally:
        close_connection(connection)


def reset_password(username, new_password):
    """Set a new password for any account (used by reset_password.py)."""

    username = username.strip().lower()

    if len(new_password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

    connection = get_connection()

    if connection is None:
        return False, "Could not connect to the database."

    try:
        cursor = connection.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (hash_password(new_password), username)
        )
        connection.commit()

        if cursor.rowcount == 0:
            return False, "No account with this username."

        return True, f"Password for '{username}' has been reset."

    except sqlite3.Error as error:
        return False, f"Database error: {error}"

    finally:
        close_connection(connection)
