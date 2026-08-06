from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.parse
import uuid
import webbrowser

import customtkinter as ctk
import requests

from ...core.paths import KICK_TOKEN
from .common import ServiceResult


class KickService:
    def __init__(self, config: dict):
        self.config = config

    def is_authorized(self) -> bool:
        return KICK_TOKEN.exists()

    def authorize(self, parent=None) -> ServiceResult:
        client_id = self.config.get("kick_client_id", "").strip()
        secret = self.config.get("kick_client_secret", "").strip()
        if not client_id or not secret:
            return ServiceResult.error("Сначала заполни Kick Client ID и Client Secret.")

        verifier = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("utf-8")).digest()
        ).decode("utf-8").rstrip("=")
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
        redirected_url = ctk.CTkInputDialog(
            title="Авторизация Kick",
            text=(
                "Войди в Kick в открывшемся браузере.\n"
                "После перехода на localhost скопируй ПОЛНУЮ ссылку\n"
                "из адресной строки и вставь сюда:"
            ),
        ).get_input()
        if not redirected_url or "code=" not in redirected_url:
            return ServiceResult.error("Авторизация отменена или ссылка не содержит code.")
        code = urllib.parse.parse_qs(urllib.parse.urlparse(redirected_url).query).get("code", [None])[0]
        if not code:
            return ServiceResult.error("Не удалось прочитать код авторизации.")
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
                KICK_TOKEN.write_text(json.dumps(response.json(), ensure_ascii=False, indent=2), encoding="utf-8")
                return ServiceResult.success("Авторизация Kick сохранена.")
            return ServiceResult.error(f"HTTP {response.status_code}: {response.text[:220]}")
        except Exception as exc:
            return ServiceResult.error(str(exc))

    def reset_token(self) -> ServiceResult:
        try:
            if KICK_TOKEN.exists():
                KICK_TOKEN.unlink()
                return ServiceResult.success("Авторизация Kick сброшена.")
            return ServiceResult.error("Kick-токен ещё не создан.")
        except Exception as exc:
            return ServiceResult.error(str(exc))

    def update(self, title: str, game: str) -> ServiceResult:
        if not KICK_TOKEN.exists():
            return ServiceResult.error("Сначала авторизуй Kick.")
        try:
            tokens = json.loads(KICK_TOKEN.read_text(encoding="utf-8"))
            access_token = tokens.get("access_token")
            if not access_token:
                return ServiceResult.error("В kick_token.json отсутствует access_token.")
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
            categories = requests.get(
                "https://api.kick.com/public/v1/categories",
                headers=headers,
                params={"q": game},
                timeout=20,
            )
            if categories.status_code == 401:
                return ServiceResult.error("Токен Kick устарел. Выполни авторизацию заново.")
            items = categories.json().get("data", []) if categories.ok else []
            if not items:
                return ServiceResult.error(f"Категория «{game}» не найдена.")
            category_response = requests.patch(
                "https://api.kick.com/public/v1/channels",
                headers=headers,
                json={"category_id": int(items[0]["id"])},
                timeout=20,
            )
            title_response = requests.patch(
                "https://api.kick.com/public/v1/channels",
                headers=headers,
                json={"title": title},
                timeout=20,
            )
            if category_response.status_code in (200, 204) and title_response.status_code in (200, 204):
                return ServiceResult.success("Название и категория обновлены.")
            return ServiceResult.error(
                f"HTTP category={category_response.status_code}, title={title_response.status_code}"
            )
        except Exception as exc:
            return ServiceResult.error(str(exc))
