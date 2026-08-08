from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .paths import BACKUPS_DIR, UPDATES_DIR, bundle_root


@dataclass(frozen=True)
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
    """Надёжные частичные обновления из публичного GitHub-репозитория."""

    CONFIG_NAME = "update_config.json"
    PENDING_CHANGELOG = UPDATES_DIR / "pending_changelog.json"
    HISTORY_FILE = UPDATES_DIR / "history.json"
    LAST_ERROR_FILE = UPDATES_DIR / "last_error.json"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=0.6,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
        )
        self._session.mount("https://", HTTPAdapter(max_retries=retry))
        self._session.mount("http://", HTTPAdapter(max_retries=retry))
        self._session.headers.update({"User-Agent": "MerzoStreamSuite-Updater/2.0"})

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def is_safe_relative_path(value: str) -> bool:
        normalized = str(value).replace("\\", "/").strip()
        path = Path(normalized)
        return bool(normalized) and not path.is_absolute() and ".." not in path.parts

    @staticmethod
    def _version_key(value: str) -> tuple[int, int, int, int]:
        """Поддерживает 0.0.1, 0.0.1a, 0.0.1b ... 0.0.2."""
        text = str(value).strip().lower()
        text = text.replace("beta", "").replace("version", "").lstrip("v").strip()
        match = re.search(r"(\d+)\.(\d+)\.(\d+)([a-z]*)", text)
        if not match:
            return (0, 0, 0, 0)
        major, minor, patch = (int(match.group(i)) for i in range(1, 4))
        suffix = match.group(4)
        suffix_rank = 0
        for char in suffix:
            suffix_rank = suffix_rank * 26 + (ord(char) - ord("a") + 1)
        return (major, minor, patch, suffix_rank)

    def load_config(self) -> dict:
        path = bundle_root() / "resources" / self.CONFIG_NAME
        default = {
            "enabled": True,
            "manifest_url": "https://raw.githubusercontent.com/Merzo4/my-app-updates/main/manifest.json",
            "repository": "Merzo4/my-app-updates",
            "channel": "beta",
            "check_on_start": True,
            "timeout_seconds": 15,
        }
        if path.exists():
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
            raise UpdateError(f"Небезопасный путь в manifest.json: {logical_path}")

        root = bundle_root()
        if logical.startswith("app/merzostream/"):
            tail = logical[len("app/merzostream/"):]
            target = (root / "app" / "merzostream" / tail) if getattr(sys, "frozen", False) else (root / "src" / "merzostream" / tail)
        elif logical.startswith(("content/", "graphics/")):
            target = root / logical
        else:
            raise UpdateError(f"Обновление пути запрещено: {logical}")

        try:
            target.resolve(strict=False).relative_to(root.resolve())
        except ValueError as exc:
            raise UpdateError(f"Путь выходит за пределы приложения: {logical}") from exc
        return target

    def _get_json(self, url: str, timeout: int) -> dict:
        separator = "&" if "?" in url else "?"
        no_cache_url = f"{url}{separator}_={int(time.time())}"
        response = self._session.get(
            no_cache_url,
            timeout=timeout,
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise UpdateError("GitHub вернул не JSON. Проверь расположение manifest.json.") from exc
        if not isinstance(payload, dict):
            raise UpdateError("manifest.json должен содержать JSON-объект")
        return payload

    def _get_file_response(self, url: str, timeout: int):
        """Download update files without stale raw.githubusercontent.com cache."""
        separator = "&" if "?" in url else "?"
        no_cache_url = f"{url}{separator}_={time.time_ns()}"
        try:
            response = self._session.get(
                no_cache_url,
                timeout=timeout,
                stream=True,
                headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise UpdateError(f"Не удалось скачать файл с GitHub: {url}\\n{exc}") from exc

    def fetch_manifest(self) -> dict:
        config = self.load_config()
        if not config.get("enabled", True):
            raise UpdateError("Проверка обновлений отключена")
        url = str(config.get("manifest_url", "")).strip()
        if not url:
            raise UpdateError("В update_config.json не указан manifest_url")
        timeout = max(5, int(config.get("timeout_seconds", 15) or 15))
        manifest = self._get_json(url, timeout)
        if not isinstance(manifest.get("files"), list):
            raise UpdateError("В manifest.json отсутствует массив files")
        return manifest

    @staticmethod
    def _validate_download_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {
            "raw.githubusercontent.com", "github.com", "objects.githubusercontent.com"
        }:
            raise UpdateError(f"Запрещённый адрес файла обновления: {url}")

    def check(self, current_version: str) -> UpdateCheck:
        manifest = self.fetch_manifest()
        remote_version = str(manifest.get("version", "0.0.0")).strip()
        expected_channel = str(self.load_config().get("channel", "beta")).lower()
        remote_channel = str(manifest.get("channel", "beta")).lower()
        if remote_channel != expected_channel:
            return UpdateCheck(False, current_version, remote_version, message="Другой канал обновлений")

        changed: list[UpdateFile] = []
        for raw in manifest.get("files", []):
            if not isinstance(raw, dict):
                raise UpdateError("Некорректная запись файла в manifest.json")
            try:
                logical = str(raw["path"])
                url = str(raw["url"])
                expected_hash = str(raw["sha256"]).lower()
            except KeyError as exc:
                raise UpdateError(f"В manifest.json отсутствует поле {exc}") from exc
            if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                raise UpdateError(f"Некорректный SHA-256: {logical}")
            self._validate_download_url(url)
            target = self._target_path(logical)
            if target.exists() and self.sha256(target).lower() == expected_hash:
                continue
            changed.append(UpdateFile(
                path=logical,
                url=url,
                sha256=expected_hash,
                size=max(0, int(raw.get("size", 0) or 0)),
                restart_required=bool(raw.get("restart_required", True)),
            ))

        remote_key = self._version_key(remote_version)
        current_key = self._version_key(current_version)
        newer = remote_key > current_key
        notes = [str(x).strip() for x in manifest.get("release_notes", []) if str(x).strip()]
        if remote_key < current_key:
            return UpdateCheck(False, current_version, remote_version, notes, [], manifest, "На GitHub лежит более старая версия — обновление не требуется")
        available = bool(changed) or newer
        return UpdateCheck(
            available=available,
            current_version=current_version,
            remote_version=remote_version,
            release_notes=notes,
            files=changed,
            manifest=manifest,
            message="Доступно обновление" if available else "Установлена актуальная версия",
        )

    def apply(self, check: UpdateCheck, progress: Callable[[int, int, str], None] | None = None) -> list[str]:
        if not check.available:
            return []
        if not check.files:
            self._save_changelog(check, [])
            return []

        if not self._lock.acquire(blocking=False):
            raise UpdateError("Другое обновление уже выполняется")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_root = BACKUPS_DIR / f"update_{timestamp}"
        UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        temp_root = Path(tempfile.mkdtemp(prefix="merzostream_update_", dir=str(UPDATES_DIR)))
        replaced: list[tuple[Path, Path | None]] = []
        updated: list[str] = []
        try:
            total_steps = max(1, len(check.files) * 2 + 1)
            timeout = max(8, int(self.load_config().get("timeout_seconds", 15) or 15))

            for index, item in enumerate(check.files, start=1):
                if progress:
                    progress(index - 1, total_steps, f"Скачивание: {item.path}")
                response = self._get_file_response(item.url, timeout)
                temp_file = temp_root / item.path
                temp_file.parent.mkdir(parents=True, exist_ok=True)
                with temp_file.open("wb") as output:
                    for chunk in response.iter_content(256 * 1024):
                        if chunk:
                            output.write(chunk)
                if self.sha256(temp_file).lower() != item.sha256:
                    raise UpdateError(f"Не совпал SHA-256: {item.path}\nGitHub мог отдать старую кэшированную версию файла.")

            backup_root.mkdir(parents=True, exist_ok=True)
            (backup_root / "backup_info.json").write_text(json.dumps({
                "from_version": check.current_version,
                "to_version": check.remote_version,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "files": [item.path for item in check.files],
            }, ensure_ascii=False, indent=2), encoding="utf-8")

            for index, item in enumerate(check.files, start=1):
                if progress:
                    progress(len(check.files) + index - 1, total_steps, f"Установка: {item.path}")
                source = temp_root / item.path
                target = self._target_path(item.path)
                backup: Path | None = None
                if target.exists():
                    backup = backup_root / item.path
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, backup)
                target.parent.mkdir(parents=True, exist_ok=True)
                replacement = target.with_name(target.name + ".update_tmp")
                shutil.copy2(source, replacement)
                os.replace(replacement, target)
                replaced.append((target, backup))
                updated.append(item.path)

            if progress:
                progress(total_steps, total_steps, "Обновление установлено. Подготовка перезапуска…")
            self._save_changelog(check, updated)
            self._clear_last_error()
            return updated
        except Exception as exc:
            rollback_errors: list[str] = []
            for target, backup in reversed(replaced):
                try:
                    if backup and backup.exists():
                        shutil.copy2(backup, target)
                    elif target.exists():
                        target.unlink()
                except Exception as rollback_exc:
                    rollback_errors.append(f"{target}: {rollback_exc}")
            message = str(exc)
            if rollback_errors:
                message += "\nОшибки отката:\n" + "\n".join(rollback_errors)
            self._save_last_error(message)
            if isinstance(exc, UpdateError):
                raise
            raise UpdateError(message) from exc
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)
            self._lock.release()

    def _save_last_error(self, message: str) -> None:
        UPDATES_DIR.mkdir(parents=True, exist_ok=True)
        self.LAST_ERROR_FILE.write_text(json.dumps({
            "time": datetime.now(timezone.utc).isoformat(),
            "error": message,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def _clear_last_error(self) -> None:
        try:
            self.LAST_ERROR_FILE.unlink(missing_ok=True)
        except Exception:
            pass

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
        history = self.history()
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
