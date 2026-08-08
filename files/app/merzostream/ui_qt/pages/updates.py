from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QTextEdit, QVBoxLayout, QWidget

from ...core.update_manager import update_manager


class _Signals(QObject):
    checked = Signal(object)
    error = Signal(str)
    progress = Signal(int, int, str)
    installed = Signal(object)


class UpdatesPage(QWidget):
    def __init__(self, theme: dict, app_info: dict, restart=None):
        super().__init__(); self.theme=theme; self.app_info=app_info; self.restart=restart; self.manager=update_manager; self.last_check=None; self.busy=False
        self.signals=_Signals(self); self.signals.checked.connect(self._show_check); self.signals.error.connect(self._show_error); self.signals.progress.connect(self._progress); self.signals.installed.connect(self._installed)
        root=QVBoxLayout(self); root.setContentsMargins(28,22,28,26); root.setSpacing(14)
        title=QLabel("Обновления"); title.setObjectName("pageTitle"); sub=QLabel("GitHub Update Engine 2.1: проверка SHA-256, резервная копия, откат и понятные ошибки."); sub.setObjectName("pageSubtitle")
        root.addWidget(title); root.addWidget(sub)
        card=QFrame(); card.setObjectName("heroCard"); cl=QHBoxLayout(card); cl.setContentsMargins(20,18,20,18)
        left=QVBoxLayout(); a=QLabel("Текущая версия"); a.setObjectName("cardText"); self.version=QLabel(f"{app_info.get('channel','Beta')} {app_info.get('version','—')}"); self.version.setObjectName("heroTitle"); left.addWidget(a); left.addWidget(self.version)
        repo=QLabel(f"Репозиторий: {self.manager.load_config().get('repository','Merzo4/my-app-updates')}"); repo.setObjectName("cardText"); left.addWidget(repo); cl.addLayout(left); cl.addStretch(1)
        root.addWidget(card)
        self.status=QLabel("Нажми «Проверить обновления»."); self.status.setObjectName("cardText"); root.addWidget(self.status)
        self.bar=QProgressBar(); self.bar.setRange(0,100); self.bar.setValue(0); root.addWidget(self.bar)
        row=QHBoxLayout(); self.check_btn=QPushButton("Проверить обновления"); self.check_btn.setObjectName("primaryButton"); self.check_btn.clicked.connect(self.check)
        self.install_btn=QPushButton("Установить и перезапустить"); self.install_btn.setEnabled(False); self.install_btn.clicked.connect(self.install); row.addWidget(self.check_btn); row.addWidget(self.install_btn); root.addLayout(row)
        h=QLabel("Что изменится / история"); h.setObjectName("cardTitle"); root.addWidget(h)
        self.details=QTextEdit(); self.details.setReadOnly(True); self.details.setMinimumHeight(270); root.addWidget(self.details,1); self._show_history()

    def _set_busy(self,v):
        self.busy=v; self.check_btn.setEnabled(not v); self.install_btn.setEnabled((not v) and bool(self.last_check and self.last_check.available))

    def _show_history(self):
        history=self.manager.history(); lines=[]
        for item in history[:8]:
            lines.append(f"{item.get('from_version','?')} → {item.get('to_version','?')}  | файлов: {len(item.get('updated_files',[]))}")
            for note in item.get('release_notes',[])[:4]: lines.append("  • "+str(note))
            lines.append("")
        self.details.setPlainText("\n".join(lines) if lines else "История обновлений пока пуста.")

    def check(self):
        if self.busy:return
        self._set_busy(True); self.status.setText("Проверяю GitHub…"); self.bar.setValue(12)
        def job():
            try:self.signals.checked.emit(self.manager.check(str(self.app_info.get('version','0.0.0'))))
            except Exception as e:self.signals.error.emit(str(e))
        threading.Thread(target=job,daemon=True).start()

    def _show_check(self,result):
        self._set_busy(False); self.last_check=result
        if not result.available:
            self.status.setText("✅ " + (result.message or "Установлена актуальная версия.")); self.bar.setValue(100); self.install_btn.setEnabled(False); self._show_history(); return
        total=sum(x.size for x in result.files); lines=[f"Версия: {result.current_version} → {result.remote_version}",f"Изменено файлов: {len(result.files)}",f"Размер: {total/1024/1024:.2f} МБ",""]
        if result.release_notes:
            lines.append("Что нового:"); lines.extend("• "+x for x in result.release_notes); lines.append("")
        if result.files:
            lines.append("Файлы:"); lines.extend("• "+x.path for x in result.files)
        self.details.setPlainText("\n".join(lines)); self.status.setText(f"🔔 Доступно обновление {result.remote_version}"); self.bar.setValue(35); self.install_btn.setEnabled(True)

    def install(self):
        if self.busy or not self.last_check:return
        if QMessageBox.question(self,"MerzoStream Suite","Скачать изменённые файлы, создать резервную копию и перезапустить программу?") != QMessageBox.Yes:return
        self._set_busy(True); self.status.setText("Устанавливаю обновление…")
        def cb(done,total,msg): self.signals.progress.emit(done,total,msg)
        def job():
            try:self.signals.installed.emit(self.manager.apply(self.last_check,cb))
            except Exception as e:self.signals.error.emit(str(e))
        threading.Thread(target=job,daemon=True).start()

    def _progress(self,done,total,msg):
        self.status.setText(msg); self.bar.setValue(int(done*100/total) if total else 0)

    def _installed(self,updated):
        self.bar.setValue(100); self.status.setText(f"✅ Обновлено файлов: {len(updated)}. Перезапуск…")
        if self.restart: self.restart()

    def _show_error(self,text):
        self._set_busy(False); self.bar.setValue(0); self.status.setText("❌ Ошибка Update Center"); self.details.setPlainText(text or "Неизвестная ошибка")
