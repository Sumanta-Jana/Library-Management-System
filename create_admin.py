from getpass import getpass
import authentication

username = input("Enter Admin username: ").strip()
password = getpass("Enter Admin password: ")
confirm_password = getpass("Confirm Admin password: ")

if not username:
    print("Error: Username cannot be empty.")
elif password != confirm_password:
    print("Error: Passwords do not match.")
else:
    ok, message = authentication.create_admin(username, password)
    print(message)
