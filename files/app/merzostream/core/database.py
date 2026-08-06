from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from .paths import DATA_DIR


class Database:
    def __init__(self, path: Path | None = None):
        self.path = path or (DATA_DIR / "merzostream.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_schema()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._lock, self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS media_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    video_id TEXT,
                    title TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_media_history_created ON media_history(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_media_history_user ON media_history(requested_by);

                CREATE TABLE IF NOT EXISTS app_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    module TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_app_events_created ON app_events(created_at DESC);

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    platform TEXT NOT NULL,
                    username TEXT NOT NULL,
                    message TEXT NOT NULL,
                    color TEXT DEFAULT '',
                    badges TEXT DEFAULT '',
                    avatar TEXT DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_chat_messages_platform ON chat_messages(platform);
                """
            )

    def add_media_event(self, video_id: str, title: str, requested_by: str, action: str, reason: str = "") -> None:
        with self._lock, self.connect() as db:
            db.execute(
                "INSERT INTO media_history(created_at, video_id, title, requested_by, action, reason) VALUES(?,?,?,?,?,?)",
                (time.time(), video_id, title, requested_by, action, reason),
            )

    def add_app_event(self, module: str, level: str, message: str) -> None:
        with self._lock, self.connect() as db:
            db.execute(
                "INSERT INTO app_events(created_at, module, level, message) VALUES(?,?,?,?)",
                (time.time(), module, level, message),
            )

    def recent_media(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock, self.connect() as db:
            rows = db.execute(
                "SELECT * FROM media_history ORDER BY created_at DESC LIMIT ?", (max(1, int(limit)),)
            ).fetchall()
        return [dict(row) for row in rows]

    def recent_app_events(self, limit: int = 500, module: str = "", level: str = "", search: str = "") -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if module:
            clauses.append("module = ?")
            params.append(module.upper())
        if level:
            clauses.append("level = ?")
            params.append(level.upper())
        if search:
            clauses.append("message LIKE ?")
            params.append(f"%{search}%")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(max(1, min(5000, int(limit))))
        with self._lock, self.connect() as db:
            rows = db.execute(
                f"SELECT * FROM app_events{where} ORDER BY created_at DESC LIMIT ?", tuple(params)
            ).fetchall()
        return [dict(row) for row in rows]

    def app_event_filters(self) -> tuple[list[str], list[str]]:
        with self._lock, self.connect() as db:
            modules = [row[0] for row in db.execute("SELECT DISTINCT module FROM app_events ORDER BY module").fetchall()]
            levels = [row[0] for row in db.execute("SELECT DISTINCT level FROM app_events ORDER BY level").fetchall()]
        return modules, levels

    def clear_app_events(self) -> None:
        with self._lock, self.connect() as db:
            db.execute("DELETE FROM app_events")

    def add_chat_message(self, platform: str, username: str, message: str, color: str = "", badges: str = "", avatar: str = "") -> None:
        with self._lock, self.connect() as db:
            db.execute(
                "INSERT INTO chat_messages(created_at, platform, username, message, color, badges, avatar) VALUES(?,?,?,?,?,?,?)",
                (time.time(), platform, username, message, color, badges, avatar),
            )

    def recent_chat(self, limit: int = 300, platform: str = "") -> list[dict[str, Any]]:
        params: list[Any] = []
        where = ""
        if platform:
            where = " WHERE platform = ?"
            params.append(platform.lower())
        params.append(max(1, min(5000, int(limit))))
        with self._lock, self.connect() as db:
            rows = db.execute(
                f"SELECT * FROM chat_messages{where} ORDER BY created_at DESC LIMIT ?", tuple(params)
            ).fetchall()
        return [dict(row) for row in rows]

    def clear_chat_messages(self) -> None:
        with self._lock, self.connect() as db:
            db.execute("DELETE FROM chat_messages")


database = Database()
