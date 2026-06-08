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
                    user_id   INTEGER PRIMARY KEY,
                    added_at  TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pending (
                    user_id   INTEGER PRIMARY KEY,
                    created_at TEXT NOT NULL
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

    def get_all_subscribers(self) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT user_id, added_at FROM subscribers ORDER BY added_at DESC"
            ).fetchall()
        return [{"user_id": r[0], "added_at": r[1]} for r in rows]

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
