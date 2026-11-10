\# Installation Guide



\## 1. Introduction



This guide explains how to install and run the Library Management System on a Windows computer.



The application is developed using Python, Tkinter, and SQLite.



\## 2. System Requirements



\- Operating System: Windows 10 or Windows 11

\- Python: Python 3

\- Code Editor: Visual Studio Code or any Python-compatible editor

\- Database: SQLite

\- RAM: 4 GB or more recommended



\## 3. Install Python



1\. Visit https://www.python.org/downloads/

2\. Download Python 3 for Windows.

3\. Run the installer.

4\. Select the option \*\*Add Python to PATH\*\*.

5\. Complete the installation.



To check Python installation, open PowerShell and run:



```powershell

python --version

```



\## 4. Open the Project Folder



Open PowerShell and navigate to the Library Management System directory.



Example:



```powershell

cd C:\\Users\\ASUS\\OneDrive\\Desktop\\PROJECT\\python\\Library\_Management\_Systemdatabase\\Library\_Management\_System

```



Use your actual project location if it is different.



\## 5. Create a Virtual Environment (Optional)



To create a separate Python environment, run:



```powershell

python -m venv venv

```



Activate it using:



```powershell

.\\venv\\Scripts\\Activate.ps1

```



If PowerShell blocks activation, you can run the application using the virtual environment's Python executable directly:



```powershell

.\\venv\\Scripts\\python.exe main.py

```



\## 6. Install Dependencies



The project uses Python's built-in Tkinter and SQLite modules.



Check Tkinter using:



```powershell

python -m tkinter

```



If the Tkinter test window opens, Tkinter is available.



No additional packages are required by the core desktop application if it uses only Python standard-library modules.



\## 7. Create the Admin Account



Run:



```powershell

python create\_admin.py

```



Follow the instructions displayed in the terminal.



If an admin account already exists, do not create another unnecessarily.



\## 8. Initialize the Database



The application initializes its database tables when it starts.



Run:



```powershell

python -c "from database import create\_tables; print(create\_tables())"

```



\## 9. Run the Application



Start the Library Management System using:



```powershell

python main.py

```



The Tkinter desktop application should open if initialization succeeds.



\## 10. Troubleshooting



\### Python is not recognized



Check whether Python is installed and added to PATH.



\### Tkinter is unavailable



Check your Python installation and install a Python distribution that includes Tkinter.



\### Database connection error



Check that the application has permission to access its database directory.



Do not delete the existing `library.db` file to solve a connection problem.



\### Application does not open



Run the application from PowerShell:



```powershell

python main.py

```



Read the complete error message and investigate the reported file and line number.



\## 11. Conclusion



After completing these steps, the Library Management System should be ready to run on a compatible Windows computer.

