from __future__ import annotations

import json
import threading

import customtkinter as ctk

from ...core.config import save
from ...core.event_log import log
from ...core.paths import CONTENT_DIR, STREAM_CONFIG
from ...services.stream import StreamManager


class StreamControlPage(ctk.CTkScrollableFrame):
    def __init__(self, parent, context):
        super().__init__(parent, fg_color="transparent")
        self.context = context
        self.cfg = context["stream_cfg"]
        self.theme = context["theme"]
        self.colors = self.theme["colors"]
        self.manager = StreamManager(self.cfg)
        self.platform_vars: dict[str, ctk.BooleanVar] = {}
        self._build()

    def _panel(self):
        return ctk.CTkFrame(self, fg_color=self.colors.get("card", "#242831"), corner_radius=14)

    def _build(self):
        ctk.CTkLabel(
            self,
            text="📡 Управление трансляциями",
            font=("Arial", 26, "bold"),
            text_color=self.colors.get("text", "#ffffff"),
        ).pack(anchor="w", padx=24, pady=(18, 4))
        ctk.CTkLabel(
            self,
            text="Одно название и категория сразу для всех выбранных платформ.",
            font=("Arial", 13),
            text_color=self.colors.get("muted", "#aeb8c4"),
        ).pack(anchor="w", padx=24, pady=(0, 14))

        form = self._panel()
        form.pack(fill="x", padx=24, pady=8)

        header = ctk.CTkFrame(form, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 4))
        ctk.CTkLabel(header, text="Название трансляции", font=("Arial", 13, "bold")).pack(side="left")
        ctk.CTkButton(
            header,
            text="🤖 Открыть AI Producer",
            width=180,
            height=30,
            command=lambda: self.context["app"].show_page("ai"),
        ).pack(side="right")

        self.title_entry = ctk.CTkEntry(form, height=44, placeholder_text="Введите название трансляции")
        self.title_entry.insert(0, self.cfg.get("title", ""))
        self.title_entry.pack(fill="x", padx=18, pady=(4, 12))

        ctk.CTkLabel(form, text="Категория / игра", font=("Arial", 13, "bold")).pack(anchor="w", padx=18)
        game_row = ctk.CTkFrame(form, fg_color="transparent")
        game_row.pack(fill="x", padx=18, pady=(4, 16))
        games = self._games()
        self.game_combo = ctk.CTkComboBox(game_row, values=games, height=40)
        self.game_combo.set(self.cfg.get("game", "Just Chatting"))
        self.game_combo.pack(side="left", fill="x", expand=True)
        self.search_button = ctk.CTkButton(
            game_row, text="🔎 Найти в Twitch", width=160, height=40, command=self.search_categories
        )
        self.search_button.pack(side="left", padx=(10, 0))

        platforms = self._panel()
        platforms.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(platforms, text="Платформы", font=("Arial", 15, "bold")).pack(anchor="w", padx=18, pady=(14, 6))
        row = ctk.CTkFrame(platforms, fg_color="transparent")
        row.pack(padx=18, pady=(0, 14), anchor="w")
        for key, title in (("twitch", "Twitch"), ("youtube", "YouTube"), ("vk", "VK Video"), ("kick", "Kick")):
            variable = ctk.BooleanVar(value=self.cfg.get("platforms", {}).get(key, True))
            self.platform_vars[key] = variable
            ctk.CTkCheckBox(
                row,
                text=title,
                variable=variable,
                command=self._platform_selection_changed,
            ).pack(side="left", padx=(0, 24))

        self.run_button = ctk.CTkButton(
            self,
            text="🚀 ОБНОВИТЬ ВЕЗДЕ",
            height=58,
            font=("Arial", 18, "bold"),
            command=self.run_all,
        )
        self.run_button.pack(fill="x", padx=24, pady=(10, 8))

        self.status = ctk.CTkTextbox(self, height=190, font=("Consolas", 12))
        self.status.pack(fill="both", expand=True, padx=24, pady=(8, 24))
        self._write("Готово к работе. Авторизации и ключи находятся в разделе «Авторизация».")


    def _platform_selection_changed(self):
        """Сохраняет выбор сразу, чтобы вкладка авторизации показывала только нужные сервисы."""
        self.cfg["platforms"] = {key: variable.get() for key, variable in self.platform_vars.items()}
        save(STREAM_CONFIG, self.cfg)

        # Если страница авторизации уже была открыта, пересоздаём её с новым набором кнопок.
        app = self.context.get("app")
        if app is not None and "auth" in getattr(app, "pages", {}):
            app.reload_page("auth")

    def _games(self) -> list[str]:
        try:
            mapping = json.loads((CONTENT_DIR / "games.json").read_text(encoding="utf-8"))
            return list(mapping.keys()) or ["Just Chatting"]
        except Exception:
            return ["Just Chatting", "SnowRunner", "Rust", "World of Tanks", "GTA 5 RP"]

    def _write(self, message: str):
        self.status.insert("end", message + "\n")
        self.status.see("end")

    def search_categories(self):
        query = self.game_combo.get().strip()
        if not query:
            self._write("Twitch: введи название игры для поиска.")
            return
        self.search_button.configure(state="disabled", text="Поиск...")

        def job():
            names, result = self.manager.twitch.search_categories(query)
            log("Twitch", result.message)
            self.after(0, lambda: self._finish_search(names, result.message))

        threading.Thread(target=job, daemon=True).start()

    def _finish_search(self, names: list[str], message: str):
        self.search_button.configure(state="normal", text="🔎 Найти в Twitch")
        self._write(f"Twitch: {message}")
        if names:
            self.game_combo.configure(values=names)
            self.game_combo.set(names[0])

    def _save_form(self):
        self.cfg["title"] = self.title_entry.get().strip()
        self.cfg["game"] = self.game_combo.get().strip()
        self.cfg["platforms"] = {key: variable.get() for key, variable in self.platform_vars.items()}
        save(STREAM_CONFIG, self.cfg)

    def run_all(self):
        self._save_form()
        title = self.cfg["title"]
        game = self.cfg["game"]
        if not title:
            self._write("Ошибка: название трансляции не заполнено.")
            return
        self.run_button.configure(state="disabled", text="⏳ ОБНОВЛЕНИЕ...")
        self._write("────────────────────────────────────────")
        self._write(f"Запуск: {game} | {title}")

        def job():
            tasks = []
            if self.platform_vars["twitch"].get():
                tasks.append(("Twitch", lambda: self.manager.twitch.update(title, game)))
            if self.platform_vars["youtube"].get():
                tasks.append(("YouTube", lambda: self.manager.youtube.update(title, game)))
            if self.platform_vars["vk"].get():
                tasks.append(("VK Video", lambda: self.manager.vk.update(title, game)))
            if self.platform_vars["kick"].get():
                tasks.append(("Kick", lambda: self.manager.kick.update(title, game)))

            for platform, callback in tasks:
                self.after(0, lambda p=platform: self._write(f"{p}: обновление..."))
                result = callback()
                log(platform, result.message)
                mark = "✅" if result.ok else "❌"
                self.after(0, lambda p=platform, r=result, m=mark: self._write(f"{m} {p}: {r.message}"))
            self.after(0, self._finish_update)

        threading.Thread(target=job, daemon=True).start()

    def _finish_update(self):
        self._write("Глобальная сессия завершена.")
        self.run_button.configure(state="normal", text="🚀 ОБНОВИТЬ ВЕЗДЕ")
