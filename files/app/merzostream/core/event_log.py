from __future__ import annotations

from datetime import datetime
from threading import RLock

from .event_bus import event_bus
from .logger import app_logger
from .paths import LOGS_DIR

_lock = RLock()
_subs = []
LOG_FILE = LOGS_DIR / "MerzoStreamSuite.log"


def subscribe(fn):
    if fn not in _subs:
        _subs.append(fn)


def unsubscribe(fn):
    try:
        _subs.remove(fn)
    except ValueError:
        pass


def log(module, message, level="INFO"):
    module = str(module).upper()
    level = str(level).upper()
    line = f"[{datetime.now():%H:%M:%S}] [{level}] [{module}] {message}"
    with _lock:
        try:
            with LOG_FILE.open("a", encoding="utf-8") as file:
                file.write(line + "\n")
        except Exception:
            pass
        try:
            app_logger.write(module, str(message), level)
        except Exception:
            pass
        for fn in list(_subs):
            try:
                fn(line)
            except Exception:
                pass
    event_bus.publish("legacy.log", line=line, module=module, level=level, message=str(message))
    print(line)
