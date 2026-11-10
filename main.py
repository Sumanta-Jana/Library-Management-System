import tkinter as tk

from database import create_tables, test_connection
from gui import LibraryApp


def main():
    # 1. Make sure the database and tables are ready
    if not create_tables():
        print("Could not create tables. Stopping.")
        return
    if not test_connection():
        return

    # 2. Start the window
    root = tk.Tk()
    app = LibraryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()