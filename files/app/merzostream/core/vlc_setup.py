from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .event_log import log
from .paths import RESOURCES_DIR


VLC_PATHS = (
    Path(r"C:\Program Files\VideoLAN\VLC\vlc.exe"),
    Path(r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"),
)


def find_vlc_executable() -> Path | None:
    for path in VLC_PATHS:
        if path.exists():
            return path
    return None


def prepare_vlc_dll_path() -> Path | None:
    """Добавляет папку установленного VLC в поиск DLL текущего процесса."""
    executable = find_vlc_executable()
    if executable is None:
        return None

    vlc_dir = executable.parent
    os.environ["PATH"] = str(vlc_dir) + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(str(vlc_dir))
        except OSError:
            pass
    return executable


def ensure_vlc_installed() -> tuple[bool, str]:
    """
    Проверяет VLC и при необходимости запускает встроенный установщик.
    Windows покажет стандартное окно UAC, после подтверждения установка идёт тихо.
    """
    existing = prepare_vlc_dll_path()
    if existing is not None:
        return True, f"VLC найден: {existing}"

    installer = RESOURCES_DIR / "vlc-installer.exe"
    if not installer.exists():
        return False, f"Не найден установщик: {installer}"

    log("VLC", "VLC не найден. Запрашиваются права администратора для тихой установки.")
    try:
        escaped = str(installer).replace("'", "''")
        command = (
            f"$p = Start-Process -FilePath '{escaped}' "
            "-ArgumentList '/L=1049','/S' -Verb RunAs -Wait -PassThru; "
            "exit $p.ExitCode"
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0:
            return False, "Установка VLC отменена или завершилась с ошибкой."
    except Exception as exc:
        log("VLC", f"Ошибка запуска установщика: {exc}")
        return False, f"Не удалось запустить установщик VLC: {exc}"

    installed = prepare_vlc_dll_path()
    if installed is None:
        return False, "Установщик завершился, но VLC не найден в стандартной папке."

    log("VLC", f"VLC успешно установлен: {installed}")
    return True, "VLC успешно установлен и подключён."
