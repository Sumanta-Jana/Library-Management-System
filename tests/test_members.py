
import os
import tempfile
import unittest
from unittest.mock import patch

import database
import members


class TestMembers(unittest.TestCase):

    def setUp(self):
        # Create a temporary database
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.test_db_path = temp_file.name
        temp_file.close()

        # Use the temporary database
        self.db_patch = patch("database.DB_PATH", self.test_db_path)
        self.db_patch.start()

        database.create_tables()

    def tearDown(self):
        self.db_patch.stop()

        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def register_sample_member(self):
        return members.register_member(
            "Sumanta Jana",
            "sumanta@example.com",
            "9876543210",
            "Medinipur",
            ""
        )

    def test_register_member_successfully(self):
        success, message = self.register_sample_member()

        self.assertTrue(success)
        self.assertIn("registered successfully", message)

    def test_register_member_with_empty_name(self):
        success, message = members.register_member(
            "",
            "sumanta@example.com",
            "9876543210",
            "Medinipur",
            ""
        )

        self.assertFalse(success)
        self.assertIn("Name cannot be empty", message)

    def test_register_member_with_invalid_email(self):
        success, message = members.register_member(
            "Sumanta Jana",
            "invalid-email",
            "9876543210",
            "Medinipur",
            ""
        )

        self.assertFalse(success)
        self.assertIn("Email format is not valid", message)

    def test_register_member_with_invalid_phone(self):
        success, message = members.register_member(
            "Sumanta Jana",
            "sumanta@example.com",
            "12345",
            "Medinipur",
            ""
        )

        self.assertFalse(success)
        self.assertIn("Phone must have", message)

    def test_duplicate_email_is_rejected(self):
        self.register_sample_member()

        success, message = self.register_sample_member()

        self.assertFalse(success)
        self.assertIn("already exists", message)

    def test_register_member_with_future_date(self):
        success, message = members.register_member(
            "Test Member",
            "test@example.com",
            "",
            "Medinipur",
            "2099-01-01"
        )

        self.assertFalse(success)
        self.assertIn("Join date must be", message)

    def test_get_all_members(self):
        self.register_sample_member()

        result = members.get_all_members_rows()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], "Sumanta Jana")

    def test_search_member_by_name(self):
        self.register_sample_member()

        result = members.search_members_rows("name", "Sumanta")

        self.assertEqual(len(result), 1)

    def test_search_member_by_email(self):
        self.register_sample_member()

        result = members.search_members_rows(
            "email", "sumanta@example.com"
        )

        self.assertEqual(len(result), 1)

    def test_search_member_by_phone(self):
        self.register_sample_member()

        result = members.search_members_rows("phone", "9876543210")

        self.assertEqual(len(result), 1)

    def test_search_member_by_id(self):
        self.register_sample_member()

        member_id = members.get_all_members_rows()[0][0]

        result = members.search_members_rows("id", str(member_id))

        self.assertEqual(len(result), 1)

    def test_update_member_successfully(self):
        self.register_sample_member()

        member_id = members.get_all_members_rows()[0][0]

        success, message = members.update_member(
            member_id,
            "Updated Name",
            "updated@example.com",
            "9876543210",
            "Vadodara"
        )

        self.assertTrue(success)
        self.assertIn("updated successfully", message)

        updated_member = members.get_member_full(member_id)

        self.assertEqual(updated_member[1], "Updated Name")

    def test_update_nonexistent_member(self):
        success, message = members.update_member(
            9999,
            "Updated Name",
            "updated@example.com",
            "9876543210",
            "Vadodara"
        )

        self.assertFalse(success)
        self.assertIn("No member found", message)

    def test_delete_member_successfully(self):
        self.register_sample_member()

        member_id = members.get_all_members_rows()[0][0]

        success, message = members.delete_member(member_id)

        self.assertTrue(success)
        self.assertIn("deleted successfully", message)

        self.assertEqual(members.get_all_members_rows(), [])

    def test_delete_nonexistent_member(self):
        success, message = members.delete_member(9999)

        self.assertFalse(success)
        self.assertIn("No member found", message)


if __name__ == "__main__":
    unittest.main()
