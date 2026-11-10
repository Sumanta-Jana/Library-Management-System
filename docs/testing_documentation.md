\# Testing Documentation



\## 1. Introduction



This document describes the testing approach for the Library Management System.



The purpose of testing is to check whether the application's modules work correctly and produce the expected results.



The project uses Python's built-in `unittest` framework for automated testing.



\## 2. Testing Objectives



\- Check database operations.

\- Verify user authentication.

\- Test book management operations.

\- Test member management operations.

\- Verify book issuing and returning.

\- Check overdue fine calculations.

\- Verify report generation.

\- Identify and fix errors.



\## 3. Testing Framework



\*\*Framework:\*\* Python unittest



The unittest framework allows developers to create and execute automated tests.



\## 4. Test Directory Structure



```text

tests/

├── \_\_init\_\_.py

├── test\_authentication.py

├── test\_books.py

├── test\_members.py

├── test\_loans.py

└── test\_reports.py

```



\## 5. Test Modules



\### 5.1 Authentication Tests



File: `test\_authentication.py`



These tests should check:



\- Admin account creation.

\- Login with valid credentials.

\- Login with invalid credentials.

\- Password verification.

\- Duplicate account handling.



\### 5.2 Book Tests



File: `test\_books.py`



These tests should check:



\- Adding a book.

\- Viewing book records.

\- Searching for books.

\- Updating book information.

\- Deleting a book.

\- Handling invalid book information.



\### 5.3 Member Tests



File: `test\_members.py`



These tests should check:



\- Adding a member.

\- Viewing member records.

\- Searching for members.

\- Updating member information.

\- Deleting a member.

\- Handling login accounts associated with members.



\### 5.4 Loan Tests



File: `test\_loans.py`



These tests should check:



\- Issuing an available book.

\- Handling unavailable books.

\- Calculating due dates.

\- Returning an issued book.

\- Calculating overdue fines.

\- Preventing duplicate returns.



\### 5.5 Report Tests



File: `test\_reports.py`



These tests should check:



\- Dashboard statistics.

\- Available books report.

\- Issued books report.

\- Overdue books report.

\- Member borrowing history.

\- Fine collection report.



\## 6. Test Database Safety



Automated tests should use a separate test database instead of the real `library.db`.



This helps protect actual library records during testing.



The test database should be created and cleaned up by the test setup and teardown procedures.



\## 7. Running Tests



Open PowerShell in the project directory.



Run all tests using:



```powershell

python -m unittest discover -s tests -v

```



Run an individual test module using:



```powershell

python -m unittest tests.test\_authentication -v

```



Replace `test\_authentication` with another test module name to run different tests.



\## 8. Test Results



Test results should be recorded after the automated tests have been created and executed.



| Test Module | Status |

|---|---|

| Authentication | Pending |

| Books | Pending |

| Members | Pending |

| Loans | Pending |

| Reports | Pending |



These statuses will be updated after actual test execution.



\## 9. Conclusion



Testing helps improve the reliability and correctness of the Library Management System. Automated tests will help identify problems and verify important application functions.

