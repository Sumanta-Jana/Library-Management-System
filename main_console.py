from database import create_tables, test_connection
from books import (add_book_from_user, view_all_books, search_book_from_user,
                   update_book_from_user, delete_book_from_user)
from members import (register_member_from_user, view_all_members,
                     search_member_from_user, update_member_from_user,
                     delete_member_from_user)
from loans import issue_book_from_user
from reports import (available_books_report, issued_books_report,
                     overdue_books_report, member_history_report)


def show_menu():
    print("\n===== Library Management System =====")
    print("1.  Add New Book")
    print("2.  View All Books")
    print("3.  Search Book")
    print("4.  Update Book")
    print("5.  Delete Book")
    print("6.  Register New Member")
    print("7.  View All Members")
    print("8.  Search Member")
    print("9.  Update Member")
    print("10. Delete Member")
    print("11. Issue Book")
    print("12. Available Books Report")
    print("13. Issued Books Report")
    print("14. Overdue Books Report")
    print("15. Member Borrowing History")
    print("16. Exit")


def main():
    if not create_tables():
        print("Could not create tables. Stopping.")
        return
    if not test_connection():
        return

    # Each menu number is linked to one function
    actions = {
        "1": add_book_from_user,
        "2": view_all_books,
        "3": search_book_from_user,
        "4": update_book_from_user,
        "5": delete_book_from_user,
        "6": register_member_from_user,
        "7": view_all_members,
        "8": search_member_from_user,
        "9": update_member_from_user,
        "10": delete_member_from_user,
        "11": issue_book_from_user,
        "12": available_books_report,
        "13": issued_books_report,
        "14": overdue_books_report,
        "15": member_history_report,
    }

    while True:
        show_menu()
        choice = input("Enter your choice (1-16): ").strip()

        if choice == "16":
            print("Goodbye!")
            break
        elif choice in actions:
            try:
                actions[choice]()
            except Exception as error:
                # Last safety net: the program never crashes
                print("ERROR: Something went wrong:", error)
        else:
            print("Invalid choice. Please enter a number from 1 to 16.")


if __name__ == "__main__":
    main()