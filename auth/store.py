import hashlib
import hmac
import os
import secrets
import sqlite3
from pathlib import Path

ITERATIONS = 600_000


def _db_path():
    return Path(os.getenv("USERS_DB_PATH", "data/users.db"))


def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "email TEXT NOT NULL UNIQUE, "
        "salt TEXT NOT NULL, "
        "password_hash TEXT NOT NULL)"
    )
    return conn


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS).hex()


def create_user(email, password):
    """Pravi korisnika. Vraća False ako email već postoji."""
    email = email.strip().lower()
    salt = secrets.token_bytes(16)
    conn = _connect()
    try:
        with conn:
            conn.execute(
                "INSERT INTO users (email, salt, password_hash) VALUES (?, ?, ?)",
                (email, salt.hex(), hash_password(password, salt)),
            )
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def verify_user(email, password):
    """Vraća email korisnika ako su podaci ispravni, inače None."""
    email = email.strip().lower()
    conn = _connect()
    try:
        row = conn.execute("SELECT salt, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        conn.close()
    if row is None:
        # Isti posao kao za pravog korisnika, da vrijeme odgovora ne otkriva da li email postoji
        hash_password(password, b"\x00" * 16)
        return None
    salt, stored = row
    if hmac.compare_digest(hash_password(password, bytes.fromhex(salt)), stored):
        return email
    return None
