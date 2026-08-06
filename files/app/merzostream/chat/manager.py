from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any, Callable

from ..core.database import database
from ..core.event_log import log


@dataclass
class ChatMessage:
    id: int
    created_at: float
    platform: str
    user: str
    message: str
    color: str = ""
    badges: str = ""
    avatar: str = ""


class ChatManager:
    """Потокобезопасная единая лента сообщений из всех платформ."""

    ALLOWED_PLATFORMS = {"twitch", "youtube", "vk", "kick", "rutony", "streamerbot", "other"}

    def __init__(self, max_messages: int = 300) -> None:
        self.max_messages = max(20, int(max_messages))
        self._lock = threading.RLock()
        self._messages: deque[ChatMessage] = deque(maxlen=self.max_messages)
        self._subscribers: list[Callable[[dict[str, Any]], None]] = []
        self._next_id = 1
        self._restore()

    @staticmethod
    def normalize_platform(value: str) -> str:
        platform = str(value or "other").strip().lower()
        aliases = {
            "yt": "youtube", "youtube live": "youtube", "vk video": "vk",
            "vkvideo": "vk", "vk video live": "vk", "twitch.tv": "twitch",
            "kick.com": "kick", "streamer.bot": "streamerbot",
        }
        platform = aliases.get(platform, platform)
        return platform if platform in ChatManager.ALLOWED_PLATFORMS else "other"

    def _restore(self) -> None:
        try:
            rows = list(reversed(database.recent_chat(self.max_messages)))
        except Exception:
            rows = []
        with self._lock:
            for row in rows:
                item = ChatMessage(
                    id=int(row.get("id") or self._next_id),
                    created_at=float(row.get("created_at") or time.time()),
                    platform=self.normalize_platform(row.get("platform", "other")),
                    user=str(row.get("username", "Зритель")),
                    message=str(row.get("message", "")),
                    color=str(row.get("color", "")),
                    badges=str(row.get("badges", "")),
                    avatar=str(row.get("avatar", "")),
                )
                self._messages.append(item)
                self._next_id = max(self._next_id, item.id + 1)

    def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass

    def add(
        self,
        platform: str,
        user: str,
        message: str,
        color: str = "",
        badges: str = "",
        avatar: str = "",
    ) -> dict[str, Any]:
        clean_message = " ".join(str(message or "").replace("\x00", "").split())
        if not clean_message:
            raise ValueError("Сообщение пустое")
        clean_user = str(user or "Зритель").strip()[:80] or "Зритель"
        clean_platform = self.normalize_platform(platform)
        now = time.time()
        with self._lock:
            item = ChatMessage(
                id=self._next_id,
                created_at=now,
                platform=clean_platform,
                user=clean_user,
                message=clean_message[:1000],
                color=str(color or "")[:32],
                badges=str(badges or "")[:300],
                avatar=str(avatar or "")[:1000],
            )
            self._next_id += 1
            self._messages.append(item)
            subscribers = list(self._subscribers)
        try:
            database.add_chat_message(
                platform=item.platform,
                username=item.user,
                message=item.message,
                color=item.color,
                badges=item.badges,
                avatar=item.avatar,
            )
        except Exception as exc:
            log("CHAT", f"Не удалось сохранить сообщение: {exc}", "WARNING")
        payload = asdict(item)
        for callback in subscribers:
            try:
                callback(payload)
            except Exception:
                pass
        log("CHAT", f"[{item.platform}] {item.user}: {item.message}", "INFO")
        return payload

    def snapshot(self, limit: int = 80, platforms: set[str] | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(300, int(limit)))
        with self._lock:
            items = list(self._messages)
        if platforms:
            normalized = {self.normalize_platform(value) for value in platforms}
            items = [item for item in items if item.platform in normalized]
        return [asdict(item) for item in items[-limit:]]

    def clear(self, clear_history: bool = False) -> None:
        with self._lock:
            self._messages.clear()
        if clear_history:
            try:
                database.clear_chat_messages()
            except Exception:
                pass
        log("CHAT", "Единый чат очищен", "SUCCESS")


chat_manager = ChatManager()
