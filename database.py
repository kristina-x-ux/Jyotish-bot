"""
╔══════════════════════════════════════╗
║   БАЗА ДАННЫХ — database.py          ║
╚══════════════════════════════════════╝
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional


class Database:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    birth_date  TEXT,
                    birth_time  TEXT,
                    birth_place TEXT,
                    lagna       TEXT,
                    sun_sign    TEXT,
                    moon_sign   TEXT,
                    moon_nakshatra TEXT,
                    mahadasha   TEXT,
                    antardasha  TEXT,
                    created_at  TEXT DEFAULT (datetime('now')),
                    updated_at  TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    role        TEXT NOT NULL,
                    content     TEXT NOT NULL,
                    created_at  TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_messages_user
                    ON messages(user_id, created_at DESC);
            """)

    def ensure_user(self, user_id: int):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
                (user_id,)
            )

    def get_user(self, user_id: int) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else {}

    def save_user_natal(self, user_id: int, data: dict):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO users (user_id, birth_date, birth_time, birth_place,
                    lagna, sun_sign, moon_sign, moon_nakshatra, mahadasha, antardasha, updated_at)
                VALUES (:user_id, :birth_date, :birth_time, :birth_place,
                    :lagna, :sun_sign, :moon_sign, :moon_nakshatra, :mahadasha, :antardasha,
                    datetime('now'))
                ON CONFLICT(user_id) DO UPDATE SET
                    birth_date     = excluded.birth_date,
                    birth_time     = excluded.birth_time,
                    birth_place    = excluded.birth_place,
                    lagna          = excluded.lagna,
                    sun_sign       = excluded.sun_sign,
                    moon_sign      = excluded.moon_sign,
                    moon_nakshatra = excluded.moon_nakshatra,
                    mahadasha      = excluded.mahadasha,
                    antardasha     = excluded.antardasha,
                    updated_at     = datetime('now')
            """, {"user_id": user_id, **data})

    def save_message(self, user_id: int, role: str, content: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )
            # Хранить только последние 20 сообщений на пользователя
            conn.execute("""
                DELETE FROM messages WHERE id IN (
                    SELECT id FROM messages WHERE user_id = ?
                    ORDER BY created_at DESC LIMIT -1 OFFSET 20
                )
            """, (user_id,))

    def get_history(self, user_id: int, limit: int = 6) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT role, content FROM messages
                WHERE user_id = ?
                ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit)).fetchall()
            return [dict(r) for r in reversed(rows)]
