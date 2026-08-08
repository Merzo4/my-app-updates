from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QRadioButton, QScrollArea,
    QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)

from ...core.paths import APP_DATA
from ...core.settings_manager import settings
from ...player.background_music import DEFAULT_MUSIC_DIR, background_music, music_directory
from .about import AboutPage
from .developer import DeveloperPage
from .help import HelpPage
from .logs import LogsPage
from .updates import UpdatesPage


class SettingsPage(QWidget):
    def __init__(self, theme: dict, app_info: dict | None = None, restart=None):
        super().__init__()
        self.theme = theme
        self.app_info = app_info or {}
        self.restart = restart
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 22)
        root.setSpacing(10)
        title = QLabel("Настройки")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Единый системный центр. Сюда перенесены служебные разделы, чтобы главное меню оставалось коротким и понятным.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(12)
        self.sections = QListWidget()
        self.sections.setObjectName("settingsNavigation")
        self.sections.setFixedWidth(205)
        self.sections.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.stack = QStackedWidget()
        self.stack.setObjectName("settingsStack")
        body.addWidget(self.sections)
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        entries = [
            ("general", "⚙ Общие", self._general_page()),
            ("player", "🎵 Медиаплеер", self._player_page()),
            ("storage", "📁 Хранилище", self._storage_page()),
            ("updates", "⬇ Обновления", UpdatesPage(theme, self.app_info, restart=restart)),
            ("help", "📘 Инструкция", HelpPage(theme)),
            ("logs", "📜 Логи", LogsPage(theme)),
            ("developer", "🛠 Разработка", DeveloperPage(theme)),
            ("about", "ℹ О программе", AboutPage(theme, self.app_info)),
        ]
        for section_id, label, page in entries:
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, section_id)
            self.sections.addItem(item)
            self.stack.addWidget(page)
        self.sections.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sections.setCurrentRow(0)

    def select_section(self, section_id: str) -> None:
        value = str(section_id or "general")
        for i in range(self.sections.count()):
            item = self.sections.item(i)
            if str(item.data(Qt.UserRole) or "") == value:
                self.sections.setCurrentRow(i)
                return

    def _card(self, title: str, text: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame(); card.setObjectName("contentCard")
        layout = QVBoxLayout(card); layout.setContentsMargins(18, 15, 18, 15); layout.setSpacing(8)
        h = QLabel(title); h.setObjectName("cardTitle")
        d = QLabel(text); d.setWordWrap(True); d.setObjectName("cardText")
        layout.addWidget(h); layout.addWidget(d)
        return card, layout

    def _general_page(self) -> QWidget:
        host = QWidget()
        root = QVBoxLayout(host); root.setContentsMargins(8, 4, 8, 8); root.setSpacing(12)
        card, l = self._card("Общие настройки", "Основные данные приложения хранятся отдельно от файлов программы, поэтому обычные обновления не должны стирать пользовательские параметры.")
        path = QLabel(f"Данные программы: {APP_DATA}"); path.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard); path.setObjectName("cardText")
        l.addWidget(path)
        open_btn = QPushButton("Открыть папку данных")
        open_btn.clicked.connect(lambda: self._open_path(APP_DATA))
        l.addWidget(open_btn)
        root.addWidget(card)
        card2, l2 = self._card("Куда переехали служебные разделы", "Обновления, Инструкция, Логи, Разработка и О программе теперь находятся в меню слева внутри этой страницы. Это уменьшает количество пунктов в основном Sidebar.")
        root.addWidget(card2)
        root.addStretch(1)
        return host

    def _player_page(self) -> QWidget:
        host = QWidget(); outer = QVBoxLayout(host); outer.setContentsMargins(8,4,8,8)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        inner=QWidget(); form=QFormLayout(inner); form.setSpacing(10)
        self.fields={}; self.checks={}; self.player_data=settings.load('player',force=True)
        specs=[('port','Порт API',1,65535),('volume','Громкость',0,100),('search_results','Результатов поиска',1,20),('search_timeout_sec','Таймаут поиска, сек',5,60),('parallel_checks','Параллельных проверок',1,8),('min_duration_sec','Мин. длительность, сек',0,3600),('max_duration_min','Макс. длительность, мин',1,300),('min_views','Мин. просмотров',0,100000000),('user_limit','Лимит на пользователя',1,100),('global_limit','Макс. очередь',1,500),('user_cooldown_min','Кулдаун, мин',0,1440)]
        for key,label,lo,hi in specs:
            sp=QSpinBox(); sp.setRange(lo,hi); sp.setValue(int(self.player_data.get(key,lo))); self.fields[key]=sp; form.addRow(label,sp)
        for key,label in [('allow_shorts','Разрешить Shorts'),('allow_live','Разрешить live'),('allow_playlists','Разрешить плейлисты'),('allow_age_restricted','Разрешить 18+'),('require_embeddable','Требовать встраивание'),('cookies_enabled','Cookies yt-dlp')]:
            ch=QCheckBox(label); ch.setChecked(bool(self.player_data.get(key,False))); self.checks[key]=ch; form.addRow('',ch)
        scroll.setWidget(inner); outer.addWidget(scroll,1)
        save=QPushButton('Сохранить настройки медиаплеера'); save.setObjectName('primaryButton'); save.clicked.connect(self._save_player); outer.addWidget(save)
        return host

    def _storage_page(self) -> QWidget:
        host = QWidget(); root=QVBoxLayout(host); root.setContentsMargins(8,4,8,8); root.setSpacing(12)
        card,l=self._card("Папка фоновой музыки", "По умолчанию музыка хранится в LocalAppData. Если на диске C мало места, выбери любую собственную папку на D:, E:, внешнем SSD или другом доступном диске. Все новые файлы и URL-импорт будут сохраняться в выбранное место.")
        data=settings.load('storage',force=True)
        self.standard_radio=QRadioButton("Стандартная папка MerzoStream Suite")
        self.custom_radio=QRadioButton("Своя папка")
        self.standard_radio.setChecked(data.get('music_library_mode','standard')!='custom')
        self.custom_radio.setChecked(data.get('music_library_mode')=='custom')
        l.addWidget(self.standard_radio); l.addWidget(self.custom_radio)
        standard=QLabel(f"Стандартная: {DEFAULT_MUSIC_DIR}"); standard.setObjectName('cardText'); standard.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard); l.addWidget(standard)
        row=QHBoxLayout()
        self.music_path=QLineEdit(str(data.get('music_library_path') or '')); self.music_path.setPlaceholderText("Например: D:\\MerzoStream Music")
        browse=QPushButton("Выбрать папку…"); browse.clicked.connect(self._choose_music_folder)
        row.addWidget(self.music_path,1); row.addWidget(browse); l.addLayout(row)
        self.move_music=QCheckBox("Скопировать существующие треки в новую папку при применении")
        self.move_music.setChecked(True); l.addWidget(self.move_music)
        self.current_music_path=QLabel(f"Сейчас используется: {music_directory()}"); self.current_music_path.setObjectName('heroTitle'); self.current_music_path.setWordWrap(True); self.current_music_path.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard); l.addWidget(self.current_music_path)
        save=QPushButton("Применить папку библиотеки"); save.setObjectName('primaryButton'); save.clicked.connect(self._save_storage); l.addWidget(save)
        root.addWidget(card); root.addStretch(1)
        return host

    def _choose_music_folder(self):
        start=self.music_path.text().strip() or str(music_directory())
        value=QFileDialog.getExistingDirectory(self,"Выбрать папку фоновой музыки",start)
        if value:
            self.music_path.setText(value); self.custom_radio.setChecked(True)

    def _save_storage(self):
        old_dir=music_directory()
        mode='custom' if self.custom_radio.isChecked() else 'standard'
        custom=self.music_path.text().strip()
        if mode=='custom' and not custom:
            QMessageBox.warning(self,'Хранилище','Для режима «Своя папка» сначала выбери папку.')
            return
        data=settings.load('storage',force=True); data['music_library_mode']=mode; data['music_library_path']=custom; settings.save('storage',data)
        new_dir=music_directory()
        try: new_dir.mkdir(parents=True,exist_ok=True)
        except Exception as exc:
            data['music_library_mode']='standard'; settings.save('storage',data)
            QMessageBox.warning(self,'Хранилище',f'Не удалось создать выбранную папку:\n{exc}\n\nВозвращена стандартная библиотека.')
            return
        copied=0; skipped=[]
        if self.move_music.isChecked() and old_dir.resolve()!=new_dir.resolve():
            try: copied,skipped=background_music.migrate_library(old_dir,new_dir)
            except Exception as exc: QMessageBox.warning(self,'Хранилище',f'Папка переключена, но не удалось перенести старые файлы:\n{exc}')
        background_music.stop(); background_music.reload_library()
        self.current_music_path.setText(f"Сейчас используется: {new_dir}")
        msg=f"Библиотека переключена на:\n{new_dir}"
        if copied: msg+=f"\n\nСкопировано треков: {copied}"
        if skipped: msg+=f"\nПропущено совпадающих файлов: {len(skipped)}"
        QMessageBox.information(self,'Хранилище',msg)

    def _save_player(self):
        data=settings.load('player',force=True)
        for k,w in self.fields.items(): data[k]=w.value()
        for k,w in self.checks.items(): data[k]=w.isChecked()
        settings.save('player',data)
        QMessageBox.information(self,'Настройки','Сохранено. Если менялся порт API — перезапусти программу.')

    @staticmethod
    def _open_path(path: Path):
        import os
        path.mkdir(parents=True,exist_ok=True)
        if os.name=='nt': os.startfile(str(path))
