"""API key management for the REST API.

A key looks like  lib_AbCd...  It is shown to the admin ONCE when it is
created.  Only a SHA-256 hash is stored in the database, so a leaked
database never leaks a working key.
"""

import hashlib
import secrets
import sqlite3
from datetime import datetime

from database import get_connection, close_connection

KEY_PREFIX = "lib_"


def _hash(key):
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_key(name):
    """Create a new key. Returns (True, plain_key) or (False, message)."""
    name = (name or "").strip()

    if not name:
        return False, "Please give the key a name (for example: Mobile app)."

    if len(name) > 60:
        return False, "Key name must be 60 characters or fewer."

    plain = KEY_PREFIX + secrets.token_urlsafe(32)

    connection = get_connection()
    if connection is None:
        return False, "Could not connect to the database."

    try:
        connection.execute(
            "INSERT INTO api_keys (name, key_hash, key_prefix, created_at) "
            "VALUES (?, ?, ?, ?)",
            (name, _hash(plain), plain[:10], _now()),
        )
        connection.commit()
        return True, plain
    except sqlite3.Error as error:
        return False, f"Database error: {error}"
    finally:
        close_connection(connection)


def verify_key(plain):
    """Return the key record (dict) if the key is valid and active."""
    if not plain or not plain.startswith(KEY_PREFIX):
        return None

    connection = get_connection(dict_rows=True)
    if connection is None:
        return None

    try:
        row = connection.execute(
            "SELECT key_id, name, key_prefix FROM api_keys "
            "WHERE key_hash = ? AND active = 1",
            (_hash(plain),),
        ).fetchone()

        if row is None:
            return None

        connection.execute(
            "UPDATE api_keys SET last_used = ? WHERE key_id = ?",
            (_now(), row["key_id"]),
        )
        connection.commit()
        return dict(row)
    except sqlite3.Error:
        return None
    finally:
        close_connection(connection)


def list_keys():
    connection = get_connection(dict_rows=True)
    if connection is None:
        return []
    try:
        rows = connection.execute(
            "SELECT key_id, name, key_prefix, created_at, last_used, active "
            "FROM api_keys ORDER BY key_id DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error:
        return []
    finally:
        close_connection(connection)


def revoke_key(key_id):
    connection = get_connection()
    if connection is None:
        return False
    try:
        cur = connection.execute(
            "UPDATE api_keys SET active = 0 WHERE key_id = ?", (key_id,))
        connection.commit()
        return cur.rowcount == 1
    except sqlite3.Error:
        return False
    finally:
        close_connection(connection)


def delete_key(key_id):
    connection = get_connection()
    if connection is None:
        return False
    try:
        cur = connection.execute(
            "DELETE FROM api_keys WHERE key_id = ?", (key_id,))
        connection.commit()
        return cur.rowcount == 1
    except sqlite3.Error:
        return False
    finally:
        close_connection(connection)
