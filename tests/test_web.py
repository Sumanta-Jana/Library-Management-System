"""End-to-end tests for the web site and REST API.

Run from the project folder:   python -m unittest discover -s tests -v
"""
import io
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TMP = tempfile.mkdtemp()

import database  # noqa: E402
# Always use a throw-away database, never the real library.db
database.DB_PATH = os.path.join(_TMP, "test.db")
database.create_tables()

import authentication  # noqa: E402
import app as library_app  # noqa: E402

authentication.create_admin("boss", "secret123")
authentication.register_new_member("Test Reader", "reader", "reader@example.com",
                                   "9876543210", "Town", "reader123")


def token(client, path="/login"):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def login(client, user, password):
    return client.post("/login", data={"username": user, "password": password,
                                       "csrf_token": token(client)})


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        library_app.app.config["TESTING"] = True

    def setUp(self):
        self.c = library_app.app.test_client()

    def admin(self):
        self.assertEqual(login(self.c, "boss", "secret123").status_code, 302)

    def post(self, path, data=None, **kw):
        data = dict(data or {})
        data["csrf_token"] = token(self.c, "/admin/dashboard")
        return self.c.post(path, data=data, **kw)

    # ---- public + security
    def test_public_pages(self):
        for p in ("/", "/books", "/login", "/register"):
            self.assertEqual(self.c.get(p).status_code, 200, p)
        self.assertEqual(self.c.get("/missing").status_code, 404)

    def test_csrf_blocks_post_without_token(self):
        r = self.c.post("/login", data={"username": "boss", "password": "secret123"})
        self.assertEqual(r.status_code, 400)

    def test_admin_pages_need_login_and_role(self):
        self.assertEqual(self.c.get("/admin/dashboard").status_code, 302)
        login(self.c, "reader", "reader123")
        self.assertEqual(self.c.get("/admin/dashboard").status_code, 403)
        self.assertEqual(self.c.get("/member/dashboard").status_code, 200)
        self.assertEqual(self.c.get("/member/profile").status_code, 200)

    def test_wrong_password(self):
        r = login(self.c, "boss", "nope")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Incorrect username or password", r.get_data(as_text=True))

    # ---- admin workflow
    def test_full_admin_workflow(self):
        self.admin()
        r = self.post("/admin/books/new", {
            "title": "Flask Tales", "author": "A. Writer", "isbn": "9781234567897",
            "category": "Tech", "publisher": "P", "publication_year": "2020",
            "total_copies": "2", "description": "Nice"})
        self.assertEqual(r.status_code, 302)
        book = database.get_connection().execute(
            "SELECT book_id, available_copies FROM books WHERE isbn='9781234567897'").fetchone()
        self.assertEqual(book[1], 2)

        r = self.post("/admin/books/new", {
            "title": "Dup", "author": "x", "isbn": "9781234567897", "total_copies": "1"},
            follow_redirects=True)
        self.assertIn("already exists", r.get_data(as_text=True))

        r = self.post("/admin/members/new", {"name": "Mem Ber", "email": "mem@example.com",
                                             "phone": "9000000000", "address": "X"})
        self.assertEqual(r.status_code, 302)
        member = database.get_connection().execute(
            "SELECT member_id FROM members WHERE email='mem@example.com'").fetchone()[0]

        r = self.post("/admin/loans/issue", {"book_id": book[0], "member_id": member},
                      follow_redirects=True)
        self.assertIn("Issued", r.get_data(as_text=True))
        avail = database.get_connection().execute(
            "SELECT available_copies FROM books WHERE book_id=?", (book[0],)).fetchone()[0]
        self.assertEqual(avail, 1)

        loan = database.get_connection().execute(
            "SELECT loan_id FROM loans WHERE book_id=?", (book[0],)).fetchone()[0]
        r = self.post(f"/admin/loans/{loan}/renew", follow_redirects=True)
        self.assertIn("Renewed", r.get_data(as_text=True))

        # cannot delete a book that is out
        r = self.post(f"/admin/books/{book[0]}/delete", follow_redirects=True)
        self.assertIn("active loans", r.get_data(as_text=True))

        r = self.post(f"/admin/loans/{loan}/return", follow_redirects=True)
        self.assertIn("returned", r.get_data(as_text=True).lower())
        r = self.post(f"/admin/loans/{loan}/return", follow_redirects=True)
        self.assertIn("already returned", r.get_data(as_text=True))

        for p in ("/admin/dashboard", "/admin/books", "/admin/members",
                  f"/admin/members/{member}", "/admin/loans?status=all",
                  "/admin/reports?tab=issued", "/admin/reports/export/available.csv",
                  "/admin/api", f"/books/{book[0]}"):
            self.assertEqual(self.c.get(p).status_code, 200, p)

    def test_overdue_fine(self):
        self.admin()
        conn = database.get_connection()
        conn.execute("INSERT INTO books (title,author,isbn,total_copies,available_copies) "
                     "VALUES ('Late','L','1111111111',1,0)")
        bid = conn.execute("SELECT book_id FROM books WHERE isbn='1111111111'").fetchone()[0]
        mid = conn.execute("SELECT member_id FROM members LIMIT 1").fetchone()[0]
        conn.execute("INSERT INTO loans (book_id,member_id,issue_date,due_date,status) "
                     "VALUES (?,?,'2020-01-01','2020-01-15','Issued')", (bid, mid))
        conn.commit(); conn.close()
        self.assertIn("overdue", self.c.get("/admin/loans?status=overdue").get_data(as_text=True).lower())
        lid = database.get_connection().execute(
            "SELECT loan_id FROM loans WHERE book_id=?", (bid,)).fetchone()[0]
        r = self.post(f"/admin/loans/{lid}/return", follow_redirects=True)
        self.assertIn("fine", r.get_data(as_text=True))
        fine = database.get_connection().execute(
            "SELECT fine_amount FROM loans WHERE loan_id=?", (lid,)).fetchone()[0]
        self.assertGreater(fine, 0)

    def test_cover_upload_rejects_non_image(self):
        self.admin()
        r = self.post("/admin/books/new", {
            "title": "Pic", "author": "a", "isbn": "2222222222", "total_copies": "1",
            "cover": (io.BytesIO(b"<?php evil ?>"), "x.php")},
            content_type="multipart/form-data", follow_redirects=True)
        self.assertIn("JPG, PNG, GIF or WEBP", r.get_data(as_text=True))


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ok, cls.key = __import__("apikeys").create_key("tests")
        assert ok

    def setUp(self):
        self.c = library_app.app.test_client()
        self.h = {"X-API-Key": self.key}

    def test_health_is_public(self):
        r = self.c.get("/api/v1/health")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["ok"])

    def test_key_required(self):
        self.assertEqual(self.c.get("/api/v1/books").status_code, 401)
        self.assertEqual(self.c.get("/api/v1/books", headers={"X-API-Key": "lib_bad"}).status_code, 401)
        r = self.c.get("/api/v1/books", headers={"Authorization": "Bearer " + self.key})
        self.assertEqual(r.status_code, 200)

    def test_book_crud_and_loans(self):
        r = self.c.post("/api/v1/books", headers=self.h, json={
            "title": "API Book", "author": "Bot", "isbn": "9780306406157", "total_copies": 3})
        self.assertEqual(r.status_code, 201, r.get_json())
        bid = r.get_json()["data"]["book_id"]

        r = self.c.put(f"/api/v1/books/{bid}", headers=self.h, json={"category": "Robots"})
        self.assertEqual(r.get_json()["data"]["category"], "Robots")

        r = self.c.post("/api/v1/members", headers=self.h, json={"name": "Api Mem", "email": "api@example.com"})
        self.assertEqual(r.status_code, 201, r.get_json())
        mid = r.get_json()["data"]["member_id"]

        r = self.c.post("/api/v1/loans", headers=self.h, json={"book_id": bid, "member_id": mid})
        self.assertEqual(r.status_code, 201, r.get_json())
        lid = r.get_json()["data"]["loan_id"]

        self.assertEqual(self.c.post(f"/api/v1/loans/{lid}/renew", headers=self.h).status_code, 200)
        self.assertEqual(self.c.delete(f"/api/v1/books/{bid}", headers=self.h).status_code, 409)
        self.assertEqual(self.c.post(f"/api/v1/loans/{lid}/return", headers=self.h).status_code, 200)
        self.assertEqual(self.c.post(f"/api/v1/loans/{lid}/return", headers=self.h).status_code, 409)
        self.assertEqual(self.c.get("/api/v1/stats", headers=self.h).status_code, 200)
        self.assertEqual(self.c.get("/api/v1/books/99999", headers=self.h).status_code, 404)
        self.assertEqual(self.c.get("/api/v1/nothing", headers=self.h).get_json()["ok"], False)

    def test_revoked_key_stops_working(self):
        import apikeys
        ok, key = apikeys.create_key("temp")
        kid = [k for k in apikeys.list_keys() if k["name"] == "temp"][0]["key_id"]
        self.assertEqual(self.c.get("/api/v1/stats", headers={"X-API-Key": key}).status_code, 200)
        apikeys.revoke_key(kid)
        self.assertEqual(self.c.get("/api/v1/stats", headers={"X-API-Key": key}).status_code, 401)


if __name__ == "__main__":
    unittest.main()
