# Project Overview

## 1. Project Name

Library Management System

## 2. What is this project?

This is a desktop application for a small library. It is made with **Python**, a **Tkinter** window and an **SQLite** database. The librarian uses it to keep records of books and members, to issue books, and to see reports.

All data is saved in one file: `library.db`.

## 3. Problem it solves

A library that uses paper registers has these problems:

- Records are slow to search.
- It is hard to know which books are available.
- It is hard to know who has a book and when it is due.
- Mistakes happen, for example the same ISBN written twice.

This project keeps all records in a database, checks the data before saving it, and shows the current numbers on a dashboard.

## 4. Who uses it?

| User | What the user does |
|---|---|
| Librarian (admin) | Adds books, registers members, issues books, and reads reports |

The code also has Admin and Member roles for login. The window does not have a login screen yet (see section 8).


## 5. Technologies

| Technology | Use |
|---|---|
| Python 3 | Programming language |
| Tkinter and ttk | Windows, buttons, tables |
| SQLite and the `sqlite3` module | Database |
| VS Code | Code editor |

No extra package is needed.

## 6. Files and their jobs

| File | Job |
|---|---|
| `main.py` | Starts the program. It prepares the database and opens the window |
| `database.py` | Connects to `library.db`, turns on foreign keys, creates the 4 tables |
| `books.py` | Add, view, search, update and delete books. Checks ISBN, copies and year |
| `members.py` | Register, view, search, update and delete members. Checks email and phone |
| `loans.py` | Issues a book (14 days). Also has the code for returning a book and the fine |
| `reports.py` | Reports and the numbers for the dashboard |
| `authentication.py` | Password hashing, login, creating the first admin, member accounts |
| `create_admin.py` | A small program to create the first admin account |
| `gui.py` | All Tkinter screens |
| `library.db` | The SQLite database file |

## 7. How the parts work together

```text
   gui.py  (what the user sees)
      |
      |  calls

      v
   books.py   members.py   loans.py   reports.py   authentication.py
      |
      |  all use
      v
   database.py  ---->  library.db
```

- The window (`gui.py`) does not write SQL. It only calls functions from the other files.
- All SQL is in `books.py`, `members.py`, `loans.py`, `reports.py` and `authentication.py`.
- All SQL uses `?` placeholders (parameterized queries). This protects against SQL injection.
- `database.py` is the only file that knows where `library.db` is.

### Example: issuing a book

1. The user types a Book ID and a Member ID and clicks **Issue Book**.
2. `gui.py` checks that both are positive numbers.
3. `gui.py` calls `issue_book()` in `loans.py`.
4. `loans.py` checks that the book exists, the member exists, and a copy is available.
5. `loans.py` sets the issue date to today and the due date to 14 days later.
6. `loans.py` saves the loan and reduces the available copies by 1, in **one transaction**. If one step fails, both are cancelled.
7. `gui.py` shows a message box with the loan details.

## 8. Current status

| Part | Status |
|---|---|
| Database with 4 tables | Working |
| Book management (code) | Working |
| Member management (code) | Working |
| Issue book (code) | Working |
| Return book and fine ₹5 per day (code) | Working in the code, **no screen in the window yet** |

| Reports (code) | Working |
| Login and password hashing (code) | Working in the code, **no login screen in the window yet** |
| Window: Dashboard, Books, Members, Issue Book, Reports | Available |
| Window: Login, Return Book, Fines, Member dashboard | **Not added yet** |

## 9. Rules used by the system

- A book is issued for **14 days**.
- The fine is **₹5 for each day** after the due date. There is no fine if the book is returned on or before the due date.
- A book that has an active loan cannot be deleted.
- A member who has an active loan cannot be deleted.
- A book with no available copy cannot be issued.
- ISBN and email must be unique.
- Passwords are never saved as plain text. They are saved as salted hashes.

## 10. Safety of the data

- `library.db` is never deleted or reset when the program starts. The program only creates a table if it is missing.
- Foreign keys are turned on, so a loan cannot point to a book or member that does not exist.
- Issue and return use transactions, so the loan and the copy count never become different.
