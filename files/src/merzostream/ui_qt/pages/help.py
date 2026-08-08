from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QTextBrowser, QVBoxLayout, QWidget

from ..help_system import _format_help, page_help


PAGE_ORDER = [
    ("home", "Главная"), ("stream", "Управление трансляцией"), ("player", "Медиаплеер"),
    ("background_music", "Фоновая музыка"), ("chat", "Единый чат"), ("ai", "AI Producer"),
    ("auth", "Авторизация"), ("designer", "Дизайнер"), ("settings", "Настройки"),
    ("logs", "Логи"), ("updates", "Обновления"), ("help", "Инструкция"),
    ("developer", "Разработка"), ("about", "О программе"),
]


class HelpPage(QWidget):
    def __init__(self, theme: dict):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 26)
        root.setSpacing(10)
        title = QLabel("Инструкция / Help Center")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Встроенная инструкция по всей программе. Найди нужный модуль, прочитай пошаговую настройку и скопируй адрес прямо из текста.")
        subtitle.setWordWrap(True); subtitle.setObjectName("pageSubtitle")
        root.addWidget(title); root.addWidget(subtitle)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по справке: OBS, музыка, обновления, Twitch, очередь…")
        self.search.textChanged.connect(self._filter)
        root.addWidget(self.search)

        body = QHBoxLayout(); body.setSpacing(12)
        self.sections = QListWidget(); self.sections.setFixedWidth(230)
        self.sections.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for page_id, label in PAGE_ORDER:
            item = QListWidgetItem(label); item.setData(Qt.UserRole, page_id); self.sections.addItem(item)
        self.sections.currentItemChanged.connect(self._show)
        body.addWidget(self.sections)

        self.browser = QTextBrowser(); self.browser.setOpenExternalLinks(True)
        self.browser.setTextInteractionFlags(Qt.TextBrowserInteraction | Qt.TextSelectableByKeyboard)
        body.addWidget(self.browser, 1)
        root.addLayout(body, 1)
        self.sections.setCurrentRow(0)

    def _show(self, current, _previous=None):
        if not current: return
        page_id = str(current.data(Qt.UserRole) or "home")
        self.browser.setHtml(_format_help(page_id))

    def _filter(self, text: str):
        needle = str(text or "").strip().casefold()
        first_visible = None
        for i in range(self.sections.count()):
            item = self.sections.item(i)
            page_id = str(item.data(Qt.UserRole) or "")
            info = page_help(page_id)
            blob = " ".join([
                item.text(), str(info.get("title", "")), str(info.get("purpose", "")),
                " ".join(map(str, info.get("steps", []) if isinstance(info.get("steps", []), list) else [])),
                " ".join(map(str, info.get("important", []) if isinstance(info.get("important", []), list) else [])),
            ]).casefold()
            visible = not needle or needle in blob
            item.setHidden(not visible)
            if visible and first_visible is None:
                first_visible = item
        if first_visible is not None and (self.sections.currentItem() is None or self.sections.currentItem().isHidden()):
            self.sections.setCurrentItem(first_visible)
