from __future__ import annotations

import threading
import webbrowser

import customtkinter as ctk

from ...core.config import save
from ...core.event_log import log
from ...core.paths import CLIENT_SECRET, KICK_TOKEN, STREAM_CONFIG, YOUTUBE_TOKEN
from ...services.stream import StreamManager


class AuthorizationPage(ctk.CTkScrollableFrame):
    VK_AUTH_URL = (
        "https://auth.live.vkvideo.ru/app/oauth2/authorize?client_id=lmn3one57wbvnwyo"
        "&response_type=token&scope=channel:stream:settings&redirect_uri=http://localhost"
    )

    def __init__(self, parent, context):
        super().__init__(parent, fg_color="transparent")
        self.context = context
        self.cfg = context["stream_cfg"]
        self.manager = StreamManager(self.cfg)
        self.fields = {}
        self.platforms = self.cfg.get("platforms", {})

        ctk.CTkLabel(self, text="🔐 Авторизация и API", font=("Arial", 26, "bold")).pack(
            anchor="w", padx=24, pady=(18, 4)
        )
        ctk.CTkLabel(
            self,
            text="Здесь отображаются только платформы, выбранные в разделе «Управление трансляцией».",
            font=("Arial", 13),
            text_color=context["theme"]["colors"].get("muted", "#aeb8c4"),
        ).pack(anchor="w", padx=24, pady=(0, 14))

        # Twitch Client ID встроен в программу. Показывать и вводить его вручную больше не нужно.
        if self._enabled("vk"):
            self._credential_panel(
                "VK Video",
                [("vk_token", "Access Token", True)],
                "Нажми кнопку авторизации ниже, затем вставь полученный токен.",
            )

        if self._enabled("kick"):
            self._credential_panel(
                "Kick",
                [("kick_client_id", "Client ID", False), ("kick_client_secret", "Client Secret", True)],
                "После сохранения нажми «Авторизовать Kick».",
            )

        self._credential_panel(
            "Groq AI",
            [("groq_key", "Groq API Key", True)],
            "Ключ используется только AI Producer.",
        )

        ctk.CTkButton(self, text="💾 Сохранить настройки", height=44, command=self.save_fields).pack(
            fill="x", padx=24, pady=10
        )

        actions = ctk.CTkFrame(self)
        actions.pack(fill="x", padx=24, pady=10)
        ctk.CTkLabel(actions, text="Браузерная авторизация", font=("Arial", 16, "bold")).pack(
            anchor="w", padx=16, pady=(14, 8)
        )

        buttons = ctk.CTkFrame(actions, fg_color="transparent")
        buttons.pack(fill="x", padx=16, pady=(0, 14))

        if self._enabled("twitch"):
            self._auth_row(
                buttons,
                "Twitch",
                self.authorize_twitch,
                self.reset_twitch,
            )
        if self._enabled("youtube"):
            self._auth_row(
                buttons,
                "YouTube",
                self.authorize_youtube,
                self.reset_youtube,
            )
        if self._enabled("kick"):
            self._auth_row(
                buttons,
                "Kick",
                self.authorize_kick,
                self.reset_kick,
            )
        if self._enabled("vk"):
            row = ctk.CTkFrame(buttons, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text="VK Video", width=110, anchor="w", font=("Arial", 13, "bold")).pack(side="left")
            ctk.CTkButton(row, text="▶ Получить токен", command=lambda: webbrowser.open(self.VK_AUTH_URL)).pack(
                side="left", padx=(8, 0)
            )

        self.status_label = ctk.CTkLabel(self, text="", justify="left", font=("Consolas", 12))
        self.status_label.pack(anchor="w", padx=28, pady=12)
        self.refresh_status()

    def _enabled(self, key: str) -> bool:
        return bool(self.platforms.get(key, False))

    def _auth_row(self, parent, title, authorize_command, reset_command):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=title, width=110, anchor="w", font=("Arial", 13, "bold")).pack(side="left")
        ctk.CTkButton(row, text="▶ Авторизовать", command=authorize_command).pack(side="left", padx=(8, 8))
        ctk.CTkButton(row, text="♻ Сбросить", fg_color="#b23b3b", command=reset_command).pack(side="left")

    def _credential_panel(self, title, fields, hint):
        panel = ctk.CTkFrame(self)
        panel.pack(fill="x", padx=24, pady=7)
        ctk.CTkLabel(panel, text=title, font=("Arial", 16, "bold")).pack(anchor="w", padx=16, pady=(12, 4))
        ctk.CTkLabel(panel, text=hint, font=("Arial", 11), text_color="#9ca7b5").pack(
            anchor="w", padx=16, pady=(0, 8)
        )
        for key, label, secret in fields:
            ctk.CTkLabel(panel, text=label).pack(anchor="w", padx=16)
            entry = ctk.CTkEntry(panel, show="*" if secret else "", height=36)
            entry.insert(0, self.cfg.get(key, ""))
            entry.pack(fill="x", padx=16, pady=(3, 10))
            self.fields[key] = entry

    def save_fields(self):
        for key, entry in self.fields.items():
            self.cfg[key] = entry.get().strip()
        save(STREAM_CONFIG, self.cfg)
        log("AUTH", "Ключи и настройки сохранены.")
        self.manager = StreamManager(self.cfg)
        self.refresh_status("✅ Настройки сохранены")

    def authorize_twitch(self):
        self.save_fields()
        self.refresh_status("⏳ Twitch: подготовка авторизации...")

        def status(message):
            self.after(0, lambda: self.refresh_status("⏳ Twitch: " + message))

        def job():
            result = self.manager.twitch.authorize(status)
            log("Twitch", result.message)
            self.after(0, lambda: self.refresh_status(("✅ " if result.ok else "❌ ") + result.message))

        threading.Thread(target=job, daemon=True).start()

    def reset_twitch(self):
        result = self.manager.twitch.reset_token()
        save(STREAM_CONFIG, self.cfg)
        log("Twitch", result.message)
        self.refresh_status(result.message)

    def authorize_youtube(self):
        self.save_fields()
        self._run_auth("YouTube", self.manager.youtube.authorize)

    def authorize_kick(self):
        self.save_fields()
        result = self.manager.kick.authorize(self)
        log("Kick", result.message)
        self.refresh_status(("✅ " if result.ok else "❌ ") + result.message)

    def reset_youtube(self):
        result = self.manager.youtube.reset_token()
        log("YouTube", result.message)
        self.refresh_status(result.message)

    def reset_kick(self):
        result = self.manager.kick.reset_token()
        log("Kick", result.message)
        self.refresh_status(result.message)

    def _run_auth(self, name, callback):
        self.refresh_status(f"⏳ {name}: ожидается авторизация в браузере...")

        def job():
            result = callback()
            log(name, result.message)
            self.after(0, lambda: self.refresh_status(("✅ " if result.ok else "❌ ") + result.message))

        threading.Thread(target=job, daemon=True).start()

    def refresh_status(self, extra=""):
        lines = [f"client_secret.json: {'✓' if CLIENT_SECRET.exists() else '—'}"]
        if self._enabled("twitch"):
            lines.append(f"Twitch: {'авторизован' if self.manager.twitch.is_authorized() else 'не авторизован'}")
        if self._enabled("youtube"):
            lines.append(f"YouTube: {'авторизован' if YOUTUBE_TOKEN.exists() else 'не авторизован'}")
        if self._enabled("vk"):
            lines.append(f"VK token: {'сохранён' if self.cfg.get('vk_token') else 'не заполнен'}")
        if self._enabled("kick"):
            lines.append(f"Kick: {'авторизован' if KICK_TOKEN.exists() else 'не авторизован'}")
        lines.append(f"Groq AI: {'настроен' if self.cfg.get('groq_key') else 'не настроен'}")

        if extra:
            lines.extend(["", extra])
        self.status_label.configure(text="\n".join(lines))
