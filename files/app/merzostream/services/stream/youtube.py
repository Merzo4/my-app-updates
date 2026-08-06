from __future__ import annotations

from ...core.paths import CLIENT_SECRET, YOUTUBE_TOKEN
from .common import ServiceResult

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


class YouTubeService:
    def is_authorized(self) -> bool:
        return YOUTUBE_TOKEN.exists()

    def reset_token(self) -> ServiceResult:
        try:
            if YOUTUBE_TOKEN.exists():
                YOUTUBE_TOKEN.unlink()
                return ServiceResult.success("Авторизация YouTube сброшена.")
            return ServiceResult.error("YouTube-токен ещё не создан.")
        except Exception as exc:
            return ServiceResult.error(f"Не удалось удалить токен: {exc}")

    def _credentials(self, force_browser: bool = False):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        credentials = None
        if YOUTUBE_TOKEN.exists() and not force_browser:
            credentials = Credentials.from_authorized_user_file(str(YOUTUBE_TOKEN), SCOPES)

        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token and not force_browser:
                credentials.refresh(Request())
            else:
                if not CLIENT_SECRET.exists():
                    raise FileNotFoundError("Не найден client_secret.json в папке AppData.")
                flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
                credentials = flow.run_local_server(port=0, open_browser=True)
            YOUTUBE_TOKEN.write_text(credentials.to_json(), encoding="utf-8")
        return credentials

    def authorize(self) -> ServiceResult:
        try:
            # Кнопка «Авторизовать» всегда запускает браузер, даже если старый токен уже есть.
            self._credentials(force_browser=True)
            return ServiceResult.success("Авторизация YouTube сохранена.")
        except Exception as exc:
            return ServiceResult.error(str(exc))

    def update(self, title: str, game: str) -> ServiceResult:
        try:
            from googleapiclient.discovery import build

            youtube = build("youtube", "v3", credentials=self._credentials())
            broadcasts = youtube.liveBroadcasts().list(
                part="id,snippet,status", mine=True
            ).execute().get("items", [])
            for broadcast in broadcasts:
                if broadcast["status"].get("lifeCycleStatus") in {"live", "ready", "testing"}:
                    snippet = broadcast["snippet"]
                    snippet["title"] = f"{game} | {title}" if game else title
                    snippet["categoryId"] = "20"
                    youtube.liveBroadcasts().update(
                        part="snippet",
                        body={"id": broadcast["id"], "snippet": snippet},
                    ).execute()
                    return ServiceResult.success("Активная трансляция обновлена.")
            return ServiceResult.error("Активная трансляция YouTube не найдена.")
        except Exception as exc:
            return ServiceResult.error(str(exc))
