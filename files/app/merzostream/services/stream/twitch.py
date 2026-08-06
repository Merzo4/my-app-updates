from __future__ import annotations

import json
import time
import webbrowser

import requests

from ...core.event_log import log
from ...core.paths import TWITCH_TOKEN
from .common import ServiceResult


class TwitchService:
    API = "https://api.twitch.tv/helix"
    AUTH = "https://id.twitch.tv/oauth2"
    REQUIRED_SCOPE = "channel:manage:broadcast"

    def __init__(self, config: dict):
        self.config = config

    def _load_tokens(self) -> dict:
        if not TWITCH_TOKEN.exists():
            return {}
        try:
            return json.loads(TWITCH_TOKEN.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_tokens(self, data: dict) -> None:
        data = dict(data)
        data["saved_at"] = int(time.time())
        TWITCH_TOKEN.parent.mkdir(parents=True, exist_ok=True)
        TWITCH_TOKEN.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _access_token(self) -> str:
        tokens = self._load_tokens()
        token = str(tokens.get("access_token", "")).strip()
        if token:
            return token
        # Migration from the old config, so existing users do not lose access immediately.
        return str(self.config.get("twitch_oauth_token", "")).removeprefix("oauth:").strip()

    def _headers(self) -> dict[str, str] | None:
        client_id = self.config.get("twitch_client_id", "").strip()
        token = self._access_token()
        if not client_id or not token:
            return None
        return {"Client-Id": client_id, "Authorization": f"Bearer {token}"}

    def authorize(self, status_callback=None) -> ServiceResult:
        """Twitch device-code OAuth: opens browser and receives token automatically."""
        client_id = self.config.get("twitch_client_id", "").strip()
        if not client_id:
            return ServiceResult.error("Сначала укажи Twitch Client ID и сохрани настройки.")
        try:
            response = requests.post(
                f"{self.AUTH}/device",
                data={"client_id": client_id, "scopes": self.REQUIRED_SCOPE},
                timeout=20,
            )
            if response.status_code != 200:
                return ServiceResult.error(f"Twitch OAuth HTTP {response.status_code}: {response.text[:200]}")
            device = response.json()
            verification_uri = device.get("verification_uri")
            user_code = device.get("user_code", "")
            device_code = device.get("device_code")
            interval = max(int(device.get("interval", 5)), 2)
            expires_at = time.time() + int(device.get("expires_in", 1800))
            if not verification_uri or not device_code:
                return ServiceResult.error("Twitch не вернул данные авторизации.")

            if status_callback:
                status_callback(f"Открылся Twitch. Подтверди код: {user_code}")
            webbrowser.open(verification_uri)

            while time.time() < expires_at:
                time.sleep(interval)
                token_response = requests.post(
                    f"{self.AUTH}/token",
                    data={
                        "client_id": client_id,
                        "scope": self.REQUIRED_SCOPE,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                    timeout=20,
                )
                if token_response.status_code == 200:
                    self._save_tokens(token_response.json())
                    self.config["twitch_oauth_token"] = ""
                    return ServiceResult.success("Twitch успешно авторизован через браузер.")

                payload = {}
                try:
                    payload = token_response.json()
                except Exception:
                    pass
                error = payload.get("message") or payload.get("error") or ""
                normalized = str(error).lower().replace("_", " ")
                if "authorization pending" in normalized or token_response.status_code in (400, 428):
                    continue
                if "slow down" in normalized:
                    interval += 2
                    continue
                if "access denied" in normalized:
                    return ServiceResult.error("Авторизация Twitch отменена.")
                if "expired" in normalized:
                    return ServiceResult.error("Код Twitch истёк. Запусти авторизацию ещё раз.")
            return ServiceResult.error("Время ожидания Twitch-авторизации истекло.")
        except Exception as exc:
            log("Twitch", f"OAuth exception: {exc}")
            return ServiceResult.error(f"Ошибка Twitch OAuth: {exc}")

    def reset_token(self) -> ServiceResult:
        try:
            if TWITCH_TOKEN.exists():
                TWITCH_TOKEN.unlink()
            self.config["twitch_oauth_token"] = ""
            return ServiceResult.success("Авторизация Twitch сброшена.")
        except Exception as exc:
            return ServiceResult.error(f"Не удалось удалить Twitch-токен: {exc}")

    def is_authorized(self) -> bool:
        return bool(self.config.get("twitch_client_id", "").strip() and self._access_token())

    def search_categories(self, query: str) -> tuple[list[str], ServiceResult]:
        headers = self._headers()
        if not headers:
            return [], ServiceResult.error("Twitch не авторизован. Открой раздел «Авторизация».")
        try:
            response = requests.get(
                f"{self.API}/search/categories",
                headers=headers,
                params={"query": query, "first": 100},
                timeout=20,
            )
            if response.status_code != 200:
                return [], ServiceResult.error(f"Twitch API {response.status_code}: {response.text[:180]}")
            names = [item["name"] for item in response.json().get("data", []) if item.get("name")]
            if not names:
                return [], ServiceResult.error("Категории не найдены.")
            return names, ServiceResult.success(f"Найдено категорий: {len(names)}")
        except Exception as exc:
            return [], ServiceResult.error(f"Ошибка поиска: {exc}")

    def update(self, title: str, game: str) -> ServiceResult:
        headers = self._headers()
        if not headers:
            return ServiceResult.error("Twitch не авторизован. Открой раздел «Авторизация».")
        try:
            categories = requests.get(
                f"{self.API}/search/categories",
                headers=headers,
                params={"query": game, "first": 100},
                timeout=20,
            )
            if categories.status_code != 200:
                return ServiceResult.error(f"Поиск категории: HTTP {categories.status_code}")
            data = categories.json().get("data", [])
            game_id = next(
                (item["id"] for item in data if item.get("name", "").casefold() == game.casefold()),
                data[0].get("id") if data else None,
            )
            if not game_id:
                return ServiceResult.error(f"Категория «{game}» не найдена.")

            users = requests.get(f"{self.API}/users", headers=headers, timeout=20)
            if users.status_code != 200:
                return ServiceResult.error(f"Получение пользователя: HTTP {users.status_code}")
            user_data = users.json().get("data", [])
            if not user_data:
                return ServiceResult.error("Twitch не вернул данные пользователя. Повтори авторизацию.")

            response = requests.patch(
                f"{self.API}/channels",
                headers=headers,
                params={"broadcaster_id": user_data[0]["id"]},
                json={"title": title, "game_id": game_id},
                timeout=20,
            )
            if response.status_code in (200, 204):
                return ServiceResult.success("Название и категория обновлены.")
            return ServiceResult.error(f"HTTP {response.status_code}: {response.text[:180]}")
        except Exception as exc:
            log("Twitch", f"Исключение: {exc}")
            return ServiceResult.error(str(exc))
