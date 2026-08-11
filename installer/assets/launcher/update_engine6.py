from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENGINE_VERSION = "6.0.0"
REQUEST_SCHEMA = 6
STATE_SCHEMA = 6
MAX_ARCHIVE_BYTES = 768 * 1024 * 1024
MAX_FILE_BYTES = 256 * 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def appdata_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MerzoStreamSuite"


def update_root() -> Path:
    return appdata_root() / "update6"


def logs_root() -> Path:
    return appdata_root() / "logs"


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_version(value: str) -> str:
    text = str(value or "").strip()
    if text.lower().startswith("v"):
        text = text[1:]
    if not re.fullmatch(r"\d+\.\d+\.\d+[a-z]*", text, re.I):
        raise ValueError(f"Некорректная версия: {value!r}")
    return text


class EngineFailure(RuntimeError):
    def __init__(self, code: str, stage: str, message: str):
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.message = message


class ResultWriter:
    def __init__(self, result_path: Path, request: dict[str, Any]):
        self.path = result_path
        self.base = {
            "schema": 6,
            "engine_version": ENGINE_VERSION,
            "transaction_id": str(request.get("transaction_id") or ""),
            "current_version": str(request.get("current_version") or ""),
            "target_version": str(request.get("target_version") or ""),
            "install_root": str(request.get("install_root") or ""),
        }

    def write(self, *, status: str, stage: str, percent: int, message: str,
              error_code: str = "", exception: str = "", **extra: Any) -> None:
        value = dict(self.base)
        value.update({
            "status": status,
            "stage": stage,
            "percent": max(0, min(100, int(percent))),
            "message": str(message),
            "error_code": str(error_code),
            "exception": str(exception),
            "updated_at_utc": utc_now(),
        })
        value.update(extra)
        atomic_json(self.path, value)


class NamedMutex:
    def __init__(self) -> None:
        self.handle = None

    def __enter__(self):
        if os.name == "nt":
            kernel32 = ctypes.windll.kernel32
            self.handle = kernel32.CreateMutexW(None, False, "Local\\MerzoStreamSuite_UpdateEngine6")
            if not self.handle:
                raise EngineFailure("ENGINE-LOCK", "preflight", "Не удалось создать блокировку Update Engine.")
            if kernel32.GetLastError() == 183:
                kernel32.CloseHandle(self.handle)
                self.handle = None
                raise EngineFailure("ENGINE-BUSY", "preflight", "Другой процесс обновления уже выполняется.")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.handle and os.name == "nt":
            ctypes.windll.kernel32.CloseHandle(self.handle)
        self.handle = None


def is_admin() -> bool:
    if os.name != "nt":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def can_write_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / f".merzostream-write-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        probe.write_bytes(b"ok")
        probe.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def elevate_and_wait(argv: list[str]) -> int:
    if os.name != "nt":
        return 1

    SEE_MASK_NOCLOSEPROCESS = 0x00000040
    SW_SHOWNORMAL = 1
    INFINITE = 0xFFFFFFFF

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong), ("fMask", ctypes.c_ulong), ("hwnd", ctypes.c_void_p),
            ("lpVerb", ctypes.c_wchar_p), ("lpFile", ctypes.c_wchar_p),
            ("lpParameters", ctypes.c_wchar_p), ("lpDirectory", ctypes.c_wchar_p),
            ("nShow", ctypes.c_int), ("hInstApp", ctypes.c_void_p), ("lpIDList", ctypes.c_void_p),
            ("lpClass", ctypes.c_wchar_p), ("hkeyClass", ctypes.c_void_p), ("dwHotKey", ctypes.c_ulong),
            ("hIcon", ctypes.c_void_p), ("hProcess", ctypes.c_void_p),
        ]

    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas"
    info.lpFile = sys.executable
    info.lpParameters = subprocess.list2cmdline(argv)
    info.lpDirectory = str(Path(__file__).resolve().parent)
    info.nShow = SW_SHOWNORMAL

    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        err = ctypes.GetLastError()
        if err == 1223:
            raise EngineFailure("UAC-CANCELLED", "elevation", "Права администратора не предоставлены. Обновление отменено.")
        raise EngineFailure("UAC-FAILED", "elevation", f"Не удалось запросить права администратора. Windows error {err}.")
    try:
        ctypes.windll.kernel32.WaitForSingleObject(info.hProcess, INFINITE)
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code))
        return int(code.value)
    finally:
        ctypes.windll.kernel32.CloseHandle(info.hProcess)


def migrate_state(install_root: Path, requested_current: str) -> dict[str, Any]:
    path = update_root() / "state.json"
    state = read_json(path)
    if state:
        state["schema"] = STATE_SCHEMA
        state["engine_version"] = ENGINE_VERSION
        return state

    old = read_json(appdata_root() / "update5" / "state.json")
    state = {
        "schema": STATE_SCHEMA,
        "engine_version": ENGINE_VERSION,
        "current_version": str(old.get("current_version") or requested_current or ""),
        "previous_version": str(old.get("previous_version") or ""),
        "last_good_version": str(old.get("last_good_version") or old.get("current_version") or requested_current or ""),
        "pending_version": "",
        "pending_since_utc": "",
        "rollback_path": "",
        "failed_version": "",
        "last_transaction_id": "",
        "last_result_path": "",
    }
    atomic_json(path, state)
    return state


def validate_request(request: dict[str, Any]) -> tuple[Path, str, str, str, int]:
    if int(request.get("schema", 0) or 0) != REQUEST_SCHEMA:
        raise EngineFailure("REQ-SCHEMA", "preflight", "Неподдерживаемый формат запроса обновления.")
    try:
        target = normalize_version(str(request.get("target_version") or ""))
        current = normalize_version(str(request.get("current_version") or ""))
    except ValueError as exc:
        raise EngineFailure("REQ-VERSION", "preflight", str(exc)) from exc
    install_root = Path(str(request.get("install_root") or "")).resolve()
    if not install_root.is_dir():
        raise EngineFailure("PRE-ROOT", "preflight", f"Папка установки не найдена: {install_root}")
    if not (install_root / "versions").is_dir():
        raise EngineFailure("PRE-VERSIONS", "preflight", "В папке установки отсутствует каталог versions.")
    url = str(request.get("package_url") or "").strip()
    if not url.lower().startswith("https://"):
        raise EngineFailure("REQ-URL", "preflight", "Пакет обновления должен загружаться по HTTPS.")
    expected = str(request.get("package_sha256") or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise EngineFailure("REQ-SHA", "preflight", "В запросе отсутствует корректный SHA-256 пакета.")
    size = int(request.get("package_size") or 0)
    if size < 0:
        raise EngineFailure("REQ-SIZE", "preflight", "Некорректный размер пакета.")
    return install_root, current, target, expected, size


def preflight_environment(install_root: Path, current: str, target: str, expected_size: int) -> dict[str, Any]:
    versions = install_root / "versions"
    current_dir = versions / current
    if not current_dir.is_dir():
        raise EngineFailure("STATE-CURRENT-MISSING", "preflight", f"Текущая версия {current} отсутствует в versions.")

    state = migrate_state(install_root, current)
    state_current = str(state.get("current_version") or "")
    pending = str(state.get("pending_version") or "")
    if pending:
        raise EngineFailure(
            "STATE-PENDING", "preflight",
            f"Предыдущее обновление {pending} ещё не завершено. Запусти MerzoStream Suite для автоматического recovery."
        )
    if state_current and state_current != current:
        raise EngineFailure(
            "STATE-CURRENT", "preflight",
            f"Update state ожидает версию {state_current}, а обновление запущено из {current}. "
            "Перезапусти MerzoStream Suite через основной ярлык."
        )

    try:
        free = shutil.disk_usage(versions).free
    except Exception as exc:
        raise EngineFailure("PRE-DISK", "preflight", f"Не удалось проверить свободное место: {exc}") from exc
    required = max(512 * 1024 * 1024, int(expected_size or 0) * 6)
    if free < required:
        raise EngineFailure(
            "PRE-DISK-SPACE", "preflight",
            f"Недостаточно свободного места для безопасного обновления. Нужно минимум {required/1073741824:.1f} ГБ, "
            f"доступно {free/1073741824:.1f} ГБ."
        )
    return state

def download_package(url: str, dest: Path, expected_sha: str, expected_size: int, writer: ResultWriter) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        if (not expected_size or dest.stat().st_size == expected_size) and sha256_file(dest) == expected_sha:
            writer.write(status="running", stage="verify", percent=48, message="Пакет уже скачан. SHA-256 подтверждён.")
            return
        dest.unlink(missing_ok=True)

    last = ""
    for attempt in range(1, 5):
        part = dest.with_suffix(dest.suffix + ".part")
        part.unlink(missing_ok=True)
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": f"MerzoStreamSuite-UpdateEngine/{ENGINE_VERSION}",
                "Accept": "application/octet-stream",
            })
            writer.write(status="running", stage="download", percent=12,
                         message=f"Скачивание пакета… попытка {attempt}/4")
            with urllib.request.urlopen(req, timeout=30) as response, part.open("wb") as fh:
                total = int(response.headers.get("Content-Length") or expected_size or 0)
                done = 0
                last_emit = 0
                while True:
                    chunk = response.read(1024 * 512)
                    if not chunk:
                        break
                    fh.write(chunk)
                    done += len(chunk)
                    if done - last_emit >= 1024 * 1024:
                        last_emit = done
                        pct = 12 + int(min(1.0, done / total) * 32) if total else 28
                        msg = (f"Скачивание пакета… {done/1048576:.1f} / {total/1048576:.1f} МБ"
                               if total else f"Скачивание пакета… {done/1048576:.1f} МБ")
                        writer.write(status="running", stage="download", percent=pct, message=msg)
            if expected_size and part.stat().st_size != expected_size:
                raise RuntimeError(f"размер {part.stat().st_size} вместо {expected_size}")
            actual = sha256_file(part)
            if actual != expected_sha:
                raise RuntimeError(f"SHA-256 {actual} вместо {expected_sha}")
            os.replace(part, dest)
            writer.write(status="running", stage="verify", percent=48, message="SHA-256 пакета подтверждён.")
            return
        except Exception as exc:
            last = str(exc)
            part.unlink(missing_ok=True)
            if attempt < 4:
                time.sleep(min(8, 2 ** (attempt - 1)))
    raise EngineFailure("NET-DOWNLOAD", "download", f"Не удалось скачать пакет после 4 попыток: {last}")


def safe_extract(zip_path: Path, staging: Path) -> None:
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
    root = staging.resolve()
    total = 0
    seen: set[str] = set()
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                if not name or name.startswith("/"):
                    raise EngineFailure("ZIP-PATH", "extract", f"Недопустимый путь в ZIP: {name!r}")
                if ".." in Path(name).parts:
                    raise EngineFailure("ZIP-PATH", "extract", f"ZIP пытается выйти из staging: {name}")
                if ((info.external_attr >> 16) & 0xF000) == 0xA000:
                    raise EngineFailure("ZIP-SYMLINK", "extract", f"ZIP содержит symbolic link: {name}")
                target = (root / Path(name)).resolve()
                try:
                    target.relative_to(root)
                except ValueError as exc:
                    raise EngineFailure("ZIP-PATH", "extract", f"ZIP entry вне staging: {name}") from exc
                key = str(target).lower()
                if key in seen:
                    raise EngineFailure("ZIP-DUP", "extract", f"ZIP содержит дубликат пути: {name}")
                seen.add(key)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if info.file_size > MAX_FILE_BYTES:
                    raise EngineFailure("ZIP-LARGE", "extract", f"Слишком большой файл в ZIP: {name}")
                total += info.file_size
                if total > MAX_ARCHIVE_BYTES:
                    raise EngineFailure("ZIP-LARGE", "extract", "Распакованный ZIP превышает безопасный лимит.")
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst, length=1024 * 1024)
    except EngineFailure:
        raise
    except Exception as exc:
        raise EngineFailure("ZIP-CORRUPT", "extract", f"Не удалось распаковать ZIP: {exc}") from exc


def verify_manifest(staging: Path, target: str, writer: ResultWriter) -> dict[str, Any]:
    manifest_path = staging / "release_manifest.json"
    if not manifest_path.is_file():
        raise EngineFailure("MANIFEST-MISSING", "manifest", "В пакете отсутствует release_manifest.json.")
    manifest = read_json(manifest_path)
    if int(manifest.get("schema", 0) or 0) != 5:
        raise EngineFailure("MANIFEST-SCHEMA", "manifest", "Неподдерживаемая schema release_manifest.json.")
    try:
        actual_version = normalize_version(str(manifest.get("version") or ""))
    except ValueError as exc:
        raise EngineFailure("MANIFEST-VERSION", "manifest", "В manifest указана некорректная версия.") from exc
    if actual_version != target:
        raise EngineFailure("MANIFEST-VERSION", "manifest", "Версия внутри ZIP не совпадает с выбранным обновлением.")
    items = manifest.get("files")
    if not isinstance(items, list) or not items:
        raise EngineFailure("MANIFEST-FILES", "manifest", "Manifest не содержит список файлов.")
    if int(manifest.get("file_count", len(items)) or 0) != len(items):
        raise EngineFailure("MANIFEST-COUNT", "manifest", "file_count manifest не совпадает со списком файлов.")

    listed: set[str] = set()
    root = staging.resolve()
    total = len(items)
    for idx, item in enumerate(items, 1):
        if not isinstance(item, dict):
            raise EngineFailure("MANIFEST-ENTRY", "manifest", "Manifest содержит некорректную запись.")
        rel = str(item.get("path") or "").replace("\\", "/")
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            raise EngineFailure("MANIFEST-PATH", "manifest", f"Некорректный путь manifest: {rel!r}")
        expected = str(item.get("sha256") or "").lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise EngineFailure("MANIFEST-SHA", "manifest", f"Некорректный SHA для {rel}")
        path = (root / rel).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise EngineFailure("MANIFEST-PATH", "manifest", f"Путь manifest вне staging: {rel}") from exc
        if not path.is_file():
            raise EngineFailure("MANIFEST-MISSING-FILE", "manifest", f"Файл из manifest отсутствует: {rel}")
        if path.stat().st_size != int(item.get("size") or 0):
            raise EngineFailure("MANIFEST-SIZE", "manifest", f"Размер файла не совпадает: {rel}")
        if sha256_file(path) != expected:
            raise EngineFailure("MANIFEST-HASH", "manifest", f"SHA-256 файла не совпадает: {rel}")
        listed.add(rel.lower())
        if idx == 1 or idx == total or idx % max(1, total // 10) == 0:
            writer.write(status="running", stage="manifest", percent=58 + int(idx * 14 / total),
                         message=f"Проверка файлов… {idx}/{total}")

    actual = {
        p.relative_to(staging).as_posix().lower()
        for p in staging.rglob("*") if p.is_file() and p.name != "release_manifest.json"
    }
    extras = actual - listed
    missing = listed - actual
    if extras:
        raise EngineFailure("MANIFEST-EXTRA", "manifest", f"В ZIP есть лишние файлы: {', '.join(sorted(extras)[:5])}")
    if missing:
        raise EngineFailure("MANIFEST-MISSING-FILE", "manifest", "В ZIP отсутствуют файлы из manifest.")
    return manifest


def _state_path() -> Path:
    return update_root() / "state.json"


def _result_path_from_state(state: dict[str, Any]) -> Path | None:
    value = str(state.get("last_result_path") or "").strip()
    return Path(value) if value else None


def _write_result_from_state(state: dict[str, Any], **changes: Any) -> None:
    path = _result_path_from_state(state)
    if not path:
        return
    result = read_json(path)
    result.update(changes)
    result["updated_at_utc"] = utc_now()
    atomic_json(path, result)


def install_version(staging: Path, install_root: Path, current: str, target: str,
                    request: dict[str, Any], result_path: Path, writer: ResultWriter) -> None:
    versions = install_root / "versions"
    target_dir = versions / target
    txn = str(request.get("transaction_id") or uuid.uuid4().hex)
    install_tmp = versions / f".install-{target}-{txn}"
    rollback_dir = versions / f".rollback-{target}-{txn}"

    if install_tmp.exists():
        shutil.rmtree(install_tmp, ignore_errors=True)
    if rollback_dir.exists():
        shutil.rmtree(rollback_dir, ignore_errors=True)

    # Copy into the protected volume first, then perform same-volume atomic renames.
    try:
        shutil.copytree(staging, install_tmp)
    except Exception as exc:
        raise EngineFailure("INSTALL-COPY", "install", f"Не удалось подготовить файлы внутри Program Files: {exc}") from exc

    rollback_path = ""
    if target_dir.exists():
        try:
            os.replace(target_dir, rollback_dir)
            rollback_path = str(rollback_dir)
        except Exception as exc:
            shutil.rmtree(install_tmp, ignore_errors=True)
            raise EngineFailure("INSTALL-BACKUP", "install", f"Не удалось создать rollback-копию версии {target}: {exc}") from exc

    try:
        os.replace(install_tmp, target_dir)
    except Exception as exc:
        if rollback_dir.exists() and not target_dir.exists():
            try:
                os.replace(rollback_dir, target_dir)
            except Exception:
                pass
        shutil.rmtree(install_tmp, ignore_errors=True)
        raise EngineFailure("INSTALL-MOVE", "install", f"Не удалось активировать файлы версии {target}: {exc}") from exc

    state_path = _state_path()
    state = migrate_state(install_root, current)
    previous = str(state.get("current_version") or current)
    state.update({
        "schema": STATE_SCHEMA,
        "engine_version": ENGINE_VERSION,
        "previous_version": previous,
        "current_version": target,
        "pending_version": target,
        "pending_since_utc": utc_now(),
        "rollback_path": rollback_path,
        "failed_version": "",
        "last_transaction_id": txn,
        "last_result_path": str(result_path),
        "last_package_sha256": str(request.get("package_sha256") or ""),
    })
    try:
        atomic_json(state_path, state)
    except Exception as exc:
        try:
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            if rollback_dir.exists():
                os.replace(rollback_dir, target_dir)
        except Exception:
            pass
        raise EngineFailure("STATE-WRITE", "state", f"Не удалось записать state.json: {exc}") from exc

    writer.write(
        status="installed", stage="health", percent=90,
        message=f"Версия {target} установлена. Выполняется первый запуск и health-check.",
        previous_version=previous, pending_version=target,
    )


def commit_transaction(install_root: Path, request: dict[str, Any], writer: ResultWriter) -> None:
    state_path = _state_path()
    state = read_json(state_path)
    target = normalize_version(str(request.get("target_version") or ""))
    if str(state.get("pending_version") or "") != target or str(state.get("current_version") or "") != target:
        raise EngineFailure("COMMIT-STATE", "commit", "State не содержит ожидаемую pending-версию для commit.")

    rollback_path = str(state.get("rollback_path") or "")
    if rollback_path:
        rb = Path(rollback_path)
        try:
            if rb.exists():
                shutil.rmtree(rb)
        except Exception as exc:
            raise EngineFailure("COMMIT-CLEANUP", "commit", f"Не удалось удалить rollback-копию: {exc}") from exc

    state.update({
        "pending_version": "",
        "pending_since_utc": "",
        "last_good_version": target,
        "rollback_path": "",
        "failed_version": "",
        "engine_version": ENGINE_VERSION,
    })
    atomic_json(state_path, state)
    writer.write(
        status="success", stage="done", percent=100, error_code="",
        message=f"MerzoStream Suite {target} установлена и успешно запущена.",
        current_version=target,
    )


def rollback_transaction(install_root: Path, request: dict[str, Any], writer: ResultWriter,
                         reason: str = "Новая версия не прошла health-check.") -> None:
    state_path = _state_path()
    state = read_json(state_path)
    target = normalize_version(str(request.get("target_version") or ""))
    target_dir = install_root / "versions" / target
    previous = str(state.get("previous_version") or state.get("last_good_version") or "")
    rollback_path = str(state.get("rollback_path") or "")
    rollback_dir = Path(rollback_path) if rollback_path else None

    try:
        if rollback_dir and rollback_dir.exists():
            if target_dir.exists():
                shutil.rmtree(target_dir)
            os.replace(rollback_dir, target_dir)
            # Reinstall of the same version: restored folder is still target.
            if previous == target or not previous:
                previous = target
        else:
            if target_dir.exists() and previous != target:
                shutil.rmtree(target_dir)
    except Exception as exc:
        raise EngineFailure("ROLLBACK-FILES", "rollback", f"Не удалось восстановить файлы предыдущей версии: {exc}") from exc

    if previous and not (install_root / "versions" / previous).is_dir():
        previous = str(state.get("last_good_version") or "")
    if not previous or not (install_root / "versions" / previous).is_dir():
        raise EngineFailure("ROLLBACK-NO-PREVIOUS", "rollback", "Предыдущая рабочая версия не найдена для rollback.")

    state.update({
        "current_version": previous,
        "pending_version": "",
        "pending_since_utc": "",
        "rollback_path": "",
        "failed_version": target,
        "engine_version": ENGINE_VERSION,
    })
    atomic_json(state_path, state)
    writer.write(
        status="failed", stage="health", percent=100,
        error_code="HEALTH-FAILED",
        message=f"{reason} Автоматически возвращена версия {previous}.",
        current_version=previous, failed_version=target,
    )


def _needs_write_elevation(install_root: Path) -> bool:
    return not can_write_dir(install_root / "versions")


def _elevate_current(action: str, request_path: Path, result_path: Path) -> int:
    child_args = [
        str(Path(__file__).resolve()), "--request", str(request_path),
        "--result", str(result_path), "--action", action, "--elevated",
    ]
    return elevate_and_wait(child_args)


def run(request_path: Path, result_path: Path, action: str = "install", elevated: bool = False) -> int:
    request = read_json(request_path)
    writer = ResultWriter(result_path, request)
    log_path = logs_root() / "update_engine6.log"
    logs_root().mkdir(parents=True, exist_ok=True)

    def log(msg: str) -> None:
        try:
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"{utc_now()} [Engine6] action={action} {msg}\n")
        except Exception:
            pass

    try:
        install_root, current, target, expected_sha, expected_size = validate_request(request)
        if action not in {"install", "commit", "rollback"}:
            raise EngineFailure("REQ-ACTION", "preflight", f"Неизвестное действие Update Engine: {action}")

        if action == "install":
            preflight_environment(install_root, current, target, expected_size)

        if _needs_write_elevation(install_root):
            if os.name == "nt" and not is_admin() and not elevated:
                writer.write(
                    status="elevation", stage="elevation", percent=7,
                    message="Для изменения Program Files требуется подтверждение Windows UAC.",
                )
                return _elevate_current(action, request_path, result_path)
            raise EngineFailure("INSTALL-PERMISSION", "elevation", f"Нет прав записи в {install_root / 'versions'}.")

        with NamedMutex():
            if action == "commit":
                log(f"commit target={target}")
                commit_transaction(install_root, request, writer)
                return 0
            if action == "rollback":
                log(f"rollback target={target}")
                rollback_transaction(install_root, request, writer)
                return 0

            writer.write(status="running", stage="preflight", percent=5, message="Предварительная проверка пройдена.")
            log(f"transaction={request.get('transaction_id')} current={current} target={target} root={install_root}")
            root = update_root()
            downloads = root / "downloads"
            staging_root = root / "staging"
            downloads.mkdir(parents=True, exist_ok=True)
            staging_root.mkdir(parents=True, exist_ok=True)
            package = downloads / f"MerzoStreamSuite-{target}.zip"
            staging = staging_root / f"{target}-{request.get('transaction_id')}"

            download_package(str(request.get("package_url") or ""), package, expected_sha, expected_size, writer)
            writer.write(status="running", stage="extract", percent=52, message="Безопасная распаковка пакета…")
            safe_extract(package, staging)
            writer.write(status="running", stage="manifest", percent=58, message="Проверка release_manifest.json…")
            verify_manifest(staging, target, writer)
            writer.write(status="running", stage="install", percent=75, message=f"Установка версии {target}…")
            install_version(staging, install_root, current, target, request, result_path, writer)
            log(f"installed target={target}; pending health-check")
            return 0
    except EngineFailure as exc:
        log(f"FAIL {exc.code} {exc.stage}: {exc.message}")
        writer.write(
            status="failed", stage=exc.stage, percent=100, message=exc.message,
            error_code=exc.code, exception=traceback.format_exc(limit=8),
        )
        return 2
    except Exception as exc:
        log(f"UNEXPECTED: {exc}")
        writer.write(
            status="failed", stage="engine", percent=100,
            message=f"Непредвиденная ошибка Update Engine: {exc}",
            error_code="ENGINE-UNEXPECTED", exception=traceback.format_exc(limit=12),
        )
        return 3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--action", choices=("install", "commit", "rollback"), default="install")
    parser.add_argument("--elevated", action="store_true")
    args = parser.parse_args()
    return run(Path(args.request), Path(args.result), args.action, args.elevated)


if __name__ == "__main__":
    raise SystemExit(main())
