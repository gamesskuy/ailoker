"""Auth sederhana: registrasi/login dengan PBKDF2-HMAC-SHA256 (hashlib stdlib),
session via cookie HttpOnly yang disimpan di DB."""
import hashlib
import hmac
import os
import secrets

from . import db

APP_SECRET = os.environ.get("APP_SECRET", "dev-secret-change-me")
SESSION_COOKIE = "ailoker_session"


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return dk.hex(), salt


def verify_password(password: str, salt: str, expected: str) -> bool:
    dk, _ = hash_password(password, salt)
    return hmac.compare_digest(dk, expected)


def create_user(email, password, role, name, company_name=None):
    pw_hash, salt = hash_password(password)
    conn = db.connect()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, salt, role, name, company_name, created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (email.strip().lower(), pw_hash, salt, role, name.strip(),
             (company_name or "").strip() or None, db.now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_by_email(email):
    conn = db.connect()
    try:
        return conn.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    finally:
        conn.close()


def get_user(user_id):
    conn = db.connect()
    try:
        return conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    finally:
        conn.close()


def create_session(user_id) -> str:
    token = secrets.token_urlsafe(32)
    conn = db.connect()
    try:
        conn.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?,?,?)",
                     (token, user_id, db.now()))
        conn.commit()
        return token
    finally:
        conn.close()


def get_session_user(token):
    if not token:
        return None
    conn = db.connect()
    try:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token=?",
            (token,),
        ).fetchone()
        return row
    finally:
        conn.close()


def delete_session(token):
    conn = db.connect()
    try:
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn.commit()
    finally:
        conn.close()
