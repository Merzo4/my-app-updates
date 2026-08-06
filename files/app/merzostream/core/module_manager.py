from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ModuleStatus:
    name: str
    loaded: bool
    error: str = ""


class ModuleManager:
    """Безопасно загружает независимые модули, не роняя всё приложение."""

    def __init__(self):
        self.statuses: dict[str, ModuleStatus] = {}

    def load(self, module_name: str) -> Any | None:
        try:
            module = importlib.import_module(module_name)
            self.statuses[module_name] = ModuleStatus(module_name, True)
            return module
        except Exception as exc:
            self.statuses[module_name] = ModuleStatus(module_name, False, str(exc))
            return None


module_manager = ModuleManager()
