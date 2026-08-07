from __future__ import annotations

import subprocess
import sys

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from ..core.content import load_app_info, load_navigation
from ..core.paths import bundle_root
from ..core.settings_manager import settings
from .system_monitor import SystemMonitorPanel
from .theme_pack import background_path, icon_path, list_qt_themes, load_qt_theme


class SkinRoot(QWidget):
    """Полнооконный графический скин под настоящими элементами PySide6."""

    def __init__(self, theme: dict):
        super().__init__()
        self.theme = theme
        self._background = QPixmap()
        path = background_path(theme)
        if path is not None:
            self._background.load(str(path))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor(str(self.theme["colors"].get("window", "#10141b"))))

        if not self._background.isNull():
            scaled = self._background.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            sx = max(0, (scaled.width() - self.width()) // 2)
            sy = max(0, (scaled.height() - self.height()) // 2)
            source = scaled.rect().adjusted(sx, sy, -sx, -sy)
            painter.drawPixmap(self.rect(), scaled, source)

        dim = int(self.theme.get("presentation", {}).get("background_dimming", 0))
        if dim > 0:
            painter.fillRect(self.rect(), QColor(0, 0, 0, max(0, min(220, dim))))


class PlaceholderPage(QWidget):
    def __init__(self, title: str, subtitle: str):
        super().__init__()
        self.setObjectName("pageContainer")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 28)

        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        text = QLabel(subtitle)
        text.setWordWrap(True)
        text.setObjectName("pageSubtitle")

        card = QFrame()
        card.setObjectName("contentCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 20)
        info = QLabel(
            "Это уже не картинка предпросмотра. Реальные элементы MerzoStream Suite "
            "работают поверх графического скина: навигация, страницы, кнопки и мониторинг ПК."
        )
        info.setWordWrap(True)
        card_layout.addWidget(info)

        layout.addWidget(heading)
        layout.addWidget(text)
        layout.addSpacing(12)
        layout.addWidget(card)
        layout.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_info = load_app_info()
        ui_cfg = settings.load("ui", force=True)
        self.theme = load_qt_theme(str(ui_cfg.get("qt_theme_id", "merzostream_dark")))

        self.setWindowTitle(
            f"MerzoStream Suite — {self.app_info.get('channel')} {self.app_info.get('version')}"
        )
        self.resize(1500, 920)
        self.setMinimumSize(1120, 720)
        self._build()
        self._apply_theme()

    def _build(self):
        root = SkinRoot(self.theme)
        root.setObjectName("skinRoot")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(12, 12, 12, 8)
        outer.setSpacing(8)

        body = QHBoxLayout()
        body.setSpacing(10)
        outer.addLayout(body, 1)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(int(self.theme["layout"]["sidebar_width"]))
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(14, 18, 14, 14)
        side_layout.setSpacing(8)

        brand = QLabel("MERZOSTREAM")
        brand.setObjectName("brand")
        version = QLabel(f"SUITE • {self.app_info.get('version')}")
        version.setObjectName("versionLabel")

        self.nav = QListWidget()
        self.nav.setObjectName("navigation")
        self.nav.setIconSize(QSize(20, 20))
        self.nav.setSpacing(2)

        for item in load_navigation().get("items", []):
            if not item.get("enabled", True):
                continue
            row = QListWidgetItem(item.get("title", item.get("id", "")))
            row.setData(Qt.UserRole, item.get("id"))
            path = icon_path(self.theme, item.get("id", ""))
            if path:
                row.setIcon(QIcon(str(path)))
            self.nav.addItem(row)

        theme_label = QLabel("Оформление")
        theme_label.setObjectName("themeLabel")
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

        switch_button = QPushButton("Классический интерфейс")
        switch_button.clicked.connect(self.return_to_classic)

        side_layout.addWidget(brand)
        side_layout.addWidget(version)
        side_layout.addSpacing(10)
        side_layout.addWidget(self.nav, 1)
        side_layout.addWidget(theme_label)
        side_layout.addWidget(self.theme_combo)
        side_layout.addWidget(switch_button)
        body.addWidget(sidebar)

        center = QFrame()
        center.setObjectName("workspace")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)

        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(int(self.theme["layout"].get("header_height", 64)))
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        self.header_title = QLabel("Главная")
        self.header_title.setObjectName("headerTitle")
        badge = QLabel("PYSIDE6 • THEME ENGINE")
        badge.setObjectName("badge")
        header_layout.addWidget(self.header_title)
        header_layout.addStretch(1)
        header_layout.addWidget(badge)

        self.stack = QStackedWidget()
        self.stack.setObjectName("pageStack")
        for index in range(self.nav.count()):
            item = self.nav.item(index)
            self.stack.addWidget(
                PlaceholderPage(
                    item.text(),
                    "Фон, иконки, прозрачность и геометрия интерфейса загружаются из пакета темы."
                )
            )

        center_layout.addWidget(header)
        center_layout.addWidget(self.stack, 1)
        body.addWidget(center, 1)

        monitor = SystemMonitorPanel(self.theme)
        monitor.setFixedWidth(int(self.theme["layout"]["monitor_width"]))
        body.addWidget(monitor)

        status = QLabel(
            f"  MerzoStream Suite • {self.app_info.get('version')} • "
            f"{self.theme.get('title')} • графический скин активен"
        )
        status.setObjectName("statusBar")
        status.setFixedHeight(28)
        outer.addWidget(status)

        self.nav.currentRowChanged.connect(self.change_page)
        if self.nav.count():
            self.nav.setCurrentRow(0)

    def change_page(self, row: int):
        if row < 0:
            return
        self.stack.setCurrentIndex(row)
        self.header_title.setText(self.nav.item(row).text())

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

    def _restart(self):
        subprocess.Popen([sys.executable] + sys.argv, cwd=str(bundle_root()))
        QApplication.quit()

    def _apply_theme(self):
        c = self.theme["colors"]
        radius = int(self.theme["layout"].get("radius", 12))
        presentation = self.theme.get("presentation", {})
        full_skin = bool(presentation.get("full_window_background", False))
        workspace_bg = "rgba(3, 10, 20, 105)" if full_skin else c["window"]

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {c['window']}; }}
            QWidget {{
                color: {c['text']};
                font-family: 'Segoe UI';
                font-size: 13px;
            }}
            #skinRoot {{ background: transparent; }}
            #sidebar {{
                background-color: {c['sidebar']};
                border: 1px solid {c['border']};
                border-radius: {radius}px;
            }}
            #workspace {{
                background-color: {workspace_bg};
                border: 1px solid {c['border']};
                border-radius: {radius}px;
            }}
            #header {{
                background-color: {c['panel']};
                border: 1px solid {c['border']};
                border-radius: {radius}px;
            }}
            #pageStack, #pageContainer {{ background: transparent; }}
            #monitorPanel {{
                background-color: {c['sidebar']};
                border: 1px solid {c['border']};
                border-radius: {radius}px;
            }}
            #brand {{ font-size: 23px; font-weight: 800; letter-spacing: 1px; }}
            #versionLabel {{ color: {c['accent']}; font-weight: 700; }}
            #headerTitle, #pageTitle {{ font-size: 23px; font-weight: 700; }}
            #pageSubtitle, #metricTitle {{ color: {c['muted']}; }}
            #panelHeading {{ font-weight: 800; letter-spacing: 1px; }}
            #metricValue {{ font-size: 15px; font-weight: 650; }}
            #themeLabel {{ color: {c['muted']}; font-size: 11px; }}
            #themeCombo {{
                background-color: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 7px;
            }}
            #themeCombo QAbstractItemView {{
                background-color: {c['panel']};
                color: {c['text']};
                selection-background-color: {c['accent']};
            }}
            #badge {{
                color: {c['accent']};
                background-color: {c['card']};
                border: 1px solid {c['accent']};
                border-radius: 10px;
                padding: 5px 10px;
                font-weight: 800;
            }}
            #contentCard, #metricCard {{
                background-color: {c['card']};
                border: 1px solid {c['border']};
                border-radius: {radius}px;
            }}
            #navigation {{
                background: transparent;
                border: none;
                outline: none;
            }}
            #navigation::item {{
                padding: 11px 10px;
                border-radius: 9px;
                margin: 1px 0;
            }}
            #navigation::item:hover {{ background-color: {c['panel']}; }}
            #navigation::item:selected {{
                background-color: {c['accent']};
                color: white;
            }}
            QPushButton {{
                background-color: {c['card']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding: 10px;
            }}
            QPushButton:hover {{ border-color: {c['accent']}; }}
            QProgressBar {{
                background: {c['panel']};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {c['accent']};
                border-radius: 3px;
            }}
            #statusBar {{
                background-color: {c['panel']};
                color: {c['muted']};
                border: 1px solid {c['border']};
                border-radius: 8px;
                padding-left: 6px;
            }}
        """)


def run_qt() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("MerzoStream Suite")
    window = MainWindow()
    window.show()
    return app.exec()
