from __future__ import annotations

import json
import random
import shutil
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from ..core.event_log import log
from ..core.paths import APP_DATA, DATA_DIR

MUSIC_DIR = APP_DATA / "music" / "youtube_safe"
STATE_FILE = DATA_DIR / "background_music_state.json"
META_FILE = MUSIC_DIR / "attribution.json"
SUPPORTED = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}


@dataclass
class MusicTrack:
    filename: str
    title: str
    author: str = ""
    source: str = ""
    attribution_required: bool = False
    attribution_text: str = ""

    @property
    def path(self) -> Path:
        return MUSIC_DIR / self.filename


class BackgroundMusicController:
    """Состояние отдельного аудио-плеера для OBS Browser Source.

    Сам звук воспроизводится браузерным источником OBS по адресу /music.
    Благодаря этому музыка выводится отдельным источником и не смешивается
    с видеозаказами /player.
    """

    def __init__(self) -> None:
        MUSIC_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.tracks: list[MusicTrack] = []
        self.current_index = -1
        self.playing = False
        self.paused = False
        self.shuffle = False
        self.repeat = True
        self.volume = 35
        self.started_at = 0.0
        self.position = 0.0
        self.reload_library()
        self._load_state()

    def _metadata(self) -> dict[str, Any]:
        if not META_FILE.exists():
            return {}
        try:
            raw = json.loads(META_FILE.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except Exception:
            return {}

    def _save_metadata(self, data: dict[str, Any]) -> None:
        META_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def reload_library(self) -> None:
        with self._lock:
            metadata = self._metadata()
            files = sorted((p for p in MUSIC_DIR.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED), key=lambda p: p.name.lower())
            self.tracks = []
            for path in files:
                item = metadata.get(path.name, {}) if isinstance(metadata.get(path.name, {}), dict) else {}
                self.tracks.append(MusicTrack(
                    filename=path.name,
                    title=str(item.get("title") or path.stem),
                    author=str(item.get("author") or ""),
                    source=str(item.get("source") or ""),
                    attribution_required=bool(item.get("attribution_required", False)),
                    attribution_text=str(item.get("attribution_text") or ""),
                ))
            if self.current_index >= len(self.tracks):
                self.current_index = 0 if self.tracks else -1
            self._save_state()

    def add_files(self, paths: list[str]) -> int:
        count = 0
        for raw in paths:
            source = Path(raw)
            if not source.exists() or source.suffix.lower() not in SUPPORTED:
                continue
            target = MUSIC_DIR / source.name
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
            count += 1
        self.reload_library()
        return count

    def update_metadata(self, filename: str, **values: Any) -> None:
        metadata = self._metadata()
        item = metadata.setdefault(filename, {})
        item.update(values)
        self._save_metadata(metadata)
        self.reload_library()

    def current(self) -> MusicTrack | None:
        with self._lock:
            if 0 <= self.current_index < len(self.tracks):
                return self.tracks[self.current_index]
            return None

    def play(self, index: int | None = None) -> None:
        with self._lock:
            if not self.tracks:
                return
            if index is not None:
                self.current_index = max(0, min(int(index), len(self.tracks) - 1))
                self.position = 0.0
            elif self.current_index < 0:
                self.current_index = 0
            self.playing = True
            self.paused = False
            self.started_at = time.time() - self.position
            self._save_state()
            track = self.current()
            if track:
                log("BACKGROUND MUSIC", f"Запущено: {track.title}")

    def pause_toggle(self) -> None:
        with self._lock:
            if not self.playing:
                self.play()
                return
            if self.paused:
                self.paused = False
                self.started_at = time.time() - self.position
            else:
                self.position = self.current_position()
                self.paused = True
            self._save_state()

    def stop(self) -> None:
        with self._lock:
            self.playing = False
            self.paused = False
            self.position = 0.0
            self._save_state()

    def next(self) -> None:
        with self._lock:
            if not self.tracks:
                return
            if self.shuffle and len(self.tracks) > 1:
                choices = [i for i in range(len(self.tracks)) if i != self.current_index]
                self.current_index = random.choice(choices)
            elif self.current_index + 1 < len(self.tracks):
                self.current_index += 1
            elif self.repeat:
                self.current_index = 0
            else:
                self.stop()
                return
            self.position = 0.0
            self.playing = True
            self.paused = False
            self.started_at = time.time()
            self._save_state()

    def previous(self) -> None:
        with self._lock:
            if not self.tracks:
                return
            self.current_index = (self.current_index - 1) % len(self.tracks)
            self.position = 0.0
            self.playing = True
            self.paused = False
            self.started_at = time.time()
            self._save_state()

    def ended(self) -> None:
        self.next()

    def set_volume(self, value: int | float) -> None:
        with self._lock:
            self.volume = max(0, min(100, int(float(value))))
            self._save_state()

    def set_position(self, seconds: float) -> None:
        with self._lock:
            self.position = max(0.0, float(seconds))
            if self.playing and not self.paused:
                self.started_at = time.time() - self.position
            self._save_state()

    def current_position(self) -> float:
        if self.playing and not self.paused and self.started_at:
            return max(0.0, time.time() - self.started_at)
        return max(0.0, self.position)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            track = self.current()
            return {
                "playing": self.playing,
                "paused": self.paused,
                "shuffle": self.shuffle,
                "repeat": self.repeat,
                "volume": self.volume,
                "position": self.current_position(),
                "current_index": self.current_index,
                "current": asdict(track) if track else None,
                "tracks": [asdict(item) for item in self.tracks],
                "music_dir": str(MUSIC_DIR),
            }

    def attribution_text(self) -> str:
        lines: list[str] = []
        for track in self.tracks:
            if track.attribution_required:
                text = track.attribution_text.strip() or " — ".join(filter(None, [track.title, track.author, track.source]))
                if text:
                    lines.append(text)
        return "\n".join(lines)

    def _save_state(self) -> None:
        payload = {
            "current_index": self.current_index,
            "playing": self.playing,
            "paused": self.paused,
            "shuffle": self.shuffle,
            "repeat": self.repeat,
            "volume": self.volume,
            "position": self.current_position(),
        }
        STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_state(self) -> None:
        if not STATE_FILE.exists():
            return
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            self.current_index = int(data.get("current_index", self.current_index))
            self.playing = bool(data.get("playing", False))
            self.paused = bool(data.get("paused", False))
            self.shuffle = bool(data.get("shuffle", False))
            self.repeat = bool(data.get("repeat", True))
            self.volume = max(0, min(100, int(data.get("volume", 35))))
            self.position = max(0.0, float(data.get("position", 0.0)))
            if self.current_index >= len(self.tracks):
                self.current_index = 0 if self.tracks else -1
            if self.playing and not self.paused:
                self.started_at = time.time() - self.position
        except Exception as exc:
            log("BACKGROUND MUSIC", f"Не удалось восстановить состояние: {exc}")


background_music = BackgroundMusicController()
