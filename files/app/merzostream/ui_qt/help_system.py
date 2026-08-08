from __future__ import annotations

import json
from typing import Any

from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit, QListWidget, QPushButton, QSlider, QSpinBox, QWidget

from ..core.paths import CONTENT_DIR


_FALLBACK_PAGES = {
    "home": "Главный центр: версия, состояние модулей, быстрые действия и список последних изменений.",
    "stream": "Меняет название и категорию на выбранных стрим-платформах.",
    "player": "Очередь зрительских музыкальных/видеозаказов и управление OBS Browser Source /player.",
    "background_music": "Отдельная фоновая музыка для OBS. Можно добавлять локальные файлы и импортировать треки по ссылке.",
    "chat": "Единая точка для будущего объединения чатов Twitch, YouTube, VK и Kick.",
    "ai": "AI-помощник для названий и подготовки контента стрима.",
    "auth": "Авторизация и токены платформ. Показываются сервисы, выбранные в Управлении трансляцией.",
    "designer": "Настройка внешнего вида MerzoStream Suite и выбор темы.",
    "settings": "Общие параметры программы, медиаплеера и вспомогательных модулей.",
    "logs": "Журнал действий и ошибок для проверки того, что происходило внутри программы.",
    "updates": "Проверка GitHub, SHA-256, установка новых файлов, резервная копия и история обновлений.",
    "help": "Справка по основным разделам и настройке программы.",
    "developer": "Служебные параметры разработки и диагностики.",
    "about": "Версия, канал и общая информация о MerzoStream Suite.",
}


def _load() -> dict[str, Any]:
    try:
        value = json.loads((CONTENT_DIR / "help_descriptions.json").read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def page_description(page_id: str) -> str:
    data = _load().get("pages", {})
    if isinstance(data, dict) and str(data.get(page_id, "")).strip():
        return str(data[page_id]).strip()
    return _FALLBACK_PAGES.get(page_id, "Рабочий раздел MerzoStream Suite.")


def control_help(text: str) -> str:
    data = _load().get("controls", {})
    if isinstance(data, dict):
        normalized = str(text or "").strip()
        for key, value in data.items():
            if str(key).casefold() in normalized.casefold() and str(value).strip():
                return str(value).strip()
    return ""


def enhance_help(root: QWidget) -> None:
    """Adds concise tooltips to controls that do not already explain themselves."""
    for button in root.findChildren(QPushButton):
        if button.toolTip().strip():
            continue
        text = button.text().strip()
        hint = control_help(text)
        button.setToolTip(hint or (f"Действие: {text}" if text else "Выполнить действие"))
    for cb in root.findChildren(QCheckBox):
        if not cb.toolTip().strip():
            cb.setToolTip(f"Включает или отключает параметр: {cb.text().strip()}")
    for edit in root.findChildren(QLineEdit):
        if not edit.toolTip().strip():
            edit.setToolTip(edit.placeholderText().strip() or "Поле ввода. Изменение применяется к настройке этого блока.")
    for combo in root.findChildren(QComboBox):
        if not combo.toolTip().strip():
            combo.setToolTip("Выбери один из доступных вариантов этого параметра.")
    for spin in root.findChildren(QSpinBox):
        if not spin.toolTip().strip():
            spin.setToolTip("Числовой параметр. Измени значение в допустимом диапазоне.")
    for slider in root.findChildren(QSlider):
        if not slider.toolTip().strip():
            slider.setToolTip("Ползунок изменяет значение этого параметра.")
    for lst in root.findChildren(QListWidget):
        if not lst.toolTip().strip():
            lst.setToolTip("Список элементов этого блока. Выбери строку, чтобы выполнить действие с ней.")
