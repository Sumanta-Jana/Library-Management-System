
import unittest
from unittest.mock import patch

from authentication import (
    hash_password,
    verify_password,
    check_new_credentials,
)


class TestAuthentication(unittest.TestCase):

    def test_password_hash_is_not_plain_text(self):
        password = "Library@123"
        hashed = hash_password(password)

        self.assertNotEqual(password, hashed)

    def test_correct_password(self):
        password = "Library@123"
        hashed = hash_password(password)

        self.assertTrue(verify_password(password, hashed))

    def test_wrong_password(self):
        hashed = hash_password("Library@123")

        self.assertFalse(verify_password("Wrong123", hashed))

    def test_invalid_password_hash(self):
        self.assertFalse(verify_password("Library@123", "invalid_hash"))

    def test_two_hashes_are_different(self):
        password = "Library@123"

        hash_one = hash_password(password)
        hash_two = hash_password(password)

        self.assertNotEqual(hash_one, hash_two)

    def test_valid_credentials(self):
        result = check_new_credentials("sumanta123", "Library@123")

        self.assertIsNone(result)

    def test_short_username(self):
        result = check_new_credentials("ab", "Library@123")

        self.assertIsNotNone(result)

    def test_short_password(self):
        result = check_new_credentials("sumanta123", "123")

        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
