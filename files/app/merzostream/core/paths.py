from pathlib import Path
import os
import sys

APP_NAME = "MerzoStreamSuite"
APP_DATA = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
SETTINGS_DIR = APP_DATA / "settings"
CREDENTIALS_DIR = APP_DATA / "credentials"
DATA_DIR = APP_DATA / "data"
LOGS_DIR = APP_DATA / "logs"
UPDATES_DIR = APP_DATA / "updates"
BACKUPS_DIR = APP_DATA / "backups"

for p in [APP_DATA, SETTINGS_DIR, CREDENTIALS_DIR, DATA_DIR, LOGS_DIR, UPDATES_DIR, BACKUPS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

APP_CONFIG = SETTINGS_DIR / "app.json"
STREAM_CONFIG = SETTINGS_DIR / "stream_control.json"
PLAYER_CONFIG = SETTINGS_DIR / "media_player.json"
YOUTUBE_TOKEN = CREDENTIALS_DIR / "youtube_token.json"
KICK_TOKEN = CREDENTIALS_DIR / "kick_token.json"
TWITCH_TOKEN = CREDENTIALS_DIR / "twitch_token.json"
VK_TOKEN = CREDENTIALS_DIR / "vk_token.json"
CLIENT_SECRET = CREDENTIALS_DIR / "client_secret.json"
NOW_PLAYING = DATA_DIR / "now_playing.txt"
PLAYER_STATE = DATA_DIR / "player_state.json"
FIRST_RUN_FLAG = APP_DATA / ".first_run_complete"


def bundle_root() -> Path:
    """Постоянная папка приложения, пригодная для частичных обновлений."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


CONTENT_DIR = bundle_root() / "content"
GRAPHICS_DIR = bundle_root() / "graphics"
RESOURCES_DIR = bundle_root() / "resources"
