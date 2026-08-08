from __future__ import annotations

import datetime as dt
import webbrowser
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget
from ...chat.manager import chat_manager
from ..runtime import get_runtime

class ChatCenterPage(QWidget):
    def __init__(self, theme: dict):
        super().__init__(); get_runtime(); self.port=5001
        root=QVBoxLayout(self); root.setContentsMargins(28,22,28,26); root.setSpacing(12)
        title=QLabel("Единый чат"); title.setObjectName("pageTitle"); sub=QLabel("Лента Twitch • YouTube • VK • Kick • RutonyChat • Streamer.bot и OBS overlay."); sub.setObjectName("pageSubtitle"); root.addWidget(title); root.addWidget(sub)
        tools=QHBoxLayout(); self.platform=QComboBox(); self.platform.addItems(['all','twitch','youtube','vk','kick','rutony','streamerbot','other']); self.platform.currentIndexChanged.connect(self.refresh); obs=QPushButton("Открыть OBS-чат"); obs.clicked.connect(lambda:webbrowser.open(f"http://127.0.0.1:{self.port}/chat")); clear=QPushButton("Очистить экран"); clear.clicked.connect(lambda:(chat_manager.clear(False),self.refresh())); tools.addWidget(self.platform); tools.addStretch(1); tools.addWidget(obs); tools.addWidget(clear); root.addLayout(tools)
        self.feed=QTextEdit(); self.feed.setReadOnly(True); root.addWidget(self.feed,1)
        row=QHBoxLayout(); self.test_platform=QComboBox(); self.test_platform.addItems(['twitch','youtube','vk','kick','rutony','streamerbot']); self.user=QLineEdit('Merzo4'); self.message=QLineEdit(); self.message.setPlaceholderText('Тестовое сообщение'); add=QPushButton('Добавить'); add.clicked.connect(self.add_test); row.addWidget(self.test_platform); row.addWidget(self.user); row.addWidget(self.message,1); row.addWidget(add); root.addLayout(row)
        hint=QLabel(f"OBS: http://127.0.0.1:{self.port}/chat\nAPI: http://127.0.0.1:{self.port}/chat/add?platform=Twitch&user=%userName%&message=%rawInput%"); hint.setObjectName('cardText'); hint.setWordWrap(True); root.addWidget(hint)
        self.timer=QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(1000); self.refresh()
    def refresh(self):
        p=self.platform.currentText() if hasattr(self,'platform') else 'all'; items=chat_manager.snapshot(200,None if p=='all' else {p}); lines=[]
        for item in items:
            stamp=dt.datetime.fromtimestamp(float(item['created_at'])).strftime('%H:%M:%S'); lines.append(f"[{stamp}] [{item['platform'].upper()}] {item['user']}: {item['message']}")
        self.feed.setPlainText('\n'.join(lines) if lines else 'Сообщений пока нет.'); self.feed.verticalScrollBar().setValue(self.feed.verticalScrollBar().maximum())
    def add_test(self):
        msg=self.message.text().strip()
        if msg: chat_manager.add(self.test_platform.currentText(),self.user.text().strip() or 'Merzo4',msg); self.message.clear(); self.refresh()
