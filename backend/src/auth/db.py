import sqlite3 as sql
from logging import Logger
from typing import Optional

from shared import DB_PATH


class AuthenticationDB:
    def __init__(self):
        self._db_path = DB_PATH

    def _connect(self, row_factory: bool = False):
        conn = sql.connect(self._db_path)
        if row_factory:
            conn.row_factory = sql.Row
        return conn

    def prepare(self, log: Logger):
        conn = self._connect()
        cur = conn.cursor()
        log.info("Connected to database")

        try:
            cur.execute("PRAGMA foreign_keys = ON;")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    totp_secret TEXT,
                    totp_enabled INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME
                );
                """
            )
            log.info("Users table ready")

            conn.commit()
            log.info("Database schema committed successfully")

        except sql.Error as e:
            conn.rollback()
            log.error(f"Database preparation failed: {e}")
            raise
        finally:
            conn.close()
            log.info("Database connection closed")

    def get_user_by_email(self, email: str) -> Optional[dict]:
        conn = self._connect(row_factory=True)
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cur.fetchone()

        conn.close()
        return dict(row) if row else None

    def get_user_by_email_or_username(self, identifier: str) -> Optional[dict]:
        conn = self._connect(row_factory=True)
        cur = conn.cursor()

        cur.execute(
            "SELECT user_id, username, email, password_hash, totp_secret, totp_enabled "
            "FROM users WHERE email = ? OR username = ?",
            (identifier, identifier),
        )
        row = cur.fetchone()

        conn.close()
        return dict(row) if row else None

    def user_exists(self, email: str, username: str) -> bool:
        conn = self._connect()
        cur = conn.cursor()

        cur.execute(
            "SELECT user_id FROM users WHERE email = ? OR username = ?",
            (email, username),
        )
        exists = cur.fetchone() is not None

        conn.close()
        return exists

    def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        totp_secret: Optional[str] = None,
        totp_enabled: bool = False,
    ) -> int | None:
        conn = self._connect()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO users (username, email, password_hash, totp_secret, totp_enabled) "
            "VALUES (?, ?, ?, ?, ?)",
            (username, email, password_hash, totp_secret, 1 if totp_enabled else 0),
        )
        user_id = cur.lastrowid
        conn.commit()
        conn.close()
        return user_id

    def get_user_by_id(
        self, user_id, fields: Optional[list[str]] = None
    ) -> Optional[dict]:
        conn = self._connect(row_factory=True)
        cur = conn.cursor()

        if fields:
            columns = ", ".join(fields)
        else:
            columns = "*"

        cur.execute(f"SELECT {columns} FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()

        conn.close()
        return dict(row) if row else None

    def is_username_taken(self, username: str, exclude_user_id=None) -> bool:
        """Check if a username is taken, optionally excluding a specific user."""
        conn = self._connect()
        cur = conn.cursor()

        if exclude_user_id is not None:
            cur.execute(
                "SELECT user_id FROM users WHERE username = ? AND user_id != ?",
                (username, exclude_user_id),
            )
        else:
            cur.execute("SELECT user_id FROM users WHERE username = ?", (username,))

        taken = cur.fetchone() is not None
        conn.close()
        return taken

    def update_username(self, user_id, new_username: str) -> None:
        """Update a user's username."""
        conn = self._connect()
        cur = conn.cursor()

        cur.execute(
            "UPDATE users SET username = ? WHERE user_id = ?", (new_username, user_id)
        )
        conn.commit()
        conn.close()

    def update_password(self, user_id, password_hash: str) -> None:
        """Update a user's password hash."""
        conn = self._connect()
        cur = conn.cursor()

        cur.execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (password_hash, user_id),
        )
        conn.commit()
        conn.close()

    def delete_user(self, user_id) -> bool:
        """Delete a user by ID. Returns True if a row was deleted."""
        conn = self._connect()
        cur = conn.cursor()

        cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def update_last_login(self, user_id) -> None:
        """Set last_login to the current timestamp."""
        conn = self._connect()
        cur = conn.cursor()

        cur.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
        conn.close()

    def enable_totp(self, user_id, totp_secret: str) -> None:
        """Enable 2FA for a user with the given TOTP secret."""
        conn = self._connect()
        cur = conn.cursor()

        cur.execute(
            "UPDATE users SET totp_secret = ?, totp_enabled = 1 WHERE user_id = ?",
            (totp_secret, user_id),
        )
        conn.commit()
        conn.close()

    def disable_totp(self, user_id) -> None:
        """Disable 2FA for a user, clearing the TOTP secret."""
        conn = self._connect()
        cur = conn.cursor()

        cur.execute(
            "UPDATE users SET totp_secret = NULL, totp_enabled = 0 WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
        conn.close()
