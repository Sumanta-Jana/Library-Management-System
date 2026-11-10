\# User Guide



\## 1. Introduction



This guide explains how to use the Library Management System desktop application.



The application is developed using Python and Tkinter, with SQLite used to store library information.



\## 2. Starting the Application



1\. Open PowerShell.

2\. Navigate to the project folder.

3\. Run the following command:



```powershell

python main.py

```



The Tkinter application window should open.



\## 3. Dashboard



The Dashboard provides an overview of library activities.



It displays summary information about books, members, and borrowing activities according to the features implemented in the application.



\## 4. Book Management



The Books section is used to manage book records.



Available operations include:



\- Add a new book.

\- View book records.

\- Search for books.

\- Update book information.

\- Delete book records.

\- Clear form fields.



\## 5. Member Management



The Members section is used to manage library members.



Available operations include:



\- Add a new member.

\- View member records.

\- Search for members.

\- Update member information.

\- Delete member records.

\- Clear form fields.



\## 6. Issue Book



The Issue Book section is used to issue books to library members.



The loan management logic uses a standard loan period of 14 days.



\## 7. Return Book and Fine Calculation



The loan management module contains the logic for returning books.



If a book is returned after its due date, the application calculates a fine.



The fine rate is ₹5 per overdue day.



\## 8. Reports



The Reports section provides access to library reports.



The implemented report functions include:



\- Available Books Report

\- Issued Books Report

\- Overdue Books Report

\- Member History Report

\- Fine Collection Report



The availability of each report in the graphical interface depends on GUI integration.



\## 9. Database Records



The application stores information in an SQLite database.



The main database tables are:



\- Books

\- Members

\- Loans

\- Users



\## 10. Important Instructions



\- Enter valid information when adding books and members.

\- Check book availability before issuing a book.

\- Keep member information accurate.

\- Return books on or before their due dates to avoid fines.

\- Do not manually delete or reset the database file.



\## 11. Troubleshooting



If the application does not open, run it through PowerShell and check the displayed error message.



Do not delete the database to fix an application error.



\## 12. Conclusion



The Library Management System helps organize library operations such as book management, member management, issuing books, tracking returns, calculating fines, and generating reports.

