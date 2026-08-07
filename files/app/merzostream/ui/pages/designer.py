from __future__ import annotations

import importlib.util
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from PIL import Image

import customtkinter as ctk

from ...core.paths import CONTENT_DIR, GRAPHICS_DIR, bundle_root
from ...core.settings_manager import settings


class DesignerPage(ctk.CTkScrollableFrame):
    """Центр нового интерфейса и пакетов пользовательского оформления."""

    def __init__(self, master, context):
        theme = context["theme"]
        super().__init__(master, fg_color="transparent")
        self.context = context
        self.colors = theme["colors"]
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Дизайнер интерфейса", font=("Arial", 24, "bold"), text_color=self.colors["text"]).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))
        ctk.CTkLabel(self, text="Экспериментальная оболочка PySide6 и пакеты собственной графики. Классический интерфейс остаётся резервным.", wraplength=850, justify="left", text_color=self.colors.get("muted_text", self.colors["text"])).grid(row=1, column=0, sticky="w", padx=10, pady=(0, 14))

        self._section_interface(2)
        self._section_theme(3)
        self._section_structure(4)

    def _card(self, row: int, title: str):
        frame = ctk.CTkFrame(self, fg_color=self.colors.get("card", "#24282f"), border_width=1, border_color=self.colors.get("border", "#3a414b"))
        frame.grid(row=row, column=0, sticky="ew", padx=10, pady=7)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=title, font=("Arial", 17, "bold"), text_color=self.colors["text"]).grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(14, 8))
        return frame

    def _section_interface(self, row: int):
        frame = self._card(row, "Новый интерфейс PySide6")
        installed = importlib.util.find_spec("PySide6") is not None
        self.qt_status = ctk.CTkLabel(frame, text="● PySide6 установлен" if installed else "● PySide6 пока не установлен", text_color=self.colors.get("success") if installed else "#f3b84b")
        self.qt_status.grid(row=1, column=0, sticky="w", padx=16, pady=8)
        ctk.CTkButton(frame, text="Установить PySide6", command=self.install_qt).grid(row=1, column=1, padx=8, pady=8)
        ctk.CTkButton(frame, text="Запустить новый интерфейс", command=self.enable_qt).grid(row=1, column=2, padx=(8,16), pady=8)
        ctk.CTkLabel(frame, text="После включения программа перезапустится. В новой оболочке уже работают навигация, постоянный мониторинг ПК и пакеты оформления. Рабочие модули будут переноситься поэтапно.", wraplength=850, justify="left", text_color=self.colors.get("muted_text", self.colors["text"])).grid(row=2, column=0, columnspan=3, sticky="w", padx=16, pady=(0,14))

    def _installed_themes(self):
        result = []
        root = CONTENT_DIR / "ui_themes"
        if root.exists():
            for folder in sorted(root.iterdir()):
                path = folder / "theme.json"
                if not path.exists():
                    continue
                try:
                    import json
                    data = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    continue
                theme_id = str(data.get("id") or folder.name)
                result.append((theme_id, str(data.get("title") or theme_id), str(data.get("description") or "")))
        return result

    def _section_theme(self, row: int):
        frame = self._card(row, "Готовые шаблоны оформления")
        self._themes = self._installed_themes()
        self._theme_title_to_id = {title: theme_id for theme_id, title, _ in self._themes}
        current_id = settings.get("ui", "qt_theme_id", "merzostream_dark")
        current_title = next((title for theme_id, title, _ in self._themes if theme_id == current_id), current_id)
        ctk.CTkLabel(frame, text="Выбери тему — это уже не просто цвет, а готовый визуальный шаблон:", text_color=self.colors["text"]).grid(row=1, column=0, columnspan=3, sticky="w", padx=16, pady=(8,4))
        self.theme_var = ctk.StringVar(value=current_title)
        values = [title for _, title, _ in self._themes] or ["MerzoStream Dark"]
        self.theme_menu = ctk.CTkOptionMenu(frame, variable=self.theme_var, values=values, width=260, command=lambda _: self._update_theme_preview())
        self.theme_menu.grid(row=2, column=0, sticky="w", padx=16, pady=8)
        ctk.CTkButton(frame, text="Сохранить тему", width=140, command=self.save_theme).grid(row=2, column=1, padx=8, pady=8, sticky="w")
        ctk.CTkButton(frame, text="Запустить и посмотреть", width=170, command=self.preview_theme).grid(row=2, column=2, padx=(8,16), pady=8, sticky="w")

        self.preview_label = ctk.CTkLabel(frame, text="", width=720, height=300)
        self.preview_label.grid(row=3, column=0, columnspan=3, padx=16, pady=(6,10), sticky="w")
        self.theme_description = ctk.CTkLabel(frame, text="", wraplength=850, justify="left", text_color=self.colors.get("muted_text", self.colors["text"]))
        self.theme_description.grid(row=4, column=0, columnspan=3, sticky="w", padx=16, pady=(0,10))
        ctk.CTkButton(frame, text="Открыть папку тем", command=lambda: self._open_folder(CONTENT_DIR / "ui_themes")).grid(row=5, column=0, padx=16, pady=(4,14), sticky="w")
        ctk.CTkButton(frame, text="Открыть папку графики", command=lambda: self._open_folder(GRAPHICS_DIR / "ui_themes")).grid(row=5, column=1, padx=8, pady=(4,14), sticky="w")
        self._update_theme_preview()

    def _selected_theme_id(self):
        return self._theme_title_to_id.get(self.theme_var.get(), self.theme_var.get().strip() or "merzostream_dark")

    def _update_theme_preview(self):
        theme_id = self._selected_theme_id()
        description = next((desc for tid, _, desc in self._themes if tid == theme_id), "")
        self.theme_description.configure(text=description)
        preview = GRAPHICS_DIR / "ui_themes" / theme_id / "preview.png"
        if preview.exists():
            try:
                img = Image.open(preview).convert("RGB")
                img.thumbnail((720, 300))
                self._preview_image = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self.preview_label.configure(image=self._preview_image, text="")
                return
            except Exception:
                pass
        self.preview_label.configure(image=None, text="Для этой темы пока нет preview.png")

    def preview_theme(self):
        self.save_theme(show_message=False)
        self.enable_qt()

    def _section_structure(self, row: int):
        frame = self._card(row, "Что можно оформлять")
        text = (
            "• фон всей рабочей области;\n• собственные иконки каждой вкладки;\n• цвета меню, карточек и правой панели;\n"
            "• размеры бокового меню и постоянного мониторинга;\n• скругления, границы и акцентный цвет;\n"
            "• в будущих 0.0.2b/0.0.2c — положение и размер блоков через визуальный конструктор."
        )
        ctk.CTkLabel(frame, text=text, justify="left", text_color=self.colors["text"]).grid(row=1, column=0, columnspan=3, sticky="w", padx=16, pady=(4,16))

    def install_qt(self):
        self.qt_status.configure(text="Установка PySide6…", text_color="#f3b84b")
        def worker():
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "PySide6", "psutil"])
                self.after(0, lambda: self.qt_status.configure(text="● PySide6 установлен", text_color=self.colors.get("success", "#48d17d")))
            except Exception as exc:
                message = str(exc)
                self.after(0, lambda e=message: messagebox.showerror("MerzoStream Suite", f"Не удалось установить PySide6:\n{e}"))
        threading.Thread(target=worker, daemon=True).start()

    def enable_qt(self):
        if importlib.util.find_spec("PySide6") is None:
            messagebox.showwarning("MerzoStream Suite", "Сначала нажми «Установить PySide6» и дождись завершения.")
            return
        settings.set("ui", "mode", "qt")
        self.context["app"].restart_application()

    def save_theme(self, show_message=True):
        theme_id = self._selected_theme_id()
        settings.set("ui", "qt_theme_id", theme_id)
        if show_message:
            messagebox.showinfo("MerzoStream Suite", "Пакет оформления сохранён. Нажми «Запустить и посмотреть», чтобы увидеть его в новом интерфейсе.")

    @staticmethod
    def _open_folder(path: Path):
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
