from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .paths import CONTENT_DIR

DEFAULT_APP_INFO = {
    "name": "MerzoStream Suite",
    "window_title": "MerzoStream Suite — Beta 0.0.2f",
    "version": "0.0.2f",
    "channel": "Beta",
    "author": "Merzo4",
    "sidebar_brand": "MERZOSTREAM",
    "sidebar_subtitle": "SUITE  •  BETA 0.0.2f",
}

DEFAULT_THEME = {
    "appearance": "dark",
    "default_color_theme": "blue",
    "backgrounds": {"main": "", "sidebar": ""},
    "colors": {
        "window": "#17191d", "sidebar": "#202329", "header": "#1e2127",
        "card": "#24282f", "selected": "#1976c9", "hover": "#30353d",
        "text": "#f5f7fa", "muted_text": "#aeb8c4", "nav_text": "#d9e0e8",
        "accent_text": "#7ab8ff", "success": "#49d17d", "input": "#2a2f36",
        "border": "#3a414b", "notice": "#1f2c3a", "notice_text": "#dbeafe",
    },
    "layout": {
        "sidebar_width": 250, "window_width": 1380, "window_height": 900,
        "min_width": 1120, "min_height": 760, "nav_button_height": 42,
        "nav_corner_radius": 8, "content_overlay": "#17191d",
    },
}


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _read_json(path: Path, default: Any) -> Any:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(default, dict) and isinstance(loaded, dict):
            return _merge(default, loaded)
        return loaded
    except (OSError, json.JSONDecodeError, TypeError):
        return deepcopy(default)


def load_json(name: str, default: Any) -> Any:
    return _read_json(CONTENT_DIR / name, default)


def load_app_info() -> dict[str, Any]:
    return load_json("app_info.json", DEFAULT_APP_INFO)


def load_theme(theme_id: str = "dark") -> dict[str, Any]:
    safe_id = theme_id if theme_id.replace("-", "").replace("_", "").isalnum() else "dark"
    theme_path = CONTENT_DIR / "themes" / safe_id / "theme.json"
    if not theme_path.exists():
        theme_path = CONTENT_DIR / "themes" / "dark" / "theme.json"
    return _read_json(theme_path, DEFAULT_THEME)


def load_theme_index() -> dict[str, Any]:
    return load_json("themes/index.json", {"themes": [{"id": "dark", "title": "Тёмная", "description": ""}]})


def load_navigation() -> dict[str, Any]:
    return load_json("navigation.json", {"items": [], "group_order": [], "show_group_separators": True})


def load_dashboard() -> dict[str, Any]:
    return load_json("dashboard.json", {"heading": "MerzoStream Suite", "subtitle": "", "cards": [], "notice": ""})


def load_texts() -> dict[str, Any]:
    return load_json("texts.json", {"status_running": "● Приложение запущено"})
