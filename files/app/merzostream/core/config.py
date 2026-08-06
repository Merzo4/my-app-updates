"""Совместимый слой конфигурации поверх нового SettingsManager.

Старые модули продолжают использовать load_app/load_stream/load_player/save,
но все значения теперь проходят безопасную нормализацию и имеют defaults.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import APP_CONFIG, PLAYER_CONFIG, STREAM_CONFIG
from .settings_manager import DEFAULTS, settings

APP_DEFAULTS = DEFAULTS["app"]
STREAM_DEFAULTS = DEFAULTS["stream"]
PLAYER_DEFAULTS = DEFAULTS["player"]

_PATH_TO_SECTION = {
    APP_CONFIG: "app",
    STREAM_CONFIG: "stream",
    PLAYER_CONFIG: "player",
}


def load(path: Path, defaults: dict[str, Any]) -> dict[str, Any]:
    section = _PATH_TO_SECTION.get(path)
    if section:
        return settings.load(section, force=True)
    data = dict(defaults)
    if path.exists():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                data.update(stored)
        except Exception:
            pass
    return data


def save(path: Path, data: dict[str, Any]) -> None:
    section = _PATH_TO_SECTION.get(path)
    if section:
        settings.save(section, data)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_app() -> dict[str, Any]:
    return settings.load("app", force=True)


def load_stream() -> dict[str, Any]:
    return settings.load("stream", force=True)


def load_player() -> dict[str, Any]:
    return settings.load("player", force=True)
