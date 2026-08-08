from PySide6.QtWidgets import QFrame,QLabel,QVBoxLayout,QWidget
class AboutPage(QWidget):
    def __init__(self,theme:dict,app_info:dict):
        super().__init__(); l=QVBoxLayout(self); l.setContentsMargins(28,22,28,26); t=QLabel('О программе'); t.setObjectName('pageTitle'); l.addWidget(t); c=QFrame(); c.setObjectName('heroCard'); x=QVBoxLayout(c); a=QLabel('MerzoStream Suite'); a.setObjectName('heroTitle'); b=QLabel(f"{app_info.get('channel','Beta')} {app_info.get('version','—')}"); b.setObjectName('cardTitle'); d=QLabel('Персональная панель управления стримами: платформы, авторизация, медиаплеер, фоновая музыка, чат, AI, мониторинг и обновления.'); d.setWordWrap(True); d.setObjectName('cardText'); x.addWidget(a); x.addWidget(b); x.addWidget(d); l.addWidget(c); l.addStretch(1)
