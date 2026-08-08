from __future__ import annotations

import html
import json
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QPushButton, QSlider, QSpinBox, QTextBrowser, QVBoxLayout, QWidget,
)

from ..core.paths import CONTENT_DIR
from ..core.settings_manager import settings


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


def page_help(page_id: str) -> dict[str, Any]:
    data = _load().get("details", {})
    item = data.get(page_id, {}) if isinstance(data, dict) else {}
    if not isinstance(item, dict):
        item = {}
    result = dict(item)
    result.setdefault("title", page_id)
    result.setdefault("purpose", page_description(page_id))
    return result


def control_help(text: str) -> str:
    data = _load().get("controls", {})
    if isinstance(data, dict):
        normalized = str(text or "").strip()
        for key, value in data.items():
            if str(key).casefold() in normalized.casefold() and str(value).strip():
                return str(value).strip()
    return ""


def _source_items() -> list[dict[str, Any]]:
    try:
        data = json.loads((CONTENT_DIR / "music_sources.json").read_text(encoding="utf-8"))
        items = data.get("sources", []) if isinstance(data, dict) else []
        return [x for x in items if isinstance(x, dict)] if isinstance(items, list) else []
    except Exception:
        return []


def _format_help(page_id: str, extra: dict[str, str] | None = None) -> str:
    extra = extra or {}
    info = page_help(page_id)
    port = int(settings.get("player", "port", 5000))
    music_dir = extra.get("music_dir", "%LOCALAPPDATA%\\MerzoStreamSuite\\music\\youtube_safe")

    def subst(value: str) -> str:
        return str(value).replace("{port}", str(port)).replace("{music_dir}", music_dir)

    chunks = [f"<h2>{html.escape(str(info.get('title', page_id)))}</h2>"]
    purpose = subst(str(info.get("purpose", "")))
    if purpose:
        chunks.append(f"<p><b>Что делает этот раздел</b><br>{html.escape(purpose)}</p>")

    steps = info.get("steps", [])
    if isinstance(steps, list) and steps:
        chunks.append("<p><b>Как пользоваться</b></p><ol>" + "".join(f"<li>{html.escape(subst(str(x)))}</li>" for x in steps) + "</ol>")

    addresses = info.get("addresses", [])
    if isinstance(addresses, list) and addresses:
        chunks.append("<p><b>Адреса и пути — их можно выделять и копировать</b></p>")
        for value in addresses:
            txt = subst(str(value))
            chunks.append(f"<div style='margin:5px 0; padding:7px; background:#101827; border-radius:6px;'><code>{html.escape(txt)}</code></div>")

    important = info.get("important", [])
    if isinstance(important, list) and important:
        chunks.append("<p><b>Важно</b></p><ul>" + "".join(f"<li>{html.escape(subst(str(x)))}</li>" for x in important) + "</ul>")

    if info.get("music_sources"):
        sources = _source_items()
        if sources:
            chunks.append("<p><b>Где брать музыку для стрима</b><br>Условия сайтов могут меняться. Проверяй лицензию выбранного трека перед публикацией.</p>")
            for source in sources:
                name = html.escape(str(source.get("name", "Источник")))
                url = str(source.get("url", ""))
                note = html.escape(str(source.get("note", "")))
                link = f"<a href='{html.escape(url, quote=True)}'>{html.escape(url)}</a>" if url else ""
                chunks.append(f"<p><b>{name}</b><br>{note}<br>{link}</p>")

    return "".join(chunks)


class PageHelpDialog(QDialog):
    def __init__(self, parent: QWidget | None, page_id: str, extra: dict[str, str] | None = None):
        super().__init__(parent)
        self.page_id = page_id
        self.extra = extra or {}
        self.setWindowTitle("MerzoStream Suite — Справка")
        self.resize(760, 650)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setTextInteractionFlags(Qt.TextBrowserInteraction | Qt.TextSelectableByKeyboard)
        browser.setHtml(_format_help(page_id, self.extra))
        self.browser = browser
        layout.addWidget(browser, 1)
        row = QHBoxLayout()
        copy = QPushButton("Копировать весь текст")
        copy.setToolTip("Скопировать всю инструкцию текущего раздела в буфер обмена.")
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(self.browser.toPlainText()))
        close = QPushButton("Закрыть")
        close.clicked.connect(self.accept)
        row.addWidget(copy)
        row.addStretch(1)
        row.addWidget(close)
        layout.addLayout(row)


def show_page_help(parent: QWidget | None, page_id: str, extra: dict[str, str] | None = None) -> None:
    PageHelpDialog(parent, page_id, extra).exec()


def enhance_help(root: QWidget) -> None:
    """Tooltips + selectable/copyable text across the PySide6 interface."""
    for label in root.findChildren(QLabel):
        # Preserve link interaction while making normal labels selectable with mouse/keyboard.
        flags = label.textInteractionFlags() | Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        label.setTextInteractionFlags(flags)
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
