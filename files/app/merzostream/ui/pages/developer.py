from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from ...core.event_log import log
from ...core.paths import APP_DATA, BACKUPS_DIR, LOGS_DIR, bundle_root


class DeveloperPage(ctk.CTkFrame):
    def __init__(self, parent, context):
        super().__init__(parent, fg_color="transparent")
        self.context = context
        self.colors = context["theme"]["colors"]
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Режим разработчика", font=("Arial", 24, "bold"), text_color=self.colors["text"]).pack(anchor="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(self, text="Инструменты подготовки обновлений и обслуживания проекта. Публикация на GitHub выполняется только после твоего подтверждения.", wraplength=850, justify="left", text_color=self.colors.get("muted_text", self.colors["text"])).pack(anchor="w", padx=18, pady=(0, 16))
        card = ctk.CTkFrame(self, fg_color=self.colors.get("card", self.colors["window"]))
        card.pack(fill="x", padx=18, pady=8)
        actions = [
            ("Подготовить GitHub-обновление", self.prepare_update),
            ("Создать резервную копию настроек", self.backup_settings),
            ("Открыть папку проекта", lambda: self.open_path(bundle_root())),
            ("Открыть AppData", lambda: self.open_path(APP_DATA)),
            ("Открыть логи", lambda: self.open_path(LOGS_DIR)),
            ("Открыть резервные копии", lambda: self.open_path(BACKUPS_DIR)),
        ]
        for title, command in actions:
            ctk.CTkButton(card, text=title, height=40, anchor="w", command=command).pack(fill="x", padx=12, pady=6)
        self.status = ctk.CTkLabel(self, text="Готово к работе", anchor="w", text_color=self.colors.get("success", "#34d399"))
        self.status.pack(fill="x", padx=20, pady=10)

    def open_path(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(path))

    def backup_settings(self):
        try:
            target = self.context["settings"].backup_all()
            self.status.configure(text=f"Резервная копия: {target}")
            log("DEVELOPER", f"Создана резервная копия настроек: {target}", "SUCCESS")
        except Exception as exc:
            messagebox.showerror("Резервная копия", str(exc))

    def prepare_update(self):
        script = bundle_root() / "tools" / "prepare_github_update.py"
        if not script.exists():
            messagebox.showerror("Подготовка обновления", f"Не найден файл: {script}")
            return
        try:
            result = subprocess.run([sys.executable, str(script)], cwd=str(bundle_root()), capture_output=True, text=True, timeout=180)
            output = (result.stdout or result.stderr or "Готово").strip()
            self.status.configure(text=output[-300:])
            log("DEVELOPER", "Пакет GitHub-обновления подготовлен", "SUCCESS" if result.returncode == 0 else "ERROR")
            if result.returncode == 0:
                upload = bundle_root() / "github_upload"
                if upload.exists():
                    os.startfile(str(upload))
            else:
                messagebox.showerror("Подготовка обновления", output)
        except Exception as exc:
            messagebox.showerror("Подготовка обновления", str(exc))
