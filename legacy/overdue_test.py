
import sqlite3

LOAN_ID = 1  # Replace with your actual Loan ID

connection = sqlite3.connect("library.db")

connection.execute(
    """
    UPDATE loans
    SET issue_date = '2026-10-01',
        due_date = '2026-10-15'
    WHERE loan_id = ?
    """,
    (LOAN_ID,)
)

connection.commit()
connection.close()

print("Loan", LOAN_ID, "is now overdue!")
