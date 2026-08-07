from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout

try:
    import psutil
except Exception:
    psutil = None


class MetricCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(5)
        self.title = QLabel(title)
        self.title.setObjectName("metricTitle")
        self.value = QLabel("—")
        self.value.setObjectName("metricValue")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.bar)

    def update_value(self, text: str, percent: float | None = None):
        self.value.setText(text)
        self.bar.setVisible(percent is not None)
        if percent is not None:
            self.bar.setValue(max(0, min(100, int(percent))))


class SystemMonitorPanel(QFrame):
    def __init__(self, theme: dict):
        super().__init__()
        self.setObjectName("monitorPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(10)
        heading = QLabel("МОНИТОРИНГ ПК")
        heading.setObjectName("panelHeading")
        layout.addWidget(heading)
        self.cards = {
            "cpu": MetricCard("CPU"), "gpu": MetricCard("GPU"),
            "ram": MetricCard("RAM"), "disk": MetricCard("Диск C:"),
            "net": MetricCard("Сеть"),
        }
        for card in self.cards.values():
            layout.addWidget(card)
        layout.addStretch(1)
        self._last_net = None
        self._last_time = time.monotonic()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(1500)
        self.refresh()

    def refresh(self):
        if psutil is None:
            self.cards["cpu"].update_value("Установи psutil")
            return
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage(str(Path.home().anchor or "C:\\"))
        self.cards["cpu"].update_value(f"{cpu:.0f}%", cpu)
        self.cards["ram"].update_value(f"{ram.used / 2**30:.1f} / {ram.total / 2**30:.1f} ГБ", ram.percent)
        self.cards["disk"].update_value(f"Свободно {disk.free / 2**30:.0f} ГБ", disk.percent)
        now = time.monotonic(); net = psutil.net_io_counters()
        if self._last_net is not None:
            dt = max(0.1, now - self._last_time)
            down = (net.bytes_recv - self._last_net.bytes_recv) / dt / 2**20
            up = (net.bytes_sent - self._last_net.bytes_sent) / dt / 2**20
            self.cards["net"].update_value(f"↓ {down:.2f}  ↑ {up:.2f} МБ/с")
        self._last_net, self._last_time = net, now
        self._refresh_gpu()

    def _refresh_gpu(self):
        exe = shutil.which("nvidia-smi")
        if not exe:
            self.cards["gpu"].update_value("NVIDIA не найдена")
            return
        try:
            result = subprocess.run([
                exe, "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits"
            ], capture_output=True, text=True, timeout=2, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            values = [x.strip() for x in result.stdout.splitlines()[0].split(",")]
            load, temp, used, total = map(float, values[:4])
            self.cards["gpu"].update_value(f"{load:.0f}% • {temp:.0f}°C • {used/1024:.1f}/{total/1024:.1f} ГБ", load)
        except Exception:
            self.cards["gpu"].update_value("Нет данных")
