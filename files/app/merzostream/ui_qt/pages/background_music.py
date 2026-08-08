from __future__ import annotations

import json
import os
import webbrowser

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget,
    QMessageBox, QPushButton, QScrollArea, QSlider, QVBoxLayout, QWidget, QCheckBox,
)

from ...core.paths import CONTENT_DIR
from ...core.settings_manager import settings
from ...player.background_music import MUSIC_DIR, background_music


class BackgroundMusicPage(QWidget):
    def __init__(self, theme: dict):
        super().__init__()
        self.theme=theme
        self.port=int(settings.get('player','port',5000))
        self.obs_url=f"http://127.0.0.1:{self.port}/music"

        outer=QVBoxLayout(self); outer.setContentsMargins(0,0,0,0)
        scroll=QScrollArea(); scroll.setObjectName('pageScroll'); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        host=QWidget(); host.setObjectName('scrollContent')
        root=QVBoxLayout(host); root.setContentsMargins(28,22,28,26); root.setSpacing(12)
        scroll.setWidget(host); outer.addWidget(scroll)

        title=QLabel("Фоновая музыка"); title.setObjectName("pageTitle")
        sub=QLabel("Отдельный аудио-источник для OBS без видеокартинки. Локальная библиотека хранится в AppData.")
        sub.setWordWrap(True); sub.setObjectName("pageSubtitle"); root.addWidget(title); root.addWidget(sub)

        card=QFrame(); card.setObjectName("heroCard"); l=QVBoxLayout(card); l.setContentsMargins(18,15,18,15)
        self.now=QLabel("Музыка не выбрана"); self.now.setObjectName("heroTitle")
        self.info=QLabel(""); self.info.setObjectName("cardText"); l.addWidget(self.now); l.addWidget(self.info)
        controls=QHBoxLayout()
        for text,fn in (("⏮",background_music.previous),("▶ Играть",background_music.play),("⏯ Пауза",background_music.pause_toggle),("⏹ Стоп",background_music.stop),("⏭",background_music.next)):
            b=QPushButton(text); b.clicked.connect(fn); controls.addWidget(b)
        controls.addWidget(QLabel("Громкость")); self.volume=QSlider(Qt.Horizontal); self.volume.setRange(0,100); self.volume.valueChanged.connect(background_music.set_volume); controls.addWidget(self.volume,1)
        self.shuffle=QCheckBox("Случайно"); self.repeat=QCheckBox("Повтор"); self.shuffle.stateChanged.connect(self._modes); self.repeat.stateChanged.connect(self._modes); controls.addWidget(self.shuffle); controls.addWidget(self.repeat); l.addLayout(controls); root.addWidget(card)

        tools=QHBoxLayout(); add=QPushButton("Добавить аудиофайлы"); add.setObjectName("primaryButton"); add.clicked.connect(self.add_files)
        ref=QPushButton("Обновить список"); ref.clicked.connect(self.reload)
        folder=QPushButton("Открыть папку"); folder.clicked.connect(self.open_folder)
        obs=QPushButton("Открыть OBS /music"); obs.clicked.connect(lambda:webbrowser.open(self.obs_url))
        attr=QPushButton("Атрибуция"); attr.clicked.connect(self.attribution)
        for b in (add,ref,folder,obs,attr): tools.addWidget(b)
        root.addLayout(tools)

        sources=QFrame(); sources.setObjectName('contentCard'); sl=QVBoxLayout(sources); sl.setContentsMargins(18,15,18,15); sl.setSpacing(8)
        st=QLabel('Где скачать музыку для стрима'); st.setObjectName('cardTitle'); sl.addWidget(st)
        sw=QLabel('Royalty-free не всегда означает «без авторских прав». Перед использованием проверяй лицензию конкретного трека и сохраняй подтверждение загрузки.')
        sw.setWordWrap(True); sw.setObjectName('cardText'); sl.addWidget(sw)
        grid=QGridLayout(); grid.setHorizontalSpacing(10); grid.setVerticalSpacing(8)
        for row, source in enumerate(self._music_sources()):
            box=QFrame(); box.setObjectName('authRow'); bl=QHBoxLayout(box); bl.setContentsMargins(12,9,12,9)
            desc=QVBoxLayout(); name=QLabel(source.get('name','Источник')); name.setObjectName('fieldLabel')
            note=QLabel(source.get('note','')); note.setWordWrap(True); note.setObjectName('cardText'); desc.addWidget(name); desc.addWidget(note)
            btn=QPushButton(source.get('button','Открыть / скачать'))
            btn.clicked.connect(lambda _=False, u=source.get('url',''): webbrowser.open(u) if u else None)
            bl.addLayout(desc,1); bl.addWidget(btn); grid.addWidget(box,row,0)
        sl.addLayout(grid); root.addWidget(sources)

        library=QFrame(); library.setObjectName('contentCard'); ll=QVBoxLayout(library); ll.setContentsMargins(18,15,18,15); ll.setSpacing(8)
        lt=QLabel('Локальная библиотека'); lt.setObjectName('cardTitle'); ll.addWidget(lt)
        self.list=QListWidget(); self.list.setMinimumHeight(240); self.list.itemDoubleClicked.connect(lambda _i:self.play_selected()); ll.addWidget(self.list)
        play=QPushButton("Играть выбранный трек"); play.clicked.connect(self.play_selected); ll.addWidget(play)
        root.addWidget(library)
        hint=QLabel(f"OBS Browser Source: {self.obs_url}\nПапка: {MUSIC_DIR}"); hint.setObjectName("cardText"); root.addWidget(hint)

        self.timer=QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(1000); self.reload(); self.refresh()

    def _music_sources(self):
        try:
            data=json.loads((CONTENT_DIR/'music_sources.json').read_text(encoding='utf-8'))
            items=data.get('sources',[]) if isinstance(data,dict) else []
            if isinstance(items,list): return [x for x in items if isinstance(x,dict)]
        except Exception:
            pass
        return []

    def reload(self):
        background_music.reload_library(); self.list.clear()
        for t in background_music.tracks:self.list.addItem(t.title + (f" — {t.author}" if t.author else ""))
    def play_selected(self):
        i=self.list.currentRow(); background_music.play(i if i>=0 else None)
    def add_files(self):
        files,_=QFileDialog.getOpenFileNames(self,"Добавить музыку","","Аудио (*.mp3 *.wav *.m4a *.aac *.ogg *.flac);;Все файлы (*.*)")
        if files:
            count=background_music.add_files(files); self.reload(); QMessageBox.information(self,"Фоновая музыка",f"Добавлено файлов: {count}")
    def open_folder(self):
        MUSIC_DIR.mkdir(parents=True,exist_ok=True)
        if os.name == 'nt': os.startfile(str(MUSIC_DIR))
        else: webbrowser.open(MUSIC_DIR.as_uri())
    def attribution(self):
        text=background_music.attribution_text() or "Для добавленных треков обязательная атрибуция не указана. Это не заменяет проверку лицензии источника."
        QMessageBox.information(self,"Атрибуция",text)
    def _modes(self):
        background_music.shuffle=self.shuffle.isChecked(); background_music.repeat=self.repeat.isChecked(); background_music._save_state()
    def refresh(self):
        snap=background_music.snapshot(); cur=snap.get('current'); self.volume.blockSignals(True); self.volume.setValue(int(snap.get('volume',35))); self.volume.blockSignals(False)
        self.shuffle.blockSignals(True); self.repeat.blockSignals(True); self.shuffle.setChecked(bool(snap.get('shuffle'))); self.repeat.setChecked(bool(snap.get('repeat',True))); self.shuffle.blockSignals(False); self.repeat.blockSignals(False)
        if cur:
            state="пауза" if snap.get('paused') else ("играет" if snap.get('playing') else "остановлено"); self.now.setText(cur.get('title','Без названия')); self.info.setText(f"{cur.get('author','')} • {state} • позиция {int(snap.get('position',0))} сек.")
        else:self.now.setText("Музыка не выбрана"); self.info.setText("")
