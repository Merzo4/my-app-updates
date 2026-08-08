from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
import urllib.parse
import uuid
import webbrowser

import requests
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core.config import save
from ...core.event_log import log
from ...core.paths import CLIENT_SECRET, KICK_TOKEN, STREAM_CONFIG, YOUTUBE_TOKEN
from ...core.settings_manager import settings
from ...services.stream import StreamManager


class _AuthSignals(QObject):
    status = Signal(str)
    auth_done = Signal(str, bool, str)


class AuthorizationPage(QWidget):
    VK_AUTH_URL = (
        "https://auth.live.vkvideo.ru/app/oauth2/authorize?client_id=lmn3one57wbvnwyo"
        "&response_type=token&scope=channel:stream:settings&redirect_uri=http://localhost"
    )

    def __init__(self, theme: dict):
        super().__init__()
        self.setObjectName("realPage")
        self.theme = theme
        self.cfg = settings.load("stream", force=True)
        self.manager = StreamManager(self.cfg)
        self.fields: dict[str, QLineEdit] = {}
        self.platform_frames: dict[str, QWidget] = {}
        self.signals = _AuthSignals(self)
        self.signals.status.connect(self._set_extra_status)
        self.signals.auth_done.connect(self._auth_finished)
        self._extra_status = ""
        self._build()
        self.reload_from_settings()

    @staticmethod
    def _card() -> QFrame:
        frame = QFrame()
        frame.setObjectName("sectionCard")
        return frame

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content.setObjectName("scrollContent")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(28, 22, 28, 26)
        self.content_layout.setSpacing(14)

        heading = QLabel("Авторизация и API")
        heading.setObjectName("pageTitle")
        subtitle = QLabel("Показываются только платформы, выбранные в разделе «Управление трансляцией».")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("pageSubtitle")
        self.content_layout.addWidget(heading)
        self.content_layout.addWidget(subtitle)

        # VK credentials
        self.vk_card = self._credential_card(
            "VK Video",
            [("vk_token", "Access Token", True)],
            "Получить токен можно кнопкой ниже, затем вставить его сюда и сохранить.",
        )
        self.platform_frames["vk"] = self.vk_card
        self.content_layout.addWidget(self.vk_card)

        # Kick credentials
        self.kick_card = self._credential_card(
            "Kick",
            [("kick_client_id", "Client ID", False), ("kick_client_secret", "Client Secret", True)],
            "Нужны только если Kick выбран как активная платформа.",
        )
        self.platform_frames["kick"] = self.kick_card
        self.content_layout.addWidget(self.kick_card)

        # Groq is independent from platform selection.
        groq = self._credential_card(
            "Groq AI",
            [("groq_key", "Groq API Key", True)],
            "Ключ используется AI Producer. Можно оставить пустым, если AI сейчас не нужен.",
        )
        self.content_layout.addWidget(groq)

        save_button = QPushButton("СОХРАНИТЬ НАСТРОЙКИ")
        save_button.setObjectName("primaryButton")
        save_button.setMinimumHeight(44)
        save_button.clicked.connect(self.save_fields)
        self.content_layout.addWidget(save_button)

        actions = self._card()
        actions_l = QVBoxLayout(actions)
        actions_l.setContentsMargins(18, 16, 18, 16)
        actions_l.setSpacing(10)
        actions_title = QLabel("Браузерная авторизация")
        actions_title.setObjectName("cardTitle")
        actions_l.addWidget(actions_title)

        self.twitch_row = self._auth_row("Twitch", self.authorize_twitch, self.reset_twitch)
        self.youtube_row = self._auth_row("YouTube", self.authorize_youtube, self.reset_youtube)
        self.kick_row = self._auth_row("Kick", self.authorize_kick, self.reset_kick)
        self.vk_row = self._vk_row()
        self.platform_frames["twitch"] = self.twitch_row
        self.platform_frames["youtube"] = self.youtube_row
        # Kick and VK have both credentials + action rows.
        self.kick_action_row = self.kick_row
        self.vk_action_row = self.vk_row
        for row in (self.twitch_row, self.youtube_row, self.kick_row, self.vk_row):
            actions_l.addWidget(row)
        self.content_layout.addWidget(actions)

        self.status_card = self._card()
        status_l = QVBoxLayout(self.status_card)
        status_l.setContentsMargins(18, 15, 18, 15)
        status_title = QLabel("Статус")
        status_title.setObjectName("cardTitle")
        self.status_label = QLabel("")
        self.status_label.setObjectName("authStatus")
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(self.status_label.textInteractionFlags())
        status_l.addWidget(status_title)
        status_l.addWidget(self.status_label)
        self.content_layout.addWidget(self.status_card)
        self.content_layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll)

    def _credential_card(self, title: str, fields: list[tuple[str, str, bool]], hint: str) -> QFrame:
        card = self._card()
        layout = QGridLayout(card)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(8)
        name = QLabel(title)
        name.setObjectName("cardTitle")
        desc = QLabel(hint)
        desc.setObjectName("cardText")
        desc.setWordWrap(True)
        layout.addWidget(name, 0, 0, 1, 2)
        layout.addWidget(desc, 1, 0, 1, 2)
        row = 2
        for key, label, secret in fields:
            field_label = QLabel(label)
            field_label.setObjectName("fieldLabel")
            entry = QLineEdit()
            if secret:
                entry.setEchoMode(QLineEdit.Password)
            self.fields[key] = entry
            layout.addWidget(field_label, row, 0)
            layout.addWidget(entry, row, 1)
            row += 1
        layout.setColumnStretch(1, 1)
        return card

    def _auth_row(self, title: str, auth_callback, reset_callback) -> QWidget:
        row = QFrame()
        row.setObjectName("authRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 7, 10, 7)
        label = QLabel(title)
        label.setObjectName("fieldLabel")
        label.setMinimumWidth(110)
        auth = QPushButton("Авторизовать")
        auth.setObjectName("primarySmallButton")
        auth.clicked.connect(auth_callback)
        reset = QPushButton("Сбросить")
        reset.setObjectName("dangerButton")
        reset.clicked.connect(reset_callback)
        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(auth)
        layout.addWidget(reset)
        return row

    def _vk_row(self) -> QWidget:
        row = QFrame()
        row.setObjectName("authRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 7, 10, 7)
        label = QLabel("VK Video")
        label.setObjectName("fieldLabel")
        button = QPushButton("Получить токен")
        button.setObjectName("primarySmallButton")
        button.clicked.connect(lambda: webbrowser.open(self.VK_AUTH_URL))
        layout.addWidget(label)
        layout.addStretch(1)
        layout.addWidget(button)
        return row

    def _enabled(self, key: str) -> bool:
        return bool(self.cfg.get("platforms", {}).get(key, False))

    def reload_from_settings(self) -> None:
        self.cfg = settings.load("stream", force=True)
        self.manager = StreamManager(self.cfg)
        for key, entry in self.fields.items():
            entry.setText(str(self.cfg.get(key, "")))

        self.vk_card.setVisible(self._enabled("vk"))
        self.kick_card.setVisible(self._enabled("kick"))
        self.twitch_row.setVisible(self._enabled("twitch"))
        self.youtube_row.setVisible(self._enabled("youtube"))
        self.kick_row.setVisible(self._enabled("kick"))
        self.vk_row.setVisible(self._enabled("vk"))
        self.refresh_status()

    def save_fields(self) -> None:
        self.cfg = settings.load("stream", force=True)
        for key, entry in self.fields.items():
            self.cfg[key] = entry.text().strip()
        save(STREAM_CONFIG, self.cfg)
        self.manager = StreamManager(self.cfg)
        log("AUTH", "Ключи и настройки сохранены.")
        self._extra_status = "✅ Настройки сохранены"
        self.refresh_status()

    def refresh_status(self) -> None:
        lines = [f"client_secret.json: {'✓ найден' if CLIENT_SECRET.exists() else '— не найден'}"]
        if self._enabled("twitch"):
            lines.append(f"Twitch: {'авторизован' if self.manager.twitch.is_authorized() else 'не авторизован'}")
        if self._enabled("youtube"):
            lines.append(f"YouTube: {'авторизован' if YOUTUBE_TOKEN.exists() else 'не авторизован'}")
        if self._enabled("vk"):
            lines.append(f"VK token: {'сохранён' if self.cfg.get('vk_token') else 'не заполнен'}")
        if self._enabled("kick"):
            lines.append(f"Kick: {'авторизован' if KICK_TOKEN.exists() else 'не авторизован'}")
        lines.append(f"Groq AI: {'настроен' if self.cfg.get('groq_key') else 'не настроен'}")
        if self._extra_status:
            lines.extend(["", self._extra_status])
        self.status_label.setText("\n".join(lines))

    def _set_extra_status(self, message: str) -> None:
        self._extra_status = message
        self.refresh_status()

    def _auth_finished(self, name: str, ok: bool, message: str) -> None:
        mark = "✅" if ok else "❌"
        self._extra_status = f"{mark} {name}: {message}"
        self.cfg = settings.load("stream", force=True)
        self.manager = StreamManager(self.cfg)
        self.refresh_status()

    def authorize_twitch(self) -> None:
        self.save_fields()
        manager = self.manager
        self.signals.status.emit("⏳ Twitch: подготовка авторизации...")

        def status(message: str) -> None:
            self.signals.status.emit("⏳ Twitch: " + message)

        def job() -> None:
            result = manager.twitch.authorize(status)
            log("Twitch", result.message)
            self.signals.auth_done.emit("Twitch", result.ok, result.message)

        threading.Thread(target=job, daemon=True).start()

    def authorize_youtube(self) -> None:
        self.save_fields()
        manager = self.manager
        self.signals.status.emit("⏳ YouTube: ожидается авторизация в браузере...")

        def job() -> None:
            result = manager.youtube.authorize()
            log("YouTube", result.message)
            self.signals.auth_done.emit("YouTube", result.ok, result.message)

        threading.Thread(target=job, daemon=True).start()

    def authorize_kick(self) -> None:
        self.save_fields()
        client_id = self.cfg.get("kick_client_id", "").strip()
        secret = self.cfg.get("kick_client_secret", "").strip()
        if not client_id or not secret:
            self._set_extra_status("❌ Kick: сначала заполни Client ID и Client Secret.")
            return

        verifier = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest()).decode("utf-8").rstrip("=")
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": "http://localhost",
            "scope": "channel:write user:read",
            "state": str(uuid.uuid4()),
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        webbrowser.open("https://id.kick.com/oauth/authorize?" + urllib.parse.urlencode(params))
        redirected_url, ok = QInputDialog.getText(
            self,
            "Авторизация Kick",
            "После перехода на localhost скопируй ПОЛНУЮ ссылку из адресной строки и вставь сюда:",
        )
        if not ok or not redirected_url or "code=" not in redirected_url:
            self._set_extra_status("❌ Kick: авторизация отменена или ссылка не содержит code.")
            return
        code = urllib.parse.parse_qs(urllib.parse.urlparse(redirected_url).query).get("code", [None])[0]
        if not code:
            self._set_extra_status("❌ Kick: не удалось прочитать код авторизации.")
            return

        self.signals.status.emit("⏳ Kick: получение токена...")

        def job() -> None:
            try:
                response = requests.post(
                    "https://id.kick.com/oauth/token",
                    data={
                        "grant_type": "authorization_code",
                        "client_id": client_id,
                        "client_secret": secret,
                        "code": code,
                        "redirect_uri": "http://localhost",
                        "code_verifier": verifier,
                    },
                    timeout=25,
                )
                if response.status_code == 200:
                    KICK_TOKEN.parent.mkdir(parents=True, exist_ok=True)
                    KICK_TOKEN.write_text(json.dumps(response.json(), ensure_ascii=False, indent=2), encoding="utf-8")
                    self.signals.auth_done.emit("Kick", True, "Авторизация Kick сохранена.")
                else:
                    self.signals.auth_done.emit("Kick", False, f"HTTP {response.status_code}: {response.text[:220]}")
            except Exception as exc:
                self.signals.auth_done.emit("Kick", False, str(exc))

        threading.Thread(target=job, daemon=True).start()

    def reset_twitch(self) -> None:
        result = self.manager.twitch.reset_token()
        save(STREAM_CONFIG, self.cfg)
        log("Twitch", result.message)
        self._auth_finished("Twitch", result.ok, result.message)

    def reset_youtube(self) -> None:
        result = self.manager.youtube.reset_token()
        log("YouTube", result.message)
        self._auth_finished("YouTube", result.ok, result.message)

    def reset_kick(self) -> None:
        result = self.manager.kick.reset_token()
        log("Kick", result.message)
        self._auth_finished("Kick", result.ok, result.message)
