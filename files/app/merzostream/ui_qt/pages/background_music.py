from __future__ import annotations

import json
import os
import webbrowser

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPushButton, QScrollArea, QSlider, QVBoxLayout, QWidget, QCheckBox,
)

from ...core.paths import CONTENT_DIR
from ...core.settings_manager import settings
from ...player.background_music import MUSIC_DIR, background_music


class MusicUrlWorker(QThread):
    status = Signal(str)
    completed = Signal(bool, str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        ok, message, _filename = background_music.import_url(self.url, progress=self.status.emit)
        self.completed.emit(ok, message)


class BackgroundMusicPage(QWidget):
    def __init__(self, theme: dict):
        super().__init__()
        self.theme = theme
        self.worker: MusicUrlWorker | None = None
        self.port = int(settings.get("player", "port", 5000))
        self.obs_url = f"http://127.0.0.1:{self.port}/music"

        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setObjectName("pageScroll"); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QWidget(); host.setObjectName("scrollContent")
        root = QVBoxLayout(host); root.setContentsMargins(28, 22, 28, 26); root.setSpacing(12)
        scroll.setWidget(host); outer.addWidget(scroll)

        title = QLabel("Фоновая музыка"); title.setObjectName("pageTitle")
        sub = QLabel("Отдельный музыкальный канал для OBS. Треки хранятся локально и не смешиваются с заказами зрителей.")
        sub.setWordWrap(True); sub.setObjectName("pageSubtitle"); root.addWidget(title); root.addWidget(sub)

        card = QFrame(); card.setObjectName("heroCard"); l = QVBoxLayout(card); l.setContentsMargins(18, 15, 18, 15); l.setSpacing(8)
        hero_help = QLabel("Сейчас играет • Управляет отдельным OBS Browser Source /music: запуск, пауза, следующий трек, повтор и громкость.")
        hero_help.setWordWrap(True); hero_help.setObjectName("cardText"); l.addWidget(hero_help)
        self.now = QLabel("Музыка не выбрана"); self.now.setObjectName("heroTitle")
        self.info = QLabel(""); self.info.setObjectName("cardText"); l.addWidget(self.now); l.addWidget(self.info)
        controls = QHBoxLayout()
        for text, fn, tip in (
            ("⏮", background_music.previous, "Предыдущий трек библиотеки."),
            ("▶ Играть", background_music.play, "Запустить выбранный или первый трек."),
            ("⏯ Пауза", background_music.pause_toggle, "Поставить музыку на паузу или продолжить."),
            ("⏹ Стоп", background_music.stop, "Остановить музыку и сбросить позицию."),
            ("⏭", background_music.next, "Перейти к следующему треку."),
        ):
            b = QPushButton(text); b.setToolTip(tip); b.clicked.connect(fn); controls.addWidget(b)
        vol = QLabel("Громкость"); vol.setToolTip("Громкость только фоновой музыки в OBS Browser Source /music."); controls.addWidget(vol)
        self.volume = QSlider(Qt.Horizontal); self.volume.setRange(0, 100); self.volume.setToolTip("Громкость фоновой музыки 0–100%."); self.volume.valueChanged.connect(background_music.set_volume); controls.addWidget(self.volume, 1)
        self.shuffle = QCheckBox("Случайно"); self.shuffle.setToolTip("Играть треки в случайном порядке.")
        self.repeat = QCheckBox("Повтор"); self.repeat.setToolTip("После последнего трека снова начать библиотеку.")
        self.shuffle.stateChanged.connect(self._modes); self.repeat.stateChanged.connect(self._modes); controls.addWidget(self.shuffle); controls.addWidget(self.repeat)
        l.addLayout(controls); root.addWidget(card)

        importer = QFrame(); importer.setObjectName("contentCard"); il = QVBoxLayout(importer); il.setContentsMargins(18, 15, 18, 15); il.setSpacing(8)
        it = QLabel("Добавить музыку"); it.setObjectName("cardTitle"); il.addWidget(it)
        idesc = QLabel(
            "Можно добавить готовый аудиофайл или вставить ссылку на трек. По ссылке MerzoStream Suite попробует скачать один аудиотрек через yt-dlp и сохранить его в локальную библиотеку. "
            "Если сайт запрещает автоматическую загрузку, используй его официальный Download и затем кнопку «Добавить аудиофайлы»."
        )
        idesc.setWordWrap(True); idesc.setObjectName("cardText"); il.addWidget(idesc)
        url_row = QHBoxLayout()
        self.url_input = QLineEdit(); self.url_input.setPlaceholderText("https://... ссылка на страницу трека или прямой аудиофайл")
        self.url_input.setToolTip("Вставь ссылку на один трек. Плейлисты специально отключены, чтобы случайно не скачать целую коллекцию.")
        self.url_button = QPushButton("Скачать и добавить по ссылке"); self.url_button.setObjectName("primaryButton"); self.url_button.setToolTip("Попробовать скачать один аудиотрек и добавить его в локальную библиотеку."); self.url_button.clicked.connect(self.add_url)
        url_row.addWidget(self.url_input, 1); url_row.addWidget(self.url_button); il.addLayout(url_row)
        self.url_status = QLabel("Поддержка зависит от конкретного сайта. Прямые ссылки и источники, которые понимает yt-dlp, добавляются автоматически.")
        self.url_status.setWordWrap(True); self.url_status.setObjectName("cardText"); il.addWidget(self.url_status)

        tools = QHBoxLayout()
        add = QPushButton("Добавить аудиофайлы"); add.setObjectName("primarySmallButton"); add.setToolTip("Скопировать выбранные MP3/WAV/M4A/AAC/OGG/FLAC/WebM/Opus в библиотеку MerzoStream Suite."); add.clicked.connect(self.add_files)
        ref = QPushButton("Обновить список"); ref.setToolTip("Повторно просканировать папку фоновой музыки."); ref.clicked.connect(self.reload)
        folder = QPushButton("Открыть папку"); folder.setToolTip("Открыть локальную папку библиотеки в Проводнике."); folder.clicked.connect(self.open_folder)
        obs = QPushButton("Открыть OBS /music"); obs.setToolTip("Открыть адрес Browser Source фоновой музыки в браузере."); obs.clicked.connect(lambda: webbrowser.open(self.obs_url))
        attr = QPushButton("Атрибуция"); attr.setToolTip("Показать сохранённые строки атрибуции для треков, которым она требуется."); attr.clicked.connect(self.attribution)
        for b in (add, ref, folder, obs, attr): tools.addWidget(b)
        il.addLayout(tools); root.addWidget(importer)

        sources = QFrame(); sources.setObjectName("contentCard"); sl = QVBoxLayout(sources); sl.setContentsMargins(18, 15, 18, 15); sl.setSpacing(8)
        st = QLabel("Где брать музыку для стрима"); st.setObjectName("cardTitle"); sl.addWidget(st)
        sw = QLabel(
            "Открой источник → выбери трек → попробуй скопировать адрес страницы трека в поле выше. Если автоматический импорт не поддерживается, нажми официальный Download на сайте и добавь скачанный файл. "
            "Royalty-free не всегда означает «без авторских прав»: проверяй лицензию конкретного трека и сохраняй подтверждение загрузки."
        )
        sw.setWordWrap(True); sw.setObjectName("cardText"); sl.addWidget(sw)
        grid = QGridLayout(); grid.setHorizontalSpacing(10); grid.setVerticalSpacing(8)
        for row, source in enumerate(self._music_sources()):
            box = QFrame(); box.setObjectName("authRow"); bl = QHBoxLayout(box); bl.setContentsMargins(12, 9, 12, 9)
            desc = QVBoxLayout(); name = QLabel(source.get("name", "Источник")); name.setObjectName("fieldLabel")
            note = QLabel(source.get("note", "")); note.setWordWrap(True); note.setObjectName("cardText"); desc.addWidget(name); desc.addWidget(note)
            btn = QPushButton(source.get("button", "Открыть / скачать")); btn.setToolTip("Открыть официальный сайт источника в браузере.")
            btn.clicked.connect(lambda _=False, u=source.get("url", ""): webbrowser.open(u) if u else None)
            bl.addLayout(desc, 1); bl.addWidget(btn); grid.addWidget(box, row, 0)
        sl.addLayout(grid); root.addWidget(sources)

        library = QFrame(); library.setObjectName("contentCard"); ll = QVBoxLayout(library); ll.setContentsMargins(18, 15, 18, 15); ll.setSpacing(8)
        lt = QLabel("Локальная библиотека"); lt.setObjectName("cardTitle"); ll.addWidget(lt)
        ld = QLabel("Здесь находятся треки, которые реально будут играть. Двойной щелчок по строке запускает выбранную композицию.")
        ld.setWordWrap(True); ld.setObjectName("cardText"); ll.addWidget(ld)
        self.list = QListWidget(); self.list.setMinimumHeight(240); self.list.setToolTip("Локальные треки. Двойной щелчок — начать воспроизведение."); self.list.itemDoubleClicked.connect(lambda _i: self.play_selected()); ll.addWidget(self.list)
        row = QHBoxLayout()
        play = QPushButton("Играть выбранный трек"); play.setToolTip("Запустить отмеченную строку библиотеки."); play.clicked.connect(self.play_selected)
        delete = QPushButton("Удалить выбранный"); delete.setObjectName("dangerButton"); delete.setToolTip("Удалить файл трека из локальной библиотеки после подтверждения."); delete.clicked.connect(self.delete_selected)
        row.addWidget(play); row.addWidget(delete); row.addStretch(1); ll.addLayout(row)
        root.addWidget(library)

        hint = QLabel(f"OBS Browser Source: {self.obs_url}\nПапка библиотеки: {MUSIC_DIR}")
        hint.setWordWrap(True); hint.setObjectName("cardText"); root.addWidget(hint)

        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(1000); self.reload(); self.refresh()

    def _music_sources(self):
        try:
            data = json.loads((CONTENT_DIR / "music_sources.json").read_text(encoding="utf-8"))
            items = data.get("sources", []) if isinstance(data, dict) else []
            if isinstance(items, list): return [x for x in items if isinstance(x, dict)]
        except Exception:
            pass
        return []

    def reload(self):
        background_music.reload_library(); self.list.clear()
        for track in background_music.tracks:
            label = track.title + (f" — {track.author}" if track.author else "")
            if track.source:
                label += "  🔗"
            self.list.addItem(label)

    def play_selected(self):
        i = self.list.currentRow(); background_music.play(i if i >= 0 else None)

    def add_url(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.information(self, "Фоновая музыка", "Вставь ссылку на один трек.")
            return
        if self.worker and self.worker.isRunning():
            return
        self.url_button.setEnabled(False)
        self.url_status.setText("Запускаю импорт…")
        self.worker = MusicUrlWorker(url, self)
        self.worker.status.connect(self.url_status.setText)
        self.worker.completed.connect(self._url_done)
        self.worker.start()

    def _url_done(self, ok: bool, message: str):
        self.url_button.setEnabled(True)
        self.url_status.setText(("✅ " if ok else "⚠ ") + message)
        if ok:
            self.url_input.clear(); self.reload()
        self.worker = None

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Добавить музыку", "",
            "Аудио (*.mp3 *.wav *.m4a *.aac *.ogg *.flac *.webm *.opus);;Все файлы (*.*)",
        )
        if files:
            count = background_music.add_files(files); self.reload(); QMessageBox.information(self, "Фоновая музыка", f"Добавлено файлов: {count}")

    def delete_selected(self):
        index = self.list.currentRow()
        if index < 0:
            QMessageBox.information(self, "Фоновая музыка", "Сначала выбери трек в библиотеке.")
            return
        track = background_music.tracks[index]
        answer = QMessageBox.question(self, "Удалить трек", f"Удалить файл «{track.title}» из локальной библиотеки?")
        if answer != QMessageBox.Yes:
            return
        ok, message = background_music.delete_track(index)
        self.reload()
        if not ok:
            QMessageBox.warning(self, "Фоновая музыка", message)

    def open_folder(self):
        MUSIC_DIR.mkdir(parents=True, exist_ok=True)
        if os.name == "nt": os.startfile(str(MUSIC_DIR))
        else: webbrowser.open(MUSIC_DIR.as_uri())

    def attribution(self):
        text = background_music.attribution_text() or "Для добавленных треков обязательная атрибуция не указана. Это не заменяет проверку лицензии источника."
        QMessageBox.information(self, "Атрибуция", text)

    def _modes(self):
        background_music.shuffle = self.shuffle.isChecked(); background_music.repeat = self.repeat.isChecked(); background_music._save_state()

    def refresh(self):
        snap = background_music.snapshot(); cur = snap.get("current")
        self.volume.blockSignals(True); self.volume.setValue(int(snap.get("volume", 35))); self.volume.blockSignals(False)
        self.shuffle.blockSignals(True); self.repeat.blockSignals(True)
        self.shuffle.setChecked(bool(snap.get("shuffle"))); self.repeat.setChecked(bool(snap.get("repeat", True)))
        self.shuffle.blockSignals(False); self.repeat.blockSignals(False)
        if cur:
            state = "пауза" if snap.get("paused") else ("играет" if snap.get("playing") else "остановлено")
            self.now.setText(cur.get("title", "Без названия"))
            source = cur.get("source", "")
            extra = f" • источник сохранён" if source else ""
            self.info.setText(f"{cur.get('author', '')} • {state} • позиция {int(snap.get('position', 0))} сек.{extra}")
        else:
            self.now.setText("Музыка не выбрана"); self.info.setText("")
