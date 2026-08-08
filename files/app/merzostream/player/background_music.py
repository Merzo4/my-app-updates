from __future__ import annotations

import json
import random
import re
import shutil
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from ..core.event_log import log
from ..core.paths import APP_DATA, DATA_DIR

MUSIC_DIR = APP_DATA / "music" / "youtube_safe"
STATE_FILE = DATA_DIR / "background_music_state.json"
META_FILE = MUSIC_DIR / "attribution.json"
SUPPORTED = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".webm", ".opus"}


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
    """Отдельная библиотека фоновой музыки для OBS Browser Source /music.

    Треки хранятся локально в AppData. Добавление по URL сначала пытается
    скачать аудио через yt-dlp. Это специально сделано как импорт в локальную
    библиотеку: после импорта музыка не зависит от открытой страницы сайта.
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
        MUSIC_DIR.mkdir(parents=True, exist_ok=True)
        META_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def reload_library(self) -> None:
        with self._lock:
            MUSIC_DIR.mkdir(parents=True, exist_ok=True)
            metadata = self._metadata()
            files = sorted(
                (p for p in MUSIC_DIR.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED),
                key=lambda p: p.name.lower(),
            )
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

    @staticmethod
    def _safe_name(value: str, fallback: str = "music") -> str:
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", str(value or "")).strip(" ._")
        name = re.sub(r"\s+", " ", name)
        return (name[:150] or fallback).strip()

    def add_files(self, paths: list[str]) -> int:
        count = 0
        for raw in paths:
            source = Path(raw)
            if not source.exists() or source.suffix.lower() not in SUPPORTED:
                continue
            target = MUSIC_DIR / source.name
            if source.resolve() != target.resolve():
                # Do not silently overwrite another track with the same file name.
                if target.exists():
                    stem, suffix = target.stem, target.suffix
                    n = 2
                    while (MUSIC_DIR / f"{stem} ({n}){suffix}").exists():
                        n += 1
                    target = MUSIC_DIR / f"{stem} ({n}){suffix}"
                shutil.copy2(source, target)
            count += 1
        self.reload_library()
        return count

    def import_url(self, url: str, progress: Callable[[str], None] | None = None) -> tuple[bool, str, str]:
        """Download one audio track from URL into the local library.

        yt-dlp is deliberately used without cookies and without playlist mode.
        Some royalty-free sites intentionally block automated downloads. In that
        case the UI tells the user to use the site's official Download button and
        then add the downloaded file manually.
        """
        value = str(url or "").strip()
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False, "Нужна обычная ссылка http:// или https://", ""

        try:
            import yt_dlp
        except Exception:
            return False, "yt-dlp не установлен. Обнови yt-dlp в настройках или добавь скачанный файл вручную.", ""

        MUSIC_DIR.mkdir(parents=True, exist_ok=True)
        if progress:
            progress("Получаю информацию о треке…")

        before = {p.resolve() for p in MUSIC_DIR.iterdir() if p.is_file()}
        title_hint = self._safe_name(Path(parsed.path).stem or parsed.netloc, "music")
        outtmpl = str(MUSIC_DIR / "%(title).150s [%(id)s].%(ext)s")

        def hook(data: dict[str, Any]):
            if not progress:
                return
            status = str(data.get("status", ""))
            if status == "downloading":
                pct = str(data.get("_percent_str", "")).strip()
                speed = str(data.get("_speed_str", "")).strip()
                progress("Скачивание" + (f" • {pct}" if pct else "") + (f" • {speed}" if speed else ""))
            elif status == "finished":
                progress("Файл скачан. Добавляю в библиотеку…")

        opts = {
            "format": "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio[ext=ogg]/bestaudio[ext=webm]/bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "restrictfilenames": False,
            "overwrites": False,
            "windowsfilenames": True,
            "progress_hooks": [hook],
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(value, download=True)
                if isinstance(info, dict) and info.get("entries"):
                    entries = [x for x in info.get("entries", []) if isinstance(x, dict)]
                    info = entries[0] if entries else info
                info = info if isinstance(info, dict) else {}

                candidates: list[Path] = []
                for data in info.get("requested_downloads", []) or []:
                    if isinstance(data, dict) and data.get("filepath"):
                        candidates.append(Path(str(data["filepath"])))
                if info.get("filepath"):
                    candidates.append(Path(str(info["filepath"])))
                try:
                    candidates.append(Path(ydl.prepare_filename(info)))
                except Exception:
                    pass

            after = [p for p in MUSIC_DIR.iterdir() if p.is_file() and p.resolve() not in before]
            for p in after:
                candidates.append(p)
            file_path = next((p for p in candidates if p.exists() and p.is_file()), None)
            if file_path is None:
                # yt-dlp may decide an existing file already satisfies the request.
                recent = sorted(
                    (p for p in MUSIC_DIR.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                file_path = recent[0] if recent else None
            if file_path is None:
                return False, "Сайт не отдал аудиофайл. Используй его кнопку Download и добавь файл вручную.", ""

            if file_path.suffix.lower() not in SUPPORTED:
                return False, f"Файл скачан в неподдерживаемом формате {file_path.suffix}. Добавь MP3/M4A/OGG/WAV/FLAC/WebM/Opus.", str(file_path)

            title = str(info.get("title") or file_path.stem or title_hint)
            author = str(info.get("artist") or info.get("uploader") or info.get("creator") or "")
            source = str(info.get("webpage_url") or value)
            self.update_metadata(
                file_path.name,
                title=title,
                author=author,
                source=source,
                attribution_required=False,
                attribution_text="",
            )
            self.reload_library()
            log("BACKGROUND MUSIC", f"Добавлен по URL: {title} • {source}")
            return True, f"Добавлено: {title}", file_path.name
        except Exception as exc:
            text = str(exc).strip().splitlines()[-1] if str(exc).strip() else exc.__class__.__name__
            log("BACKGROUND MUSIC", f"URL import error: {text}")
            return False, "Не удалось скачать автоматически. Открой сайт, нажми официальный Download и добавь полученный файл вручную.\n" + text[:500], ""

    def delete_track(self, index: int) -> tuple[bool, str]:
        with self._lock:
            if not (0 <= int(index) < len(self.tracks)):
                return False, "Трек не выбран"
            track = self.tracks[int(index)]
            try:
                if self.current_index == int(index):
                    self.stop()
                path = track.path
                if path.exists():
                    path.unlink()
                metadata = self._metadata()
                metadata.pop(track.filename, None)
                self._save_metadata(metadata)
                self.reload_library()
                return True, f"Удалено: {track.title}"
            except Exception as exc:
                return False, str(exc)

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
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
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
