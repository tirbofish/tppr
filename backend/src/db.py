import sqlite3 as sql
from logging import Logger
from shared import DB_PATH


def prepare(log: Logger):
    conn = sql.connect(DB_PATH)
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


def get_user_by_email(email):
    conn = sql.connect(DB_PATH)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()

    conn.close()

    return dict(row) if row else None
