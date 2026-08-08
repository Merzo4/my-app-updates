from __future__ import annotations
from PySide6.QtWidgets import QCheckBox,QFormLayout,QFrame,QHBoxLayout,QLabel,QMessageBox,QPushButton,QScrollArea,QSpinBox,QVBoxLayout,QWidget
from ...core.settings_manager import settings

class SettingsPage(QWidget):
    def __init__(self,theme:dict):
        super().__init__(); self.fields={}; self.checks={}; self.data=settings.load('player',force=True)
        root=QVBoxLayout(self); root.setContentsMargins(28,22,28,26); t=QLabel('Настройки'); t.setObjectName('pageTitle'); s=QLabel('Основные параметры медиаплеера и фильтров. Значения сохраняются в AppData.'); s.setObjectName('pageSubtitle'); root.addWidget(t); root.addWidget(s)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame); host=QWidget(); form=QFormLayout(host); form.setSpacing(10)
        specs=[('port','Порт API',1,65535),('volume','Громкость',0,100),('search_results','Результатов поиска',1,20),('search_timeout_sec','Таймаут поиска, сек',5,60),('parallel_checks','Параллельных проверок',1,8),('min_duration_sec','Мин. длительность, сек',0,3600),('max_duration_min','Макс. длительность, мин',1,300),('min_views','Мин. просмотров',0,100000000),('user_limit','Лимит на пользователя',1,100),('global_limit','Макс. очередь',1,500),('user_cooldown_min','Кулдаун, мин',0,1440)]
        for key,label,lo,hi in specs:
            sp=QSpinBox(); sp.setRange(lo,hi); sp.setValue(int(self.data.get(key,lo))); self.fields[key]=sp; form.addRow(label,sp)
        for key,label in [('allow_shorts','Разрешить Shorts'),('allow_live','Разрешить live'),('allow_playlists','Разрешить плейлисты'),('allow_age_restricted','Разрешить 18+'),('require_embeddable','Требовать встраивание'),('cookies_enabled','Cookies yt-dlp')]:
            ch=QCheckBox(label); ch.setChecked(bool(self.data.get(key,False))); self.checks[key]=ch; form.addRow('',ch)
        scroll.setWidget(host); root.addWidget(scroll,1); save=QPushButton('Сохранить настройки'); save.setObjectName('primaryButton'); save.clicked.connect(self.save); root.addWidget(save)
    def save(self):
        data=settings.load('player',force=True)
        for k,w in self.fields.items():data[k]=w.value()
        for k,w in self.checks.items():data[k]=w.isChecked()
        settings.save('player',data); QMessageBox.information(self,'Настройки','Сохранено. Если менялся порт API — перезапусти программу.')
