"""Local account passwords and revocable bearer sessions."""

import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.schemas.student import ProfileUpdate, RegisterRequest, TeacherRegisterRequest
from app.services.database import database


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"


def _check_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, digest = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        calculated = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(calculated, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


def _public_user(row) -> dict:
    return {key: row[key] for key in ("id", "email", "role", "display_name", "preferred_language", "learning_goals")}


def _issue_session(db, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    db.execute("INSERT INTO auth_sessions VALUES (?, ?, ?, ?)", (
        hashlib.sha256(token.encode()).hexdigest(), user_id, now(),
        (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    ))
    return token


def _register(request: RegisterRequest, role: str) -> dict:
    user_id = str(uuid4())
    with database() as db:
        try:
            db.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)", (user_id, request.email, _hash_password(request.password), role, now()))
            db.execute("INSERT INTO student_profiles VALUES (?, ?, 'english', '', ?)", (user_id, request.display_name, now()))
        except sqlite3.IntegrityError as error:
            raise ValueError("An account with this email already exists") from error
        token = _issue_session(db, user_id)
    return {"token": token, "user": get_user(token)}


def register(request: RegisterRequest) -> dict:
    return _register(request, "student")


def register_teacher(request: TeacherRegisterRequest) -> dict:
    configured = os.environ.get("TEACHER_REGISTRATION_CODE", "")
    if not configured:
        raise PermissionError("Teacher registration is not configured on this server")
    if not hmac.compare_digest(request.teacher_code, configured):
        raise PermissionError("Invalid teacher registration code")
    return _register(request, "teacher")


def login(email: str, password: str) -> dict | None:
    with database() as db:
        row = db.execute("SELECT id, password_hash FROM users WHERE email = ? COLLATE NOCASE", (email.strip(),)).fetchone()
        if not row or not _check_password(password, row["password_hash"]):
            return None
        token = _issue_session(db, row["id"])
    return {"token": token, "user": get_user(token)}


def get_user(token: str) -> dict | None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with database() as db:
        row = db.execute("SELECT u.id, u.email, u.role, p.display_name, p.preferred_language, p.learning_goals "
                         "FROM auth_sessions s JOIN users u ON u.id = s.user_id "
                         "JOIN student_profiles p ON p.user_id = u.id "
                         "WHERE s.token_hash = ? AND s.expires_at > ?", (token_hash, now())).fetchone()
        return _public_user(row) if row else None


def logout(token: str) -> None:
    with database() as db:
        db.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (hashlib.sha256(token.encode()).hexdigest(),))


def update_profile(user_id: str, update: ProfileUpdate) -> dict:
    with database() as db:
        db.execute("UPDATE student_profiles SET display_name = ?, preferred_language = ?, learning_goals = ?, updated_at = ? WHERE user_id = ?",
                   (update.display_name, update.preferred_language, update.learning_goals, now(), user_id))
        row = db.execute("SELECT u.id, u.email, u.role, p.display_name, p.preferred_language, p.learning_goals FROM users u JOIN student_profiles p ON p.user_id = u.id WHERE u.id = ?", (user_id,)).fetchone()
        return _public_user(row)
