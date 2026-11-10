"""Library Management System - Flask web application.

Run:   python app.py        then open  http://127.0.0.1:5000
Admin: python create_admin.py   (first time)  or  reset_password.py
"""

import csv
import hmac
import io
import os
import secrets
import sqlite3
import time
from datetime import timedelta
from functools import wraps

import click
from flask import (Flask, Response, abort, flash, g, jsonify, redirect,
                   render_template, request, session, url_for)

import apikeys
import authentication
import books as books_module
import loans as loans_module
import members as members_module
import webdata
from api import api as api_blueprint
from database import create_tables, repair_data

BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_FOLDER, "static", "uploads", "covers")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==========================================================
# 1. CONFIGURATION
# ==========================================================

def load_secret_key():
    """Secret key: environment variable first, otherwise a saved random key."""
    key = os.environ.get("LIBRARY_SECRET_KEY")
    if key:
        return key

    key_file = os.path.join(BASE_FOLDER, "secret_key.txt")

    if not os.path.exists(key_file):
        with open(key_file, "w") as file:
            file.write(secrets.token_hex(32))

    with open(key_file, "r") as file:
        key = file.read().strip().lstrip("\ufeff")

    if not key:  # empty file: make a fresh key
        key = secrets.token_hex(32)
        with open(key_file, "w") as file:
            file.write(key)

    return key


app = Flask(__name__)
app.config.update(
    SECRET_KEY=load_secret_key(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    MAX_CONTENT_LENGTH=3 * 1024 * 1024,   # 3 MB uploads
    JSON_SORT_KEYS=False,
)

app.register_blueprint(api_blueprint)

create_tables()
repair_data()


# ==========================================================
# 2. CSRF PROTECTION  (built in - no extra package needed)
# ==========================================================

def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def check_csrf():
    if request.method in ("POST", "PUT", "PATCH", "DELETE") \
            and not request.path.startswith("/api/"):
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRFToken", "")
        expected = session.get("_csrf", "")
        if not expected or not hmac.compare_digest(sent, expected):
            abort(400, description="csrf")


# ==========================================================
# 3. LOGGED-IN USER, TEMPLATE HELPERS, SECURITY HEADERS
# ==========================================================

@app.before_request
def load_logged_in_user():
    g.user = None
    user_id = session.get("user_id")

    if user_id is not None:
        g.user = authentication.get_user_by_id(user_id)
        if g.user is None:
            session.clear()


@app.context_processor
def inject_globals():
    return {
        "current_user": g.get("user"),
        "LOAN_DAYS": webdata.LOAN_DAYS,
        "FINE_PER_DAY": webdata.FINE_PER_DAY,
        "MAX_RENEWALS": webdata.MAX_RENEWALS,
        "RENEW_DAYS": webdata.RENEW_DAYS,
        "today": webdata.today_text(),
    }


@app.template_filter("inr")
def inr_filter(value):
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0
    return f"₹{number:,.0f}" if number == int(number) else f"₹{number:,.2f}"


@app.template_filter("nice_date")
def nice_date_filter(value):
    from datetime import datetime
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d %b %Y")
    except (TypeError, ValueError):
        return value or "—"


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if not request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# ==========================================================
# 4. ROLE-BASED ACCESS CONTROL
# ==========================================================

def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                flash("Please log in first.", "warning")
                return redirect(url_for("login", next=request.path))
            if g.user["role"] != role:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


admin_required = role_required("Admin")
member_required = role_required("Member")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in first.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def dashboard_url_for(user):
    return url_for("admin_dashboard" if user["role"] == "Admin"
                   else "member_dashboard")


def page_number():
    try:
        return max(1, int(request.args.get("page", 1)))
    except ValueError:
        return 1


def safe_next(target):
    """Only allow redirects to pages inside this site."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


# ==========================================================
# 5. LOGIN ATTEMPT LIMIT (stops password guessing)
# ==========================================================

FAILED = {}
MAX_FAILS, WINDOW = 6, 300


def too_many_attempts(key):
    now = time.time()
    FAILED[key] = [t for t in FAILED.get(key, []) if now - t < WINDOW]
    return len(FAILED[key]) >= MAX_FAILS


# ==========================================================
# 6. PUBLIC PAGES
# ==========================================================

@app.route("/")
def index():
    stats = webdata.overview_stats()
    featured = webdata.list_books(sort="popular", availability="available",
                                  per_page=5)["items"]
    return render_template("index.html", stats=stats, featured=featured)


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(dashboard_url_for(g.user))

    username = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        key = f"{request.remote_addr}|{username.lower()}"

        if too_many_attempts(key):
            flash("Too many failed attempts. Please wait 5 minutes and try again.",
                  "danger")
            return render_template("login.html", username=username), 429

        success, result = authentication.login(username, password)

        if not success:
            FAILED.setdefault(key, []).append(time.time())
            flash(result, "danger")
            return render_template("login.html", username=username)

        FAILED.pop(key, None)
        session.clear()
        session["user_id"] = result["user_id"]
        session.permanent = True
        flash(f"Welcome back, {result['username']}!", "success")

        return redirect(safe_next(request.args.get("next"))
                        or dashboard_url_for(result))

    return render_template("login.html", username=username)


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(dashboard_url_for(g.user))

    form = {}

    if request.method == "POST":
        form = {k: request.form.get(k, "").strip()
                for k in ("name", "username", "email", "phone", "address")}
        password = request.form.get("password", "")

        if password != request.form.get("confirm_password", ""):
            flash("The two passwords are not the same.", "danger")
        else:
            success, message = authentication.register_new_member(
                form["name"], form["username"], form["email"],
                form["phone"], form["address"], password)
            if success:
                flash(message, "success")
                return redirect(url_for("login"))
            flash(message, "danger")

    return render_template("register.html", form=form)


@app.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if g.user is None:
        return redirect(url_for("login"))
    return redirect(dashboard_url_for(g.user))


@app.route("/books")
def catalog():
    result = webdata.list_books(
        search=request.args.get("q", "").strip(),
        category=request.args.get("category", "").strip(),
        availability=request.args.get("availability", ""),
        sort=request.args.get("sort", "title"),
        page=page_number(), per_page=12)
    return render_template("catalog.html", result=result,
                           categories=webdata.list_categories(),
                           args=request.args)


@app.route("/books/<int:book_id>")
def book_detail(book_id):
    book = webdata.get_book(book_id)
    if book is None:
        abort(404)
    history = []
    if g.user is not None and g.user["role"] == "Admin":
        history = webdata.book_loan_history(book_id)
    return render_template("book_detail.html", book=book, history=history)


# ==========================================================
# 7. ADMIN - DASHBOARD
# ==========================================================

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    return render_template(
        "admin/dashboard.html",
        stats=webdata.overview_stats(),
        recent_loans=webdata.list_loans("all", per_page=6)["items"],
        overdue=webdata.list_loans("overdue", per_page=5)["items"],
        categories=webdata.category_breakdown(),
        daily=webdata.loans_last_days(7),
        top=webdata.top_books(5),
        recent_members=webdata.list_members(per_page=5)["items"],
    )


# ==========================================================
# 8. ADMIN - BOOKS
# ==========================================================

ALLOWED_IMAGES = {b"\xff\xd8\xff": "jpg", b"\x89PNG": "png",
                  b"GIF8": "gif", b"RIFF": "webp"}


def save_cover(file_storage):
    """Save an uploaded cover. Returns (filename or None, error or None)."""
    if file_storage is None or not file_storage.filename:
        return None, None

    head = file_storage.stream.read(12)
    file_storage.stream.seek(0)
    extension = next((ext for magic, ext in ALLOWED_IMAGES.items()
                      if head.startswith(magic)), None)

    if extension is None or (extension == "webp" and head[8:12] != b"WEBP"):
        return None, "Cover must be a JPG, PNG, GIF or WEBP image."

    name = f"{secrets.token_hex(8)}.{extension}"
    file_storage.save(os.path.join(UPLOAD_FOLDER, name))
    return f"uploads/covers/{name}", None


BOOK_FIELDS = ("title", "author", "isbn", "category", "publisher",
               "publication_year", "total_copies", "description")


@app.route("/admin/books")
@admin_required
def manage_books():
    result = webdata.list_books(
        search=request.args.get("q", "").strip(),
        category=request.args.get("category", "").strip(),
        availability=request.args.get("availability", ""),
        sort=request.args.get("sort", "newest"),
        page=page_number(), per_page=10)
    return render_template("admin/books.html", result=result,
                           categories=webdata.list_categories(),
                           args=request.args)


@app.route("/admin/books/new", methods=["GET", "POST"])
@admin_required
def add_book():
    form = {"total_copies": "1"}

    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in BOOK_FIELDS}
        cover, error = save_cover(request.files.get("cover"))

        if error:
            flash(error, "danger")
        else:
            success, message, book_id = webdata.create_book(
                form["title"], form["author"], form["isbn"], form["category"],
                form["publisher"], form["publication_year"],
                form["total_copies"], form["description"], cover)
            if success:
                flash(message, "success")
                return redirect(url_for("manage_books"))
            flash(message, "danger")

    return render_template("admin/book_form.html", form=form, book=None,
                           categories=webdata.list_categories())


@app.route("/admin/books/<int:book_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_book(book_id):
    book = webdata.get_book(book_id)
    if book is None:
        abort(404)

    form = {k: ("" if book[k] is None else str(book[k])) for k in BOOK_FIELDS}

    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in BOOK_FIELDS}
        cover, error = save_cover(request.files.get("cover"))

        if error:
            flash(error, "danger")
        else:
            success, message = webdata.edit_book(
                book_id, form["title"], form["author"], form["isbn"],
                form["category"], form["publisher"], form["publication_year"],
                form["total_copies"], form["description"], cover,
                clear_cover=bool(request.form.get("remove_cover")))
            if success:
                flash(message, "success")
                return redirect(url_for("manage_books"))
            flash(message, "danger")

    return render_template("admin/book_form.html", form=form, book=book,
                           categories=webdata.list_categories())


@app.post("/admin/books/<int:book_id>/delete")
@admin_required
def delete_book(book_id):
    success, message = books_module.delete_book(book_id)
    flash(message, "success" if success else "danger")
    return redirect(url_for("manage_books"))


# ==========================================================
# 9. ADMIN - MEMBERS
# ==========================================================

MEMBER_FIELDS = ("name", "email", "phone", "address")


@app.route("/admin/members")
@admin_required
def manage_members():
    result = webdata.list_members(search=request.args.get("q", "").strip(),
                                  page=page_number(), per_page=12)
    return render_template("admin/members.html", result=result, args=request.args)


@app.route("/admin/members/new", methods=["GET", "POST"])
@admin_required
def add_member():
    form = {}

    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in MEMBER_FIELDS}
        success, message = members_module.register_member(
            form["name"], form["email"], form["phone"], form["address"], "")
        if success:
            flash(message, "success")
            return redirect(url_for("manage_members"))
        flash(message, "danger")

    return render_template("admin/member_form.html", form=form, member=None)


@app.route("/admin/members/<int:member_id>")
@admin_required
def member_detail(member_id):
    member = webdata.get_member(member_id)
    if member is None:
        abort(404)
    return render_template(
        "admin/member_detail.html", member=member,
        summary=webdata.member_summary(member_id),
        loans=webdata.list_loans("all", member_id=member_id, per_page=50)["items"])


@app.route("/admin/members/<int:member_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_member(member_id):
    member = webdata.get_member(member_id)
    if member is None:
        abort(404)

    form = {k: member[k] or "" for k in MEMBER_FIELDS}

    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in MEMBER_FIELDS}
        success, message = members_module.update_member(
            member_id, form["name"], form["email"], form["phone"], form["address"])
        if success:
            flash(message, "success")
            return redirect(url_for("member_detail", member_id=member_id))
        flash(message, "danger")

    return render_template("admin/member_form.html", form=form, member=member)


@app.post("/admin/members/<int:member_id>/delete")
@admin_required
def delete_member(member_id):
    success, message = members_module.delete_member(member_id)
    flash(message, "success" if success else "danger")
    return redirect(url_for("manage_members"))


@app.post("/admin/members/<int:member_id>/create-login")
@admin_required
def create_member_login(member_id):
    member = webdata.get_member(member_id)
    if member is None:
        abort(404)

    success, message = authentication.register_member_account(
        member_id, member["email"] or "",
        request.form.get("username", ""), request.form.get("password", ""))
    flash(message, "success" if success else "danger")
    return redirect(url_for("member_detail", member_id=member_id))


# ==========================================================
# 10. ADMIN - LOANS (issue / return / renew)
# ==========================================================

@app.route("/admin/loans")
@admin_required
def manage_loans():
    status = request.args.get("status", "active")
    if status not in ("active", "overdue", "returned", "all"):
        status = "active"

    result = webdata.list_loans(status, request.args.get("q", "").strip(),
                                page=page_number(), per_page=12)
    return render_template(
        "admin/loans.html", result=result, status=status, args=request.args,
        book_options=webdata.available_rows(),
        member_options=webdata.query(
            "SELECT member_id, name FROM members ORDER BY name COLLATE NOCASE"))


@app.post("/admin/loans/issue")
@admin_required
def issue_loan():
    try:
        book_id = int(request.form.get("book_id", ""))
        member_id = int(request.form.get("member_id", ""))
    except ValueError:
        flash("Please choose both a book and a member.", "danger")
        return redirect(url_for("manage_loans"))

    success, result = webdata.issue_checked(book_id, member_id)

    if success:
        flash(f"Issued “{result['title']}” to {result['member_name']}. "
              f"Due on {result['due_date']}.", "success")
    else:
        flash(result, "danger")

    return redirect(url_for("manage_loans"))


@app.post("/admin/loans/<int:loan_id>/return")
@admin_required
def return_loan(loan_id):
    success, result = loans_module.return_book(loan_id)

    if success:
        message = f"Book returned on {result['return_date']}."
        if result["fine"]:
            message += (f" Late by {result['overdue_days']} day(s) — "
                        f"fine {webdata_inr(result['fine'])} to collect.")
        flash(message, "warning" if result["fine"] else "success")
    else:
        flash(result, "danger")

    return redirect(request.referrer or url_for("manage_loans"))


def webdata_inr(value):
    return inr_filter(value)


@app.post("/admin/loans/<int:loan_id>/renew")
@admin_required
def renew_loan_admin(loan_id):
    success, message = webdata.renew_loan(loan_id)
    flash(message, "success" if success else "danger")
    return redirect(request.referrer or url_for("manage_loans"))


# ==========================================================
# 11. ADMIN - REPORTS + CSV EXPORT
# ==========================================================

def report_data(name):
    """Return (title, headers, rows) for a report."""
    today = webdata.today_text()

    if name == "available":
        rows = webdata.available_rows()
        return ("Available books",
                ["ID", "Title", "Author", "Category", "Total", "Available"],
                [[r["book_id"], r["title"], r["author"], r["category"] or "—",
                  r["total_copies"], r["available_copies"]] for r in rows])

    if name == "issued":
        rows = webdata.list_loans("active", per_page=100000)["items"]
        return ("Issued books",
                ["Loan", "Book", "Member", "Issued", "Due", "Status"],
                [[r["loan_id"], r["title"], r["member_name"], r["issue_date"],
                  r["due_date"], "Overdue" if r["is_overdue"] else "On time"]
                 for r in rows])

    if name == "overdue":
        rows = webdata.list_loans("overdue", per_page=100000)["items"]
        return ("Overdue books",
                ["Loan", "Book", "Member", "Phone", "Due", "Days late", "Fine (₹)"],
                [[r["loan_id"], r["title"], r["member_name"],
                  r["member_phone"] or "—", r["due_date"], r["overdue_days"],
                  r["current_fine"]] for r in rows])

    if name == "fines":
        rows = webdata.fine_rows()
        return ("Fines collected",
                ["Loan", "Book", "Member", "Due", "Returned", "Fine (₹)"],
                [[r["loan_id"], r["title"], r["member_name"], r["due_date"],
                  r["return_date"], r["fine_amount"]] for r in rows])

    return None


REPORT_TABS = [("available", "Available"), ("issued", "Issued"),
               ("overdue", "Overdue"), ("fines", "Fines")]


@app.route("/admin/reports")
@admin_required
def reports_page():
    tab = request.args.get("tab", "available")
    data = report_data(tab) or report_data("available")
    if report_data(tab) is None:
        tab = "available"
    title, headers, rows = data
    return render_template("admin/reports.html", tab=tab, tabs=REPORT_TABS,
                           title=title, headers=headers, rows=rows,
                           stats=webdata.overview_stats())


@app.route("/admin/reports/export/<name>.csv")
@admin_required
def export_report(name):
    data = report_data(name)
    if data is None:
        abort(404)

    title, headers, rows = data
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)

    for row in rows:
        # A leading = + - @ could run as a formula in Excel: neutralise it
        writer.writerow([("'" + c) if isinstance(c, str) and c[:1] in "=+-@" else c
                         for c in row])

    return Response(
        "\ufeff" + buffer.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=library_{name}.csv"})


# ==========================================================
# 12. ADMIN - API KEYS + DOCUMENTATION
# ==========================================================

@app.route("/admin/api")
@admin_required
def api_page():
    new_key = session.pop("new_api_key", None)
    return render_template("admin/api.html", keys=apikeys.list_keys(),
                           new_key=new_key,
                           base_url=request.host_url.rstrip("/"))


@app.post("/admin/api/create")
@admin_required
def api_create_key():
    success, result = apikeys.create_key(request.form.get("name", ""))
    if success:
        session["new_api_key"] = result
        flash("API key created. Copy it now — it will not be shown again.",
              "success")
    else:
        flash(result, "danger")
    return redirect(url_for("api_page"))


@app.post("/admin/api/<int:key_id>/revoke")
@admin_required
def api_revoke_key(key_id):
    flash("API key revoked." if apikeys.revoke_key(key_id) else "Key not found.",
          "success")
    return redirect(url_for("api_page"))


@app.post("/admin/api/<int:key_id>/delete")
@admin_required
def api_delete_key(key_id):
    flash("API key deleted." if apikeys.delete_key(key_id) else "Key not found.",
          "success")
    return redirect(url_for("api_page"))


# ==========================================================
# 13. MEMBER AREA
# ==========================================================

@app.route("/member/dashboard")
@member_required
def member_dashboard():
    member = webdata.get_member(g.user["member_id"])
    if member is None:
        abort(404)

    member_id = member["member_id"]
    return render_template(
        "member/dashboard.html", member=member,
        stats=webdata.member_summary(member_id),
        current=webdata.list_loans("active", member_id=member_id, per_page=50)["items"],
        history=webdata.list_loans("returned", member_id=member_id, per_page=50)["items"],
        suggestions=webdata.list_books(sort="popular", availability="available",
                                       per_page=4)["items"])


@app.post("/member/loans/<int:loan_id>/renew")
@member_required
def member_renew(loan_id):
    success, message = webdata.renew_loan(loan_id, g.user["member_id"])
    flash(message, "success" if success else "danger")
    return redirect(url_for("member_dashboard"))


@app.route("/member/profile", methods=["GET", "POST"])
@member_required
def member_profile():
    member_id = g.user["member_id"]
    member = webdata.get_member(member_id)
    if member is None:
        abort(404)

    form = {k: member[k] or "" for k in MEMBER_FIELDS}

    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in MEMBER_FIELDS}
        success, message = members_module.update_member(
            member_id, form["name"], form["email"], form["phone"], form["address"])
        flash(message, "success" if success else "danger")
        if success:
            return redirect(url_for("member_profile"))

    return render_template("member/profile.html", member=member, form=form)


@app.post("/account/password")
@login_required
def change_password():
    if request.form.get("new_password") != request.form.get("confirm_password"):
        flash("The two new passwords are not the same.", "danger")
    else:
        success, message = authentication.change_password(
            g.user["user_id"], request.form.get("old_password", ""),
            request.form.get("new_password", ""))
        flash(message, "success" if success else "danger")

    return redirect(request.referrer or dashboard_url_for(g.user))


# ==========================================================
# 14. ERROR PAGES
# ==========================================================

def error_response(code, message, title):
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": message}), code
    return render_template("errors/error.html", code=code, title=title,
                           message=message), code


@app.errorhandler(400)
def bad_request(error):
    if getattr(error, "description", "") == "csrf":
        return error_response(400, "Your form has expired. Go back, refresh "
                              "the page and try again.", "Form expired")
    return error_response(400, "That request could not be understood.", "Bad request")


@app.errorhandler(403)
def forbidden(error):
    return error_response(403, "You do not have permission to open this page.",
                          "Shelf locked")


@app.errorhandler(404)
def not_found(error):
    return error_response(404, "We couldn't find the page you were looking for.",
                          "Page not found")


@app.errorhandler(405)
def method_not_allowed(error):
    return error_response(405, "This action is not allowed here.", "Not allowed")


@app.errorhandler(413)
def too_large(error):
    return error_response(413, "That file is too large (3 MB maximum).", "File too large")


@app.errorhandler(sqlite3.Error)
@app.errorhandler(500)
def server_error(error):
    app.logger.exception("Server error: %s", error)
    return error_response(500, "Something went wrong on our side. Please try again.",
                          "Server error")


# ==========================================================
# 15. COMMAND LINE + RUN
# ==========================================================

@app.cli.command("create-admin")
def create_admin_command():
    """Create the first admin account:  flask --app app create-admin"""
    username = click.prompt("Admin username")
    password = click.prompt("Password (at least 6 characters)",
                            hide_input=True, confirmation_prompt=True)
    click.echo(authentication.create_admin(username, password)[1])


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
    )
