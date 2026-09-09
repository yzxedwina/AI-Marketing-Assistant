"""Small account/session store for the five-person MVP trial."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "memory.sqlite3"
bearer = HTTPBearer(auto_error=False)


def _db_path() -> Path:
    return Path(os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH)))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), actual_salt, 210_000)
    return actual_salt.hex(), digest.hex()


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    username: str
    display_name: str


class AuthStore:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else _db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES accounts(user_id)
                );
                """
            )

    def create_account(self, user_id: str, username: str, password: str, display_name: str) -> bool:
        salt, password_hash = _hash_password(password)
        with self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM accounts WHERE user_id=? OR username=?", (user_id, username)
            ).fetchone()
            if exists:
                return False
            connection.execute(
                """INSERT INTO accounts(
                    user_id, username, display_name, password_salt,
                    password_hash, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?)""",
                (user_id, username, display_name, salt, password_hash, _now().isoformat()),
            )
        return True

    def authenticate(self, username: str, password: str) -> tuple[str, AuthenticatedUser] | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT user_id, username, display_name, password_salt, password_hash
                FROM accounts WHERE username=? AND is_active=1""",
                (username.strip(),),
            ).fetchone()
            if not row:
                return None
            _, supplied_hash = _hash_password(password, bytes.fromhex(row["password_salt"]))
            if not hmac.compare_digest(supplied_hash, row["password_hash"]):
                return None
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expires_at = _now() + timedelta(days=14)
            connection.execute(
                "INSERT INTO auth_sessions(token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
                (token_hash, row["user_id"], expires_at.isoformat(), _now().isoformat()),
            )
        return token, AuthenticatedUser(row["user_id"], row["username"], row["display_name"])

    def session_user(self, token: str) -> AuthenticatedUser | None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self._connect() as connection:
            row = connection.execute(
                """SELECT a.user_id, a.username, a.display_name, s.expires_at
                FROM auth_sessions s JOIN accounts a ON a.user_id=s.user_id
                WHERE s.token_hash=? AND a.is_active=1""",
                (token_hash,),
            ).fetchone()
            if not row:
                return None
            if datetime.fromisoformat(row["expires_at"]) <= _now():
                connection.execute("DELETE FROM auth_sessions WHERE token_hash=?", (token_hash,))
                return None
        return AuthenticatedUser(row["user_id"], row["username"], row["display_name"])

    def revoke(self, token: str) -> None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self._connect() as connection:
            connection.execute("DELETE FROM auth_sessions WHERE token_hash=?", (token_hash,))

    def seed_from_environment(self) -> int:
        raw = os.getenv("PRESEEDED_ACCOUNTS_JSON", "").strip()
        if not raw:
            return 0
        try:
            accounts = json.loads(raw)
        except json.JSONDecodeError as error:
            raise RuntimeError("PRESEEDED_ACCOUNTS_JSON 不是有效 JSON") from error
        created = 0
        for item in accounts:
            created += int(self.create_account(
                item["user_id"], item["username"], item["password"], item["display_name"]
            ))
        return created


auth_store = AuthStore()
auth_store.seed_from_environment()


def require_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> AuthenticatedUser:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="请先登录")
    user = auth_store.session_user(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return user


def require_same_user(requested_user_id: str, current_user: AuthenticatedUser) -> str:
    if requested_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="不能访问其他账号的数据")
    return current_user.user_id
