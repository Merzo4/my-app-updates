from __future__ import annotations

import os
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ...player.background_music import MUSIC_DIR, background_music


class BackgroundMusicPage(ctk.CTkFrame):
    def __init__(self, parent, context):
        self.context = context
        self.colors = context["theme"]["colors"]
        self.port = int(context["player_cfg"].get("port", 5000))
        self.obs_url = f"http://127.0.0.1:{self.port}/music"
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_header()
        self._build_controls()
        self._build_library()
        self.after(500, self._refresh_loop)

    def _card(self):
        return ctk.CTkFrame(self, fg_color=self.colors.get("card", "#20242b"), corner_radius=14,
                            border_width=1, border_color=self.colors.get("border", "#353941"))

    def _build_header(self):
        card = self._card(); card.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6)); card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="🎼 Фоновая музыка без клипов", font=("Arial", 20, "bold"),
                     text_color=self.colors["text"]).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(card, text="Отдельный аудио-источник для OBS. Видео заказов сюда не попадает.",
                     text_color=self.colors.get("muted_text", self.colors["text"])).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
        row = ctk.CTkFrame(card, fg_color="transparent"); row.grid(row=0, column=1, rowspan=2, padx=12)
        ctk.CTkButton(row, text="Открыть OBS-источник", command=lambda: webbrowser.open(self.obs_url)).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Открыть папку музыки", command=self.open_folder).pack(side="left", padx=4)

    def _build_controls(self):
        card = self._card(); card.grid(row=1, column=0, sticky="ew", padx=8, pady=6); card.grid_columnconfigure(0, weight=1)
        self.title_label = ctk.CTkLabel(card, text="Музыка не выбрана", font=("Arial", 16, "bold"), text_color=self.colors["text"])
        self.title_label.grid(row=0, column=0, sticky="w", padx=16, pady=(14, 2))
        self.info_label = ctk.CTkLabel(card, text="", text_color=self.colors.get("muted_text", self.colors["text"])); self.info_label.grid(row=1, column=0, sticky="w", padx=16)
        row = ctk.CTkFrame(card, fg_color="transparent"); row.grid(row=2, column=0, sticky="ew", padx=12, pady=12)
        ctk.CTkButton(row, text="⏮", width=50, command=background_music.previous).pack(side="left", padx=3)
        ctk.CTkButton(row, text="▶ Играть", width=90, command=background_music.play).pack(side="left", padx=3)
        ctk.CTkButton(row, text="⏯ Пауза", width=90, command=background_music.pause_toggle).pack(side="left", padx=3)
        ctk.CTkButton(row, text="⏹ Стоп", width=80, command=background_music.stop).pack(side="left", padx=3)
        ctk.CTkButton(row, text="⏭", width=50, command=background_music.next).pack(side="left", padx=3)
        ctk.CTkLabel(row, text="Громкость", text_color=self.colors["text"]).pack(side="left", padx=(18, 5))
        self.volume = ctk.CTkSlider(row, from_=0, to=100, width=160, command=background_music.set_volume); self.volume.pack(side="left", padx=4)
        self.shuffle_var = ctk.BooleanVar(value=background_music.shuffle)
        self.repeat_var = ctk.BooleanVar(value=background_music.repeat)
        ctk.CTkSwitch(row, text="Случайно", variable=self.shuffle_var, command=self._apply_modes).pack(side="left", padx=8)
        ctk.CTkSwitch(row, text="Повтор", variable=self.repeat_var, command=self._apply_modes).pack(side="left", padx=8)

    def _build_library(self):
        card = self._card(); card.grid(row=2, column=0, sticky="nsew", padx=8, pady=(6, 8)); card.grid_columnconfigure(0, weight=1); card.grid_rowconfigure(1, weight=1)
        top = ctk.CTkFrame(card, fg_color="transparent"); top.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        ctk.CTkButton(top, text="Добавить аудиофайлы", command=self.add_files).pack(side="left", padx=3)
        ctk.CTkButton(top, text="Обновить список", command=self.reload).pack(side="left", padx=3)
        ctk.CTkButton(top, text="Скопировать атрибуцию", command=self.show_attribution).pack(side="left", padx=3)
        ctk.CTkLabel(top, text=f"OBS Browser Source: {self.obs_url}", font=("Consolas", 11),
                     text_color=self.colors.get("muted_text", self.colors["text"])).pack(side="right")
        self.list_frame = ctk.CTkScrollableFrame(card, fg_color="transparent"); self.list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.reload()

    def reload(self):
        background_music.reload_library()
        for child in self.list_frame.winfo_children(): child.destroy()
        for index, track in enumerate(background_music.tracks):
            row = ctk.CTkFrame(self.list_frame, fg_color=self.colors.get("panel", self.colors.get("card", "#20242b")))
            row.pack(fill="x", pady=3); row.grid_columnconfigure(0, weight=1)
            text = track.title + (f" — {track.author}" if track.author else "")
            ctk.CTkLabel(row, text=text, anchor="w", text_color=self.colors["text"]).grid(row=0, column=0, sticky="ew", padx=10, pady=8)
            ctk.CTkButton(row, text="Играть", width=70, command=lambda i=index: background_music.play(i)).grid(row=0, column=1, padx=4)
            ctk.CTkButton(row, text="Данные", width=70, command=lambda i=index: self.edit_metadata(i)).grid(row=0, column=2, padx=(0, 8))
        if not background_music.tracks:
            ctk.CTkLabel(self.list_frame, text="Добавь MP3/WAV из YouTube Audio Library или другой лицензированной библиотеки.",
                         text_color=self.colors.get("muted_text", self.colors["text"])).pack(anchor="w", padx=10, pady=20)

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("Аудио", "*.mp3 *.wav *.m4a *.aac *.ogg *.flac"), ("Все файлы", "*.*")])
        if files:
            count = background_music.add_files(list(files)); self.reload(); messagebox.showinfo("Фоновая музыка", f"Добавлено файлов: {count}")

    def edit_metadata(self, index: int):
        if not (0 <= index < len(background_music.tracks)): return
        track = background_music.tracks[index]
        dialog = ctk.CTkToplevel(self); dialog.title("Данные трека"); dialog.geometry("560x480"); dialog.grab_set()
        fields = {}
        for label, key, value in [("Название", "title", track.title), ("Автор", "author", track.author), ("Источник / ссылка", "source", track.source)]:
            ctk.CTkLabel(dialog, text=label).pack(anchor="w", padx=20, pady=(12, 2)); e=ctk.CTkEntry(dialog); e.insert(0, value); e.pack(fill="x", padx=20); fields[key]=e
        attr_var = ctk.BooleanVar(value=track.attribution_required)
        ctk.CTkSwitch(dialog, text="Требуется указание автора", variable=attr_var).pack(anchor="w", padx=20, pady=14)
        ctk.CTkLabel(dialog, text="Текст атрибуции для описания YouTube").pack(anchor="w", padx=20)
        box=ctk.CTkTextbox(dialog, height=120); box.insert("1.0", track.attribution_text); box.pack(fill="both", expand=True, padx=20, pady=(4, 12))
        def save():
            background_music.update_metadata(track.filename, title=fields["title"].get().strip() or Path(track.filename).stem,
                author=fields["author"].get().strip(), source=fields["source"].get().strip(),
                attribution_required=attr_var.get(), attribution_text=box.get("1.0", "end").strip())
            dialog.destroy(); self.reload()
        ctk.CTkButton(dialog, text="Сохранить", command=save).pack(pady=(0, 16))

    def show_attribution(self):
        text = background_music.attribution_text() or "Для добавленных треков обязательная атрибуция не указана."
        dialog=ctk.CTkToplevel(self); dialog.title("Атрибуция для YouTube"); dialog.geometry("650x420"); dialog.grab_set()
        box=ctk.CTkTextbox(dialog); box.insert("1.0", text); box.pack(fill="both", expand=True, padx=14, pady=14)

    def open_folder(self):
        MUSIC_DIR.mkdir(parents=True, exist_ok=True); os.startfile(MUSIC_DIR)

    def _apply_modes(self):
        background_music.shuffle = self.shuffle_var.get(); background_music.repeat = self.repeat_var.get(); background_music._save_state()

    def _refresh_loop(self):
        if not self.winfo_exists(): return
        snap=background_music.snapshot(); current=snap.get("current")
        self.volume.set(snap.get("volume", 35))
        if current:
            self.title_label.configure(text=current.get("title", "Без названия")); self.info_label.configure(text=f"{current.get('author','')}  •  позиция {int(snap.get('position',0))} сек.")
        else:
            self.title_label.configure(text="Музыка не выбрана"); self.info_label.configure(text="")
        self.after(1000, self._refresh_loop)
