
import os
import tempfile
import unittest
from unittest.mock import patch

import database
import books


class TestBooks(unittest.TestCase):

    def setUp(self):
        # Create a separate temporary database for testing
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.test_db_path = temp_file.name
        temp_file.close()

        # Redirect database connections to the temporary database
        self.db_patch = patch(
            "database.DB_PATH",
            self.test_db_path
        )
        self.db_patch.start()

        database.create_tables()

    def tearDown(self):
        # Restore the original database path
        self.db_patch.stop()

        # Delete the temporary test database
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def add_sample_book(self):
        return books.add_book(
            "Python Basics",
            "John Smith",
            "1234567890",
            "Programming",
            "ABC Publisher",
            "2024",
            5,
            5
        )

    def test_add_book_successfully(self):
        success, message = self.add_sample_book()

        self.assertTrue(success)
        self.assertIn("Book added successfully", message)

    def test_add_book_with_empty_title(self):
        success, message = books.add_book(
            "", "John Smith", "1234567890",
            "Programming", "ABC Publisher",
            "2024", 5, 5
        )

        self.assertFalse(success)
        self.assertIn("cannot be empty", message)

    def test_add_book_with_invalid_isbn(self):
        success, message = books.add_book(
            "Python Basics", "John Smith", "12345",
            "Programming", "ABC Publisher",
            "2024", 5, 5
        )

        self.assertFalse(success)
        self.assertIn("ISBN must be", message)

    def test_duplicate_isbn_is_rejected(self):
        self.add_sample_book()

        success, message = self.add_sample_book()

        self.assertFalse(success)
        self.assertIn("already exists", message)

    def test_invalid_available_copies(self):
        success, message = books.add_book(
            "Python Basics", "John Smith", "1234567890",
            "Programming", "ABC Publisher",
            "2024", 5, 8
        )

        self.assertFalse(success)
        self.assertIn("Available copies", message)

    def test_get_all_books(self):
        self.add_sample_book()

        result = books.get_all_books_rows()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], "Python Basics")

    def test_search_book_by_title(self):
        self.add_sample_book()

        result = books.search_books_rows("title", "Python")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], "Python Basics")

    def test_search_book_by_author(self):
        self.add_sample_book()

        result = books.search_books_rows("author", "John")

        self.assertEqual(len(result), 1)

    def test_update_book_successfully(self):
        self.add_sample_book()

        book_rows = books.get_all_books_rows()
        book_id = book_rows[0][0]

        success, message = books.update_book(
            book_id,
            "Advanced Python",
            "John Smith",
            "1234567890",
            "Programming",
            "ABC Publisher",
            "2025",
            5,
            5
        )

        self.assertTrue(success)
        self.assertIn("updated successfully", message)

        updated_book = books.get_book_full(book_id)
        self.assertEqual(updated_book[1], "Advanced Python")

    def test_update_nonexistent_book(self):
        success, message = books.update_book(
            9999,
            "Advanced Python",
            "John Smith",
            "1234567890",
            "Programming",
            "ABC Publisher",
            "2025",
            5,
            5
        )

        self.assertFalse(success)
        self.assertIn("No book found", message)

    def test_delete_book_successfully(self):
        self.add_sample_book()

        book_id = books.get_all_books_rows()[0][0]

        success, message = books.delete_book(book_id)

        self.assertTrue(success)
        self.assertIn("deleted successfully", message)

        self.assertEqual(books.get_all_books_rows(), [])

    def test_delete_nonexistent_book(self):
        success, message = books.delete_book(9999)

        self.assertFalse(success)
        self.assertIn("No book found", message)


if __name__ == "__main__":
    unittest.main()
