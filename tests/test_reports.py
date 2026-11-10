
import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch

import database
import books
import members
import loans
import reports


class TestReports(unittest.TestCase):

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

        # Add sample book
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

        # Add sample member
        success, message = members.register_member(
            "Sumanta Jana",
            "sumanta@example.com",
            "9876543210",
            "Medinipur",
            date.today().strftime("%Y-%m-%d")
        )
        self.assertTrue(success, message)

        # Get IDs
        self.book = books.get_all_books_rows()[0]
        self.member = members.get_all_members_rows()[0]

        self.book_id = self.book[0]
        self.member_id = self.member[0]

    def tearDown(self):
        self.db_patch.stop()

        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    # Helper function to issue a book
    def issue_sample_book(self):
        success, result = loans.issue_book(
            self.book_id,
            self.member_id
        )

        self.assertTrue(success)
        return result["loan_id"]

    # Helper function to make a loan overdue
    def make_loan_overdue(self, loan_id):
        old_due_date = (
            date.today() - timedelta(days=5)
        ).strftime("%Y-%m-%d")

        connection = database.get_connection()

        connection.execute(
            """
            UPDATE loans
            SET due_date = ?
            WHERE loan_id = ?
            """,
            (old_due_date, loan_id)
        )

        connection.commit()
        database.close_connection(connection)

    # ==========================================
    # AVAILABLE BOOKS REPORT TESTS
    # ==========================================

    def test_available_books_rows(self):
        rows = reports.available_books_rows()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Python Programming")
        self.assertEqual(rows[0][5], 3)

    def test_available_books_rows_after_all_copies_issued(self):
        # Issue all three copies
        for _ in range(3):
            success, result = loans.issue_book(
                self.book_id,
                self.member_id
            )
            self.assertTrue(success)

        rows = reports.available_books_rows()

        self.assertEqual(len(rows), 0)

    # ==========================================
    # ISSUED BOOKS REPORT TESTS
    # ==========================================

    def test_issued_books_rows(self):
        self.issue_sample_book()

        rows = reports.issued_books_rows()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], "Python Programming")
        self.assertEqual(rows[0][4], "Sumanta Jana")
        self.assertEqual(rows[0][7], "Issued")

    def test_issued_books_rows_without_issued_books(self):
        rows = reports.issued_books_rows()

        self.assertEqual(len(rows), 0)

    # ==========================================
    # OVERDUE BOOKS REPORT TESTS
    # ==========================================

    def test_overdue_books_rows(self):
        loan_id = self.issue_sample_book()

        self.make_loan_overdue(loan_id)

        rows = reports.overdue_books_rows()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Python Programming")
        self.assertEqual(rows[0][2], "Sumanta Jana")
        self.assertEqual(rows[0][6], 5)

    def test_overdue_books_rows_without_overdue_books(self):
        self.issue_sample_book()

        rows = reports.overdue_books_rows()

        self.assertEqual(len(rows), 0)

    # ==========================================
    # MEMBER HISTORY REPORT TESTS
    # ==========================================

    def test_member_history_successfully(self):
        self.issue_sample_book()

        success, member_name, rows = (
            reports.member_history_rows(self.member_id)
        )

        self.assertTrue(success)
        self.assertEqual(member_name, "Sumanta Jana")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Python Programming")

    def test_member_history_for_nonexistent_member(self):
        success, message, rows = (
            reports.member_history_rows(9999)
        )

        self.assertFalse(success)
        self.assertIn("No member found", message)
        self.assertEqual(rows, [])

    def test_member_history_without_borrowing(self):
        success, member_name, rows = (
            reports.member_history_rows(self.member_id)
        )

        self.assertTrue(success)
        self.assertEqual(member_name, "Sumanta Jana")
        self.assertEqual(rows, [])

    # ==========================================
    # ADMIN DASHBOARD STATISTICS TESTS
    # ==========================================

    def test_dashboard_stats_without_loans(self):
        stats = reports.dashboard_stats()

        self.assertEqual(stats["total_books"], 1)
        self.assertEqual(stats["total_copies"], 3)
        self.assertEqual(stats["available_copies"], 3)
        self.assertEqual(stats["total_members"], 1)
        self.assertEqual(stats["total_fine"], 0)
        self.assertEqual(stats["issued_books"], 0)
        self.assertEqual(stats["overdue_books"], 0)

    def test_dashboard_stats_with_issued_book(self):
        self.issue_sample_book()

        stats = reports.dashboard_stats()

        self.assertEqual(stats["issued_books"], 1)
        self.assertEqual(stats["available_copies"], 2)

    def test_dashboard_stats_with_overdue_book(self):
        loan_id = self.issue_sample_book()

        self.make_loan_overdue(loan_id)

        stats = reports.dashboard_stats()

        self.assertEqual(stats["overdue_books"], 1)
        self.assertEqual(stats["issued_books"], 1)

    # ==========================================
    # FINE COLLECTION REPORT TESTS
    # ==========================================

    def test_fine_collection_rows(self):
        loan_id = self.issue_sample_book()

        self.make_loan_overdue(loan_id)

        success, result = loans.return_book(loan_id)

        self.assertTrue(success)
        self.assertEqual(result["fine"], 25)

        rows = reports.fine_collection_rows()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Python Programming")
        self.assertEqual(rows[0][2], "Sumanta Jana")
        self.assertEqual(rows[0][5], 25)

    def test_fine_collection_without_fines(self):
        loan_id = self.issue_sample_book()

        loans.return_book(loan_id)

        rows = reports.fine_collection_rows()

        self.assertEqual(len(rows), 0)

    # ==========================================
    # MEMBER ISSUED BOOKS TESTS
    # ==========================================

    def test_member_issued_rows(self):
        self.issue_sample_book()

        rows = reports.member_issued_rows(self.member_id)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Python Programming")
        self.assertEqual(rows[0][5], 0)
        self.assertEqual(rows[0][6], "₹0.00")

    def test_member_issued_rows_with_overdue_book(self):
        loan_id = self.issue_sample_book()

        self.make_loan_overdue(loan_id)

        rows = reports.member_issued_rows(self.member_id)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][5], 5)
        self.assertEqual(rows[0][6], "₹25.00")

    def test_member_issued_rows_without_books(self):
        rows = reports.member_issued_rows(self.member_id)

        self.assertEqual(len(rows), 0)

    # ==========================================
    # MEMBER DASHBOARD TESTS
    # ==========================================

    def test_member_dashboard_data(self):
        self.issue_sample_book()

        result = reports.member_dashboard_data(self.member_id)

        self.assertIsNotNone(result)

        stats, rows = result

        self.assertEqual(stats["borrowed"], 1)
        self.assertEqual(stats["overdue"], 0)
        self.assertEqual(stats["pending_fine"], 0)
        self.assertEqual(len(rows), 1)

    def test_member_dashboard_with_overdue_book(self):
        loan_id = self.issue_sample_book()

        self.make_loan_overdue(loan_id)

        result = reports.member_dashboard_data(self.member_id)

        stats, rows = result

        self.assertEqual(stats["borrowed"], 1)
        self.assertEqual(stats["overdue"], 1)
        self.assertEqual(stats["pending_fine"], 25)

    def test_member_dashboard_without_borrowed_books(self):
        result = reports.member_dashboard_data(self.member_id)

        stats, rows = result

        self.assertEqual(stats["borrowed"], 0)
        self.assertEqual(stats["overdue"], 0)
        self.assertEqual(stats["pending_fine"], 0)
        self.assertEqual(rows, [])

    # ==========================================
    # RECENT ISSUES TESTS
    # ==========================================

    def test_recent_issues_rows(self):
        self.issue_sample_book()

        rows = reports.recent_issues_rows()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Python Programming")
        self.assertEqual(rows[0][2], "Sumanta Jana")

    def test_recent_issues_with_custom_limit(self):
        self.issue_sample_book()
        self.issue_sample_book()

        rows = reports.recent_issues_rows(limit=1)

        self.assertEqual(len(rows), 1)

    # ==========================================
    # RECENT MEMBERS TESTS
    # ==========================================

    def test_recent_members_rows(self):
        rows = reports.recent_members_rows()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Sumanta Jana")
        self.assertEqual(rows[0][2], "sumanta@example.com")

    def test_recent_members_with_custom_limit(self):
        # Add a second member
        success, message = members.register_member(
            "Rahul Sharma",
            "rahul@example.com",
            "9876543211",
            "Kolkata",
            date.today().strftime("%Y-%m-%d")
        )

        self.assertTrue(success, message)

        rows = reports.recent_members_rows(limit=1)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Rahul Sharma")


if __name__ == "__main__":
    unittest.main()
