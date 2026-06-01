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
                    active_card_id INTEGER,
                    created_at  TEXT DEFAULT (datetime('now')),
                    updated_at  TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS cards (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    person_name TEXT,
                    birth_date  TEXT,
                    birth_time  TEXT,
                    birth_place TEXT,
                    lagna       TEXT,
                    sun_sign    TEXT,
                    moon_sign   TEXT,
                    moon_nakshatra TEXT,
                    mahadasha   TEXT,
                    antardasha  TEXT,
                    created_at  TEXT DEFAULT (datetime('now'))
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

                CREATE INDEX IF NOT EXISTS idx_cards_user
                    ON cards(user_id);
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

    # ── Карты ──────────────────────────────────────────────────────────
    def save_card(self, user_id: int, data: dict) -> int:
        """Сохраняет новую карту, возвращает её id"""
        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO cards (user_id, person_name, birth_date, birth_time, birth_place,
                    lagna, sun_sign, moon_sign, moon_nakshatra, mahadasha, antardasha)
                VALUES (:user_id, :person_name, :birth_date, :birth_time, :birth_place,
                    :lagna, :sun_sign, :moon_sign, :moon_nakshatra, :mahadasha, :antardasha)
            """, {"user_id": user_id, **data})
            return cursor.lastrowid

    def get_all_cards(self, user_id: int) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM cards WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_card_by_id(self, card_id: int) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM cards WHERE id = ?", (card_id,)
            ).fetchone()
            return dict(row) if row else {}

    def set_active_card(self, user_id: int, card_id: int):
        self.ensure_user(user_id)
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET active_card_id = ? WHERE user_id = ?",
                (card_id, user_id)
            )

    def get_active_card(self, user_id: int) -> dict:
        with self._conn() as conn:
            row = conn.execute("""
                SELECT c.* FROM cards c
                JOIN users u ON u.active_card_id = c.id
                WHERE u.user_id = ?
            """, (user_id,)).fetchone()
            return dict(row) if row else {}

    def delete_card(self, card_id: int, user_id: int):
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM cards WHERE id = ? AND user_id = ?",
                (card_id, user_id)
            )
            # Если удалили активную — сбросить
            conn.execute("""
                UPDATE users SET active_card_id = NULL
                WHERE user_id = ? AND active_card_id = ?
            """, (user_id, card_id))

    # ── Сообщения ──────────────────────────────────────────────────────
    def save_message(self, user_id: int, role: str, content: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )
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

    # Оставляем для совместимости
    def save_user_natal(self, user_id: int, data: dict):
        self.save_card(user_id, data)
    
