\# Library Management System – Project Report



\*\*Project Title:\*\* Library Management System



\*\*Developed By:\*\* Sumanta Jana



\*\*Course:\*\* B.Tech Computer Science and Engineering (AI \& ML)



\*\*Programming Language:\*\* Python



\## 1. Abstract



The Library Management System is a desktop-based application developed using Python, Tkinter, and SQLite.



The main purpose of this project is to organize library activities such as book management, member management, book issuing, book returning, fine calculation, and report generation.



The application uses SQLite to store information and Tkinter to provide a graphical user interface.



\## 2. Introduction



Libraries manage many books and members. Maintaining all records manually can be difficult and time-consuming.



The Library Management System provides a computerized approach to managing library information.



It helps organize records and makes common library operations easier.



\## 3. Problem Statement



Manual library management can create several problems:



\- Difficulty maintaining book records.

\- Difficulty tracking issued books.

\- Time-consuming member record management.

\- Problems identifying overdue books.

\- Difficulty calculating fines.

\- Difficulty preparing library reports.



This project aims to address these problems through a desktop application.



\## 4. Objectives



The main objectives are:



1\. Develop a desktop-based library management application.

2\. Manage book records.

3\. Maintain member information.

4\. Provide user authentication.

5\. Manage book issuing and returning.

6\. Calculate overdue fines.

7\. Generate library reports.

8\. Store records using SQLite.



\## 5. Technologies Used



| Technology | Purpose |

|---|---|

| Python | Main programming language |

| Tkinter | Graphical user interface |

| SQLite | Database management |

| hashlib | Password hashing |

| unittest | Automated testing |



\## 6. System Modules



\### 6.1 Database Module



Manages database connections and creates the required database tables.



\### 6.2 Authentication Module



Handles user account creation, password hashing, and login verification.



\### 6.3 Book Management Module



Provides operations for adding, viewing, searching, updating, and deleting books.



\### 6.4 Member Management Module



Maintains library member records.



\### 6.5 Loan Management Module



Handles book issuing, returning, due dates, and fine calculation.



\### 6.6 Reports Module



Provides reports about available books, issued books, overdue books, member history, and fines.



\### 6.7 GUI Module



Provides the graphical desktop interface using Tkinter.



\## 7. Database Design



The application uses SQLite with four main tables:



\- `books`

\- `members`

\- `loans`

\- `users`



These tables store book details, member information, loan records, and user login details.



\## 8. Loan and Fine Calculation



The application uses the following rules:



\- Standard loan period: 14 days.

\- Fine rate: ₹5 per overdue day.



The fine depends on the number of days a book is returned after its due date.



\## 9. Testing



The project uses Python's `unittest` framework for automated testing.



Separate test modules are planned for authentication, books, members, loans, and reports.



Actual test results will be added after the test suite is implemented and executed.



\## 10. Advantages



\- Organized library records.

\- Easier book management.

\- Faster member record handling.

\- Book issue and return tracking.

\- Overdue fine calculation.

\- Report generation.

\- Local database storage.



\## 11. Future Scope



Possible future improvements include:



\- Complete role-based admin and member interfaces.

\- Integrated login screen.

\- Dedicated book return screen.

\- Dedicated fine management screen.

\- Improved dashboard.

\- Book cover images.

\- Advanced search and filtering.

\- Database backup and restore.



\## 12. Conclusion



The Library Management System demonstrates the use of Python, Tkinter, and SQLite to develop a desktop application.



It provides a foundation for managing library records, book loans, fines, and reports.



Further development and testing can improve its functionality and usability.



\## 13. Author



\*\*Sumanta Jana\*\*



B.Tech Computer Science and Engineering (AI \& ML)



Medinipur, West Bengal, India

