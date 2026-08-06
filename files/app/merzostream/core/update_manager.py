from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

import requests

from .paths import BACKUPS_DIR, UPDATES_DIR, bundle_root


@dataclass
class UpdateFile:
    path: str
    url: str
    sha256: str
    size: int = 0
    restart_required: bool = True


@dataclass
class UpdateCheck:
    available: bool
    current_version: str
    remote_version: str
    release_notes: list[str] = field(default_factory=list)
    files: list[UpdateFile] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)
    message: str = ""


class UpdateError(RuntimeError):
    pass


class UpdateManager:
    """Частичные обновления из публичного GitHub-репозитория."""

    CONFIG_NAME = "update_config.json"
    PENDING_CHANGELOG = UPDATES_DIR / "pending_changelog.json"
    HISTORY_FILE = UPDATES_DIR / "history.json"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "MerzoStreamSuite-Updater/0.0.1"})

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def is_safe_relative_path(value: str) -> bool:
        path = Path(value.replace("\\", "/"))
        return bool(value) and not path.is_absolute() and ".." not in path.parts

    @staticmethod
    def _version_tuple(value: str) -> tuple[int, ...]:
        clean = str(value).strip().lower().replace("beta", "").replace("v", "")
        parts = []
        for token in clean.split("."):
            digits = "".join(ch for ch in token if ch.isdigit())
            parts.append(int(digits or 0))
        return tuple(parts or [0])

    def load_config(self) -> dict:
        path = bundle_root() / "resources" / self.CONFIG_NAME
        default = {
            "enabled": True,
            "manifest_url": "https://raw.githubusercontent.com/Merzo4/my-app-updates/main/manifest.json",
            "repository": "Merzo4/my-app-updates",
            "channel": "beta",
            "check_on_start": True,
            "timeout_seconds": 12,
        }
        if not path.exists():
            return default
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                default.update(loaded)
        except Exception:
            pass
        return default

    def _target_path(self, logical_path: str) -> Path:
        logical = logical_path.replace("\\", "/").lstrip("/")
        if not self.is_safe_relative_path(logical):
            raise UpdateError(f"Небезопасный путь в манифесте: {logical_path}")

        root = bundle_root()
        if logical.startswith("app/merzostream/"):
            tail = logical[len("app/merzostream/"):]
            if getattr(sys, "frozen", False):
                target = root / "app" / "merzostream" / tail
            else:
                target = root / "src" / "merzostream" / tail
        elif logical.startswith("content/") or logical.startswith("graphics/"):
            target = root / logical
        else:
            raise UpdateError(f"Обновление этого пути запрещено: {logical}")

        resolved_root = root.resolve()
        resolved_target = target.resolve(strict=False)
        try:
            resolved_target.relative_to(resolved_root)
        except ValueError as exc:
            raise UpdateError(f"Путь выходит за пределы приложения: {logical}") from exc
        return target

    def fetch_manifest(self) -> dict:
        config = self.load_config()
        if not config.get("enabled", True):
            raise UpdateError("Проверка обновлений отключена в update_config.json")
        url = str(config.get("manifest_url", "")).strip()
        if not url:
            raise UpdateError("Не указан manifest_url")
        timeout = max(3, int(config.get("timeout_seconds", 12)))
        response = self._session.get(url, timeout=timeout, headers={"Cache-Control": "no-cache"})
        response.raise_for_status()
        manifest = response.json()
        if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
            raise UpdateError("GitHub вернул некорректный manifest.json")
        return manifest

    def check(self, current_version: str) -> UpdateCheck:
        manifest = self.fetch_manifest()
        remote_version = str(manifest.get("version", "0.0.0"))
        config = self.load_config()
        expected_channel = str(config.get("channel", "beta")).lower()
        remote_channel = str(manifest.get("channel", "beta")).lower()
        if remote_channel != expected_channel:
            return UpdateCheck(False, current_version, remote_version, message="Обновление относится к другому каналу")

        changed: list[UpdateFile] = []
        for item in manifest.get("files", []):
            try:
                logical = str(item["path"])
                target = self._target_path(logical)
                expected_hash = str(item["sha256"]).lower()
                if target.exists() and self.sha256(target).lower() == expected_hash:
                    continue
                changed.append(UpdateFile(
                    path=logical,
                    url=str(item["url"]),
                    sha256=expected_hash,
                    size=int(item.get("size", 0) or 0),
                    restart_required=bool(item.get("restart_required", True)),
                ))
            except KeyError as exc:
                raise UpdateError(f"В manifest.json отсутствует поле: {exc}") from exc

        newer_version = self._version_tuple(remote_version) > self._version_tuple(current_version)
        available = bool(changed) or newer_version
        notes = [str(x) for x in manifest.get("release_notes", []) if str(x).strip()]
        message = "Доступно обновление" if available else "Установлена актуальная версия"
        return UpdateCheck(available, current_version, remote_version, notes, changed, manifest, message)

    def apply(self, check: UpdateCheck, progress: Callable[[int, int, str], None] | None = None) -> list[str]:
        if not check.files:
            self._save_changelog(check, [])
            return []

        with self._lock:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_root = BACKUPS_DIR / f"update_{timestamp}"
            temp_root = Path(tempfile.mkdtemp(prefix="merzostream_update_", dir=str(UPDATES_DIR)))
            updated: list[str] = []
            replaced: list[tuple[Path, Path | None]] = []
            try:
                total = len(check.files)
                timeout = max(5, int(self.load_config().get("timeout_seconds", 12)))
                for index, item in enumerate(check.files, start=1):
                    if progress:
                        progress(index - 1, total, f"Загрузка: {item.path}")
                    response = self._session.get(item.url, timeout=timeout, stream=True)
                    response.raise_for_status()
                    temp_file = temp_root / item.path
                    temp_file.parent.mkdir(parents=True, exist_ok=True)
                    with temp_file.open("wb") as output:
                        for chunk in response.iter_content(1024 * 256):
                            if chunk:
                                output.write(chunk)
                    actual = self.sha256(temp_file).lower()
                    if actual != item.sha256.lower():
                        raise UpdateError(f"Контрольная сумма не совпала: {item.path}")

                for index, item in enumerate(check.files, start=1):
                    if progress:
                        progress(index - 1, total, f"Установка: {item.path}")
                    source = temp_root / item.path
                    target = self._target_path(item.path)
                    backup = None
                    if target.exists():
                        backup = backup_root / item.path
                        backup.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(target, backup)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    replacement = target.with_suffix(target.suffix + ".new")
                    shutil.copy2(source, replacement)
                    os.replace(replacement, target)
                    replaced.append((target, backup))
                    updated.append(item.path)

                if progress:
                    progress(total, total, "Обновление установлено")
                self._save_changelog(check, updated)
                return updated
            except Exception:
                for target, backup in reversed(replaced):
                    try:
                        if backup and backup.exists():
                            shutil.copy2(backup, target)
                        elif target.exists():
                            target.unlink()
                    except Exception:
                        pass
                raise
            finally:
                shutil.rmtree(temp_root, ignore_errors=True)

    def _save_changelog(self, check: UpdateCheck, updated_files: Iterable[str]) -> None:
        payload = {
            "from_version": check.current_version,
            "to_version": check.remote_version,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "release_notes": check.release_notes,
            "updated_files": list(updated_files),
        }
        UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        self.PENDING_CHANGELOG.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        history = []
        if self.HISTORY_FILE.exists():
            try:
                history = json.loads(self.HISTORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                history = []
        if not isinstance(history, list):
            history = []
        history.insert(0, payload)
        self.HISTORY_FILE.write_text(json.dumps(history[:50], ensure_ascii=False, indent=2), encoding="utf-8")

    def pop_pending_changelog(self) -> dict | None:
        if not self.PENDING_CHANGELOG.exists():
            return None
        try:
            data = json.loads(self.PENDING_CHANGELOG.read_text(encoding="utf-8"))
        except Exception:
            data = None
        try:
            self.PENDING_CHANGELOG.unlink()
        except Exception:
            pass
        return data if isinstance(data, dict) else None

    def history(self) -> list[dict]:
        if not self.HISTORY_FILE.exists():
            return []
        try:
            value = json.loads(self.HISTORY_FILE.read_text(encoding="utf-8"))
            return value if isinstance(value, list) else []
        except Exception:
            return []


update_manager = UpdateManager()
