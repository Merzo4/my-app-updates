from __future__ import annotations
import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QComboBox,QFrame,QHBoxLayout,QLabel,QPushButton,QVBoxLayout,QWidget
from ...core.paths import bundle_root
from ...core.settings_manager import settings
from ..theme_pack import list_qt_themes,load_qt_theme,background_path

class DesignerPage(QWidget):
    def __init__(self,theme:dict,restart=None):
        super().__init__(); self.restart=restart; self.ids=[]; l=QVBoxLayout(self); l.setContentsMargins(28,22,28,26); t=QLabel('Дизайнер'); t.setObjectName('pageTitle'); s=QLabel('Выбор пакета оформления. Полноценный визуальный редактор будет следующим этапом.'); s.setObjectName('pageSubtitle'); l.addWidget(t); l.addWidget(s); self.combo=QComboBox(); current=settings.get('ui','qt_theme_id','aurora_glass_pro')
        idx=0
        for i,x in enumerate(list_qt_themes()):self.combo.addItem(x['title']); self.ids.append(x['id']); idx=i if x['id']==current else idx
        self.combo.setCurrentIndex(idx); self.combo.currentIndexChanged.connect(self.preview); l.addWidget(self.combo); self.image=QLabel(); self.image.setAlignment(Qt.AlignCenter); self.image.setMinimumHeight(320); self.image.setObjectName('contentCard'); l.addWidget(self.image,1); row=QHBoxLayout(); apply=QPushButton('Применить и перезапустить'); apply.setObjectName('primaryButton'); apply.clicked.connect(self.apply); folder=QPushButton('Открыть папку тем'); folder.clicked.connect(self.open_folder); row.addWidget(apply); row.addWidget(folder); l.addLayout(row); self.preview()
    def preview(self):
        if not self.ids:return
        theme=load_qt_theme(self.ids[self.combo.currentIndex()]); p=background_path(theme)
        if p and p.exists():self.image.setPixmap(QPixmap(str(p)).scaled(self.image.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
    def resizeEvent(self,e):super().resizeEvent(e); self.preview()
    def apply(self):settings.set('ui','qt_theme_id',self.ids[self.combo.currentIndex()]); self.restart() if self.restart else None
    def open_folder(self):
        p=bundle_root()/'content'/'ui_themes'; p.mkdir(parents=True,exist_ok=True); os.startfile(str(p))
