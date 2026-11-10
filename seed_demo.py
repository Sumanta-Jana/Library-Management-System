"""Optional: add three sample books (with cover pictures) to the library.

Usage:  python seed_demo.py
Safe to run more than once - books that already exist are skipped.
"""
import database

SAMPLE_BOOKS = [
    ("The Alchemist", "Paulo Coelho", "9780062315007", "Fiction", "HarperOne", 1988, 4,
     "A shepherd boy travels from Spain to Egypt in search of treasure — and learns to follow his dreams.",
     "images/book_covers/the_alchemist.jpg"),
    ("Rich Dad Poor Dad", "Robert T. Kiyosaki", "9781612680194", "Finance", "Plata Publishing", 1997, 3,
     "What the rich teach their kids about money that the poor and middle class do not.",
     "images/book_covers/richdad.jpg"),
    ("Atomic Habits", "James Clear", "9780735211292", "Self-help", "Avery", 2018, 5,
     "An easy and proven way to build good habits and break bad ones.",
     "images/book_covers/atomic_habits.jpg"),
]

database.create_tables()
connection = database.get_connection()
added = 0

for title, author, isbn, category, publisher, year, copies, description, cover in SAMPLE_BOOKS:
    if connection.execute("SELECT 1 FROM books WHERE isbn = ?", (isbn,)).fetchone():
        continue
    connection.execute(
        "INSERT INTO books (title, author, isbn, category, publisher, publication_year, "
        "total_copies, available_copies, description, cover_image) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (title, author, isbn, category, publisher, year, copies, copies, description, cover))
    added += 1

connection.commit()
database.close_connection(connection)
print(f"Added {added} sample book(s).")
