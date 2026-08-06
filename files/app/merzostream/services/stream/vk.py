from __future__ import annotations

import requests

from .common import ServiceResult


class VKService:
    API = "https://apidev.live.vkvideo.ru/v1"

    def __init__(self, config: dict, game_mapping: dict[str, str]):
        self.config = config
        self.game_mapping = game_mapping

    def is_authorized(self) -> bool:
        return bool(self.config.get("vk_token", "").strip())

    def update(self, title: str, game: str) -> ServiceResult:
        token = self.config.get("vk_token", "").strip()
        if not token:
            return ServiceResult.error("Не заполнен VK Access Token.")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            current = requests.get(f"{self.API}/current_user", headers=headers, timeout=20)
            if current.status_code != 200:
                return ServiceResult.error(f"Проверка токена: HTTP {current.status_code}")
            channel_url = current.json().get("data", {}).get("channel", {}).get("url")
            if not channel_url:
                return ServiceResult.error("VK не вернул адрес канала.")

            query = self.game_mapping.get(game, game)
            categories = requests.get(
                f"{self.API}/category/search",
                headers=headers,
                params={"query": query, "type": "game", "limit": 1},
                timeout=20,
            )
            items = categories.json().get("data", {}).get("categories", []) if categories.ok else []
            category_id = str(items[0].get("id")) if items else "1"
            response = requests.post(
                f"{self.API}/channel/stream/edit",
                headers=headers,
                params={"channel_url": channel_url},
                json={"stream": {"title": title, "category": {"id": category_id}}},
                timeout=20,
            )
            if response.status_code in (200, 204):
                return ServiceResult.success("Название и категория обновлены.")
            return ServiceResult.error(f"HTTP {response.status_code}: {response.text[:180]}")
        except Exception as exc:
            return ServiceResult.error(str(exc))
