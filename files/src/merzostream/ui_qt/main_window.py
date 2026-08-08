from __future__ import annotations

import subprocess
import sys

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from ..core.content import load_app_info, load_navigation
from ..core.paths import bundle_root
from ..core.settings_manager import settings
from .system_monitor import SystemMonitorPanel
from .theme_pack import background_path, icon_path, list_qt_themes, load_qt_theme
from .pages.authorization import AuthorizationPage
from .pages.stream_control import StreamControlPage
from .pages.home import HomePage
from .pages.media_player import MediaPlayerPage
from .pages.background_music import BackgroundMusicPage
from .pages.chat_center import ChatCenterPage
from .pages.ai_producer import AIProducerPage
from .pages.designer import DesignerPage
from .pages.settings import SettingsPage
from .pages.logs import LogsPage
from .pages.updates import UpdatesPage
from .pages.help import HelpPage
from .pages.developer import DeveloperPage
from .pages.about import AboutPage
from .runtime import get_runtime
from .help_system import enhance_help, page_description, show_page_help


class SkinRoot(QWidget):
    def __init__(self, theme: dict):
        super().__init__()
        self.theme = theme
        self._background = QPixmap()
        path = background_path(theme)
        if path is not None:
            self._background.load(str(path))

    def paintEvent(self, event):
        c = self.theme["colors"]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(str(c.get("window", "#071019"))))
        grad.setColorAt(1.0, QColor("#040812"))
        painter.fillRect(self.rect(), grad)

        if not self._background.isNull():
            scaled = self._background.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            sx = max(0, (scaled.width() - self.width()) // 2)
            sy = max(0, (scaled.height() - self.height()) // 2)
            painter.setOpacity(0.88)
            painter.drawPixmap(self.rect(), scaled, scaled.rect().adjusted(sx, sy, -sx, -sy))
            painter.setOpacity(1.0)

        dim = int(self.theme.get("presentation", {}).get("background_dimming", 0))
        if dim > 0:
            painter.fillRect(self.rect(), QColor(0, 0, 0, max(0, min(220, dim))))

        glow = QLinearGradient(0, 0, self.width(), 0)
        glow.setColorAt(0.0, QColor(255, 255, 255, 8))
        glow.setColorAt(0.5, QColor(255, 255, 255, 22))
        glow.setColorAt(1.0, QColor(255, 255, 255, 8))
        painter.fillRect(0, 0, self.width(), 110, glow)


class InfoCard(QFrame):
    def __init__(self, title: str, body: str):
        super().__init__()
        self.setObjectName("contentCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        h = QLabel(title)
        h.setObjectName("cardTitle")
        t = QLabel(body)
        t.setWordWrap(True)
        t.setObjectName("cardText")
        layout.addWidget(h)
        layout.addWidget(t)


class PlaceholderPage(QWidget):
    def __init__(self, title: str, subtitle: str):
        super().__init__()
        self.setObjectName("pageContainer")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 26)
        layout.setSpacing(14)

        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        text = QLabel(subtitle)
        text.setWordWrap(True)
        text.setObjectName("pageSubtitle")

        hero = QFrame()
        hero.setObjectName("heroCard")
        hero_l = QVBoxLayout(hero)
        hero_l.setContentsMargins(22, 20, 22, 20)
        hero_l.setSpacing(8)
        hero_title = QLabel("MerzoStream Suite")
        hero_title.setObjectName("heroTitle")
        hero_body = QLabel(
            "Теперь тема оформляет настоящий интерфейс, а не подменяет его картинкой. "
            "Следующий шаг — наполнить реальные модули и дать дизайнеру возможность конструировать своё оформление."
        )
        hero_body.setWordWrap(True)
        hero_body.setObjectName("heroText")
        hero_l.addWidget(hero_title)
        hero_l.addWidget(hero_body)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        cards = [
            ("Тема", "Фон художественный, а панели, меню и карточки собираются кодом PySide6."),
            ("Sidebar", "Иконки и пункты меню настоящие, поэтому тема может менять стиль, не ломая структуру."),
            ("Dashboard", "Справа всегда виден мониторинг ПК — это реальный блок, а не часть изображения."),
            ("Следующий этап", "После этой базы можно делать редактор темы: свои фоны, кнопки, цвета и пакеты иконок."),
        ]
        for i, (a, b) in enumerate(cards):
            card = InfoCard(a, b)
            grid.addWidget(card, i // 2, i % 2)

        layout.addWidget(heading)
        layout.addWidget(text)
        layout.addWidget(hero)
        layout.addLayout(grid)
        layout.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_info = load_app_info()
        ui_cfg = settings.load("ui", force=True)
        self.theme = load_qt_theme(str(ui_cfg.get("qt_theme_id", "merzostream_dark")))
        self.runtime = get_runtime()
        self.setWindowTitle(f"MerzoStream Suite — {self.app_info.get('channel')} {self.app_info.get('version')}")
        self.resize(1536, 930)
        self.setMinimumSize(1220, 760)
        self._build()
        self._apply_theme()
        enhance_help(self)

    def _build(self):
        root = SkinRoot(self.theme)
        root.setObjectName("skinRoot")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 14, 14, 10)
        outer.setSpacing(10)

        body = QHBoxLayout()
        body.setSpacing(12)
        outer.addLayout(body, 1)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(int(self.theme["layout"].get("sidebar_width", 230)))
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(16, 16, 16, 16)
        side.setSpacing(8)
        brand = QLabel("MERZOSTREAM")
        brand.setObjectName("brand")
        version = QLabel(f"SUITE • {self.app_info.get('version')}")
        version.setObjectName("versionLabel")
        side.addWidget(brand)
        side.addWidget(version)
        side.addSpacing(8)

        self.nav = QListWidget()
        self.nav.setObjectName("navigation")
        self.nav.setIconSize(QSize(20, 20))
        self.nav.setSpacing(4)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.nav.setTextElideMode(Qt.ElideRight)
        self.nav.setWordWrap(False)
        self.nav.setToolTip("Навигация MerzoStream Suite. Длинные названия теперь не создают горизонтальную прокрутку.")
        for item in load_navigation().get("items", []):
            if not item.get("enabled", True):
                continue
            row = QListWidgetItem(item.get("title", item.get("id", "")))
            row.setData(Qt.UserRole, item.get("id"))
            row.setToolTip(page_description(str(item.get("id", ""))))
            path = icon_path(self.theme, item.get("id", ""))
            if path:
                row.setIcon(QIcon(str(path)))
            self.nav.addItem(row)
        side.addWidget(self.nav, 1)

        self.theme_label = QLabel("Оформление")
        self.theme_label.setObjectName("themeLabel")
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("themeCombo")
        self._theme_ids = []
        current_theme_id = str(self.theme.get("id", "merzostream_dark"))
        current_index = 0
        for idx, item in enumerate(list_qt_themes()):
            self.theme_combo.addItem(item["title"])
            self._theme_ids.append(item["id"])
            if item["id"] == current_theme_id:
                current_index = idx
        if self._theme_ids:
            self.theme_combo.setCurrentIndex(current_index)
            self.theme_combo.currentIndexChanged.connect(self.change_theme)
        classic = QPushButton("Классический интерфейс")
        classic.setObjectName("secondaryButton")
        classic.clicked.connect(self.return_to_classic)
        side.addWidget(self.theme_label)
        side.addWidget(self.theme_combo)
        side.addWidget(classic)
        body.addWidget(sidebar)

        center = QFrame()
        center.setObjectName("workspace")
        center_l = QVBoxLayout(center)
        center_l.setContentsMargins(0, 0, 0, 0)
        center_l.setSpacing(10)

        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(int(self.theme["layout"].get("header_height", 72)))
        hl = QHBoxLayout(header)
        hl.setContentsMargins(26, 0, 26, 0)
        self.header_title = QLabel("Главная")
        self.header_title.setObjectName("headerTitle")
        self.header_subtitle = QLabel(page_description("home"))
        self.header_subtitle.setObjectName("headerSubtitle")
        left = QVBoxLayout()
        left.setSpacing(1)
        left.addWidget(self.header_title)
        left.addWidget(self.header_subtitle)
        left_w = QWidget()
        left_w.setLayout(left)
        self.help_button = QPushButton("⚙ Справка")
        self.help_button.setObjectName("helpButton")
        self.help_button.setToolTip("Подробная инструкция по текущей вкладке: назначение, шаги, адреса и важные замечания.")
        self.help_button.clicked.connect(self.open_current_help)
        badge = QLabel("PYSIDE6 • HELP CENTER")
        badge.setObjectName("badge")
        hl.addWidget(left_w)
        hl.addStretch(1)
        hl.addWidget(self.help_button)
        hl.addWidget(badge)
        center_l.addWidget(header)

        page_shell = QFrame()
        page_shell.setObjectName("pageShell")
        ps_l = QVBoxLayout(page_shell)
        ps_l.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.stack.setObjectName("pageStack")
        self.pages_by_id = {}
        for i in range(self.nav.count()):
            item = self.nav.item(i)
            page_id = str(item.data(Qt.UserRole) or "")
            page = self._create_page(page_id, item.text())
            self.pages_by_id[page_id] = page
            self.stack.addWidget(page)
        ps_l.addWidget(self.stack)
        center_l.addWidget(page_shell, 1)
        body.addWidget(center, 1)

        self.monitor = SystemMonitorPanel(self.theme)
        self.monitor.setFixedWidth(int(self.theme["layout"].get("monitor_width", 310)))
        body.addWidget(self.monitor)

        status = QLabel(f"  MerzoStream Suite • {self.app_info.get('version')} • {self.theme.get('title')} • Help Center • Selectable Text • Music Repeat")
        status.setObjectName("statusBar")
        status.setFixedHeight(28)
        outer.addWidget(status)

        self.nav.currentRowChanged.connect(self.change_page)
        if self.nav.count():
            self.nav.setCurrentRow(0)

    def _create_page(self, page_id: str, title: str):
        if page_id == "home":
            return HomePage(self.theme, self.app_info, navigate=self.navigate_to_id)
        if page_id == "stream":
            return StreamControlPage(self.theme, navigate=self.navigate_to_id, platforms_changed=self.refresh_authorization_page)
        if page_id == "player":
            return MediaPlayerPage(self.theme)
        if page_id == "background_music":
            return BackgroundMusicPage(self.theme, open_help=lambda: self.open_help_for("background_music"))
        if page_id == "chat":
            return ChatCenterPage(self.theme)
        if page_id == "ai":
            return AIProducerPage(self.theme, use_title=self.use_ai_title)
        if page_id == "auth":
            return AuthorizationPage(self.theme)
        if page_id == "designer":
            return DesignerPage(self.theme, restart=self._restart)
        if page_id == "settings":
            return SettingsPage(self.theme)
        if page_id == "logs":
            return LogsPage(self.theme)
        if page_id == "updates":
            return UpdatesPage(self.theme, self.app_info, restart=self._restart)
        if page_id == "help":
            return HelpPage(self.theme)
        if page_id == "developer":
            return DeveloperPage(self.theme)
        if page_id == "about":
            return AboutPage(self.theme, self.app_info)
        return PlaceholderPage(title, "Страница подключается к новому интерфейсу.")

    def use_ai_title(self, title: str):
        page = getattr(self, "pages_by_id", {}).get("stream")
        if page is not None and hasattr(page, "title_entry"):
            page.title_entry.setText(title)
        self.navigate_to_id("stream")

    def navigate_to_id(self, page_id: str):
        for row in range(self.nav.count()):
            item = self.nav.item(row)
            if str(item.data(Qt.UserRole) or "") == page_id:
                self.nav.setCurrentRow(row)
                return

    def refresh_authorization_page(self):
        page = getattr(self, "pages_by_id", {}).get("auth")
        if page is not None and hasattr(page, "reload_from_settings"):
            page.reload_from_settings()

    def open_help_for(self, page_id: str):
        page = getattr(self, "pages_by_id", {}).get(page_id)
        extra = {}
        if page is not None and hasattr(page, "help_context"):
            try:
                value = page.help_context()
                if isinstance(value, dict):
                    extra = {str(k): str(v) for k, v in value.items()}
            except Exception:
                extra = {}
        show_page_help(self, page_id, extra)

    def open_current_help(self):
        row = self.nav.currentRow()
        if row < 0:
            return
        item = self.nav.item(row)
        self.open_help_for(str(item.data(Qt.UserRole) or "home"))

    def change_page(self, row: int):
        if row < 0:
            return
        item = self.nav.item(row)
        page_id = str(item.data(Qt.UserRole) or "")
        if page_id == "auth":
            self.refresh_authorization_page()
        self.stack.setCurrentIndex(row)
        self.header_title.setText(item.text())
        self.header_subtitle.setText(page_description(page_id))

    def change_theme(self, index: int):
        if index < 0 or index >= len(getattr(self, "_theme_ids", [])):
            return
        theme_id = self._theme_ids[index]
        if theme_id == str(self.theme.get("id", "")):
            return
        settings.set("ui", "qt_theme_id", theme_id)
        self._restart()

    def return_to_classic(self):
        settings.set("ui", "mode", "classic")
        self._restart()

    def _shutdown_pages(self):
        for page in getattr(self, "pages_by_id", {}).values():
            shutdown = getattr(page, "shutdown", None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception:
                    pass

    def closeEvent(self, event):
        self._shutdown_pages()
        event.accept()

    def _restart(self):
        self._shutdown_pages()
        subprocess.Popen([sys.executable] + sys.argv, cwd=str(bundle_root()))
        QApplication.quit()

    def _apply_theme(self):
        c = self.theme["colors"]
        radius = int(self.theme["layout"].get("radius", 14))
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {c['window']}; }}
            QWidget {{ color: {c['text']}; font-family: 'Segoe UI'; font-size: 13px; }}
            #sidebar, #monitorPanel, #workspace, #header, #pageShell, #contentCard, #metricCard, #heroCard {{
                border: 1px solid {c['border']};
                border-radius: {radius}px;
            }}
            #sidebar {{ background-color: {c['sidebar']}; }}
            #monitorPanel {{ background-color: {c['sidebar']}; }}
            #workspace {{ background-color: rgba(6, 12, 24, 120); }}
            #header {{ background-color: rgba(9, 17, 36, 170); }}
            #pageShell {{ background-color: rgba(5, 10, 22, 72); }}
            #contentCard {{ background-color: rgba(13, 22, 47, 146); }}
            #heroCard {{ background-color: rgba(10, 19, 43, 112); }}
            #metricCard {{ background-color: rgba(13, 22, 47, 138); }}
            #brand {{ font-size: 23px; font-weight: 800; letter-spacing: 0.6px; }}
            #versionLabel {{ color: {c['accent']}; font-weight: 700; }}
            #headerTitle, #pageTitle {{ font-size: 22px; font-weight: 800; }}
            #headerSubtitle, #pageSubtitle, #metricTitle, #cardText, #heroText {{ color: {c['muted']}; }}
            #cardTitle, #heroTitle, #panelHeading {{ font-size: 15px; font-weight: 700; }}
            #heroTitle {{ color: {c.get('accent2', c['accent'])}; font-size: 18px; }}
            #metricValue {{ font-size: 15px; font-weight: 700; }}
            #themeLabel {{ color: {c['muted']}; font-size: 11px; margin-top: 6px; }}
            #themeCombo {{ background-color: rgba(255,255,255,0.04); border: 1px solid {c['border']}; border-radius: 8px; padding: 8px; }}
            #themeCombo QAbstractItemView {{ background-color: {c['panel']}; color: {c['text']}; selection-background-color: {c['accent']}; }}
            #badge {{ color: {c['accent']}; background-color: rgba(255,255,255,0.04); border: 1px solid {c['border']}; border-radius: 10px; padding: 8px 14px; font-weight: 800; }}
            #navigation {{ background: transparent; border: none; outline: none; }}
            #navigation::item {{ padding: 12px 12px; border-radius: 11px; margin: 1px 0; }}
            #navigation::item:hover {{ background-color: rgba(255,255,255,0.05); }}
            #navigation::item:selected {{ background-color: {c['accent']}; color: white; }}
            QPushButton {{ background-color: rgba(255,255,255,0.04); border: 1px solid {c['border']}; border-radius: 9px; padding: 10px 12px; }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.08); }}
            QProgressBar {{ background: rgba(255,255,255,0.05); border: none; border-radius: 4px; }}
            QProgressBar::chunk {{ background: {c['accent']}; border-radius: 4px; }}
            #statusBar {{ background-color: rgba(9, 17, 36, 168); color: {c['muted']}; border: 1px solid {c['border']}; border-radius: 8px; padding-left: 6px; }}
            #sectionCard {{ background-color: rgba(13, 22, 47, 146); border: 1px solid {c['border']}; border-radius: {radius}px; }}
            #authRow {{ background-color: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.05); border-radius: 9px; }}
            #fieldLabel {{ font-weight: 650; }}
            QLineEdit, QComboBox, QSpinBox, QTextEdit, QListWidget {{
                background-color: rgba(5, 10, 22, 165);
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 9px 10px;
                selection-background-color: {c['accent']};
            }}
            QComboBox QAbstractItemView {{ background-color: {c['panel']}; color: {c['text']}; selection-background-color: {c['accent']}; }}
            QTextEdit#statusBox {{ font-family: 'Consolas'; }}
            QCheckBox {{ spacing: 7px; padding: 5px 8px; }}
            #primaryButton, #primarySmallButton {{ background-color: {c['accent']}; color: white; border: 1px solid {c['accent']}; font-weight: 750; }}
            #primaryButton:hover, #primarySmallButton:hover {{ background-color: {c.get('accent2', c['accent'])}; }}
            #dangerButton {{ background-color: rgba(160, 50, 67, 150); border: 1px solid rgba(255, 100, 120, 170); }}
            #pageScroll, #scrollContent, #realPage {{ background: transparent; border: none; }}
            #authStatus {{ color: {c['muted']}; font-family: 'Consolas'; }}
            #dashboardScroll, #dashboardHost {{ background: transparent; border: none; }}
            QToolTip {{ background-color: {c['panel']}; color: {c['text']}; border: 1px solid {c['border']}; padding: 6px; }}
        """)


def run_qt() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("MerzoStream Suite")
    window = MainWindow()
    window.show()
    return app.exec()
