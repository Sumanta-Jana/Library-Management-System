"""REST API  (/api/v1/...)

Authentication: send your API key in one of these headers
    X-API-Key: lib_xxxxxxxx
    Authorization: Bearer lib_xxxxxxxx
Keys are created by an admin on the "API & Keys" page.

Every response is JSON:
    {"ok": true,  "data": ...}
    {"ok": false, "error": "message"}
"""

import sqlite3
from functools import wraps

from flask import Blueprint, g, jsonify, request

import apikeys
import loans as loans_module
import authentication
import books as books_module
import members as members_module
import webdata

api = Blueprint("api", __name__, url_prefix="/api/v1")


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------

def ok(data=None, status=200, **extra):
    body = {"ok": True, "data": data}
    body.update(extra)
    return jsonify(body), status


def fail(message, status=400):
    return jsonify({"ok": False, "error": message}), status


def api_key_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        key = request.headers.get("X-API-Key", "").strip()

        if not key:
            header = request.headers.get("Authorization", "")
            if header.lower().startswith("bearer "):
                key = header[7:].strip()

        if not key:
            return fail("Missing API key. Send it in the X-API-Key header.", 401)

        record = apikeys.verify_key(key)

        if record is None:
            return fail("Invalid or revoked API key.", 401)

        g.api_key = record
        return view(*args, **kwargs)

    return wrapped


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def text(data, name):
    value = data.get(name, "")
    return "" if value is None else str(value)


def int_arg(name, default, minimum=1, maximum=100):
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def page_meta(result):
    return {"page": result["page"], "pages": result["pages"],
            "total": result["total"], "per_page": result["per_page"]}


def book_json(row):
    return {k: row[k] for k in (
        "book_id", "title", "author", "isbn", "category", "publisher",
        "publication_year", "total_copies", "available_copies",
        "description")}


# ----------------------------------------------------------
# Public
# ----------------------------------------------------------

@api.get("/health")
def health():
    try:
        webdata.scalar("SELECT COUNT(*) FROM books")
        return ok({"status": "running", "database": "connected"})
    except sqlite3.Error:
        return fail("Database is not reachable.", 503)


# ----------------------------------------------------------
# Books
# ----------------------------------------------------------

@api.get("/books")
@api_key_required
def list_books():
    availability = "available" if request.args.get("available") in ("1", "true") else ""
    result = webdata.list_books(
        search=request.args.get("q", "").strip(),
        category=request.args.get("category", "").strip(),
        availability=availability,
        sort=request.args.get("sort", "title"),
        page=int_arg("page", 1, 1, 100000),
        per_page=int_arg("per_page", 20),
    )
    return ok([book_json(b) for b in result["items"]], meta=page_meta(result))


@api.get("/books/<int:book_id>")
@api_key_required
def get_book(book_id):
    book = webdata.get_book(book_id)
    if book is None:
        return fail("Book not found.", 404)
    return ok(book_json(book))


@api.post("/books")
@api_key_required
def create_book():
    d = body()
    success, message, book_id = webdata.create_book(
        text(d, "title"), text(d, "author"), text(d, "isbn"),
        text(d, "category"), text(d, "publisher"),
        text(d, "publication_year"), text(d, "total_copies") or "1",
        text(d, "description"),
    )
    if not success:
        return fail(message, 400)
    return ok(book_json(webdata.get_book(book_id)), 201)


@api.put("/books/<int:book_id>")
@api_key_required
def update_book(book_id):
    current = webdata.get_book(book_id)
    if current is None:
        return fail("Book not found.", 404)

    d = body()

    def pick(name):
        return text(d, name) if name in d else str(current[name] or "")

    success, message = webdata.edit_book(
        book_id, pick("title"), pick("author"), pick("isbn"),
        pick("category"), pick("publisher"), pick("publication_year"),
        pick("total_copies"), pick("description"),
    )
    if not success:
        return fail(message, 400)
    return ok(book_json(webdata.get_book(book_id)))


@api.delete("/books/<int:book_id>")
@api_key_required
def delete_book(book_id):
    success, message = books_module.delete_book(book_id)
    if not success:
        return fail(message, 404 if "No book" in message else 409)
    return ok({"deleted": book_id})


# ----------------------------------------------------------
# Members
# ----------------------------------------------------------

def member_json(row):
    return {k: row[k] for k in (
        "member_id", "name", "email", "phone", "address", "join_date")}


@api.get("/members")
@api_key_required
def list_members():
    result = webdata.list_members(
        search=request.args.get("q", "").strip(),
        page=int_arg("page", 1, 1, 100000),
        per_page=int_arg("per_page", 20),
    )
    return ok([member_json(m) for m in result["items"]], meta=page_meta(result))


@api.get("/members/<int:member_id>")
@api_key_required
def get_member(member_id):
    member = webdata.get_member(member_id)
    if member is None:
        return fail("Member not found.", 404)
    data = member_json(member)
    data["summary"] = webdata.member_summary(member_id)
    return ok(data)


@api.post("/members")
@api_key_required
def create_member():
    d = body()
    success, message = members_module.register_member(
        text(d, "name"), text(d, "email"), text(d, "phone"),
        text(d, "address"), text(d, "join_date"))
    if not success:
        return fail(message, 400)

    row = webdata.query_one(
        "SELECT member_id FROM members WHERE email = ?",
        (text(d, "email").strip().lower(),))
    return ok(member_json(webdata.get_member(row["member_id"])), 201)


@api.put("/members/<int:member_id>")
@api_key_required
def update_member(member_id):
    current = webdata.get_member(member_id)
    if current is None:
        return fail("Member not found.", 404)

    d = body()

    def pick(name):
        return text(d, name) if name in d else str(current[name] or "")

    success, message = members_module.update_member(
        member_id, pick("name"), pick("email"), pick("phone"), pick("address"))
    if not success:
        return fail(message, 400)
    return ok(member_json(webdata.get_member(member_id)))


@api.delete("/members/<int:member_id>")
@api_key_required
def delete_member(member_id):
    success, message = members_module.delete_member(member_id)
    if not success:
        return fail(message, 404 if "No member" in message else 409)
    return ok({"deleted": member_id})


# ----------------------------------------------------------
# Loans
# ----------------------------------------------------------

LOAN_FIELDS = ("loan_id", "book_id", "title", "member_id", "member_name",
               "issue_date", "due_date", "return_date", "status", "renewals",
               "overdue_days", "current_fine")


def loan_json(row):
    return {k: row[k] for k in LOAN_FIELDS}


@api.get("/loans")
@api_key_required
def list_loans():
    status = request.args.get("status", "active")
    if status not in ("active", "overdue", "returned", "all"):
        return fail("status must be active, overdue, returned or all.")

    result = webdata.list_loans(
        status=status,
        search=request.args.get("q", "").strip(),
        page=int_arg("page", 1, 1, 100000),
        per_page=int_arg("per_page", 20),
    )
    return ok([loan_json(l) for l in result["items"]], meta=page_meta(result))


@api.post("/loans")
@api_key_required
def issue_loan():
    d = body()
    try:
        book_id, member_id = int(d.get("book_id")), int(d.get("member_id"))
    except (TypeError, ValueError):
        return fail("book_id and member_id must be whole numbers.")

    success, result = webdata.issue_checked(book_id, member_id)
    if not success:
        return fail(result, 409)
    return ok(loan_json(webdata.get_loan(result["loan_id"])), 201)


@api.post("/loans/<int:loan_id>/return")
@api_key_required
def return_loan(loan_id):
    success, result = loans_module.return_book(loan_id)
    if not success:
        return fail(result, 404 if "not found" in result.lower() else 409)
    return ok(result)


@api.post("/loans/<int:loan_id>/renew")
@api_key_required
def renew_loan(loan_id):
    success, message = webdata.renew_loan(loan_id)
    if not success:
        return fail(message, 404 if "not found" in message.lower() else 409)
    return ok(loan_json(webdata.get_loan(loan_id)), message=message)


# ----------------------------------------------------------
# Reports
# ----------------------------------------------------------

@api.get("/stats")
@api_key_required
def stats():
    return ok(webdata.overview_stats())


@api.get("/reports/overdue")
@api_key_required
def overdue_report():
    result = webdata.list_loans("overdue", per_page=1000)
    return ok([loan_json(l) for l in result["items"]])


# ----------------------------------------------------------
# JSON errors for everything under /api/v1
# ----------------------------------------------------------

@api.errorhandler(404)
def api_not_found(error):
    return fail("Endpoint not found.", 404)


@api.errorhandler(405)
def api_method_not_allowed(error):
    return fail("Method not allowed for this endpoint.", 405)


@api.errorhandler(Exception)
def api_error(error):
    from werkzeug.exceptions import HTTPException
    if isinstance(error, HTTPException):
        return fail(error.description, error.code)
    return fail("Server error. Please try again.", 500)
