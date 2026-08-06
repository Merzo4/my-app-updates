from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Any, Callable


class EventBus:
    """Небольшая потокобезопасная шина событий для независимых модулей."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._subscribers: dict[str, list[Callable[[str, dict[str, Any]], None]]] = defaultdict(list)

    def subscribe(self, event: str, callback: Callable[[str, dict[str, Any]], None]) -> Callable[[], None]:
        with self._lock:
            if callback not in self._subscribers[event]:
                self._subscribers[event].append(callback)

        def unsubscribe() -> None:
            with self._lock:
                try:
                    self._subscribers[event].remove(callback)
                except (KeyError, ValueError):
                    pass

        return unsubscribe

    def publish(self, event: str, **payload: Any) -> None:
        with self._lock:
            callbacks = list(self._subscribers.get(event, ())) + list(self._subscribers.get("*", ()))
        for callback in callbacks:
            try:
                callback(event, dict(payload))
            except Exception:
                # Ошибка одного подписчика не должна ломать остальные модули.
                continue


event_bus = EventBus()
