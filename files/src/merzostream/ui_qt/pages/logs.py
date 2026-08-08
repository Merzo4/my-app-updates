from __future__ import annotations
import os
from PySide6.QtWidgets import QHBoxLayout,QLabel,QPushButton,QTextEdit,QVBoxLayout,QWidget
from ...core.event_log import LOG_FILE

class LogsPage(QWidget):
    def __init__(self,theme:dict):
        super().__init__(); l=QVBoxLayout(self); l.setContentsMargins(28,22,28,26); t=QLabel('Логи'); t.setObjectName('pageTitle'); s=QLabel('Последние события MerzoStream Suite.'); s.setObjectName('pageSubtitle'); l.addWidget(t); l.addWidget(s); row=QHBoxLayout(); ref=QPushButton('Обновить'); ref.clicked.connect(self.refresh); folder=QPushButton('Открыть папку логов'); folder.clicked.connect(self.open_folder); row.addWidget(ref); row.addWidget(folder); row.addStretch(1); l.addLayout(row); self.box=QTextEdit(); self.box.setReadOnly(True); l.addWidget(self.box,1); self.refresh()
    def refresh(self):
        try:
            lines=LOG_FILE.read_text(encoding='utf-8',errors='replace').splitlines(); self.box.setPlainText('\n'.join(lines[-1200:])); self.box.verticalScrollBar().setValue(self.box.verticalScrollBar().maximum())
        except Exception as e:self.box.setPlainText(str(e))
    def open_folder(self):LOG_FILE.parent.mkdir(parents=True,exist_ok=True); os.startfile(str(LOG_FILE.parent))
