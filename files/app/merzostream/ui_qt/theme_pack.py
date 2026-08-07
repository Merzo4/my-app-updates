from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.paths import CONTENT_DIR, GRAPHICS_DIR

DEFAULT_THEME: dict[str, Any] = {
    "id": "merzostream_dark",
    "title": "MerzoStream Dark",
    "colors": {
        "window": "#11151b",
        "sidebar": "#171d25",
        "panel": "#1b222c",
        "card": "#202936",
        "border": "#2f3b49",
        "text": "#f4f7fb",
        "muted": "#9ba9ba",
        "accent": "#2b8cff",
        "success": "#48d17d",
        "warning": "#f3b84b",
        "danger": "#ff6470",
    },
    "layout": {
        "sidebar_width": 230,
        "monitor_width": 270,
        "radius": 12,
        "header_height": 70,
    },
    "assets": {
        "background": "",
        "preview": "",
        "icons_dir": "icons",
    },
    "presentation": {
        "full_window_background": False,
        "background_dimming": 0,
        "sidebar_border": True,
        "monitor_border": True,
    },
}


def _merge(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_qt_theme(theme_id: str) -> dict[str, Any]:
    safe = theme_id if theme_id.replace("-", "").replace("_", "").isalnum() else "merzostream_dark"
    path = CONTENT_DIR / "ui_themes" / safe / "theme.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError
    except Exception:
        payload = {}

    theme = _merge(DEFAULT_THEME, payload)
    theme["theme_dir"] = str(path.parent)
    theme["graphics_dir"] = str(GRAPHICS_DIR / "ui_themes" / safe)
    return theme


def icon_path(theme: dict[str, Any], icon_name: str) -> Path | None:
    icons_dir = str(theme.get("assets", {}).get("icons_dir", "icons"))
    root = Path(theme.get("graphics_dir", "")) / icons_dir
    for suffix in (".svg", ".png", ".webp"):
        candidate = root / f"{icon_name}{suffix}"
        if candidate.exists():
            return candidate
    return None


def background_path(theme: dict[str, Any]) -> Path | None:
    name = str(theme.get("assets", {}).get("background", "")).strip()
    if not name:
        return None
    candidate = Path(theme.get("graphics_dir", "")) / name
    return candidate if candidate.exists() else None


def list_qt_themes() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    root = CONTENT_DIR / "ui_themes"
    if not root.exists():
        return result

    for folder in sorted(root.iterdir()):
        if not folder.is_dir():
            continue
        path = folder / "theme.json"
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue

        theme_id = str(data.get("id") or folder.name).strip()
        preview_name = str(data.get("assets", {}).get("preview", "preview.png"))
        result.append({
            "id": theme_id,
            "title": str(data.get("title") or theme_id),
            "description": str(data.get("description") or ""),
            "preview": str(GRAPHICS_DIR / "ui_themes" / theme_id / preview_name),
        })
    return result
