from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .paths import APP_DATA

PLUGINS_DIR = APP_DATA / "plugins"
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class PluginInfo:
    plugin_id: str
    name: str
    version: str
    path: Path
    enabled: bool = True


class PluginManager:
    """Каркас плагинов. В Beta 0.0.1 только обнаруживает manifest.json."""

    def discover(self) -> list[PluginInfo]:
        result: list[PluginInfo] = []
        for manifest in PLUGINS_DIR.glob("*/manifest.json"):
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                result.append(
                    PluginInfo(
                        plugin_id=str(data.get("id", manifest.parent.name)),
                        name=str(data.get("name", manifest.parent.name)),
                        version=str(data.get("version", "0.0.0")),
                        path=manifest.parent,
                        enabled=bool(data.get("enabled", True)),
                    )
                )
            except Exception:
                continue
        return result


plugin_manager = PluginManager()
