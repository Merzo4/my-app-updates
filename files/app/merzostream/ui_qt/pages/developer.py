from PySide6.QtWidgets import QLabel,QTextEdit,QVBoxLayout,QWidget
class DeveloperPage(QWidget):
    def __init__(self,theme:dict):
        super().__init__(); l=QVBoxLayout(self); l.setContentsMargins(28,22,28,26); t=QLabel('Разработка'); t.setObjectName('pageTitle'); l.addWidget(t); box=QTextEdit(); box.setReadOnly(True); box.setPlainText('Текущий этап: 0.0.2f — Core Pages + Update Center\\n\\nГотово в новом PySide6:\\n• Главная\\n• Управление трансляцией\\n• Медиаплеер\\n• Фоновая музыка\\n• Единый чат\\n• AI Producer\\n• Авторизация\\n• Дизайнер тем\\n• Настройки\\n• Логи\\n• Обновления\\n• Инструкция\\n• О программе\\n\\nСледующие крупные этапы:\\n0.0.3 — OBS Center\\n0.0.4 — Automation / Macros\\n0.0.5 — Unified Chat Pro\\n0.0.6 — Plugin / SDK'); l.addWidget(box,1)
