from __future__ import annotations

from typing import Any

from ..core.event_log import log
from ..core.vlc_setup import prepare_vlc_dll_path


class PlayerEngine:
    """Небольшая обёртка над VLC для встроенного видеоплеера."""

    def __init__(self, hwnd: int, volume: int = 30):
        self.vlc: Any | None = None
        self.instance: Any | None = None
        self.player: Any | None = None
        self.last_error = ""

        try:
            prepare_vlc_dll_path()
            import vlc

            self.vlc = vlc
            self.instance = vlc.Instance(
                "--quiet",
                "--no-video-title-show",
                "--network-caching=5000",
            )
            self.player = self.instance.media_player_new()
            self.player.set_hwnd(hwnd)
            self.player.audio_set_volume(int(volume))
            log("PLAYER", "VLC-движок подключён к окну программы.")
        except Exception as exc:
            self.last_error = str(exc)
            self.vlc = None
            self.instance = None
            self.player = None
            log("PLAYER", f"VLC недоступен: {exc}")

    @property
    def available(self) -> bool:
        return self.player is not None and self.instance is not None and self.vlc is not None

    def play(self, url: str) -> bool:
        if not self.available or not url:
            return False
        try:
            media = self.instance.media_new(url)
            self.player.set_media(media)
            self.player.play()
            return True
        except Exception as exc:
            self.last_error = str(exc)
            log("PLAYER", f"Ошибка запуска видео: {exc}")
            return False

    def resume(self) -> None:
        if self.available:
            self.player.set_pause(0)

    def pause(self) -> None:
        if self.available:
            self.player.set_pause(1)

    def toggle_pause(self) -> bool:
        if not self.available:
            return False
        paused = bool(self.player.get_state() == self.vlc.State.Paused)
        self.player.set_pause(0 if paused else 1)
        return not paused

    def stop(self) -> None:
        if self.available:
            self.player.stop()

    def set_volume(self, value: float | int) -> None:
        if self.available:
            self.player.audio_set_volume(max(0, min(100, int(float(value)))))

    def set_position_percent(self, percent: float) -> None:
        if not self.available:
            return
        length = self.length_ms()
        if length > 0:
            target = int(length * max(0.0, min(100.0, float(percent))) / 100.0)
            self.player.set_time(target)

    def time_ms(self) -> int:
        if not self.available:
            return 0
        value = self.player.get_time()
        return max(0, int(value if value is not None else 0))

    def length_ms(self) -> int:
        if not self.available:
            return 0
        value = self.player.get_length()
        return max(0, int(value if value is not None else 0))

    def state(self) -> Any | None:
        return self.player.get_state() if self.available else None

    def is_finished(self) -> bool:
        if not self.available:
            return False
        return self.state() in {
            self.vlc.State.Ended,
            self.vlc.State.Error,
        }

    def release(self) -> None:
        try:
            if self.player is not None:
                self.player.stop()
                self.player.release()
        except Exception:
            pass
        try:
            if self.instance is not None:
                self.instance.release()
        except Exception:
            pass
        self.player = None
        self.instance = None
