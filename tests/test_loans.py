
import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch

import database
import books
import members
import loans


class TestLoans(unittest.TestCase):

    def setUp(self):
        # Create a temporary database for each test
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.test_db_path = temp_file.name
        temp_file.close()

        self.db_patch = patch(
            "database.DB_PATH",
            self.test_db_path
        )
        self.db_patch.start()

        database.create_tables()

        # Add a sample book
        success, message = books.add_book(
            "Python Programming",
            "John Smith",
            "9780130000001",
            "Computer",
            "ABC Publisher",
            2024,
            3,
            3
        )

        self.assertTrue(success, message)

        # Add a sample member
        success, message = members.register_member(
            "Sumanta Jana",
            "sumanta@example.com",
            "9876543210",
            "Medinipur",
            date.today().strftime("%Y-%m-%d")
        )

        self.assertTrue(success, message)

        # Get book and member IDs
        self.book = books.get_all_books_rows()[0]
        self.member = members.get_all_members_rows()[0]

        self.book_id = self.book[0]
        self.member_id = self.member[0]

    def tearDown(self):
        self.db_patch.stop()

        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    # ==========================================
    # ISSUE BOOK TESTS
    # ==========================================

    def test_issue_book_successfully(self):
        success, result = loans.issue_book(
            self.book_id,
            self.member_id
        )

        self.assertTrue(success)
        self.assertEqual(result["title"], "Python Programming")
        self.assertEqual(result["member_name"], "Sumanta Jana")
        self.assertEqual(result["status"], "Issued")

        # Check available copies
        updated_book = books.get_book_full(self.book_id)

        # available_copies is at tuple index 8
        self.assertEqual(updated_book[8], 2)

    def test_issue_nonexistent_book(self):
        success, result = loans.issue_book(
            9999,
            self.member_id
        )

        self.assertFalse(success)
        self.assertIn("No book found", result)

    def test_issue_book_to_nonexistent_member(self):
        success, result = loans.issue_book(
            self.book_id,
            9999
        )

        self.assertFalse(success)
        self.assertIn("No member found", result)

    def test_issue_book_when_no_copies_available(self):
        # Set available copies to zero
        connection = database.get_connection()

        connection.execute(
            """
            UPDATE books
            SET available_copies = 0
            WHERE book_id = ?
            """,
            (self.book_id,)
        )

        connection.commit()
        database.close_connection(connection)

        success, result = loans.issue_book(
            self.book_id,
            self.member_id
        )

        self.assertFalse(success)
        self.assertEqual(result, "No copies available.")

    # ==========================================
    # CALCULATE FINE TESTS
    # ==========================================

    def test_calculate_fine_with_no_overdue_days(self):
        due_date = date.today()

        overdue_days, fine = loans.calculate_fine(
            due_date.strftime("%Y-%m-%d"),
            date.today()
        )

        self.assertEqual(overdue_days, 0)
        self.assertEqual(fine, 0)

    def test_calculate_fine_with_overdue_days(self):
        due_date = date.today() - timedelta(days=5)

        overdue_days, fine = loans.calculate_fine(
            due_date.strftime("%Y-%m-%d"),
            date.today()
        )

        self.assertEqual(overdue_days, 5)
        self.assertEqual(fine, 25)

    def test_calculate_fine_for_early_return(self):
        due_date = date.today() + timedelta(days=5)

        overdue_days, fine = loans.calculate_fine(
            due_date.strftime("%Y-%m-%d"),
            date.today()
        )

        self.assertEqual(overdue_days, 0)
        self.assertEqual(fine, 0)

    # ==========================================
    # FIND ACTIVE LOAN TESTS
    # ==========================================

    def test_find_active_loan_successfully(self):
        success, issued = loans.issue_book(
            self.book_id,
            self.member_id
        )

        self.assertTrue(success)

        success, result = loans.find_active_loan(
            issued["loan_id"]
        )

        self.assertTrue(success)
        self.assertEqual(result["title"], "Python Programming")
        self.assertEqual(result["member_name"], "Sumanta Jana")

    def test_find_nonexistent_loan(self):
        success, result = loans.find_active_loan(9999)

        self.assertFalse(success)
        self.assertIn("Loan not found", result)

    def test_find_already_returned_loan(self):
        success, issued = loans.issue_book(
            self.book_id,
            self.member_id
        )

        self.assertTrue(success)

        loans.return_book(issued["loan_id"])

        success, result = loans.find_active_loan(
            issued["loan_id"]
        )

        self.assertFalse(success)
        self.assertIn("already returned", result)

    # ==========================================
    # RETURN BOOK TESTS
    # ==========================================

    def test_return_book_successfully(self):
        success, issued = loans.issue_book(
            self.book_id,
            self.member_id
        )

        self.assertTrue(success)

        success, result = loans.return_book(
            issued["loan_id"]
        )

        self.assertTrue(success)
        self.assertEqual(result["fine"], 0)
        self.assertEqual(result["overdue_days"], 0)

        # Check available copies
        updated_book = books.get_book_full(self.book_id)

        # Available copies should return to 3
        self.assertEqual(updated_book[8], 3)

    def test_return_nonexistent_loan(self):
        success, result = loans.return_book(9999)

        self.assertFalse(success)
        self.assertIn("Loan not found", result)

    def test_return_same_book_twice(self):
        success, issued = loans.issue_book(
            self.book_id,
            self.member_id
        )

        self.assertTrue(success)

        first_success, first_result = loans.return_book(
            issued["loan_id"]
        )

        self.assertTrue(first_success)

        second_success, second_result = loans.return_book(
            issued["loan_id"]
        )

        self.assertFalse(second_success)
        self.assertIn("already returned", second_result)


if __name__ == "__main__":
    unittest.main()
