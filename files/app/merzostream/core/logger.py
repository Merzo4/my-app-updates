from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .database import database
from .paths import LOGS_DIR


class AppLogger:
    def __init__(self):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger("MerzoStreamSuite")
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            handler = RotatingFileHandler(
                LOGS_DIR / "merzostream.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
            )
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s"))
            self._logger.addHandler(handler)

    def write(self, module: str, message: str, level: str = "INFO") -> None:
        numeric = getattr(logging, level.upper(), logging.INFO)
        self._logger.log(numeric, f"[{module}] {message}")
        try:
            database.add_app_event(module, level.upper(), message)
        except Exception:
            pass


app_logger = AppLogger()
