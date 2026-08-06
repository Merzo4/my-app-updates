from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..core.config import save
from ..core.event_log import log
from ..core.database import database
from ..core.paths import PLAYER_CONFIG, PLAYER_STATE


@dataclass(slots=True)
class QueueItem:
    id: str
    url: str
    title: str
    user: str
    webpage_url: str = ""
    duration: int = 0
    view_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueueItem":
        return cls(
            id=str(data.get("id", "")),
            url=str(data.get("url", "")),
            title=str(data.get("title", "Без названия")),
            user=str(data.get("user", "Зритель")),
            webpage_url=str(data.get("webpage_url", "")),
            duration=int(data.get("duration", 0) or 0),
            view_count=int(data.get("view_count", 0) or 0),
        )


class QueueManager:
    """Потокобезопасная очередь с автоматическим сохранением между запусками."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.lock = threading.RLock()
        self.items: list[QueueItem] = []
        self.current: QueueItem | None = None
        self.user_last_order: dict[str, float] = {}
        self.resume_position_seconds = 0.0
        self.was_paused = False
        self.was_stopped = False
        self._last_saved_position = -1
        self._load_state()

    def _save_config(self) -> None:
        save(PLAYER_CONFIG, self.config)

    @staticmethod
    def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)

    def _load_state(self) -> None:
        if not PLAYER_STATE.exists():
            return
        try:
            with PLAYER_STATE.open("r", encoding="utf-8") as file:
                data = json.load(file)
            current = data.get("current")
            queue = data.get("queue", [])
            self.current = QueueItem.from_dict(current) if isinstance(current, dict) else None
            self.items = [QueueItem.from_dict(x) for x in queue if isinstance(x, dict)]
            self.user_last_order = {
                str(k): float(v) for k, v in dict(data.get("user_last_order", {})).items()
            }
            self.resume_position_seconds = max(0.0, float(data.get("position_seconds", 0.0) or 0.0))
            self.was_paused = bool(data.get("paused", False))
            self.was_stopped = bool(data.get("stopped", False))
            log(
                "PLAYER",
                f"Восстановлено после прошлого запуска: текущий трек — "
                f"{'да' if self.current else 'нет'}, в очереди — {len(self.items)}.",
            )
        except Exception as exc:
            log("PLAYER", f"Не удалось восстановить очередь: {exc}")

    def save_state(
        self,
        position_seconds: float | None = None,
        paused: bool | None = None,
        stopped: bool | None = None,
        force: bool = False,
    ) -> None:
        with self.lock:
            if position_seconds is not None:
                position_seconds = max(0.0, float(position_seconds))
                rounded = int(position_seconds)
                if not force and rounded == self._last_saved_position:
                    return
                self.resume_position_seconds = position_seconds
                self._last_saved_position = rounded
            if paused is not None:
                self.was_paused = bool(paused)
            if stopped is not None:
                self.was_stopped = bool(stopped)

            payload = {
                "saved_at": time.time(),
                "current": self.current.to_dict() if self.current else None,
                "queue": [item.to_dict() for item in self.items],
                "user_last_order": self.user_last_order,
                "position_seconds": self.resume_position_seconds,
                "paused": self.was_paused,
                "stopped": self.was_stopped,
            }
            try:
                self._atomic_json_write(PLAYER_STATE, payload)
            except Exception as exc:
                log("PLAYER", f"Не удалось сохранить очередь: {exc}")

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "current": self.current.to_dict() if self.current else None,
                "queue": [item.to_dict() for item in self.items],
                "queue_length": len(self.items),
                "position_seconds": self.resume_position_seconds,
            }


    def _safe_int(self, key: str, default: int, minimum: int | None = None) -> int:
        try:
            value = int(self.config.get(key, default))
        except (TypeError, ValueError):
            value = default
        return max(minimum, value) if minimum is not None else value

    def validate_request(self, user: str, video_id: str, duration: int, view_count: int) -> tuple[bool, str]:
        with self.lock:
            blocked_users = {str(x).lower() for x in self.config.get("blocked_users", [])}
            blocked_videos = {str(x) for x in self.config.get("blocked_videos", [])}
            if user.lower() in blocked_users:
                return False, f"❌ @{user}, вы находитесь в списке блокировок."
            if video_id in blocked_videos:
                return False, f"❌ @{user}, это видео заблокировано."
            global_limit = self._safe_int("global_limit", 20, 1)
            if len(self.items) >= global_limit:
                return False, f"❌ @{user}, очередь заполнена. Максимум: {global_limit}."
            user_limit = self._safe_int("user_limit", 3, 1)
            user_count = sum(1 for item in self.items if item.user.lower() == user.lower())
            if self.current and self.current.user.lower() == user.lower():
                user_count += 1
            if user_count >= user_limit:
                return False, f"❌ @{user}, ваш лимит заказов: {user_limit}."
            cooldown_minutes = self._safe_int("user_cooldown_min", 5, 0)
            last_order = self.user_last_order.get(user.lower(), 0.0)
            remaining = cooldown_minutes * 60 - (time.time() - last_order)
            if remaining > 0:
                wait_minutes = max(1, int(remaining // 60) + 1)
                return False, f"❌ @{user}, подождите ещё {wait_minutes} мин."
            max_duration = self._safe_int("max_duration_min", 10, 1) * 60
            if duration and duration > max_duration:
                return False, f"❌ @{user}, видео длиннее {max_duration // 60} мин."
            min_views = self._safe_int("min_views", 0, 0)
            if view_count < min_views:
                return False, f"❌ @{user}, нужно минимум {min_views} просмотров."
            return True, ""

    def add(self, item: QueueItem) -> int:
        with self.lock:
            self.items.append(item)
            self.user_last_order[item.user.lower()] = time.time()
            self.save_state(force=True)
            try:
                database.add_media_event(item.id, item.title, item.user, "queued")
            except Exception:
                pass
            return len(self.items)

    def pop_next(self) -> QueueItem | None:
        with self.lock:
            if not self.items:
                return None
            self.current = self.items.pop(0)
            self.resume_position_seconds = 0.0
            self.was_paused = False
            self.was_stopped = False
            self.save_state(force=True)
            return self.current

    def get(self, index: int) -> QueueItem | None:
        with self.lock:
            return self.items[index] if 0 <= index < len(self.items) else None

    def remove(self, index: int) -> QueueItem | None:
        with self.lock:
            if 0 <= index < len(self.items):
                item = self.items.pop(index)
                self.save_state(force=True)
                return item
            return None

    def clear(self) -> int:
        with self.lock:
            count = len(self.items)
            self.items.clear()
            self.save_state(force=True)
            return count

    def set_current(self, item: QueueItem | None) -> None:
        with self.lock:
            self.current = item
            self.save_state(force=True)

    def finish_current(self) -> QueueItem | None:
        with self.lock:
            previous = self.current
            self.current = None
            self.resume_position_seconds = 0.0
            self.was_paused = False
            self.was_stopped = False
            self.save_state(force=True)
            if previous:
                try:
                    database.add_media_event(previous.id, previous.title, previous.user, "played")
                except Exception:
                    pass
            return previous

    def block_user(self, user: str) -> int:
        normalized = user.strip()
        if not normalized:
            return 0
        with self.lock:
            blocked = self.config.setdefault("blocked_users", [])
            if normalized.lower() not in {str(x).lower() for x in blocked}:
                blocked.append(normalized)
            before = len(self.items)
            self.items[:] = [item for item in self.items if item.user.lower() != normalized.lower()]
            removed = before - len(self.items)
            self._save_config()
            self.save_state(force=True)
            return removed

    def block_video(self, video_id: str) -> int:
        normalized = video_id.strip()
        if not normalized:
            return 0
        with self.lock:
            blocked = self.config.setdefault("blocked_videos", [])
            if normalized not in {str(x) for x in blocked}:
                blocked.append(normalized)
            before = len(self.items)
            self.items[:] = [item for item in self.items if item.id != normalized]
            removed = before - len(self.items)
            self._save_config()
            self.save_state(force=True)
            return removed
