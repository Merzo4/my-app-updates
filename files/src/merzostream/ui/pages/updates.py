from __future__ import annotations

import threading
import tkinter.messagebox as messagebox

import customtkinter as ctk


class UpdatesPage(ctk.CTkFrame):
    def __init__(self, parent, context):
        super().__init__(parent, fg_color="transparent")
        self.context = context
        self.app = context["app"]
        self.manager = context["update_manager"]
        self.app_info = context["app_info"]
        self._busy = False
        self._last_check = None

        ctk.CTkLabel(self, text="⬇️ Обновления", font=("Arial", 26, "bold")).pack(anchor="w", padx=24, pady=(20, 5))
        ctk.CTkLabel(
            self,
            text="Программа сравнивает SHA-256 и скачивает только изменившиеся файлы.",
            text_color="#aeb8c4",
            font=("Arial", 13),
        ).pack(anchor="w", padx=24, pady=(0, 20))

        card = ctk.CTkFrame(self, fg_color="#24282f", corner_radius=14)
        card.pack(fill="x", padx=24, pady=10)
        ctk.CTkLabel(card, text="Текущая версия", font=("Arial", 14, "bold")).pack(anchor="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(
            card,
            text=f'{self.app_info.get("channel", "Beta")} {self.app_info.get("version", "0.0.1")}',
            text_color="#70b7ff",
            font=("Arial", 20, "bold"),
        ).pack(anchor="w", padx=18)
        cfg = self.manager.load_config()
        ctk.CTkLabel(
            card,
            text=f'Reпозиторий: {cfg.get("repository", "Merzo4/my-app-updates")}',
            text_color="#aeb8c4",
        ).pack(anchor="w", padx=18, pady=(6, 18))

        self.status = ctk.CTkLabel(self, text="Нажми «Проверить обновления».", anchor="w")
        self.status.pack(fill="x", padx=24, pady=(8, 4))
        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(fill="x", padx=24, pady=4)
        self.progress.set(0)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=24, pady=10)
        self.check_button = ctk.CTkButton(buttons, text="Проверить обновления", height=42, command=self.check_updates)
        self.check_button.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.install_button = ctk.CTkButton(
            buttons,
            text="Установить и перезапустить",
            height=42,
            state="disabled",
            command=self.install_update,
        )
        self.install_button.pack(side="left", fill="x", expand=True, padx=(6, 0))

        ctk.CTkLabel(self, text="Что изменится", font=("Arial", 16, "bold")).pack(anchor="w", padx=24, pady=(16, 6))
        self.details = ctk.CTkTextbox(self, height=220)
        self.details.pack(fill="both", expand=True, padx=24, pady=(0, 20))
        self._write_details("История обновлений появится здесь после первой проверки.")

    def _set_busy(self, value: bool):
        self._busy = value
        self.check_button.configure(state="disabled" if value else "normal")
        if value:
            self.install_button.configure(state="disabled")

    def _write_details(self, text: str):
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", text or "Неизвестная ошибка")
        self.details.configure(state="disabled")

    def check_updates(self):
        if self._busy:
            return
        self._set_busy(True)
        self.status.configure(text="Проверяю GitHub…")
        self.progress.set(0.15)

        def worker():
            try:
                result = self.manager.check(str(self.app_info.get("version", "0.0.1")))
                self.after(0, lambda result=result: self._show_check_result(result))
            except Exception as exc:
                error_text = str(exc) or repr(exc)
                self.after(0, lambda text=error_text: self._show_error("Проверка обновления", text))

        threading.Thread(target=worker, daemon=True).start()

    def _show_check_result(self, result):
        self._set_busy(False)
        self._last_check = result
        if not result.available:
            self.status.configure(text="✅ Установлена актуальная версия.")
            self.progress.set(1)
            self.install_button.configure(state="disabled")
            self._write_details("Новых или изменённых файлов нет.")
            return

        total_size = sum(item.size for item in result.files)
        lines = [
            f"Версия: {result.current_version} → {result.remote_version}",
            f"Изменено файлов: {len(result.files)}",
            f"Размер: {total_size / 1024 / 1024:.2f} МБ",
            "",
        ]
        if result.release_notes:
            lines.append("Что нового:")
            lines.extend(f"• {note}" for note in result.release_notes)
            lines.append("")
        if result.files:
            lines.append("Файлы:")
            lines.extend(f"• {item.path}" for item in result.files)

        self.status.configure(text=f"🔔 Доступно обновление {result.remote_version}")
        self.progress.set(0.35)
        self.install_button.configure(state="normal")
        self._write_details("\n".join(lines))

    def _show_error(self, stage: str, text: str):
        self._set_busy(False)
        self.progress.set(0)
        self.status.configure(text=f"❌ Ошибка: {stage}")
        self._write_details(text)

    def install_update(self):
        if self._busy or not self._last_check:
            return
        if not messagebox.askyesno(
            "MerzoStream Suite",
            "Будет создана резервная копия, затем заменятся только изменённые файлы. Продолжить?",
        ):
            return

        self._set_busy(True)
        self.status.configure(text="Подготовка обновления…")
        self.progress.set(0.02)

        def progress(done, total, message):
            ratio = done / total if total else 0
            self.after(0, lambda text=message: self.status.configure(text=text))
            self.after(0, lambda value=ratio: self.progress.set(max(0, min(1, value))))

        def worker():
            try:
                updated = self.manager.apply(self._last_check, progress)
                self.after(0, lambda files=updated: self._finish_install(files))
            except Exception as exc:
                error_text = str(exc) or repr(exc)
                self.after(0, lambda text=error_text: self._show_error("Установка обновления", text))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_install(self, updated):
        self.progress.set(1)
        self.status.configure(text=f"✅ Обновлено файлов: {len(updated)}. Перезапуск…")
        self.after(900, self.app.restart_application)
