from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget


class DeveloperPage(QWidget):
    def __init__(self, theme: dict):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 26)
        title = QLabel("Разработка")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        box = QTextEdit()
        box.setReadOnly(True)
        box.setPlainText(
            "Текущий этап: 0.0.2h — UX Fixes + Music URL Import + Context Help\n\n"
            "Готово в новом PySide6:\n"
            "• Главная\n• Управление трансляцией\n• Медиаплеер\n• Фоновая музыка\n"
            "• Единый чат\n• AI Producer\n• Авторизация\n• Дизайнер тем\n"
            "• Настройки\n• Логи\n• Обновления\n• Инструкция\n• О программе\n\n"
            "В 0.0.2h исправлены Sidebar/Dashboard, добавлен URL-импорт фоновой музыки "
            "и единая система контекстных подсказок.\n\n"
            "Следующие крупные этапы:\n"
            "0.0.3 — OBS Center\n0.0.4 — Automation / Macros\n"
            "0.0.5 — Unified Chat Pro\n0.0.6 — Plugin / SDK"
        )
        layout.addWidget(box, 1)
