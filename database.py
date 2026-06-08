import sqlite3
from datetime import datetime


class Database:
    def __init__(self, path: str):
        self.path = path
        self._init()

    def _conn(self):
        return sqlite3.connect(self.path)

    def _init(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS subscribers (
                    user_id    INTEGER PRIMARY KEY,
                    full_name  TEXT,
                    username   TEXT,
                    added_at   TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pending (
                    user_id    INTEGER PRIMARY KEY,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

    # ── Subscribers ──────────────────────────────────────────────────────────
    def is_subscriber(self, user_id: int) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM subscribers WHERE user_id = ?", (user_id,)
            ).fetchone()
        return row is not None

    def add_subscriber(self, user_id: int):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO subscribers (user_id, added_at) VALUES (?, ?)",
                (user_id, datetime.now().strftime("%d.%m.%Y %H:%M"))
            )

    def add_subscriber_with_name(self, user_id: int, full_name: str, username: str):
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO subscribers (user_id, full_name, username, added_at)
                   VALUES (?, ?, ?, ?)""",
                (user_id, full_name, username, datetime.now().strftime("%d.%m.%Y %H:%M"))
            )

    def get_all_subscribers(self) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT user_id, full_name, username, added_at FROM subscribers ORDER BY added_at DESC"
            ).fetchall()
        return [{"user_id": r[0], "full_name": r[1], "username": r[2], "added_at": r[3]} for r in rows]

    def get_subscriber_count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]

    # ── Pending ───────────────────────────────────────────────────────────────
    def has_pending(self, user_id: int) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM pending WHERE user_id = ?", (user_id,)
            ).fetchone()
        return row is not None

    def add_pending(self, user_id: int):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO pending (user_id, created_at) VALUES (?, ?)",
                (user_id, datetime.now().strftime("%d.%m.%Y %H:%M"))
            )

    def remove_pending(self, user_id: int):
        with self._conn() as conn:
            conn.execute("DELETE FROM pending WHERE user_id = ?", (user_id,))

    def get_pending_count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM pending").fetchone()[0]

    # ── Settings ──────────────────────────────────────────────────────────────
    def save_setting(self, key: str, value: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )

    def get_setting(self, key: str):
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else None

    def delete_setting(self, key: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM settings WHERE key = ?", (key,))
