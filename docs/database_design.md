\# Database Design



\## 1. Introduction



The Library Management System uses SQLite as its database management system.



The database stores information about books, library members, loans, and user login accounts.



The database file is named `library.db`.



\## 2. Database Tables



The database contains four main tables:



1\. books

2\. members

3\. loans

4\. users



\## 3. Books Table



The `books` table stores information about books available in the library.



| Column | Data Type | Description |

|---|---|---|

| book\_id | INTEGER | Primary key; automatically generated |

| title | TEXT | Book title |

| author | TEXT | Book author |

| isbn | TEXT | Unique book ISBN |

| category | TEXT | Book category |

| publisher | TEXT | Publisher name |

| publication\_year | INTEGER | Year of publication |

| total\_copies | INTEGER | Total number of copies |

| available\_copies | INTEGER | Number of available copies |



\## 4. Members Table



The `members` table stores library member details.



| Column | Data Type | Description |

|---|---|---|

| member\_id | INTEGER | Primary key; automatically generated |

| name | TEXT | Member name |

| email | TEXT | Unique email address |

| phone | TEXT | Contact number |

| address | TEXT | Member address |

| join\_date | TEXT | Membership joining date |



\## 5. Loans Table



The `loans` table stores book issue and return information.



| Column | Data Type | Description |

|---|---|---|

| loan\_id | INTEGER | Primary key; automatically generated |

| book\_id | INTEGER | Foreign key referencing books |

| member\_id | INTEGER | Foreign key referencing members |

| issue\_date | TEXT | Date the book was issued |

| due\_date | TEXT | Expected return date |

| return\_date | TEXT | Actual return date |

| fine\_amount | REAL | Fine amount |

| status | TEXT | Loan status |



The `book\_id` and `member\_id` columns connect the loans table to the books and members tables.



\## 6. Users Table



The `users` table stores login account information.



| Column | Data Type | Description |

|---|---|---|

| user\_id | INTEGER | Primary key; automatically generated |

| username | TEXT | Unique login username |

| password\_hash | TEXT | Hashed password |

| role | TEXT | Admin or Member |

| member\_id | INTEGER | Associated member ID, when applicable |

| created\_at | TEXT | Account creation date and time |



The role column accepts only `Admin` and `Member`.



\## 7. Database Relationships



The database uses foreign keys to connect related records.



\- A loan references one book through `book\_id`.

\- A loan references one member through `member\_id`.

\- A user account can reference a member through `member\_id`.



\### Relationship overview



```text

BOOKS

&#x20; |

&#x20; | book\_id

&#x20; |

&#x20; +---------- LOANS

&#x20;                |

&#x20;                | member\_id

&#x20;                |

&#x20;             MEMBERS

&#x20;                |

&#x20;                | member\_id

&#x20;                |

&#x20;              USERS

```



\## 8. Primary Keys



Each main table has an automatically generated primary key:



\- books: book\_id

\- members: member\_id

\- loans: loan\_id

\- users: user\_id



Primary keys uniquely identify records.



\## 9. Foreign Keys



Foreign keys maintain relationships between database tables.



The application enables SQLite foreign-key support using:



```python

connection.execute("PRAGMA foreign\_keys = ON;")

```



\## 10. Data Security



The users table stores `password\_hash` instead of storing the original password as plain text.



This helps protect user login credentials.



\## 11. Conclusion



The SQLite database provides organized storage for the Library Management System. Its primary keys and foreign keys connect books, members, loans, and user accounts.

