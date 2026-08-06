from __future__ import annotations

from datetime import datetime
from threading import RLock

from .logger import app_logger
from .paths import LOGS_DIR

_lock = RLock()
_subs = []
LOG_FILE = LOGS_DIR / "MerzoStreamSuite.log"


def subscribe(fn):
    _subs.append(fn)


def log(module, message, level="INFO"):
    line = f"[{datetime.now():%H:%M:%S}] [{module}] {message}"
    with _lock:
        try:
            with LOG_FILE.open("a", encoding="utf-8") as file:
                file.write(line + "\n")
        except Exception:
            pass
        try:
            app_logger.write(str(module), str(message), str(level))
        except Exception:
            pass
        for fn in list(_subs):
            try:
                fn(line)
            except Exception:
                pass
    print(line)
