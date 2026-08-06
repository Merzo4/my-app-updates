from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .database import database
from .event_bus import event_bus
from .paths import LOGS_DIR


LEVELS = {"DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"}


class AppLogger:
    def __init__(self) -> None:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.path = LOGS_DIR / "merzostream.log"
        self._logger = logging.getLogger("MerzoStreamSuite")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False
        if not self._logger.handlers:
            handler = RotatingFileHandler(self.path, maxBytes=3_000_000, backupCount=8, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
            self._logger.addHandler(handler)

    def write(self, module: str, message: str, level: str = "INFO", **extra: Any) -> None:
        module = str(module or "APP").upper()
        level = str(level or "INFO").upper()
        if level not in LEVELS:
            level = "INFO"
        numeric = logging.INFO if level == "SUCCESS" else getattr(logging, level, logging.INFO)
        text = str(message)
        self._logger.log(numeric, f"[{module}] {text}")
        try:
            database.add_app_event(module, level, text)
        except Exception:
            pass
        event_bus.publish("log.created", module=module, level=level, message=text, extra=extra)

    def export_path(self) -> Path:
        return self.path


app_logger = AppLogger()
