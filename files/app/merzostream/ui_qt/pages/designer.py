from __future__ import annotations
import os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QCheckBox,QComboBox,QFrame,QFormLayout,QHBoxLayout,QLabel,QPushButton,QVBoxLayout,QWidget
from ...core.paths import bundle_root
from ...core.settings_manager import settings
from ..theme_pack import list_qt_themes,load_qt_theme,background_path

class DesignerPage(QWidget):
    def __init__(self,theme:dict,restart=None):
        super().__init__(); self.restart=restart; self.ids=[]
        l=QVBoxLayout(self); l.setContentsMargins(28,22,28,26); l.setSpacing(12)
        t=QLabel('Дизайнер'); t.setObjectName('pageTitle')
        s=QLabel('Темы и производительность оформления. Эти параметры меняют только внешний вид и не затрагивают рабочие данные модулей.'); s.setWordWrap(True); s.setObjectName('pageSubtitle'); l.addWidget(t); l.addWidget(s)
        self.combo=QComboBox(); current=settings.get('ui','qt_theme_id','aurora_glass_pro'); idx=0
        for i,x in enumerate(list_qt_themes()): self.combo.addItem(x['title']); self.ids.append(x['id']); idx=i if x['id']==current else idx
        self.combo.setCurrentIndex(idx); self.combo.currentIndexChanged.connect(self.preview); l.addWidget(self.combo)
        self.image=QLabel(); self.image.setAlignment(Qt.AlignCenter); self.image.setMinimumHeight(260); self.image.setObjectName('contentCard'); l.addWidget(self.image,1)

        perf=QFrame(); perf.setObjectName('contentCard'); pl=QFormLayout(perf); pl.setContentsMargins(18,15,18,15); pl.setSpacing(9)
        self.quality=QComboBox(); self.quality.addItem('Высокое','high'); self.quality.addItem('Среднее','medium'); self.quality.addItem('Экономичное','economy')
        q=str(settings.get('ui','graphics_quality','high')); qi=self.quality.findData(q); self.quality.setCurrentIndex(qi if qi>=0 else 0)
        self.background=QCheckBox('Показывать фоновое изображение'); self.background.setChecked(settings.get_bool('ui','background_enabled',True))
        self.transparency=QCheckBox('Прозрачные панели'); self.transparency.setChecked(settings.get_bool('ui','transparency_enabled',True))
        self.effects=QCheckBox('Декоративные эффекты/свечение'); self.effects.setChecked(settings.get_bool('ui','effects_enabled',True))
        self.economy_bg=QCheckBox('В экономичном режиме полностью отключать фон'); self.economy_bg.setChecked(settings.get_bool('ui','economy_disable_background',False))
        pl.addRow('Качество графики',self.quality); pl.addRow('',self.background); pl.addRow('',self.transparency); pl.addRow('',self.effects); pl.addRow('',self.economy_bg)
        note=QLabel('Высокое — максимальное качество. Среднее — быстрее масштабирование. Экономичное — минимум нагрузки при изменении размера окна. Фон теперь кэшируется и не пересчитывается на каждом кадре.'); note.setWordWrap(True); note.setObjectName('cardText'); pl.addRow(note)
        l.addWidget(perf)
        row=QHBoxLayout(); apply=QPushButton('Применить и перезапустить'); apply.setObjectName('primaryButton'); apply.clicked.connect(self.apply); folder=QPushButton('Открыть папку тем'); folder.clicked.connect(self.open_folder); row.addWidget(apply); row.addWidget(folder); l.addLayout(row)
        self.preview_timer=QTimer(self); self.preview_timer.setSingleShot(True); self.preview_timer.timeout.connect(self._render_preview); self.preview()
    def preview(self): self.preview_timer.start(120)
    def _render_preview(self):
        if not self.ids:return
        theme=load_qt_theme(self.ids[self.combo.currentIndex()]); p=background_path(theme)
        if p and p.exists(): self.image.setPixmap(QPixmap(str(p)).scaled(self.image.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
    def resizeEvent(self,e): super().resizeEvent(e); self.preview_timer.start(160)
    def apply(self):
        data=settings.load('ui',force=True); data['qt_theme_id']=self.ids[self.combo.currentIndex()]; data['graphics_quality']=str(self.quality.currentData() or 'high'); data['background_enabled']=self.background.isChecked(); data['transparency_enabled']=self.transparency.isChecked(); data['effects_enabled']=self.effects.isChecked(); data['economy_disable_background']=self.economy_bg.isChecked(); settings.save('ui',data); self.restart() if self.restart else None
    def open_folder(self):
        p=bundle_root()/'content'/'ui_themes'; p.mkdir(parents=True,exist_ok=True); os.startfile(str(p))
