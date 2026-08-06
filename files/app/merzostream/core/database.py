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


database = Database()
