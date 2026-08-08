from __future__ import annotations
import threading
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QListWidget, QPushButton, QVBoxLayout, QWidget
from ...core.settings_manager import settings
from ...services.stream import StreamManager

class _Sig(QObject): done=Signal(list,str)
class AIProducerPage(QWidget):
    def __init__(self, theme:dict, use_title=None):
        super().__init__(); self.manager=StreamManager(settings.load('stream',force=True)); self.use_title=use_title; self.sig=_Sig(self); self.sig.done.connect(self.show_results)
        l=QVBoxLayout(self); l.setContentsMargins(28,22,28,26); l.setSpacing(12); t=QLabel('AI Producer'); t.setObjectName('pageTitle'); s=QLabel('Сгенерируй варианты названия и отправь выбранный прямо в Управление трансляцией.'); s.setObjectName('pageSubtitle'); l.addWidget(t); l.addWidget(s)
        self.prompt=QLineEdit(); self.prompt.setPlaceholderText('Например: SnowRunner, Вашингтон, тяжёлые грузы и грязь'); l.addWidget(self.prompt); self.btn=QPushButton('✨ Сгенерировать 25 названий'); self.btn.setObjectName('primaryButton'); self.btn.clicked.connect(self.generate); l.addWidget(self.btn); self.list=QListWidget(); self.list.itemDoubleClicked.connect(lambda _i:self.take()); l.addWidget(self.list,1); take=QPushButton('Использовать выбранное название'); take.clicked.connect(self.take); l.addWidget(take); self.status=QLabel(''); self.status.setObjectName('cardText'); l.addWidget(self.status)
    def generate(self):
        p=self.prompt.text().strip()
        if not p:return
        self.btn.setEnabled(False); self.status.setText('ИИ думает…'); manager=self.manager
        def job():
            titles,res=manager.groq.generate_titles(p); self.sig.done.emit(titles,res.message)
        threading.Thread(target=job,daemon=True).start()
    def show_results(self,titles,msg):
        self.btn.setEnabled(True); self.list.clear(); self.list.addItems([str(x) for x in titles]); self.status.setText(msg)
    def take(self):
        item=self.list.currentItem()
        if item and self.use_title:self.use_title(item.text())
