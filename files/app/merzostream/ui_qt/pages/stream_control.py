from __future__ import annotations

import json
import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.config import save
from ...core.event_log import log
from ...core.paths import CONTENT_DIR, STREAM_CONFIG
from ...core.settings_manager import settings
from ...services.stream import StreamManager


class _StreamSignals(QObject):
    log_line = Signal(str)
    search_done = Signal(list, str)
    update_done = Signal()


class StreamControlPage(QWidget):
    """Настоящая PySide6-страница управления трансляциями."""

    def __init__(
        self,
        theme: dict,
        navigate: Callable[[str], None] | None = None,
        platforms_changed: Callable[[], None] | None = None,
    ):
        super().__init__()
        self.setObjectName("realPage")
        self.theme = theme
        self.navigate = navigate
        self.platforms_changed = platforms_changed
        self.cfg = settings.load("stream", force=True)
        self.manager = StreamManager(self.cfg)
        self.signals = _StreamSignals(self)
        self.signals.log_line.connect(self._write)
        self.signals.search_done.connect(self._finish_search)
        self.signals.update_done.connect(self._finish_update)
        self.platform_checks: dict[str, QCheckBox] = {}
        self._build()

    @staticmethod
    def _card() -> QFrame:
        frame = QFrame()
        frame.setObjectName("sectionCard")
        return frame

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 26)
        root.setSpacing(14)

        title_row = QHBoxLayout()
        title_box = QVBoxLayout()
        heading = QLabel("Управление трансляцией")
        heading.setObjectName("pageTitle")
        subtitle = QLabel("Одно название и категория сразу для всех выбранных платформ.")
        subtitle.setObjectName("pageSubtitle")
        title_box.addWidget(heading)
        title_box.addWidget(subtitle)
        title_row.addLayout(title_box, 1)
        ai_button = QPushButton("AI Producer")
        ai_button.setObjectName("secondaryButton")
        ai_button.clicked.connect(lambda: self.navigate("ai") if self.navigate else None)
        title_row.addWidget(ai_button)
        root.addLayout(title_row)

        form = self._card()
        form_l = QGridLayout(form)
        form_l.setContentsMargins(20, 18, 20, 18)
        form_l.setHorizontalSpacing(12)
        form_l.setVerticalSpacing(9)

        title_label = QLabel("Название трансляции")
        title_label.setObjectName("fieldLabel")
        self.title_entry = QLineEdit()
        self.title_entry.setPlaceholderText("Введите название трансляции")
        self.title_entry.setText(str(self.cfg.get("title", "")))

        game_label = QLabel("Категория / игра")
        game_label.setObjectName("fieldLabel")
        self.game_combo = QComboBox()
        self.game_combo.setEditable(True)
        self.game_combo.addItems(self._games())
        self.game_combo.setCurrentText(str(self.cfg.get("game", "Just Chatting")))
        self.search_button = QPushButton("Найти в Twitch")
        self.search_button.setObjectName("secondaryButton")
        self.search_button.clicked.connect(self.search_categories)

        form_l.addWidget(title_label, 0, 0, 1, 2)
        form_l.addWidget(self.title_entry, 1, 0, 1, 2)
        form_l.addWidget(game_label, 2, 0, 1, 2)
        form_l.addWidget(self.game_combo, 3, 0)
        form_l.addWidget(self.search_button, 3, 1)
        form_l.setColumnStretch(0, 1)
        root.addWidget(form)

        platforms = self._card()
        platforms_l = QVBoxLayout(platforms)
        platforms_l.setContentsMargins(20, 16, 20, 16)
        platforms_l.setSpacing(10)
        p_title = QLabel("Платформы")
        p_title.setObjectName("cardTitle")
        p_hint = QLabel("Выбор сохраняется сразу. В Авторизации будут показаны только выбранные сервисы.")
        p_hint.setObjectName("cardText")
        p_hint.setWordWrap(True)
        platforms_l.addWidget(p_title)
        platforms_l.addWidget(p_hint)

        checks = QHBoxLayout()
        current = self.cfg.get("platforms", {})
        for key, caption in (
            ("twitch", "Twitch"),
            ("youtube", "YouTube"),
            ("vk", "VK Video"),
            ("kick", "Kick"),
        ):
            check = QCheckBox(caption)
            check.setChecked(bool(current.get(key, key != "kick")))
            check.stateChanged.connect(self._platform_selection_changed)
            self.platform_checks[key] = check
            checks.addWidget(check)
        checks.addStretch(1)
        platforms_l.addLayout(checks)
        root.addWidget(platforms)

        self.run_button = QPushButton("ОБНОВИТЬ НА ВЫБРАННЫХ ПЛАТФОРМАХ")
        self.run_button.setObjectName("primaryButton")
        self.run_button.setMinimumHeight(50)
        self.run_button.clicked.connect(self.run_all)
        root.addWidget(self.run_button)

        self.status = QTextEdit()
        self.status.setObjectName("statusBox")
        self.status.setReadOnly(True)
        self.status.setMinimumHeight(170)
        root.addWidget(self.status, 1)
        self._write("Готово к работе. Авторизации и ключи находятся в разделе «Авторизация».")

    def _games(self) -> list[str]:
        try:
            mapping = json.loads((CONTENT_DIR / "games.json").read_text(encoding="utf-8"))
            games = list(mapping.keys())
            if games:
                return games
        except Exception:
            pass
        return ["Just Chatting", "SnowRunner", "Rust", "World of Tanks", "GTA 5 RP"]

    def _write(self, message: str) -> None:
        self.status.append(message)
        bar = self.status.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _selected_platforms(self) -> dict[str, bool]:
        return {key: check.isChecked() for key, check in self.platform_checks.items()}

    def _platform_selection_changed(self) -> None:
        self.cfg = settings.load("stream", force=True)
        self.cfg["platforms"] = self._selected_platforms()
        save(STREAM_CONFIG, self.cfg)
        if self.platforms_changed:
            self.platforms_changed()

    def _save_form(self) -> tuple[str, str, dict[str, bool]]:
        self.cfg = settings.load("stream", force=True)
        title = self.title_entry.text().strip()
        game = self.game_combo.currentText().strip()
        platforms = self._selected_platforms()
        self.cfg["title"] = title
        self.cfg["game"] = game
        self.cfg["platforms"] = platforms
        save(STREAM_CONFIG, self.cfg)
        self.manager = StreamManager(self.cfg)
        return title, game, platforms

    def search_categories(self) -> None:
        query = self.game_combo.currentText().strip()
        if not query:
            self._write("Twitch: введи название игры для поиска.")
            return
        self.search_button.setEnabled(False)
        self.search_button.setText("Поиск...")
        manager = self.manager

        def job() -> None:
            names, result = manager.twitch.search_categories(query)
            log("Twitch", result.message)
            self.signals.search_done.emit(names, result.message)

        threading.Thread(target=job, daemon=True).start()

    def _finish_search(self, names: list, message: str) -> None:
        self.search_button.setEnabled(True)
        self.search_button.setText("Найти в Twitch")
        self._write(f"Twitch: {message}")
        if names:
            self.game_combo.clear()
            self.game_combo.addItems([str(x) for x in names])
            self.game_combo.setCurrentIndex(0)

    def run_all(self) -> None:
        title, game, platforms = self._save_form()
        if not title:
            self._write("Ошибка: название трансляции не заполнено.")
            return
        if not any(platforms.values()):
            self._write("Ошибка: не выбрана ни одна платформа.")
            return

        self.run_button.setEnabled(False)
        self.run_button.setText("ОБНОВЛЕНИЕ...")
        self._write("────────────────────────────────────────")
        self._write(f"Запуск: {game} | {title}")
        manager = self.manager

        def job() -> None:
            tasks = []
            if platforms.get("twitch"):
                tasks.append(("Twitch", lambda: manager.twitch.update(title, game)))
            if platforms.get("youtube"):
                tasks.append(("YouTube", lambda: manager.youtube.update(title, game)))
            if platforms.get("vk"):
                tasks.append(("VK Video", lambda: manager.vk.update(title, game)))
            if platforms.get("kick"):
                tasks.append(("Kick", lambda: manager.kick.update(title, game)))

            for platform, callback in tasks:
                self.signals.log_line.emit(f"{platform}: обновление...")
                try:
                    result = callback()
                    log(platform, result.message)
                    mark = "✅" if result.ok else "❌"
                    self.signals.log_line.emit(f"{mark} {platform}: {result.message}")
                except Exception as exc:
                    log(platform, f"Ошибка: {exc}")
                    self.signals.log_line.emit(f"❌ {platform}: {exc}")
            self.signals.update_done.emit()

        threading.Thread(target=job, daemon=True).start()

    def _finish_update(self) -> None:
        self._write("Глобальная сессия завершена.")
        self.run_button.setEnabled(True)
        self.run_button.setText("ОБНОВИТЬ НА ВЫБРАННЫХ ПЛАТФОРМАХ")
