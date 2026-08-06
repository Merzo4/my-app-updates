from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional

import customtkinter as ctk

try:
    import psutil
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "psutil", "--disable-pip-version-check", "--quiet"], check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    import psutil

from ...core.event_bus import event_bus


@dataclass
class GpuStats:
    name: str = "GPU"
    load: Optional[float] = None
    temperature: Optional[float] = None
    memory_used: Optional[float] = None
    memory_total: Optional[float] = None


class SystemMonitorPanel(ctk.CTkFrame):
    """Постоянная правая панель: ПК, текущий трек и последние события."""

    UPDATE_INTERVAL_MS = 1500

    def __init__(self, master, theme: dict):
        colors = theme["colors"]
        super().__init__(master, width=252, corner_radius=0, fg_color=colors.get("sidebar", colors["window"]), border_width=1, border_color=colors.get("border", "#3a414b"))
        self.theme = theme
        self.colors = colors
        self._running = True
        self._last_net = psutil.net_io_counters()
        self._last_net_time = time.monotonic()
        self._labels: dict[str, ctk.CTkLabel] = {}
        self._bars: dict[str, ctk.CTkProgressBar] = {}
        self._events: list[str] = []
        self._unsubscribe = event_bus.subscribe("log.created", self._on_log_event)
        self.grid_propagate(False)
        self._build()
        self.after(250, self._refresh)

    def _build(self):
        c = self.colors
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(14, 5))
        ctk.CTkLabel(header, text="Dashboard", font=("Arial", 16, "bold"), text_color=c["text"]).pack(side="left")
        ctk.CTkLabel(header, text="ВСЕГДА ВИДЕН", font=("Arial", 9, "bold"), text_color=c.get("success", "#34d399")).pack(side="right")

        self._metric("cpu", "CPU")
        self._metric("gpu", "GPU")
        self._metric("ram", "RAM")
        self._metric("disk", "Диск C:")

        network = self._card("Сеть")
        self._labels["network"] = ctk.CTkLabel(network, text="↓ 0 КБ/с   ↑ 0 КБ/с", font=("Arial", 11), text_color=c.get("accent_text", c["text"]))
        self._labels["network"].pack(anchor="w", padx=10, pady=(0, 9))

        gpu_details = self._card("Видеокарта")
        self._labels["gpu_details"] = ctk.CTkLabel(gpu_details, text="Получение данных...", wraplength=210, justify="left", font=("Arial", 10), text_color=c.get("muted_text", "#aeb8c4"))
        self._labels["gpu_details"].pack(anchor="w", padx=10, pady=(0, 9))

        playing = self._card("Сейчас играет")
        self._labels["playing"] = ctk.CTkLabel(playing, text="Нет активного заказа", wraplength=210, justify="left", font=("Arial", 10), text_color=c.get("muted_text", "#aeb8c4"))
        self._labels["playing"].pack(anchor="w", padx=10, pady=(0, 9))

        events = self._card("Последние события")
        self._labels["events"] = ctk.CTkLabel(events, text="Приложение запущено", wraplength=210, justify="left", anchor="nw", font=("Consolas", 9), text_color=c.get("muted_text", "#aeb8c4"))
        self._labels["events"].pack(fill="x", padx=10, pady=(0, 9))

    def _card(self, title: str):
        c = self.colors
        frame = ctk.CTkFrame(self, fg_color=c.get("card", c["window"]), corner_radius=10)
        frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(frame, text=title, font=("Arial", 11, "bold"), text_color=c["text"]).pack(anchor="w", padx=10, pady=(8, 3))
        return frame

    def _metric(self, key: str, title: str):
        c = self.colors
        frame = ctk.CTkFrame(self, fg_color=c.get("card", c["window"]), corner_radius=10)
        frame.pack(fill="x", padx=10, pady=5)
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(8, 3))
        ctk.CTkLabel(header, text=title, font=("Arial", 11, "bold"), text_color=c["text"]).pack(side="left")
        value = ctk.CTkLabel(header, text="—", font=("Arial", 10, "bold"), text_color=c.get("accent_text", c["text"]))
        value.pack(side="right")
        bar = ctk.CTkProgressBar(frame, height=7, progress_color=c.get("selected", "#1976c9"))
        bar.pack(fill="x", padx=10, pady=(0, 8)); bar.set(0)
        self._labels[key] = value; self._bars[key] = bar

    def _on_log_event(self, _event: str, payload: dict):
        module = payload.get("module", "APP")
        level = payload.get("level", "INFO")
        message = str(payload.get("message", ""))
        short = message if len(message) <= 44 else message[:41] + "..."
        self._events.append(f"[{level}] {module}: {short}")
        self._events = self._events[-5:]
        if self.winfo_exists():
            self.after(0, lambda: self._labels["events"].configure(text="\n".join(self._events)))
        if module == "PLAYER" and message.startswith("Запущено:"):
            self.after(0, lambda value=message[len("Запущено:"):].strip(): self._labels["playing"].configure(text=value))

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(100.0, float(value)))

    @staticmethod
    def _format_rate(value: float) -> str:
        return f"{value / (1024 ** 2):.1f} МБ/с" if value >= 1024 ** 2 else f"{value / 1024:.0f} КБ/с"

    def _read_gpu(self) -> GpuStats:
        try:
            result = subprocess.run(["nvidia-smi", "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=1.2, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode != 0 or not result.stdout.strip():
                return GpuStats()
            parts = [part.strip() for part in result.stdout.splitlines()[0].split(",")]
            return GpuStats(parts[0], float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
        except Exception:
            return GpuStats()

    def _set_metric(self, key: str, percent: float, text: str):
        percent = self._clamp(percent); self._labels[key].configure(text=text); self._bars[key].set(percent / 100.0)

    def _refresh(self):
        if not self._running or not self.winfo_exists():
            return
        try:
            cpu = psutil.cpu_percent(interval=None); self._set_metric("cpu", cpu, f"{cpu:.0f}%")
            memory = psutil.virtual_memory(); used_gb = (memory.total - memory.available) / (1024 ** 3); total_gb = memory.total / (1024 ** 3)
            self._set_metric("ram", memory.percent, f"{used_gb:.1f}/{total_gb:.0f} ГБ")
            disk = psutil.disk_usage("C:\\"); self._set_metric("disk", disk.percent, f"{disk.percent:.0f}% · {disk.free / (1024 ** 3):.0f} ГБ")
            gpu = self._read_gpu()
            if gpu.load is None:
                self._labels["gpu"].configure(text="нет данных"); self._bars["gpu"].set(0); self._labels["gpu_details"].configure(text="nvidia-smi недоступен")
            else:
                self._set_metric("gpu", gpu.load, f"{gpu.load:.0f}% · {gpu.temperature:.0f}°C")
                vram = f"VRAM {gpu.memory_used / 1024:.1f}/{gpu.memory_total / 1024:.1f} ГБ" if gpu.memory_total else ""
                self._labels["gpu_details"].configure(text=f"{gpu.name}\n{vram}")
            current = psutil.net_io_counters(); now = time.monotonic(); elapsed = max(now - self._last_net_time, .1)
            down = max(0, current.bytes_recv - self._last_net.bytes_recv) / elapsed; up = max(0, current.bytes_sent - self._last_net.bytes_sent) / elapsed
            self._labels["network"].configure(text=f"↓ {self._format_rate(down)}   ↑ {self._format_rate(up)}")
            self._last_net, self._last_net_time = current, now
        except Exception as exc:
            self._labels["network"].configure(text=f"Ошибка: {exc}")
        finally:
            if self._running and self.winfo_exists():
                self.after(self.UPDATE_INTERVAL_MS, self._refresh)

    def shutdown(self):
        self._running = False
        try:
            self._unsubscribe()
        except Exception:
            pass
