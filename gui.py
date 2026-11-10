
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date, timedelta

import authentication
import books
import members
import loans
import reports

from database import is_positive_integer


# ============================================================
# COLORS
# ============================================================

BG = "#f4f6fb"
SIDEBAR = "#1f2a44"
ACCENT = "#3b6fd4"
CARD = "#ffffff"


# ============================================================
# REUSABLE TABLE HELPERS
# ============================================================

def setup_table(tree, columns, widths):
    tree["columns"] = columns

    for column, width in zip(columns, widths):
        tree.heading(column, text=column)
        tree.column(
            column,
            width=width,
            anchor="w",
            stretch=False
        )


def make_table(parent, columns, widths, height=10):

    frame = ttk.Frame(parent)

    tree = ttk.Treeview(
        frame,
        show="headings",
        height=height
    )

    setup_table(tree, columns, widths)

    vertical = ttk.Scrollbar(
        frame,
        orient="vertical",
        command=tree.yview
    )

    horizontal = ttk.Scrollbar(
        frame,
        orient="horizontal",
        command=tree.xview
    )

    tree.configure(
        yscrollcommand=vertical.set,
        xscrollcommand=horizontal.set
    )

    tree.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")

    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    return frame, tree


def fill_table(tree, rows):

    tree.delete(*tree.get_children())

    for row in rows:
        tree.insert(
            "",
            "end",
            values=[
                "-" if value is None or value == "" else value
                for value in row
            ]
        )


# ============================================================
# COMMON FORM PAGE
# ============================================================

class FormPage(ttk.Frame):

    TITLE = ""
    FIELDS = []
    COLUMNS = []
    WIDTHS = []
    BUTTONS = []
    SEARCH_OPTIONS = []
    SEARCH_BUTTON = "Search"

    def __init__(self, parent):

        super().__init__(parent)

        ttk.Label(
            self,
            text=self.TITLE,
            style="Title.TLabel"
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 4)
        )

        form = ttk.LabelFrame(
            self,
            text="Details"
        )

        form.pack(
            fill="x",
            padx=15,
            pady=4
        )

        self.entries = {}

        for index, name in enumerate(self.FIELDS):

            row, column = divmod(index, 3)

            ttk.Label(
                form,
                text=name
            ).grid(
                row=row,
                column=column * 2,
                sticky="e",
                padx=(10, 4),
                pady=4
            )

            entry = ttk.Entry(
                form,
                width=24
            )

            entry.grid(
                row=row,
                column=column * 2 + 1,
                padx=(0, 10),
                pady=4
            )

            self.entries[name] = entry

        self.entries[self.FIELDS[0]].configure(
            state="readonly"
        )

        button_row = ttk.Frame(self)

        button_row.pack(
            fill="x",
            padx=15,
            pady=4
        )

        for text, method_name in self.BUTTONS:

            ttk.Button(
                button_row,
                text=text,
                command=getattr(self, method_name)
            ).pack(
                side="left",
                padx=(0, 6)
            )

        search_row = ttk.Frame(self)

        search_row.pack(
            fill="x",
            padx=15,
            pady=4
        )

        ttk.Label(
            search_row,
            text="Search by:"
        ).pack(side="left")

        self.search_type = ttk.Combobox(
            search_row,
            values=self.SEARCH_OPTIONS,
            state="readonly",
            width=12
        )

        self.search_type.current(0)

        self.search_type.pack(
            side="left",
            padx=6
        )

        self.search_text = ttk.Entry(
            search_row,
            width=30
        )

        self.search_text.pack(
            side="left",
            padx=6
        )

        ttk.Button(
            search_row,
            text=self.SEARCH_BUTTON,
            command=self.search_records
        ).pack(side="left")

        table_frame, self.tree = make_table(
            self,
            self.COLUMNS,
            self.WIDTHS
        )

        table_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(4, 12)
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.on_select
        )

    def get_values(self):

        return {
            name: self.entries[name].get().strip()
            for name in self.FIELDS
        }

    def set_values(self, values):

        for name, value in zip(self.FIELDS, values):

            entry = self.entries[name]

            entry.configure(state="normal")
            entry.delete(0, "end")

            entry.insert(
                0,
                "" if value is None else str(value)
            )

        self.entries[self.FIELDS[0]].configure(
            state="readonly"
        )

    def clear_fields(self):

        self.set_values([""] * len(self.FIELDS))

        self.tree.selection_remove(
            self.tree.selection()
        )

    def selected_id(self):

        text = self.entries[self.FIELDS[0]].get().strip()

        if not is_positive_integer(text):

            messagebox.showwarning(
                "Select a record",
                "Please click a row in the table first."
            )

            return None

        return int(text)

    def show_rows(self, rows):

        if rows is None:

            messagebox.showerror(
                "Database error",
                "Could not read the database."
            )

            return False

        fill_table(self.tree, rows)

        return True

    def on_show(self):
        self.refresh()

    def on_select(self, event):

        selection = self.tree.selection()

        if selection:

            record_id = self.tree.item(
                selection[0]
            )["values"][0]

            self.load_record(int(record_id))

    def show_result(self, ok, message):

        if ok:

            messagebox.showinfo(
                "Success",
                message
            )

            self.clear_fields()
            self.refresh()

        else:

            messagebox.showerror(
                "Error",
                message
            )

    def get_search_input(self):

        keyword = self.search_text.get().strip()

        if keyword == "":

            messagebox.showwarning(
                "Search",
                "Please type something to search."
            )

            return None, None

        return self.search_type.get().lower(), keyword

    def show_search_result(self, rows):

        if self.show_rows(rows) and len(rows) == 0:

            messagebox.showinfo(
                "Search",
                "No record found."
            )


# ============================================================
# BOOK MANAGEMENT
# ============================================================

class BooksPage(FormPage):

    TITLE = "Book Management"

    FIELDS = [
        "Book ID",
        "Title",
        "Author",
        "ISBN",
        "Category",
        "Publisher",
        "Publication Year",
        "Total Copies",
        "Available Copies"
    ]

    COLUMNS = [
        "Book ID",
        "Title",
        "Author",
        "ISBN",
        "Genre",
        "Total Copies",
        "Available Copies"
    ]

    WIDTHS = [70, 240, 170, 130, 120, 100, 120]

    BUTTONS = [
        ("Add Book", "add_record"),
        ("View Books", "refresh"),
        ("Update Book", "update_record"),
        ("Delete Book", "delete_record"),
        ("Clear Fields", "clear_fields")
    ]

    SEARCH_OPTIONS = ["Title", "Author", "ISBN"]

    SEARCH_BUTTON = "Search Book"

    def refresh(self):

        self.show_rows(
            books.get_all_books_rows()
        )

    def load_record(self, book_id):

        book = books.get_book_full(book_id)

        if book is not None:
            self.set_values(book)

    def add_record(self):

        v = self.get_values()

        total = v["Total Copies"]
        available = v["Available Copies"] or total

        ok, message = books.add_book(
            v["Title"],
            v["Author"],
            v["ISBN"],
            v["Category"],
            v["Publisher"],
            v["Publication Year"],
            total,
            available
        )

        self.show_result(ok, message)

    def update_record(self):

        book_id = self.selected_id()

        if book_id is None:
            return

        v = self.get_values()

        ok, message = books.update_book(
            book_id,
            v["Title"],
            v["Author"],
            v["ISBN"],
            v["Category"],
            v["Publisher"],
            v["Publication Year"],
            v["Total Copies"],
            v["Available Copies"]
        )

        self.show_result(ok, message)

    def delete_record(self):

        book_id = self.selected_id()

        if book_id is None:
            return

        if not messagebox.askyesno(
            "Confirm delete",
            f"Delete Book ID {book_id}?"
        ):
            return

        ok, message = books.delete_book(book_id)

        self.show_result(ok, message)

    def search_records(self):

        search_type, keyword = self.get_search_input()

        if keyword is not None:

            self.show_search_result(
                books.search_books_rows(
                    search_type,
                    keyword
                )
            )


# ============================================================
# MEMBER MANAGEMENT
# ============================================================

class MembersPage(FormPage):

    TITLE = "Member Management"

    FIELDS = [
        "Member ID",
        "Name",
        "Email",
        "Phone",
        "Address",
        "Join Date"
    ]

    COLUMNS = [
        "Member ID",
        "Name",
        "Email",
        "Phone",
        "Address",
        "Join Date"
    ]

    WIDTHS = [80, 180, 230, 130, 200, 110]

    BUTTONS = [
        ("Register Member", "add_record"),
        ("View Members", "refresh"),
        ("Update Member", "update_record"),
        ("Delete Member", "delete_record"),
        ("Clear Fields", "clear_fields")
    ]

    SEARCH_OPTIONS = [
        "ID",
        "Name",
        "Email",
        "Phone"
    ]

    SEARCH_BUTTON = "Search Member"

    def refresh(self):

        self.show_rows(
            members.get_all_members_rows()
        )

    def load_record(self, member_id):

        member = members.get_member_full(member_id)

        if member is not None:
            self.set_values(member)

    def add_record(self):

        v = self.get_values()

        ok, message = members.register_member(
            v["Name"],
            v["Email"],
            v["Phone"],
            v["Address"],
            v["Join Date"]
        )

        self.show_result(ok, message)

    def update_record(self):

        member_id = self.selected_id()

        if member_id is None:
            return

        v = self.get_values()

        ok, message = members.update_member(
            member_id,
            v["Name"],
            v["Email"],
            v["Phone"],
            v["Address"]
        )

        self.show_result(ok, message)

    def delete_record(self):

        member_id = self.selected_id()

        if member_id is None:
            return

        if not messagebox.askyesno(
            "Confirm delete",
            f"Delete Member ID {member_id}?"
        ):
            return

        ok, message = members.delete_member(member_id)

        self.show_result(ok, message)

    def search_records(self):

        search_type, keyword = self.get_search_input()

        if keyword is not None:

            self.show_search_result(
                members.search_members_rows(
                    search_type,
                    keyword
                )
            )


# ============================================================
# ISSUE BOOK PAGE
# ============================================================

class IssuePage(ttk.Frame):

    COLUMNS = [
        "Loan ID",
        "Book ID",
        "Title",
        "Member ID",
        "Member",
        "Issue Date",
        "Due Date",
        "Status"
    ]

    WIDTHS = [70, 70, 230, 80, 160, 100, 100, 80]

    def __init__(self, parent):

        super().__init__(parent)

        ttk.Label(
            self,
            text="Issue Book",
            style="Title.TLabel"
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 4)
        )

        form = ttk.LabelFrame(
            self,
            text="Issue a book to a member"
        )

        form.pack(
            anchor="w",
            padx=15,
            pady=8
        )

        ttk.Label(
            form,
            text="Book ID"
        ).grid(
            row=0,
            column=0,
            padx=8,
            pady=6
        )

        self.book_entry = ttk.Entry(
            form,
            width=20
        )

        self.book_entry.grid(
            row=0,
            column=1,
            padx=8,
            pady=6
        )

        ttk.Label(
            form,
            text="Member ID"
        ).grid(
            row=1,
            column=0,
            padx=8,
            pady=6
        )

        self.member_entry = ttk.Entry(
            form,
            width=20
        )

        self.member_entry.grid(
            row=1,
            column=1,
            padx=8,
            pady=6
        )

        ttk.Label(
            form,
            text="Issue Date"
        ).grid(
            row=0,
            column=2,
            padx=8,
            pady=6
        )

        self.issue_date_entry = ttk.Entry(
            form,
            width=20,
            state="readonly"
        )

        self.issue_date_entry.grid(
            row=0,
            column=3,
            padx=8,
            pady=6
        )

        ttk.Label(
            form,
            text="Due Date"
        ).grid(
            row=1,
            column=2,
            padx=8,
            pady=6
        )

        self.due_date_entry = ttk.Entry(
            form,
            width=20,
            state="readonly"
        )

        self.due_date_entry.grid(
            row=1,
            column=3,
            padx=8,
            pady=6
        )

        button_row = ttk.Frame(form)

        button_row.grid(
            row=2,
            column=0,
            columnspan=4,
            pady=8
        )

        ttk.Button(
            button_row,
            text="Issue Book",
            command=self.issue
        ).pack(
            side="left",
            padx=6
        )

        ttk.Button(
            button_row,
            text="Clear Fields",
            command=self.clear_fields
        ).pack(
            side="left",
            padx=6
        )

        ttk.Label(
            self,
            text="Currently issued books",
            style="Sub.TLabel"
        ).pack(
            anchor="w",
            padx=15,
            pady=(8, 2)
        )

        table_frame, self.tree = make_table(
            self,
            self.COLUMNS,
            self.WIDTHS
        )

        table_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(2, 12)
        )

    def show_dates(self):

        today = date.today()

        due = today + timedelta(
            days=loans.LOAN_DAYS
        )

        for entry, value in (
            (self.issue_date_entry, today),
            (self.due_date_entry, due)
        ):

            entry.configure(state="normal")
            entry.delete(0, "end")

            entry.insert(
                0,
                value.strftime("%Y-%m-%d")
            )

            entry.configure(state="readonly")

    def on_show(self):

        self.show_dates()

        rows = reports.issued_books_rows()

        if rows is not None:
            fill_table(self.tree, rows)

    def clear_fields(self):

        self.book_entry.delete(0, "end")
        self.member_entry.delete(0, "end")

    def issue(self):

        book_text = self.book_entry.get().strip()
        member_text = self.member_entry.get().strip()

        if (
            not is_positive_integer(book_text)
            or not is_positive_integer(member_text)
        ):

            messagebox.showwarning(
                "Invalid input",
                "Book ID and Member ID must be positive whole numbers."
            )

            return

        ok, result = loans.issue_book(
            int(book_text),
            int(member_text)
        )

        if not ok:

            messagebox.showerror(
                "Cannot issue book",
                result
            )

            return

        messagebox.showinfo(
            "Book Issued",
            f"Loan ID: {result['loan_id']}\n"
            f"Book: {result['title']} (ID {result['book_id']})\n"
            f"Member: {result['member_name']} "
            f"(ID {result['member_id']})\n"
            f"Issue Date: {result['issue_date']}\n"
            f"Due Date: {result['due_date']}\n"
            f"Status: {result['status']}"
        )

        self.clear_fields()
        self.on_show()


# ============================================================
# RETURN BOOK PAGE
# ============================================================

class ReturnPage(ttk.Frame):

    FIELDS = [
        "Loan ID",
        "Book ID",
        "Member ID",
        "Book Title",
        "Issue Date",
        "Due Date",
        "Return Date",
        "Overdue Days",
        "Fine Amount"
    ]

    COLUMNS = [
        "Loan ID",
        "Book ID",
        "Title",
        "Member ID",
        "Member",
        "Issue Date",
        "Due Date",
        "Status"
    ]

    WIDTHS = [70, 70, 230, 80, 160, 100, 100, 80]

    def __init__(self, parent):

        super().__init__(parent)

        ttk.Label(
            self,
            text="Return Book",
            style="Title.TLabel"
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 4)
        )

        form = ttk.LabelFrame(
            self,
            text="Loan Details"
        )

        form.pack(
            fill="x",
            padx=15,
            pady=4
        )

        self.entries = {}

        for index, name in enumerate(self.FIELDS):

            row, column = divmod(index, 3)

            ttk.Label(
                form,
                text=name
            ).grid(
                row=row,
                column=column * 2,
                sticky="e",
                padx=(10, 4),
                pady=4
            )

            entry = ttk.Entry(
                form,
                width=24
            )

            entry.grid(
                row=row,
                column=column * 2 + 1,
                padx=(0, 10),
                pady=4
            )

            if name != "Loan ID":
                entry.configure(state="readonly")

            self.entries[name] = entry

        buttons = ttk.Frame(self)

        buttons.pack(
            fill="x",
            padx=15,
            pady=4
        )

        ttk.Button(
            buttons,
            text="Search Loan",
            command=self.search_loan
        ).pack(
            side="left",
            padx=(0, 6)
        )

        ttk.Button(
            buttons,
            text="Return Book",
            command=self.return_book
        ).pack(
            side="left",
            padx=(0, 6)
        )

        ttk.Button(
            buttons,
            text="Clear Fields",
            command=self.clear_fields
        ).pack(side="left")

        ttk.Label(
            self,
            text="Currently issued books (click a row to select it)",
            style="Sub.TLabel"
        ).pack(
            anchor="w",
            padx=15,
            pady=(8, 2)
        )

        table_frame, self.tree = make_table(
            self,
            self.COLUMNS,
            self.WIDTHS
        )

        table_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(2, 12)
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.on_select
        )

    def set_entry(self, name, text):

        entry = self.entries[name]

        was_readonly = name != "Loan ID"

        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, str(text))

        if was_readonly:
            entry.configure(state="readonly")

    def clear_details(self):

        for name in self.FIELDS[1:]:
            self.set_entry(name, "")

    def clear_fields(self):

        self.set_entry("Loan ID", "")
        self.clear_details()

        self.tree.selection_remove(
            self.tree.selection()
        )

    def refresh_table(self):

        rows = reports.issued_books_rows()

        if rows is not None:
            fill_table(self.tree, rows)

    def on_show(self):
        self.refresh_table()

    def on_select(self, event):

        selection = self.tree.selection()

        if selection:

            loan_id = self.tree.item(
                selection[0]
            )["values"][0]

            self.set_entry(
                "Loan ID",
                str(loan_id)
            )

            self.search_loan()

    def search_loan(self):

        text = self.entries["Loan ID"].get().strip()

        if not is_positive_integer(text):

            messagebox.showwarning(
                "Invalid input",
                "Loan ID must be a positive whole number."
            )

            return None

        ok, result = loans.find_active_loan(
            int(text)
        )

        if not ok:

            self.clear_details()

            messagebox.showerror(
                "Cannot return book",
                result
            )

            return None

        self.set_entry("Book ID", result["book_id"])
        self.set_entry("Member ID", result["member_id"])
        self.set_entry("Book Title", result["title"])
        self.set_entry("Issue Date", result["issue_date"])
        self.set_entry("Due Date", result["due_date"])
        self.set_entry("Return Date", result["return_date"])
        self.set_entry("Overdue Days", result["overdue_days"])

        self.set_entry(
            "Fine Amount",
            f"₹{result['fine']:.2f}"
        )

        return result

    def return_book(self):

        details = self.search_loan()

        if details is None:
            return

        question = (
            f"Return this book?\n\n"
            f"Book: {details['title']}\n"
            f"Member: {details['member_name']}\n"
            f"Overdue days: {details['overdue_days']}\n"
            f"Fine: ₹{details['fine']:.2f}"
        )

        if not messagebox.askyesno(
            "Confirm return",
            question
        ):
            return

        ok, result = loans.return_book(
            details["loan_id"]
        )

        if not ok:

            messagebox.showerror(
                "Cannot return book",
                result
            )

            return

        messagebox.showinfo(
            "Book Returned",
            f"Book returned successfully.\n\n"
            f"Loan ID: {result['loan_id']}\n"
            f"Return Date: {result['return_date']}\n"
            f"Overdue Days: {result['overdue_days']}\n"
            f"Fine to pay: ₹{result['fine']:.2f}"
        )

        self.clear_fields()
        self.refresh_table()


# ============================================================
# REPORTS PAGE
# ============================================================

class ReportsPage(ttk.Frame):

    def __init__(self, parent):

        super().__init__(parent)

        ttk.Label(
            self,
            text="Reports",
            style="Title.TLabel"
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 4)
        )

        buttons = ttk.Frame(self)

        buttons.pack(
            fill="x",
            padx=15,
            pady=6
        )

        for text, command in (
            ("Available Books", self.show_available),
            ("Issued Books", self.show_issued),
            ("Overdue Books", self.show_overdue),
            ("Fine Collection", self.show_fine),
            ("Member Borrowing History", self.show_history)
        ):

            ttk.Button(
                buttons,
                text=text,
                command=command
            ).pack(
                side="left",
                padx=(0, 6)
            )

        self.report_title = ttk.Label(
            self,
            text="Click a button to see a report.",
            style="Sub.TLabel"
        )

        self.report_title.pack(
            anchor="w",
            padx=15,
            pady=(8, 2)
        )

        table_frame, self.tree = make_table(
            self,
            ["Report"],
            [300],
            height=14
        )

        table_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(2, 12)
        )

    def on_show(self):
        pass

    def show_report(self, title, columns, widths, rows):

        if rows is None:

            messagebox.showerror(
                "Database error",
                "Could not read the database."
            )

            return

        self.report_title.config(
            text=f"{title} ({len(rows)} rows)"
        )

        setup_table(
            self.tree,
            columns,
            widths
        )

        fill_table(
            self.tree,
            rows
        )

        if len(rows) == 0:

            messagebox.showinfo(
                title,
                "No records found for this report."
            )

    def show_available(self):

        self.show_report(
            "Available Books Report",
            [
                "Book ID",
                "Title",
                "Author",
                "Category",
                "Total Copies",
                "Available Copies"
            ],
            [70, 260, 180, 140, 100, 120],
            reports.available_books_rows()
        )

    def show_issued(self):

        self.show_report(
            "Issued Books Report",
            [
                "Loan ID",
                "Book ID",
                "Title",
                "Member ID",
                "Member",
                "Issue Date",
                "Due Date",
                "Status"
            ],
            [70, 70, 230, 80, 160, 100, 100, 80],
            reports.issued_books_rows()
        )

    def show_overdue(self):

        self.show_report(
            "Overdue Books Report",
            [
                "Loan ID",
                "Title",
                "Member",
                "Phone",
                "Issue Date",
                "Due Date",
                "Overdue Days"
            ],
            [70, 240, 170, 120, 100, 100, 100],
            reports.overdue_books_rows()
        )

    def show_fine(self):

        rows = reports.fine_collection_rows()

        total = sum(
            row[5] for row in rows
        ) if rows else 0

        self.show_report(
            f"Fine Collection Report - Total ₹{total:.2f}",
            [
                "Loan ID",
                "Book Title",
                "Member",
                "Due Date",
                "Return Date",
                "Fine"
            ],
            [70, 260, 170, 100, 100, 80],
            rows
        )

    def show_history(self):

        text = simpledialog.askstring(
            "Member History",
            "Enter Member ID:",
            parent=self
        )

        if text is None:
            return

        text = text.strip()

        if not is_positive_integer(text):

            messagebox.showwarning(
                "Invalid input",
                "Member ID must be a positive whole number."
            )

            return

        ok, name_or_error, rows = reports.member_history_rows(
            int(text)
        )

        if not ok:

            messagebox.showerror(
                "Error",
                name_or_error
            )

            return

        if len(rows) == 0:

            messagebox.showinfo(
                "Member History",
                f"{name_or_error} has not borrowed any books yet."
            )

        self.show_report(
            f"Borrowing History of {name_or_error}",
            [
                "Loan ID",
                "Title",
                "Author",
                "Issue Date",
                "Due Date",
                "Return Date",
                "Fine",
                "Status"
            ],
            [70, 220, 150, 100, 100, 100, 60, 80],
            rows
        )


# ============================================================
# REUSABLE DASHBOARD CARD
# ============================================================

def make_card(grid, text, index):

    card = ttk.Frame(
        grid,
        style="Card.TFrame",
        padding=20
    )

    card.grid(
        row=index // 3,
        column=index % 3,
        padx=10,
        pady=10
    )

    ttk.Label(
        card,
        text=text,
        style="CardText.TLabel",
        width=22,
        anchor="center"
    ).pack()

    value = ttk.Label(
        card,
        text="0",
        style="CardNumber.TLabel",
        width=10,
        anchor="center"
    )

    value.pack(pady=(8, 0))

    return value


# ============================================================
# ADMIN DASHBOARD
# ============================================================

class DashboardPage(ttk.Frame):

    ITEMS = [
        ("Total Books", "total_books"),
        ("Total Book Copies", "total_copies"),
        ("Available Copies", "available_copies"),
        ("Total Members", "total_members"),
        ("Currently Issued Books", "issued_books"),
        ("Overdue Books", "overdue_books"),
        ("Total Fine Collected", "total_fine")
    ]

    def __init__(self, parent):

        super().__init__(parent)

        ttk.Label(
            self,
            text="Admin Dashboard",
            style="Title.TLabel"
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 4)
        )

        grid = ttk.Frame(self)

        grid.pack(
            anchor="w",
            padx=15,
            pady=10
        )

        self.value_labels = {}

        for index, (text, key) in enumerate(self.ITEMS):

            self.value_labels[key] = make_card(
                grid,
                text,
                index
            )

        ttk.Button(
            self,
            text="Refresh",
            command=self.on_show
        ).pack(
            anchor="w",
            padx=25,
            pady=10
        )

    def on_show(self):

        stats = reports.dashboard_stats()

        if stats is None:

            messagebox.showerror(
                "Database error",
                "Could not read the database."
            )

            return

        for key, label in self.value_labels.items():

            value = stats[key]

            if key == "total_fine":
                label.config(text=f"₹{value:.2f}")
            else:
                label.config(text=str(value))


# ============================================================
# LOGIN PAGE
# ============================================================

class LoginPage(ttk.Frame):

    def __init__(self, parent, app):

        super().__init__(parent)

        self.app = app

        card = ttk.Frame(
            self,
            style="Card.TFrame",
            padding=35
        )

        card.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        ttk.Label(
            card,
            text="Library Management System",
            style="CardTitle.TLabel"
        ).pack()

        ttk.Label(
            card,
            text="Please log in to continue",
            style="CardText.TLabel"
        ).pack(pady=(4, 20))

        ttk.Label(
            card,
            text="Username",
            style="CardText.TLabel"
        ).pack(anchor="w")

        self.username_entry = ttk.Entry(
            card,
            width=34
        )

        self.username_entry.pack(
            pady=(2, 12)
        )

        ttk.Label(
            card,
            text="Password",
            style="CardText.TLabel"
        ).pack(anchor="w")

        self.password_entry = ttk.Entry(
            card,
            width=34,
            show="*"
        )

        self.password_entry.pack(
            pady=(2, 6)
        )

        self.show_password = tk.BooleanVar(
            value=False
        )

        ttk.Checkbutton(
            card,
            text="Show password",
            variable=self.show_password,
            command=self.toggle_password,
            style="Card.TCheckbutton"
        ).pack(
            anchor="w",
            pady=(0, 12)
        )

        buttons = ttk.Frame(
            card,
            style="Card.TFrame"
        )

        buttons.pack()

        ttk.Button(
            buttons,
            text="Login",
            command=self.login
        ).pack(
            side="left",
            padx=5
        )

        ttk.Button(
            buttons,
            text="Clear",
            command=self.clear
        ).pack(
            side="left",
            padx=5
        )

        ttk.Separator(card).pack(
            fill="x",
            pady=18
        )

        ttk.Button(
            card,
            text="Member Sign Up",
            command=self.open_sign_up
        ).pack(fill="x")

        self.admin_button = None

        if not authentication.admin_exists():

            self.admin_button = ttk.Button(
                card,
                text="Create First Admin",
                command=self.create_first_admin
            )

            self.admin_button.pack(
                fill="x",
                pady=(8, 0)
            )

        self.username_entry.bind(
            "<Return>",
            lambda event: self.login()
        )

        self.password_entry.bind(
            "<Return>",
            lambda event: self.login()
        )

        self.username_entry.focus()

    def toggle_password(self):

        self.password_entry.config(
            show="" if self.show_password.get() else "*"
        )

    def clear(self):

        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")

        self.username_entry.focus()

    def login(self):

        ok, result = authentication.login(
            self.username_entry.get(),
            self.password_entry.get()
        )

        if not ok:

            messagebox.showerror(
                "Login failed",
                result
            )

            self.password_entry.delete(0, "end")

            return

        self.app.start_session(result)

    def open_sign_up(self):

        SignUpWindow(self)

    def create_first_admin(self):

        if authentication.admin_exists():

            messagebox.showinfo(
                "Admin",
                "An admin account already exists."
            )

            return

        username = simpledialog.askstring(
            "First Admin",
            "Choose an admin username:",
            parent=self
        )

        if username is None:
            return

        password = simpledialog.askstring(
            "First Admin",
            "Choose a password (at least 6 characters):",
            parent=self,
            show="*"
        )

        if password is None:
            return

        again = simpledialog.askstring(
            "First Admin",
            "Type the password again:",
            parent=self,
            show="*"
        )

        if again != password:

            messagebox.showerror(
                "Error",
                "The two passwords are not the same."
            )

            return

        ok, message = authentication.create_admin(
            username,
            password
        )

        if ok:

            messagebox.showinfo(
                "Success",
                message
            )

            if self.admin_button:
                self.admin_button.destroy()
                self.admin_button = None

        else:

            messagebox.showerror(
                "Error",
                message
            )


# ============================================================
# MEMBER SIGN UP WINDOW
# ============================================================

class SignUpWindow(tk.Toplevel):

    LABELS = [
        "Member ID",
        "Registered Email",
        "Username",
        "Password",
        "Confirm Password"
    ]

    def __init__(self, parent):

        super().__init__(parent)

        self.title("Member Sign Up")
        self.configure(bg=BG)
        self.resizable(False, False)

        self.grab_set()

        frame = ttk.Frame(
            self,
            padding=20
        )

        frame.pack()

        ttk.Label(
            frame,
            text="Create your member login",
            style="Sub.TLabel"
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            pady=(0, 10)
        )

        self.entries = {}

        for row, label in enumerate(self.LABELS, start=1):

            ttk.Label(
                frame,
                text=label
            ).grid(
                row=row,
                column=0,
                sticky="e",
                padx=6,
                pady=5
            )

            entry = ttk.Entry(
                frame,
                width=30,
                show="*" if "Password" in label else ""
            )

            entry.grid(
                row=row,
                column=1,
                pady=5
            )

            self.entries[label] = entry

        ttk.Label(
            frame,
            text=(
                "Ask the admin to register you first.\n"
                "Use the same email the admin saved."
            )
        ).grid(
            row=6,
            column=0,
            columnspan=2,
            pady=(8, 0)
        )

        ttk.Button(
            frame,
            text="Create Account",
            command=self.create_account
        ).grid(
            row=7,
            column=0,
            columnspan=2,
            pady=(12, 0)
        )

    def create_account(self):

        member_text = self.entries["Member ID"].get().strip()
        email = self.entries["Registered Email"].get().strip()
        username = self.entries["Username"].get().strip()
        password = self.entries["Password"].get()
        confirm = self.entries["Confirm Password"].get()

        if not is_positive_integer(member_text):

            messagebox.showwarning(
                "Invalid input",
                "Member ID must be a positive whole number.",
                parent=self
            )

            return

        if email == "" or username == "" or password == "":

            messagebox.showwarning(
                "Missing data",
                "Please fill all the boxes.",
                parent=self
            )

            return

        if password != confirm:

            messagebox.showerror(
                "Error",
                "The two passwords are not the same.",
                parent=self
            )

            return

        ok, message = authentication.register_member_account(
            int(member_text),
            email,
            username,
            password
        )

        if ok:

            messagebox.showinfo(
                "Success",
                message,
                parent=self
            )

            self.destroy()

        else:

            messagebox.showerror(
                "Error",
                message,
                parent=self
            )


# ============================================================
# MEMBER DASHBOARD
# ============================================================

class MemberDashboardPage(ttk.Frame):

    COLUMNS = [
        "Loan ID",
        "Title",
        "Author",
        "Issue Date",
        "Due Date",
        "Overdue Days",
        "Fine So Far"
    ]

    WIDTHS = [70, 240, 160, 100, 100, 100, 100]

    def __init__(self, parent, member_id):

        super().__init__(parent)

        self.member_id = member_id

        self.welcome = ttk.Label(
            self,
            text="Welcome",
            style="Title.TLabel"
        )

        self.welcome.pack(
            anchor="w",
            padx=15,
            pady=(12, 4)
        )

        grid = ttk.Frame(self)

        grid.pack(
            anchor="w",
            padx=15,
            pady=6
        )

        self.borrowed_label = make_card(
            grid,
            "Books Currently Borrowed",
            0
        )

        self.overdue_label = make_card(
            grid,
            "Overdue Books",
            1
        )

        self.fine_label = make_card(
            grid,
            "Pending Fine",
            2
        )

        ttk.Label(
            self,
            text="My issued books and due dates",
            style="Sub.TLabel"
        ).pack(
            anchor="w",
            padx=15,
            pady=(8, 2)
        )

        table_frame, self.tree = make_table(
            self,
            self.COLUMNS,
            self.WIDTHS
        )

        table_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(2, 12)
        )

    def on_show(self):

        member = members.get_member_full(
            self.member_id
        )

        if member is not None:

            self.welcome.config(
                text=f"Welcome, {member[1]}"
            )

        data = reports.member_dashboard_data(
            self.member_id
        )

        if data is None:

            messagebox.showerror(
                "Database error",
                "Could not read the database."
            )

            return

        stats, rows = data

        self.borrowed_label.config(
            text=str(stats["borrowed"])
        )

        self.overdue_label.config(
            text=str(stats["overdue"])
        )

        self.fine_label.config(
            text=f"₹{stats['pending_fine']:.2f}"
        )

        fill_table(
            self.tree,
            rows
        )


# ============================================================
# MEMBER TABLE PAGE
# ============================================================

class MemberTablePage(ttk.Frame):

    def __init__(
        self,
        parent,
        title,
        columns,
        widths,
        loader
    ):

        super().__init__(parent)

        self.loader = loader

        ttk.Label(
            self,
            text=title,
            style="Title.TLabel"
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 4)
        )

        self.count_label = ttk.Label(
            self,
            text="",
            style="Sub.TLabel"
        )

        self.count_label.pack(
            anchor="w",
            padx=15
        )

        table_frame, self.tree = make_table(
            self,
            columns,
            widths,
            height=14
        )

        table_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(4, 12)
        )

    def on_show(self):

        rows = self.loader()

        if rows is None:

            messagebox.showerror(
                "Database error",
                "Could not read the database."
            )

            return

        fill_table(
            self.tree,
            rows
        )

        self.count_label.config(
            text=f"{len(rows)} records"
        )


# ============================================================
# MEMBER SEARCH BOOKS PAGE
# ============================================================

class SearchBooksPage(ttk.Frame):

    COLUMNS = [
        "Book ID",
        "Title",
        "Author",
        "ISBN",
        "Genre",
        "Total Copies",
        "Available Copies"
    ]

    WIDTHS = [70, 240, 170, 130, 120, 100, 120]

    def __init__(self, parent):

        super().__init__(parent)

        ttk.Label(
            self,
            text="Search Books",
            style="Title.TLabel"
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 4)
        )

        row = ttk.Frame(self)

        row.pack(
            fill="x",
            padx=15,
            pady=6
        )

        ttk.Label(
            row,
            text="Search by:"
        ).pack(side="left")

        self.search_type = ttk.Combobox(
            row,
            values=["Title", "Author", "ISBN"],
            state="readonly",
            width=12
        )

        self.search_type.current(0)

        self.search_type.pack(
            side="left",
            padx=6
        )

        self.search_text = ttk.Entry(
            row,
            width=30
        )

        self.search_text.pack(
            side="left",
            padx=6
        )

        ttk.Button(
            row,
            text="Search",
            command=self.search
        ).pack(
            side="left",
            padx=3
        )

        ttk.Button(
            row,
            text="Show All",
            command=self.show_all
        ).pack(
            side="left",
            padx=3
        )

        table_frame, self.tree = make_table(
            self,
            self.COLUMNS,
            self.WIDTHS,
            height=14
        )

        table_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(4, 12)
        )

    def show_rows(self, rows):

        if rows is None:

            messagebox.showerror(
                "Database error",
                "Could not read the database."
            )

            return False

        fill_table(
            self.tree,
            rows
        )

        return True

    def show_all(self):

        self.show_rows(
            books.get_all_books_rows()
        )

    def on_show(self):

        self.show_all()

    def search(self):

        keyword = self.search_text.get().strip()

        if keyword == "":

            messagebox.showwarning(
                "Search",
                "Please type something to search."
            )

            return

        rows = books.search_books_rows(
            self.search_type.get().lower(),
            keyword
        )

        if self.show_rows(rows) and len(rows) == 0:

            messagebox.showinfo(
                "Search",
                "No book found."
            )


# ============================================================
# MEMBER PROFILE PAGE
# ============================================================

class MemberProfilePage(ttk.Frame):

    LABELS = [
        "Member ID",
        "Name",
        "Email",
        "Phone",
        "Address",
        "Join Date"
    ]

    def __init__(self, parent, member_id, username):

        super().__init__(parent)

        self.member_id = member_id

        ttk.Label(
            self,
            text="My Profile",
            style="Title.TLabel"
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 4)
        )

        box = ttk.LabelFrame(
            self,
            text="My details"
        )

        box.pack(
            anchor="w",
            padx=15,
            pady=10
        )

        self.value_labels = {}

        for row, label in enumerate(
            self.LABELS + ["Username"]
        ):

            ttk.Label(
                box,
                text=label + ":",
                style="Sub.TLabel"
            ).grid(
                row=row,
                column=0,
                sticky="e",
                padx=(15, 8),
                pady=6
            )

            value = ttk.Label(
                box,
                text=""
            )

            value.grid(
                row=row,
                column=1,
                sticky="w",
                padx=(0, 30),
                pady=6
            )

            self.value_labels[label] = value

        self.value_labels["Username"].config(
            text=username
        )

    def on_show(self):

        member = members.get_member_full(
            self.member_id
        )

        if member is None:

            messagebox.showerror(
                "Error",
                "Could not load your profile."
            )

            return

        for label, value in zip(
            self.LABELS,
            member
        ):

            self.value_labels[label].config(
                text="-" if value in (None, "") else str(value)
            )


# ============================================================
# MAIN LIBRARY APPLICATION
# ============================================================

class LibraryApp:

    def __init__(self, root):

        self.root = root

        self.user = None
        self.pages = {}

        root.title(
            "Library Management System"
        )

        root.geometry(
            "1150x680"
        )

        root.minsize(
            1000,
            600
        )

        root.configure(
            bg=BG
        )

        root.report_callback_exception = (
            self.show_unexpected_error
        )

        self.setup_styles()

        self.show_login()

    # --------------------------------------------------------
    # LOGIN AND LOGOUT
    # --------------------------------------------------------

    def clear_window(self):

        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login(self):

        self.user = None
        self.pages = {}

        self.clear_window()

        LoginPage(
            self.root,
            self
        ).pack(
            fill="both",
            expand=True
        )

    def start_session(self, user):

        self.user = user

        if user["role"] == "Admin":

            self.open_main_ui(
                self.create_admin_pages,
                f"Admin: {user['username']}"
            )

        elif user["role"] == "Member":

            member = members.get_member_full(
                user["member_id"]
            )

            name = (
                member[1]
                if member
                else user["username"]
            )

            self.open_main_ui(
                self.create_member_pages,
                f"Member: {name}"
            )

        else:

            messagebox.showerror(
                "Error",
                "Unknown user role."
            )

            self.show_login()

    def logout(self):

        if messagebox.askyesno(
            "Logout",
            "Do you want to log out?"
        ):

            self.show_login()

    def exit_app(self):

        if messagebox.askyesno(
            "Exit",
            "Do you want to close the application?"
        ):

            self.root.destroy()

    # --------------------------------------------------------
    # ADMIN PAGES
    # --------------------------------------------------------

    def create_admin_pages(self, content):

        if (
            self.user is None
            or self.user["role"] != "Admin"
        ):

            raise PermissionError(
                "Only an admin can open these screens."
            )

        return {

            "Dashboard": DashboardPage(content),

            "Books": BooksPage(content),

            "Members": MembersPage(content),

            "Issue Book": IssuePage(content),

            "Return Book": ReturnPage(content),

            "Reports": ReportsPage(content),

        }

    # --------------------------------------------------------
    # MEMBER PAGES
    # --------------------------------------------------------

    def create_member_pages(self, content):

        member_id = self.user["member_id"]

        return {

            "Dashboard": MemberDashboardPage(
                content,
                member_id
            ),

            "Available Books": MemberTablePage(
                content,
                "Available Books",
                [
                    "Book ID",
                    "Title",
                    "Author",
                    "Category",
                    "Total Copies",
                    "Available Copies"
                ],
                [70, 260, 180, 140, 100, 120],
                reports.available_books_rows
            ),

            "Search Books": SearchBooksPage(content),

            "My Issued Books": MemberTablePage(
                content,
                "My Issued Books",
                MemberDashboardPage.COLUMNS,
                MemberDashboardPage.WIDTHS,
                lambda: reports.member_issued_rows(member_id)
            ),

            "My Borrowing History": MemberTablePage(
                content,
                "My Borrowing History",
                [
                    "Loan ID",
                    "Title",
                    "Author",
                    "Issue Date",
                    "Due Date",
                    "Return Date",
                    "Fine",
                    "Status"
                ],
                [70, 220, 150, 100, 100, 100, 60, 80],
                lambda: reports.member_history_rows(member_id)[2]
            ),

            "My Profile": MemberProfilePage(
                content,
                member_id,
                self.user["username"]
            ),

        }

    # --------------------------------------------------------
    # MAIN SCREEN WITH SIDEBAR
    # --------------------------------------------------------

    def open_main_ui(
        self,
        create_pages,
        welcome_text
    ):

        self.clear_window()

        sidebar = ttk.Frame(
            self.root,
            style="Side.TFrame"
        )

        sidebar.pack(
            side="left",
            fill="y"
        )

        ttk.Label(
            sidebar,
            text="Library\nManagement\nSystem",
            style="Logo.TLabel"
        ).pack(
            padx=20,
            pady=(25, 8)
        )

        ttk.Label(
            sidebar,
            text=welcome_text,
            style="User.TLabel"
        ).pack(
            pady=(0, 18)
        )

        content = ttk.Frame(
            self.root
        )

        content.pack(
            side="right",
            fill="both",
            expand=True
        )

        self.pages = create_pages(content)

        for page in self.pages.values():

            page.place(
                relx=0,
                rely=0,
                relwidth=1,
                relheight=1
            )

        for name in self.pages:

            ttk.Button(
                sidebar,
                text=name,
                style="Nav.TButton",
                command=lambda n=name: self.show_page(n)
            ).pack(
                fill="x",
                padx=10,
                pady=3
            )

        ttk.Button(
            sidebar,
            text="Exit",
            style="Nav.TButton",
            command=self.exit_app
        ).pack(
            side="bottom",
            fill="x",
            padx=10,
            pady=(3, 15)
        )

        ttk.Button(
            sidebar,
            text="Logout",
            style="Nav.TButton",
            command=self.logout
        ).pack(
            side="bottom",
            fill="x",
            padx=10,
            pady=3
        )

        self.show_page(
            next(iter(self.pages))
        )

    # --------------------------------------------------------
    # PAGE NAVIGATION
    # --------------------------------------------------------

    def show_page(self, name):

        page = self.pages[name]

        page.tkraise()

        page.on_show()

    # --------------------------------------------------------
    # APPLICATION STYLES
    # --------------------------------------------------------

    def setup_styles(self):

        style = ttk.Style()

        style.theme_use("clam")

        font = ("Segoe UI", 10)

        style.configure(
            "TFrame",
            background=BG
        )

        style.configure(
            "TLabel",
            background=BG,
            font=font
        )

        style.configure(
            "TLabelframe",
            background=BG
        )

        style.configure(
            "TLabelframe.Label",
            background=BG,
            foreground=ACCENT,
            font=("Segoe UI", 10, "bold")
        )

        style.configure(
            "TButton",
            font=font,
            padding=6
        )

        style.configure(
            "TCheckbutton",
            background=BG,
            font=font
        )

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 18, "bold"),
            foreground=SIDEBAR
        )

        style.configure(
            "Sub.TLabel",
            font=("Segoe UI", 11, "bold"),
            foreground=SIDEBAR
        )

        style.configure(
            "Side.TFrame",
            background=SIDEBAR
        )

        style.configure(
            "Logo.TLabel",
            background=SIDEBAR,
            foreground="white",
            font=("Segoe UI", 15, "bold"),
            justify="center"
        )

        style.configure(
            "User.TLabel",
            background=SIDEBAR,
            foreground="#b8c4e0",
            font=("Segoe UI", 10)
        )

        style.configure(
            "Nav.TButton",
            background=SIDEBAR,
            foreground="white",
            font=("Segoe UI", 11),
            padding=10,
            borderwidth=0,
            anchor="w"
        )

        style.map(
            "Nav.TButton",
            background=[("active", ACCENT)]
        )

        style.configure(
            "Card.TFrame",
            background=CARD,
            relief="solid",
            borderwidth=1
        )

        style.configure(
            "CardTitle.TLabel",
            background=CARD,
            foreground=SIDEBAR,
            font=("Segoe UI", 17, "bold")
        )

        style.configure(
            "CardText.TLabel",
            background=CARD,
            foreground="#555555",
            font=("Segoe UI", 11)
        )

        style.configure(
            "CardNumber.TLabel",
            background=CARD,
            foreground=ACCENT,
            font=("Segoe UI", 26, "bold")
        )

        style.configure(
            "Card.TCheckbutton",
            background=CARD,
            font=font
        )

        style.configure(
            "Treeview",
            rowheight=26,
            font=font
        )

        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold")
        )

    # --------------------------------------------------------
    # HANDLE UNEXPECTED ERRORS
    # --------------------------------------------------------

    def show_unexpected_error(
        self,
        error_type,
        error,
        trace
    ):

        messagebox.showerror(
            "Unexpected error",
            str(error)
        )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = LibraryApp(root)

    root.mainloop()
