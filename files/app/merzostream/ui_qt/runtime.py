from __future__ import annotations

from collections.abc import Callable
from threading import RLock

from ..chat.manager import chat_manager
from ..chat.server import ChatWebServer
from ..core.settings_manager import settings
from ..player.queue_manager import QueueManager
from ..player.web_server import PlayerWebServer


class QtRuntime:
    def __init__(self):
        self._lock = RLock()
        self._callbacks: list[Callable[[], None]] = []
        self.player_config = settings.load("player", force=True)
        self.queue = QueueManager(self.player_config)
        self.player_state = {"url": "", "paused": False, "stopped": False, "time": 0}
        self.player_server = PlayerWebServer(self.queue, self.player_config, self.player_state, self._queue_changed)
        self.chat_server = ChatWebServer(chat_manager, port=5001)
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self.player_server.start()
        self.chat_server.start()

    def subscribe_queue(self, callback: Callable[[], None]) -> None:
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def unsubscribe_queue(self, callback: Callable[[], None]) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def _queue_changed(self) -> None:
        with self._lock:
            callbacks = list(self._callbacks)
        for callback in callbacks:
            try:
                callback()
            except Exception:
                pass


_runtime: QtRuntime | None = None


def get_runtime() -> QtRuntime:
    global _runtime
    if _runtime is None:
        _runtime = QtRuntime()
    _runtime.start()
    return _runtime
