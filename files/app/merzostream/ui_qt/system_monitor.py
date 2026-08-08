from __future__ import annotations

import hashlib
import json
import os
import shutil
import string
import subprocess
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from ..core.settings_manager import settings

try:
    import psutil
except Exception:
    psutil = None


def _windows_creationflags() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def detect_disks() -> list[dict[str, str]]:
    """Return mounted Windows drive letters. On other OSes, return real mounted disks."""
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    if os.name == "nt":
        for letter in string.ascii_uppercase:
            mount = f"{letter}:\\"
            try:
                if not os.path.exists(mount):
                    continue
                if psutil is not None:
                    usage = psutil.disk_usage(mount)
                    if usage.total <= 0:
                        continue
                key = mount.upper()
                if key not in seen:
                    seen.add(key)
                    found.append({"id": key, "mount": mount, "title": f"Диск {letter}:"})
            except Exception:
                continue
        return found

    if psutil is None:
        return found
    try:
        for part in psutil.disk_partitions(all=False):
            mount = str(part.mountpoint)
            if not mount or mount in seen:
                continue
            try:
                if psutil.disk_usage(mount).total <= 0:
                    continue
            except Exception:
                continue
            seen.add(mount)
            found.append({"id": mount, "mount": mount, "title": f"Диск {mount}"})
    except Exception:
        pass
    return found


def _discover_windows_gpu_names() -> list[str]:
    if os.name != "nt":
        return []
    command = [
        "powershell", "-NoProfile", "-NonInteractive", "-Command",
        "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress",
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=4,
            creationflags=_windows_creationflags(),
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        payload = json.loads(result.stdout.strip())
        if isinstance(payload, str):
            payload = [payload]
        if isinstance(payload, list):
            return [str(x).strip() for x in payload if str(x).strip()]
    except Exception:
        pass
    return []


def _nvidia_snapshots() -> list[dict[str, Any]]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return []
    try:
        result = subprocess.run(
            [
                exe,
                "--query-gpu=index,name,utilization.gpu,temperature.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=3,
            creationflags=_windows_creationflags(),
        )
        if result.returncode != 0:
            return []
        items: list[dict[str, Any]] = []
        for line in result.stdout.splitlines():
            parts = [x.strip() for x in line.split(",")]
            if len(parts) < 6:
                continue
            index, name = parts[0], parts[1]
            try:
                load, temp, used, total = map(float, parts[2:6])
            except Exception:
                continue
            items.append({
                "id": f"nvidia:{index}", "name": name, "kind": "nvidia",
                "load": load, "temp": temp, "used": used, "total": total,
            })
        return items
    except Exception:
        return []


def detect_gpus() -> list[dict[str, str]]:
    """Detect all video controllers. NVIDIA gets live sensors; Intel/AMD are still selectable."""
    result: list[dict[str, str]] = []
    seen_names: set[str] = set()
    for item in _nvidia_snapshots():
        name = str(item.get("name", "GPU")).strip()
        result.append({"id": str(item["id"]), "name": name, "kind": "nvidia"})
        seen_names.add(name.casefold())

    for idx, name in enumerate(_discover_windows_gpu_names()):
        if name.casefold() in seen_names:
            continue
        stable = hashlib.sha1(name.encode("utf-8", "ignore")).hexdigest()[:10]
        result.append({"id": f"win:{idx}:{stable}", "name": name, "kind": "generic"})
        seen_names.add(name.casefold())
    return result


class MetricCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(13, 9, 13, 9)
        layout.setSpacing(4)
        self.title = QLabel(title)
        self.title.setObjectName("metricTitle")
        self.value = QLabel("—")
        self.value.setWordWrap(True)
        self.value.setObjectName("metricValue")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(7)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.bar)

    def update_value(self, text: str, percent: float | None = None):
        self.value.setText(text)
        self.bar.setVisible(percent is not None)
        if percent is not None:
            self.bar.setValue(max(0, min(100, int(percent))))


class MonitorSettingsDialog(QDialog):
    def __init__(self, parent, disks: list[dict[str, str]], gpus: list[dict[str, str]], config: dict):
        super().__init__(parent)
        self.setWindowTitle("Что показывать в Dashboard")
        self.setMinimumWidth(480)
        self.disks = disks
        self.gpus = gpus
        self.config = dict(config)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(10)

        title = QLabel("Dashboard Pro")
        title.setObjectName("pageTitle")
        sub = QLabel("Оставь только те показатели, которые нужны. Настройка сохраняется в AppData.")
        sub.setWordWrap(True)
        sub.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(sub)

        self.simple: dict[str, QCheckBox] = {}
        for key, label in (
            ("show_cpu", "CPU"),
            ("show_ram", "RAM"),
            ("show_network", "Сеть"),
            ("show_platforms", "Выбранные стрим-платформы"),
            ("show_media_queue", "Очередь медиаплеера"),
            ("show_background_music", "Фоновая музыка"),
        ):
            cb = QCheckBox(label)
            cb.setChecked(bool(config.get(key, True)))
            self.simple[key] = cb
            root.addWidget(cb)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine); root.addWidget(sep)
        self.all_disks = QCheckBox("Автоматически показывать все подключённые диски")
        self.all_disks.setChecked(config.get("disk_mode", "all") == "all")
        root.addWidget(self.all_disks)
        selected_disks = {str(x) for x in config.get("disks", [])}
        self.disk_checks: dict[str, QCheckBox] = {}
        for disk in disks:
            cb = QCheckBox(f"{disk['title']}   ({disk['mount']})")
            cb.setChecked(self.all_disks.isChecked() or disk["id"] in selected_disks)
            self.disk_checks[disk["id"]] = cb
            root.addWidget(cb)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine); root.addWidget(sep2)
        self.all_gpus = QCheckBox("Автоматически показывать все найденные GPU")
        self.all_gpus.setChecked(config.get("gpu_mode", "all") == "all")
        root.addWidget(self.all_gpus)
        selected_gpus = {str(x) for x in config.get("gpus", [])}
        self.gpu_checks: dict[str, QCheckBox] = {}
        if gpus:
            for gpu in gpus:
                cb = QCheckBox(gpu["name"])
                cb.setChecked(self.all_gpus.isChecked() or gpu["id"] in selected_gpus)
                self.gpu_checks[gpu["id"]] = cb
                root.addWidget(cb)
        else:
            msg = QLabel("GPU пока не обнаружены. После перезапуска список обновится автоматически.")
            msg.setWordWrap(True); msg.setObjectName("cardText"); root.addWidget(msg)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def result_config(self) -> dict:
        data = dict(self.config)
        for key, cb in self.simple.items():
            data[key] = cb.isChecked()
        data["disk_mode"] = "all" if self.all_disks.isChecked() else "custom"
        data["disks"] = [key for key, cb in self.disk_checks.items() if cb.isChecked()]
        data["gpu_mode"] = "all" if self.all_gpus.isChecked() else "custom"
        data["gpus"] = [key for key, cb in self.gpu_checks.items() if cb.isChecked()]
        return data


class SystemMonitorPanel(QFrame):
    def __init__(self, theme: dict):
        super().__init__()
        self.setObjectName("monitorPanel")
        self.theme = theme
        self._last_net = None
        self._last_time = time.monotonic()
        self.disks = detect_disks()
        self.gpus = detect_gpus()
        self.config = settings.load("monitor", force=True)
        self.cards: dict[str, MetricCard] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 14, 12, 14)
        root.setSpacing(8)

        header = QHBoxLayout()
        labels = QVBoxLayout(); labels.setSpacing(0)
        heading = QLabel("DASHBOARD PRO"); heading.setObjectName("panelHeading")
        subtitle = QLabel("Система • диски • GPU • стрим")
        subtitle.setObjectName("metricTitle")
        labels.addWidget(heading); labels.addWidget(subtitle)
        self.settings_button = QPushButton("⚙")
        self.settings_button.setToolTip("Выбрать, что показывать")
        self.settings_button.setFixedSize(34, 34)
        self.settings_button.clicked.connect(self.open_settings)
        header.addLayout(labels, 1); header.addWidget(self.settings_button)
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("dashboardScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.host = QWidget(); self.host.setObjectName("dashboardHost")
        self.cards_layout = QVBoxLayout(self.host)
        self.cards_layout.setContentsMargins(0, 2, 4, 2)
        self.cards_layout.setSpacing(8)
        self.scroll.setWidget(self.host)
        root.addWidget(self.scroll, 1)

        self._rebuild_cards()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(int(self.config.get("refresh_ms", 1500)))
        self.refresh()

    def _selected_disk_ids(self) -> set[str]:
        if self.config.get("disk_mode", "all") == "all":
            return {d["id"] for d in self.disks}
        return {str(x) for x in self.config.get("disks", [])}

    def _selected_gpu_ids(self) -> set[str]:
        if self.config.get("gpu_mode", "all") == "all":
            return {g["id"] for g in self.gpus}
        return {str(x) for x in self.config.get("gpus", [])}

    def _add_card(self, key: str, title: str):
        card = MetricCard(title)
        self.cards[key] = card
        self.cards_layout.addWidget(card)

    def _clear_layout(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _rebuild_cards(self):
        self._clear_layout()
        self.cards = {}
        if self.config.get("show_cpu", True): self._add_card("cpu", "CPU")
        if self.config.get("show_ram", True): self._add_card("ram", "RAM")
        for gpu in self.gpus:
            if gpu["id"] in self._selected_gpu_ids():
                self._add_card(f"gpu:{gpu['id']}", f"GPU • {gpu['name']}")
        for disk in self.disks:
            if disk["id"] in self._selected_disk_ids():
                self._add_card(f"disk:{disk['id']}", disk["title"])
        if self.config.get("show_network", True): self._add_card("net", "Сеть")
        if self.config.get("show_platforms", True): self._add_card("platforms", "Стрим-платформы")
        if self.config.get("show_media_queue", True): self._add_card("queue", "Очередь медиаплеера")
        if self.config.get("show_background_music", True): self._add_card("music", "Фоновая музыка")
        self.cards_layout.addStretch(1)

    def open_settings(self):
        self.disks = detect_disks()
        self.gpus = detect_gpus()
        dialog = MonitorSettingsDialog(self, self.disks, self.gpus, self.config)
        if dialog.exec() == QDialog.Accepted:
            self.config = dialog.result_config()
            settings.save("monitor", self.config)
            self.timer.setInterval(int(self.config.get("refresh_ms", 1500)))
            self._rebuild_cards()
            self.refresh()

    def refresh(self):
        if psutil is not None:
            self._refresh_system()
        elif "cpu" in self.cards:
            self.cards["cpu"].update_value("Установи psutil")
        self._refresh_gpu()
        self._refresh_stream_media()

    def _refresh_system(self):
        if "cpu" in self.cards:
            cpu = psutil.cpu_percent(interval=None)
            self.cards["cpu"].update_value(f"{cpu:.0f}%", cpu)
        if "ram" in self.cards:
            ram = psutil.virtual_memory()
            self.cards["ram"].update_value(f"{ram.used / 2**30:.1f} / {ram.total / 2**30:.1f} ГБ", ram.percent)

        for disk in self.disks:
            key = f"disk:{disk['id']}"
            if key not in self.cards:
                continue
            try:
                usage = psutil.disk_usage(disk["mount"])
                used = usage.used / 2**30
                total = usage.total / 2**30
                free = usage.free / 2**30
                self.cards[key].update_value(f"{used:.0f}/{total:.0f} ГБ • свободно {free:.0f} ГБ", usage.percent)
            except Exception:
                self.cards[key].update_value("Диск временно недоступен")

        if "net" in self.cards:
            now = time.monotonic(); net = psutil.net_io_counters()
            if self._last_net is not None:
                dt = max(0.1, now - self._last_time)
                down = (net.bytes_recv - self._last_net.bytes_recv) / dt / 2**20
                up = (net.bytes_sent - self._last_net.bytes_sent) / dt / 2**20
                self.cards["net"].update_value(f"↓ {down:.2f}  ↑ {up:.2f} МБ/с")
            else:
                self.cards["net"].update_value("Расчёт скорости…")
            self._last_net, self._last_time = net, now

    def _refresh_gpu(self):
        selected = self._selected_gpu_ids()
        nvidia = {str(item["id"]): item for item in _nvidia_snapshots()}
        for gpu in self.gpus:
            if gpu["id"] not in selected:
                continue
            key = f"gpu:{gpu['id']}"
            card = self.cards.get(key)
            if card is None:
                continue
            if gpu["id"] in nvidia:
                item = nvidia[gpu["id"]]
                total = float(item.get("total", 0) or 0)
                used = float(item.get("used", 0) or 0)
                text = f"{item['load']:.0f}% • {item['temp']:.0f}°C"
                if total > 0:
                    text += f" • {used/1024:.1f}/{total/1024:.1f} ГБ"
                card.update_value(text, float(item["load"]))
            else:
                card.update_value("Обнаружена • датчики загрузки недоступны")

    def _refresh_stream_media(self):
        if "platforms" in self.cards:
            stream = settings.load("stream")
            names = [("twitch", "Twitch"), ("youtube", "YouTube"), ("vk", "VK"), ("kick", "Kick")]
            selected = [name for key, name in names if stream.get("platforms", {}).get(key)]
            self.cards["platforms"].update_value(" • ".join(selected) if selected else "Не выбраны")

        if "queue" in self.cards:
            try:
                from .runtime import get_runtime
                snap = get_runtime().queue.snapshot()
                current = snap.get("current") or {}
                qlen = int(snap.get("queue_length", 0) or 0)
                title = str(current.get("title", "")).strip()
                text = f"В очереди: {qlen}"
                if title:
                    text += f" • сейчас: {title[:42]}"
                self.cards["queue"].update_value(text)
            except Exception:
                self.cards["queue"].update_value("Состояние пока недоступно")

        if "music" in self.cards:
            try:
                from ..player.background_music import background_music
                snap = background_music.snapshot()
                current = snap.get("current") or {}
                if current:
                    state = "пауза" if snap.get("paused") else ("играет" if snap.get("playing") else "стоп")
                    title = str(current.get("title", "Без названия"))
                    self.cards["music"].update_value(f"{title[:46]} • {state}")
                else:
                    self.cards["music"].update_value("Трек не выбран")
            except Exception:
                self.cards["music"].update_value("Состояние пока недоступно")
