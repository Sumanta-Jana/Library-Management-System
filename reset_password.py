"""Reset the password of any account (admin or member).

Usage:  python reset_password.py
"""
from getpass import getpass

import authentication

username = input("Username: ").strip()
password = getpass("New password (min 6 characters): ")
confirm = getpass("Confirm new password: ")

if password != confirm:
    print("Error: passwords do not match.")
else:
    print(authentication.reset_password(username, password)[1])
