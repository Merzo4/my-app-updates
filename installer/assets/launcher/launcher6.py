from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENGINE_VERSION = "6.0.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def appdata() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MerzoStreamSuite"


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def version_key(value: str) -> tuple[int, int, int, int]:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)([a-z]*)", str(value or "").strip().lower().lstrip("v"))
    if not m:
        return (0, 0, 0, 0)
    rank = 0
    for c in m.group(4):
        rank = rank * 26 + ord(c) - ord("a") + 1
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), rank


def highest_version(versions: Path) -> str:
    values = []
    if versions.is_dir():
        for p in versions.iterdir():
            if p.is_dir() and (p / "release_manifest.json").is_file() and version_key(p.name) != (0, 0, 0, 0):
                values.append(p.name)
    return max(values, key=version_key) if values else ""


def ensure_state(install_root: Path) -> tuple[Path, dict[str, Any]]:
    path = appdata() / "update6" / "state.json"
    state = read_json(path)
    if not state:
        old = read_json(appdata() / "update5" / "state.json")
        current = str(old.get("current_version") or "")
        if not current or not (install_root / "versions" / current).is_dir():
            current = highest_version(install_root / "versions")
        state = {
            "schema": 6,
            "engine_version": ENGINE_VERSION,
            "current_version": current,
            "previous_version": str(old.get("previous_version") or ""),
            "last_good_version": str(old.get("last_good_version") or current),
            "pending_version": "",
            "pending_since_utc": "",
            "rollback_path": "",
            "failed_version": "",
            "last_transaction_id": "",
            "last_result_path": "",
        }
        atomic_json(path, state)
    return path, state


def write_transaction_result(state: dict[str, Any], **changes: Any) -> None:
    result_path = str(state.get("last_result_path") or "")
    if not result_path:
        return
    path = Path(result_path)
    result = read_json(path)
    result.update(changes)
    result["updated_at_utc"] = utc_now()
    atomic_json(path, result)


def launch_version(install_root: Path, version: str, health: bool, timeout: int) -> bool:
    version_root = install_root / "versions" / version
    run_script = version_root / "RUN_VERSION.ps1"
    if not run_script.is_file():
        raise RuntimeError(f"Не найден RUN_VERSION.ps1 версии {version}")

    env = os.environ.copy()
    env["MERZOSTREAM_INSTALL_ROOT"] = str(install_root)
    env["MERZOSTREAM_SHARED_ROOT"] = str(install_root / "shared")
    env["MERZOSTREAM_ACTIVE_VERSION"] = version
    health_file = appdata() / "update6" / "health" / f"{version}.json"
    health_file.parent.mkdir(parents=True, exist_ok=True)
    if health:
        health_file.unlink(missing_ok=True)
        env["MERZOSTREAM_HEALTH_FILE"] = str(health_file)
    else:
        env["MERZOSTREAM_HEALTH_FILE"] = ""

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    proc = subprocess.run([
        "powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(run_script), "-AppRoot", str(version_root),
    ], cwd=str(version_root), env=env, creationflags=flags, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"RUN_VERSION.ps1 завершился с кодом {proc.returncode}")
    if not health:
        return True

    deadline = time.monotonic() + max(10, timeout)
    while time.monotonic() < deadline:
        h = read_json(health_file)
        if bool(h.get("ok")) and str(h.get("version") or "") == version:
            return True
        time.sleep(0.25)
    return False



def engine_action(install_root: Path, state: dict[str, Any], action: str) -> int:
    result_path_value = str(state.get("last_result_path") or "")
    if not result_path_value:
        raise RuntimeError("Для pending-обновления не найден result.json транзакции")
    result_path = Path(result_path_value)
    request_path = result_path.with_name("request.json")
    engine = install_root / "launcher" / "update_engine6.py"
    if not request_path.is_file() or not engine.is_file():
        raise RuntimeError("Не найдены файлы транзакции Update Engine 6")
    proc = subprocess.run([
        sys.executable, str(engine), "--request", str(request_path),
        "--result", str(result_path), "--action", action,
    ], cwd=str(install_root), timeout=180)
    return int(proc.returncode)


def activate_version(install_root: Path, version: str) -> str:
    """Installer-only activation. No protected file moves are performed here."""
    target = str(version or "").strip().lower().lstrip("v")
    if version_key(target) == (0, 0, 0, 0):
        raise RuntimeError(f"Некорректная версия для активации: {version!r}")
    target_dir = install_root / "versions" / target
    if not target_dir.is_dir() or not (target_dir / "release_manifest.json").is_file():
        raise RuntimeError(f"Версия {target} не установлена полностью")

    state_path, old = ensure_state(install_root)
    previous = str(old.get("current_version") or "")
    state = {
        "schema": 6,
        "engine_version": ENGINE_VERSION,
        "current_version": target,
        "previous_version": previous if previous != target else str(old.get("previous_version") or ""),
        "last_good_version": target,
        "pending_version": "",
        "pending_since_utc": "",
        "rollback_path": "",
        "failed_version": "",
        "last_transaction_id": "installer-activation",
        "last_result_path": "",
        "activated_at_utc": utc_now(),
    }
    atomic_json(state_path, state)
    return target

def run(install_root: Path, activate: str = "") -> int:
    log_path = appdata() / "logs" / "launcher6.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(message: str) -> None:
        try:
            with log_path.open("a", encoding="utf-8") as f:
                f.write(f"{utc_now()} [Launcher6] {message}\n")
        except Exception:
            pass

    try:
        if activate:
            activated = activate_version(install_root, activate)
            log(f"installer activation: {activated}")

        state_path, state = ensure_state(install_root)
        current = str(state.get("current_version") or "")
        if not current or not (install_root / "versions" / current).is_dir():
            current = highest_version(install_root / "versions")
            if not current:
                raise RuntimeError("Не найдена установленная версия MerzoStream Suite")
            state["current_version"] = current
            if not state.get("last_good_version"):
                state["last_good_version"] = current
            atomic_json(state_path, state)

        config = read_json(install_root / "launcher" / "config.json")
        timeout = int(config.get("startup_health_timeout_seconds", 45) or 45)

        if str(state.get("pending_version") or "") == current:
            # Recovery path for an update whose Update Host was interrupted.
            log(f"pending recovery health-check start {current}")
            healthy = False
            try:
                healthy = launch_version(install_root, current, True, timeout)
            except Exception as exc:
                log(f"health launch failed: {exc}")

            if healthy:
                code = engine_action(install_root, state, "commit")
                log(f"pending recovery commit exit={code}")
                return 0 if code == 0 else code

            code = engine_action(install_root, state, "rollback")
            log(f"pending recovery rollback exit={code}")
            state = read_json(state_path)
            previous = str(state.get("current_version") or "")
            if previous:
                launch_version(install_root, previous, False, timeout)
            return 20 if code == 0 else code

        launch_version(install_root, current, False, timeout)
        return 0
    except Exception as exc:
        log(f"FATAL: {exc}")
        try:
            if os.name == "nt":
                import ctypes
                ctypes.windll.user32.MessageBoxW(None, str(exc), "MerzoStream Suite — Launcher 6", 0x10)
        except Exception:
            pass
        return 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--install-root", required=True)
    p.add_argument("--activate-version", default="")
    args = p.parse_args()
    return run(Path(args.install_root).resolve(), args.activate_version)


if __name__ == "__main__":
    raise SystemExit(main())
