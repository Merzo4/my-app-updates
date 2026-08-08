from __future__ import annotations

import json

from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from ...core.paths import CLIENT_SECRET, CONTENT_DIR, KICK_TOKEN, YOUTUBE_TOKEN
from ...core.settings_manager import settings
from ...core.update_manager import update_manager
from ..system_monitor import detect_disks, detect_gpus


class HomePage(QWidget):
    def __init__(self, theme: dict, app_info: dict, navigate=None):
        super().__init__()
        self.theme = theme
        self.app_info = app_info
        self.navigate = navigate

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setObjectName("pageScroll"); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        host = QWidget(); host.setObjectName("scrollContent")
        root = QVBoxLayout(host); root.setContentsMargins(28, 22, 28, 26); root.setSpacing(14)
        scroll.setWidget(host); outer.addWidget(scroll)

        title = QLabel("Главная"); title.setObjectName("pageTitle")
        subtitle = QLabel("Центр MerzoStream Suite: версия, быстрые действия, состояние модулей и история изменений.")
        subtitle.setWordWrap(True); subtitle.setObjectName("pageSubtitle")
        root.addWidget(title); root.addWidget(subtitle)

        quick = QFrame(); quick.setObjectName("heroCard")
        ql = QVBoxLayout(quick); ql.setContentsMargins(18, 16, 18, 16); ql.setSpacing(10)
        qtitle = QLabel(f"MerzoStream Suite • {self.app_info.get('channel','Beta')} {self.app_info.get('version','—')}")
        qtitle.setObjectName("heroTitle"); ql.addWidget(qtitle)
        qr = QHBoxLayout(); qr.setSpacing(8)
        for label, page_id in (
            ("📡 Трансляция", "stream"), ("🎵 Медиаплеер", "player"),
            ("🎼 Фоновая музыка", "background_music"), ("⬇ Обновления", "updates"),
            ("⚙ Настройки", "settings"),
        ):
            b = QPushButton(label); b.clicked.connect(lambda _=False, p=page_id: self.navigate(p) if self.navigate else None); qr.addWidget(b)
        ql.addLayout(qr); root.addWidget(quick)

        cards = QGridLayout(); cards.setSpacing(12)
        stream = settings.load("stream", force=True); player = settings.load("player", force=True)
        selected = [name for key, name in (("twitch","Twitch"),("youtube","YouTube"),("vk","VK"),("kick","Kick")) if stream.get("platforms",{}).get(key)]
        auth = []
        if CLIENT_SECRET.exists(): auth.append("OAuth config ✓")
        if YOUTUBE_TOKEN.exists(): auth.append("YouTube ✓")
        if KICK_TOKEN.exists(): auth.append("Kick ✓")
        try: disks = detect_disks()
        except Exception: disks = []
        try: gpus = detect_gpus()
        except Exception: gpus = []
        monitor = settings.load("monitor", force=True)
        monitor_parts = [f"Дисков: {len(disks)}", f"GPU: {len(gpus)}"]
        if monitor.get("disk_mode") == "custom": monitor_parts.append("диски: выборочно")
        if monitor.get("gpu_mode") == "custom": monitor_parts.append("GPU: выборочно")

        info = [
            ("Версия", f"{self.app_info.get('channel','Beta')} {self.app_info.get('version','—')}", "Текущая установленная версия"),
            ("Платформы", " • ".join(selected) or "Не выбраны", "Выбор из Управления трансляцией"),
            ("Медиаплеер", f"127.0.0.1:{player.get('port',5000)}", "API заказов и OBS Browser Source"),
            ("Dashboard Pro", " • ".join(monitor_parts), "Настраивается шестерёнкой в правой панели"),
            ("Авторизация", " • ".join(auth) or "Проверь Авторизацию", "Токены хранятся вне папки программы"),
            ("Фоновая музыка", "Каталог источников добавлен", "YouTube Audio Library • StreamBeats • Pixabay • Mixkit"),
        ]
        for i,(name,value,detail) in enumerate(info):
            card=QFrame(); card.setObjectName("contentCard"); l=QVBoxLayout(card); l.setContentsMargins(18,15,18,15)
            h=QLabel(name); h.setObjectName("cardTitle")
            v=QLabel(value); v.setObjectName("heroTitle"); v.setWordWrap(True)
            d=QLabel(detail); d.setObjectName("cardText"); d.setWordWrap(True)
            l.addWidget(h); l.addWidget(v); l.addWidget(d); cards.addWidget(card,i//2,i%2)
        root.addLayout(cards)

        release=QFrame(); release.setObjectName("heroCard"); rl=QVBoxLayout(release); rl.setContentsMargins(20,18,20,18); rl.setSpacing(8)
        head=QHBoxLayout(); ht=QLabel(f"Что нового в {self.app_info.get('version','')}"); ht.setObjectName("heroTitle")
        up=QPushButton("Открыть обновления"); up.setObjectName("primarySmallButton"); up.clicked.connect(lambda: self.navigate("updates") if self.navigate else None)
        head.addWidget(ht); head.addStretch(1); head.addWidget(up); rl.addLayout(head)
        notes=self._release_notes()
        for note in notes[:10]:
            q=QLabel("• "+note); q.setWordWrap(True); q.setObjectName("cardText"); rl.addWidget(q)
        root.addWidget(release)

        hist=update_manager.history()
        history=QFrame(); history.setObjectName("contentCard"); hl=QVBoxLayout(history); hl.setContentsMargins(18,15,18,15)
        hh=QLabel("Последние установленные обновления"); hh.setObjectName("cardTitle"); hl.addWidget(hh)
        if hist:
            for item in hist[:4]:
                txt=f"{item.get('from_version','?')} → {item.get('to_version','?')}  •  файлов: {len(item.get('updated_files',[]))}"
                lab=QLabel(txt); lab.setObjectName("cardText"); hl.addWidget(lab)
        else:
            lab=QLabel("История появится после обновлений через встроенный Update Center."); lab.setObjectName("cardText"); hl.addWidget(lab)
        root.addWidget(history)
        root.addStretch(1)

    def _release_notes(self):
        try:
            data=json.loads((CONTENT_DIR/'release_notes.json').read_text(encoding='utf-8'))
            return [str(x) for x in data.get('items',[]) if str(x).strip()]
        except Exception:
            return ["Новая версия интерфейса установлена."]
