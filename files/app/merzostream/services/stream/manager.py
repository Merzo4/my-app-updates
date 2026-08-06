from __future__ import annotations

import json

from ...core.paths import CONTENT_DIR
from .groq import GroqService
from .kick import KickService
from .twitch import TwitchService
from .vk import VKService
from .youtube import YouTubeService


class StreamManager:
    def __init__(self, config: dict):
        self.config = config
        self.game_mapping = self._load_game_mapping()
        self.twitch = TwitchService(config)
        self.youtube = YouTubeService()
        self.vk = VKService(config, self.game_mapping)
        self.kick = KickService(config)
        self.groq = GroqService(config)

    @staticmethod
    def _load_game_mapping() -> dict[str, str]:
        try:
            return json.loads((CONTENT_DIR / "games.json").read_text(encoding="utf-8"))
        except Exception:
            return {}
