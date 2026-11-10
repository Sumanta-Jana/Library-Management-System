
import os
import sqlite3

# Keep library.db in the same folder as this file
# (set the LIBRARY_DB environment variable to use a different file)
DB_PATH = os.environ.get("LIBRARY_DB") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "library.db"
)


def get_connection(dict_rows=False):
    """Open a connection to library.db and enable foreign keys.

    dict_rows=True returns rows that can be read by column name
    (row["title"]); the default keeps plain tuples so that the older
    console / desktop modules keep working unchanged.
    """
    try:
        connection = sqlite3.connect(DB_PATH, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.execute("PRAGMA journal_mode = WAL;")
        if dict_rows:
            connection.row_factory = sqlite3.Row
        return connection

    except sqlite3.Error as error:
        print("Database connection error:", error)
        return None


def close_connection(connection):
    """Close the database connection safely."""
    if connection is not None:
        connection.close()


def add_column_if_missing(cursor, table, column, definition):
    """Add a column to an existing table only when it is not there yet."""
    cursor.execute(f"PRAGMA table_info({table})")
    if column not in [row[1] for row in cursor.fetchall()]:
        cursor.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


def repair_data():
    """Fix common data problems so every table agrees with every other.

    1. available_copies is recalculated as total_copies - active loans.
    2. join_date values like 2026-10-4 become 2026-10-04.
    Safe to run any number of times.
    """
    connection = get_connection()
    if connection is None:
        return False

    try:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE books
            SET available_copies = MAX(0, total_copies - (
                SELECT COUNT(*) FROM loans
                WHERE loans.book_id = books.book_id
                  AND loans.return_date IS NULL
            ))
        """)

        cursor.execute("SELECT member_id, join_date FROM members")
        for member_id, join_date in cursor.fetchall():
            if not join_date:
                continue
            parts = join_date.split("-")
            if len(parts) == 3 and all(p.isdigit() for p in parts):
                fixed = f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                if fixed != join_date:
                    cursor.execute(
                        "UPDATE members SET join_date = ? "
                        "WHERE member_id = ?", (fixed, member_id))

        connection.commit()
        return True

    except sqlite3.Error as error:
        print("Data repair error:", error)
        return False

    finally:
        close_connection(connection)


def create_tables():
    """Create all four database tables if they do not exist."""

    connection = get_connection()

    if connection is None:
        return False

    try:
        cursor = connection.cursor()

        # 1. Books table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                book_id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title            TEXT NOT NULL,
                author           TEXT NOT NULL,
                isbn             TEXT UNIQUE,
                category         TEXT,
                publisher        TEXT,
                publication_year INTEGER,
                total_copies     INTEGER NOT NULL,
                available_copies INTEGER NOT NULL
            );
        """)

        # 2. Members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                member_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name      TEXT NOT NULL,
                email     TEXT UNIQUE,
                phone     TEXT,
                address   TEXT,
                join_date TEXT
            );
        """)

        # 3. Loans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loans (
                loan_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id     INTEGER NOT NULL,
                member_id   INTEGER NOT NULL,
                issue_date  TEXT NOT NULL,
                due_date    TEXT NOT NULL,
                return_date TEXT,
                fine_amount REAL DEFAULT 0,
                status      TEXT NOT NULL,
                FOREIGN KEY (book_id) REFERENCES books(book_id),
                FOREIGN KEY (member_id) REFERENCES members(member_id)
            );
        """)

        # 4. Users table (Admin and Member login)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL
                              CHECK (role IN ('Admin', 'Member')),
                member_id     INTEGER,
                created_at    TEXT NOT NULL,
                FOREIGN KEY (member_id)
                    REFERENCES members(member_id)
            );
        """)

        # 5. API keys table (for the REST API)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                key_hash   TEXT NOT NULL UNIQUE,
                key_prefix TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_used  TEXT,
                active     INTEGER NOT NULL DEFAULT 1
            );
        """)

        # Upgrade older databases with the newer optional columns
        add_column_if_missing(cursor, "loans", "renewals",
                              "INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(cursor, "books", "cover_image", "TEXT")
        add_column_if_missing(cursor, "books", "description", "TEXT")

        # Helpful indexes for fast searching
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loans_member "
                       "ON loans(member_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loans_book "
                       "ON loans(book_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loans_status "
                       "ON loans(status)")

        # Save all table creation changes
        connection.commit()

        print("All database tables created successfully.")
        return True

    except sqlite3.Error as error:
        print("Error creating tables:", error)
        return False

    finally:
        close_connection(connection)


def test_connection():
    """Check database connection and foreign key support."""

    connection = get_connection()

    if connection is None:
        print("Connection test FAILED.")
        return False

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT sqlite_version();")
        print("SQLite version:", cursor.fetchone()[0])

        cursor.execute("PRAGMA foreign_keys;")
        status = cursor.fetchone()[0]

        print(
            "Foreign keys:",
            "ON" if status == 1 else "OFF"
        )

        print("Connection test PASSED.")
        return True

    except sqlite3.Error as error:
        print("Connection test FAILED:", error)
        return False

    finally:
        close_connection(connection)


def is_positive_integer(text):
    """Check whether the input is a positive whole number."""

    if text is None:
        return False

    text = str(text).strip()

    return (
        text.isascii()
        and text.isdigit()
        and int(text) > 0
    )


if __name__ == "__main__":
    print("Testing Library Management System Database...")

    if create_tables():
        test_connection()
