from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from tkinter import Menu

import customtkinter as ctk

from ...core.event_log import log
from ...core.vlc_setup import ensure_vlc_installed
from ...player.engine import PlayerEngine
from ...player.queue_manager import QueueItem, QueueManager
from ...player.web_server import PlayerWebServer
from ...player.background_music import background_music
from ...services import yandex_music


class MediaPlayerPage(ctk.CTkFrame):
    """Современная вкладка медиаплеера с VLC, очередью и API Streamer.bot."""

    def __init__(self, parent, context):
        theme = context["theme"]
        self.colors = theme["colors"]
        self.config = context["player_cfg"]
        super().__init__(parent, fg_color="transparent")

        self.port = int(self.config.get("port", 5000))
        self.player_state = {"url": "", "paused": False, "stopped": False, "time": 0}
        self.queue = QueueManager(self.config)
        self.engine: PlayerEngine | None = None
        self.is_seeking = False
        self.manual_stop = False
        self.destroyed = False
        self.queue_line_targets: dict[int, tuple[str, int | None]] = {}
        self.play_in_progress = False
        self._resolve_token = 0
        self._shutdown_done = False
        self.last_state_save = 0.0
        self._yandex_paused_by_player = False
        self._background_paused_by_player = False

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_player_panel()
        self._build_queue_panel()

        self.status_url = f"http://127.0.0.1:{self.port}/status"
        self.player_url = f"http://127.0.0.1:{self.port}/player"
        self.web_server = PlayerWebServer(
            self.queue,
            self.config,
            self.player_state,
            lambda: self.after(0, self.on_queue_changed),
        )
        self.web_server.start()

        self.after(250, self._init_engine)
        self.after(900, self.check_server)
        self.after(1000, self._update_loop)
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.refresh_queue()

    def _card_color(self) -> str:
        return self.colors.get("card", self.colors.get("panel", "#22252b"))

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=self._card_color())
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 6))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Медиаплеер заказов",
            font=("Arial", 20, "bold"),
            text_color=self.colors["text"],
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 2))

        self.server_status = ctk.CTkLabel(
            header,
            text=f"● API запускается на порту {self.port}",
            text_color=self.colors.get("warning", "#f1c40f"),
            font=("Arial", 12, "bold"),
        )
        self.server_status.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

        links = ctk.CTkFrame(header, fg_color="transparent")
        links.grid(row=0, column=1, rowspan=2, sticky="e", padx=12)
        ctk.CTkButton(links, text="API /status", width=105, command=lambda: webbrowser.open(self.status_url)).pack(
            side="left", padx=4
        )
        ctk.CTkButton(links, text="OBS /player", width=105, command=lambda: webbrowser.open(self.player_url)).pack(
            side="left", padx=4
        )

    def _build_player_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color=self._card_color())
        panel.grid(row=1, column=0, sticky="nsew", padx=(8, 5), pady=(6, 8))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=1)

        self.video_frame = ctk.CTkFrame(panel, fg_color="#000000", corner_radius=10)
        self.video_frame.grid(row=0, column=0, sticky="nsew", padx=14, pady=(14, 8))

        self.now_title = ctk.CTkLabel(
            panel,
            text="Сейчас ничего не играет",
            font=("Arial", 16, "bold"),
            text_color=self.colors["text"],
            anchor="w",
        )
        self.now_title.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 0))

        self.now_user = ctk.CTkLabel(
            panel,
            text="Очередь ожидает заказов",
            font=("Arial", 12),
            text_color=self.colors.get("muted_text", self.colors["text"]),
            anchor="w",
        )
        self.now_user.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 5))

        seek_row = ctk.CTkFrame(panel, fg_color="transparent")
        seek_row.grid(row=3, column=0, sticky="ew", padx=14, pady=2)
        seek_row.grid_columnconfigure(0, weight=1)
        self.seek_slider = ctk.CTkSlider(seek_row, from_=0, to=100, command=self.seek)
        self.seek_slider.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.seek_slider.set(0)
        self.time_label = ctk.CTkLabel(
            seek_row,
            text="00:00 / 00:00",
            width=105,
            font=("Consolas", 12, "bold"),
            text_color=self.colors.get("muted_text", self.colors["text"]),
        )
        self.time_label.grid(row=0, column=1)

        controls = ctk.CTkFrame(panel, fg_color="transparent")
        controls.grid(row=4, column=0, sticky="ew", padx=10, pady=8)
        self.pause_button = ctk.CTkButton(controls, text="⏸ Пауза", width=100, command=self.toggle_pause)
        self.pause_button.pack(side="left", padx=4)
        self.stop_button = ctk.CTkButton(controls, text="⏹ Стоп", width=90, command=self.toggle_stop)
        self.stop_button.pack(side="left", padx=4)
        ctk.CTkButton(controls, text="⏭ Скип", width=90, command=self.skip).pack(side="left", padx=4)
        ctk.CTkLabel(controls, text="🔊", text_color=self.colors["text"]).pack(side="right", padx=(6, 2))
        self.volume_slider = ctk.CTkSlider(controls, width=145, from_=0, to=100, command=self.set_volume)
        self.volume_slider.pack(side="right", padx=4)
        self.volume_slider.set(int(self.config.get("volume", 30)))

        test = ctk.CTkFrame(panel, fg_color="transparent")
        test.grid(row=5, column=0, sticky="ew", padx=14, pady=(2, 14))
        test.grid_columnconfigure(1, weight=1)
        self.user_entry = ctk.CTkEntry(test, width=120)
        self.user_entry.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        self.user_entry.insert(0, "Merzo4")
        self.query_entry = ctk.CTkEntry(test, placeholder_text="Ссылка YouTube или название трека")
        self.query_entry.grid(row=0, column=1, padx=6, sticky="ew")
        ctk.CTkButton(test, text="Добавить", width=95, command=self.add_test_order).grid(row=0, column=2, padx=(6, 0))

        self.result_label = ctk.CTkLabel(
            panel,
            text="",
            justify="left",
            anchor="w",
            wraplength=700,
            text_color=self.colors.get("muted_text", self.colors["text"]),
        )
        self.result_label.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 10))

        if bool(self.config.get("yandex_enabled", True)):
            yrow = ctk.CTkFrame(panel, fg_color="transparent")
            yrow.grid(row=7, column=0, sticky="ew", padx=14, pady=(0, 12))
            ctk.CTkLabel(yrow, text="Яндекс Музыка:", text_color=self.colors["text"]).pack(side="left", padx=(0, 8))
            ctk.CTkButton(yrow, text="Открыть", width=75, command=yandex_music.launch).pack(side="left", padx=3)
            ctk.CTkButton(yrow, text="⏮", width=45, command=yandex_music.previous_track).pack(side="left", padx=3)
            ctk.CTkButton(yrow, text="⏯", width=45, command=yandex_music.play_pause).pack(side="left", padx=3)
            ctk.CTkButton(yrow, text="⏭", width=45, command=yandex_music.next_track).pack(side="left", padx=3)

    def _build_queue_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color=self._card_color())
        panel.grid(row=1, column=1, sticky="nsew", padx=(5, 8), pady=(6, 8))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            panel,
            text="Очередь заказов",
            font=("Arial", 17, "bold"),
            text_color=self.colors["text"],
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        self.queue_box = ctk.CTkTextbox(panel, font=("Arial", 13), state="disabled")
        self.queue_box.grid(row=1, column=0, sticky="nsew", padx=14, pady=6)
        self.queue_box._textbox.bind("<Button-3>", self.show_queue_menu, add="+")

        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="ew", padx=10, pady=(4, 12))
        ctk.CTkButton(buttons, text="Обновить", width=85, command=self.refresh_queue).pack(side="left", padx=3)
        ctk.CTkButton(buttons, text="Удалить первый", width=115, command=self.remove_first).pack(side="left", padx=3)
        ctk.CTkButton(buttons, text="Очистить", width=85, command=self.clear_queue).pack(side="left", padx=3)

        ctk.CTkLabel(
            panel,
            text=(
                "Streamer.bot Fetch URL:\n"
                f"http://127.0.0.1:{self.port}/add?user=%userName%&query=%rawInput%"
            ),
            justify="left",
            wraplength=390,
            font=("Consolas", 11),
            text_color=self.colors.get("muted_text", self.colors["text"]),
        ).grid(row=3, column=0, sticky="w", padx=16, pady=(0, 14))

    def _init_engine(self) -> None:
        if self.destroyed:
            return
        self._show_result("Проверка VLC...")

        def worker() -> None:
            ok, message = ensure_vlc_installed()
            if self.destroyed:
                return
            self.after(0, lambda: self._finish_engine_init(ok, message))

        threading.Thread(target=worker, name="VLCSetup", daemon=True).start()

    def _finish_engine_init(self, vlc_ready: bool, message: str) -> None:
        if self.destroyed:
            return
        self._show_result(message)
        if not vlc_ready:
            return
        self.video_frame.update_idletasks()
        self.engine = PlayerEngine(self.video_frame.winfo_id(), int(self.config.get("volume", 30)))
        if not self.engine.available:
            self._show_result(f"VLC установлен, но движок не подключился: {self.engine.last_error}")
            return
        if self.queue.current is not None:
            position = self.queue.resume_position_seconds
            self._show_result(
                f"Восстановлен незавершённый трек. Продолжение с {self._format_time(int(position * 1000))}."
            )
            self._play_item(self.queue.current, position)
        else:
            self._show_result("VLC готов. Первый заказ запустится автоматически.")
            self.start_next_if_needed()

    def _show_result(self, text: str) -> None:
        self.result_label.configure(text=text)

    def _get_json(self, url: str) -> dict:
        with urllib.request.urlopen(url, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))

    def add_test_order(self) -> None:
        query = self.query_entry.get().strip()
        user = self.user_entry.get().strip() or "Merzo4"
        if not query:
            self._show_result("Введите ссылку YouTube или название видео.")
            return
        url = f"http://127.0.0.1:{self.port}/add?" + urllib.parse.urlencode({"user": user, "query": query})
        self._show_result("Поиск видео и добавление в очередь...")

        def worker() -> None:
            try:
                data = self._get_json(url)
                text = data.get("message", json.dumps(data, ensure_ascii=False))
            except Exception as exc:
                text = f"Ошибка запроса: {exc}"
            self.after(0, lambda: self._show_result(text))
            self.after(0, self.on_queue_changed)

        threading.Thread(target=worker, daemon=True).start()

    def check_server(self) -> None:
        try:
            data = self._get_json(f"http://127.0.0.1:{self.port}/health")
            if data.get("ok"):
                self.server_status.configure(text=f"● API работает: 127.0.0.1:{self.port}", text_color="#2ecc71")
                return
        except Exception as exc:
            log("PLAYER UI", f"Проверка API: {exc}")
        self.server_status.configure(text=f"● API недоступен на порту {self.port}", text_color="#e74c3c")

    def on_queue_changed(self) -> None:
        self.refresh_queue()
        self.start_next_if_needed()

    def start_next_if_needed(self) -> None:
        if self.destroyed or self.manual_stop or not self.engine or not self.engine.available:
            return
        if self.queue.current is not None:
            return
        item = self.queue.pop_next()
        if item is not None:
            self._play_item(item)

    def _play_item(self, item: QueueItem, resume_seconds: float = 0.0) -> None:
        if not self.engine or not self.engine.available or self.play_in_progress:
            return

        self.play_in_progress = True
        self._resolve_token += 1
        token = self._resolve_token
        self._show_result(f"Подготовка видео: {item.title}")

        source = item.webpage_url or (f"https://www.youtube.com/watch?v={item.id}" if item.id else "")
        saved_url = item.url

        # Защита от зависания yt-dlp: через 15 секунд пробуем сохранённую прямую ссылку.
        def fallback() -> None:
            if self.destroyed or token != self._resolve_token or not self.play_in_progress:
                return
            if saved_url:
                log("PLAYER", "Обновление ссылки заняло слишком долго. Используется сохранённая ссылка.")
                self._resolve_token += 1
                self._start_resolved_item(item, saved_url, resume_seconds)
            else:
                self.play_in_progress = False
                self._show_result("Не удалось подготовить видео: ссылка отсутствует.")

        self.after(15000, fallback)

        def worker() -> None:
            fresh_url = saved_url
            error_text = ""
            if source:
                try:
                    import yt_dlp

                    options = {
                        "quiet": True,
                        "no_warnings": True,
                        "noplaylist": True,
                        "format": "best[ext=mp4]/best",
                        "socket_timeout": 12,
                        "retries": 1,
                        "extractor_retries": 1,
                    }
                    with yt_dlp.YoutubeDL(options) as ydl:
                        info = ydl.extract_info(source, download=False)
                    fresh_url = str(info.get("url") or fresh_url)
                    item.url = fresh_url
                    if info.get("webpage_url"):
                        item.webpage_url = str(info["webpage_url"])
                    self.queue.save_state(force=True)
                except Exception as exc:
                    error_text = str(exc)
                    log("PLAYER", f"Не удалось обновить ссылку видео: {exc}")

            def finish() -> None:
                if self.destroyed or token != self._resolve_token or not self.play_in_progress:
                    return
                if not fresh_url:
                    self.play_in_progress = False
                    self._show_result(
                        f"Не удалось подготовить видео{': ' + error_text if error_text else ''}."
                    )
                    return
                self._resolve_token += 1
                self._start_resolved_item(item, fresh_url, resume_seconds)

            try:
                self.after(0, finish)
            except Exception:
                pass

        threading.Thread(target=worker, name="ResolvePlayerURL", daemon=True).start()

    def _start_resolved_item(self, item: QueueItem, url: str, resume_seconds: float) -> None:
        self.play_in_progress = False
        if self.destroyed or not self.engine or not self.engine.available:
            return
        if self.engine.play(url):
            if background_music.playing and not background_music.paused and not self._background_paused_by_player:
                background_music.pause_toggle()
                self._background_paused_by_player = True
                log("BACKGROUND MUSIC", "Фоновая музыка поставлена на паузу из-за заказа зрителя.")
            if bool(self.config.get("auto_pause_yandex", True)) and not self._yandex_paused_by_player:
                try:
                    yandex_music.play_pause()
                    self._yandex_paused_by_player = True
                except Exception:
                    pass
            self.manual_stop = False
            self.player_state.update({"url": url, "paused": False, "stopped": False, "time": resume_seconds})
            self.pause_button.configure(text="⏸ Пауза")
            self.stop_button.configure(text="⏹ Стоп")
            log("PLAYER", f"Запущено: {item.title} — @{item.user}")
            self.refresh_queue()
            if resume_seconds > 1:
                self.after(1800, lambda: self._restore_position(resume_seconds))
            else:
                self.queue.save_state(position_seconds=0, paused=False, stopped=False, force=True)
        else:
            log("PLAYER", f"Не удалось запустить: {item.title}")
            self._show_result("VLC не смог открыть видео. Пробую следующий заказ.")
            self.queue.finish_current()
            self.after(500, self.start_next_if_needed)

    def _restore_position(self, seconds: float) -> None:
        if not self.engine or not self.engine.available or self.queue.current is None:
            return
        length = self.engine.length_ms()
        if length > 0:
            target = min(int(seconds * 1000), max(0, length - 1000))
            self.engine.player.set_time(target)
            self.queue.save_state(position_seconds=target / 1000.0, paused=False, stopped=False, force=True)
            self._show_result(f"Воспроизведение продолжено с {self._format_time(target)}.")

    def toggle_pause(self) -> None:
        if not self.engine or not self.engine.available or self.queue.current is None:
            return
        paused = self.engine.toggle_pause()
        self.player_state["paused"] = paused
        self.queue.save_state(position_seconds=self.engine.time_ms() / 1000.0, paused=paused, stopped=False, force=True)
        self.pause_button.configure(text="▶ Продолжить" if paused else "⏸ Пауза")

    def toggle_stop(self) -> None:
        if not self.engine or not self.engine.available or self.queue.current is None:
            return
        if not self.manual_stop:
            self.manual_stop = True
            self.engine.stop()
            self.player_state["stopped"] = True
            self.queue.save_state(position_seconds=self.engine.time_ms() / 1000.0, paused=False, stopped=True, force=True)
            self.stop_button.configure(text="▶ Сначала")
            self._show_result("Воспроизведение остановлено. Нажми «Сначала», чтобы запустить текущий трек заново.")
        else:
            current = self.queue.current
            self.manual_stop = False
            if current:
                self._play_item(current)

    def skip(self) -> None:
        if self.engine:
            self.engine.stop()
        previous = self.queue.finish_current()
        self.manual_stop = False
        self.player_state.update({"url": "", "paused": False, "stopped": False, "time": 0})
        if previous:
            log("PLAYER", f"Пропущено: {previous.title}")
        self.refresh_queue()
        self.after(300, self.start_next_if_needed)

    def seek(self, value: float) -> None:
        if self.is_seeking or not self.engine or self.queue.current is None:
            return
        self.engine.set_position_percent(float(value))
        self.after(250, lambda: self.queue.save_state(position_seconds=self.engine.time_ms() / 1000.0, force=True) if self.engine else None)

    def set_volume(self, value: float) -> None:
        if self.engine:
            self.engine.set_volume(value)

    def remove_first(self) -> None:
        removed = self.queue.remove(0)
        self._show_result(f"Удалено: {removed.title}" if removed else "Очередь уже пуста.")
        self.refresh_queue()

    def clear_queue(self) -> None:
        count = self.queue.clear()
        self._show_result(f"Очередь очищена. Удалено: {count}.")
        self.refresh_queue()

    def refresh_queue(self) -> None:
        snapshot = self.queue.snapshot()
        current = snapshot["current"]
        if current:
            self.now_title.configure(text=current["title"])
            self.now_user.configure(text=f"Заказал: @{current['user']}")
        else:
            self.now_title.configure(text="Сейчас ничего не играет")
            self.now_user.configure(text="Очередь ожидает заказов")

        lines: list[str] = []
        self.queue_line_targets = {}
        line_no = 1
        if current:
            current_lines = ["▶ СЕЙЧАС ИГРАЕТ", current["title"], f"@{current['user']}", "", "────────────", ""]
            lines.extend(current_lines)
            for mapped_line in range(line_no, line_no + 3):
                self.queue_line_targets[mapped_line] = ("current", None)
            line_no += len(current_lines)
        if snapshot["queue"]:
            for index, item in enumerate(snapshot["queue"]):
                item_lines = [f"#{index + 1} {item['title']}", f"@{item['user']}", ""]
                lines.extend(item_lines)
                self.queue_line_targets[line_no] = ("queue", index)
                self.queue_line_targets[line_no + 1] = ("queue", index)
                line_no += len(item_lines)
        elif current:
            lines.append("Следующих заказов нет.")
        else:
            lines.append("Очередь пуста.")

        self.queue_box.configure(state="normal")
        self.queue_box.delete("1.0", "end")
        self.queue_box.insert("end", "\n".join(lines))
        self.queue_box.configure(state="disabled")


    def show_queue_menu(self, event) -> str:
        try:
            index = self.queue_box._textbox.index(f"@{event.x},{event.y}")
            line = int(index.split(".")[0])
        except Exception:
            return "break"

        target = self.queue_line_targets.get(line)
        if target is None:
            return "break"

        kind, queue_index = target
        menu = Menu(self, tearoff=0)
        if kind == "current":
            menu.add_command(label="⏭ Скипнуть текущий трек", command=self.skip)
            menu.add_separator()
            menu.add_command(label="🚫 Заблокировать зрителя", command=self.block_current_user)
            menu.add_command(label="🎥 Заблокировать видео", command=self.block_current_video)
        else:
            assert queue_index is not None
            menu.add_command(label="❌ Удалить из очереди", command=lambda i=queue_index: self.remove_queue_item(i))
            menu.add_separator()
            menu.add_command(label="🚫 Заблокировать зрителя", command=lambda i=queue_index: self.block_queued_user(i))
            menu.add_command(label="🎥 Заблокировать видео", command=lambda i=queue_index: self.block_queued_video(i))
        menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def remove_queue_item(self, index: int) -> None:
        removed = self.queue.remove(index)
        self._show_result(f"Удалено из очереди: {removed.title}" if removed else "Заказ уже отсутствует.")
        self.refresh_queue()

    def block_current_user(self) -> None:
        current = self.queue.current
        if current is None:
            return
        removed = self.queue.block_user(current.user)
        self._show_result(f"Зритель @{current.user} заблокирован. Удалено будущих заказов: {removed}.")
        self.skip()

    def block_current_video(self) -> None:
        current = self.queue.current
        if current is None:
            return
        removed = self.queue.block_video(current.id)
        self._show_result(f"Видео заблокировано. Удалено повторов из очереди: {removed}.")
        self.skip()

    def block_queued_user(self, index: int) -> None:
        item = self.queue.get(index)
        if item is None:
            return
        removed = self.queue.block_user(item.user)
        self._show_result(f"Зритель @{item.user} заблокирован. Удалено заказов: {removed}.")
        self.refresh_queue()

    def block_queued_video(self, index: int) -> None:
        item = self.queue.get(index)
        if item is None:
            return
        removed = self.queue.block_video(item.id)
        self._show_result(f"Видео «{item.title}» заблокировано. Удалено заказов: {removed}.")
        self.refresh_queue()

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        total_seconds = max(0, int(milliseconds // 1000))
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}" if hours else f"{minutes:02}:{seconds:02}"

    def _update_loop(self) -> None:
        if self.destroyed:
            return
        try:
            if self.engine and self.engine.available:
                if self.queue.current is not None and not self.manual_stop:
                    current_ms = self.engine.time_ms()
                    length_ms = self.engine.length_ms()
                    self.player_state["time"] = current_ms / 1000.0
                    now = time.time()
                    if now - self.last_state_save >= 5.0:
                        self.last_state_save = now
                        self.queue.save_state(
                            position_seconds=current_ms / 1000.0,
                            paused=bool(self.player_state.get("paused", False)),
                            stopped=bool(self.player_state.get("stopped", False)),
                        )
                    self.time_label.configure(text=f"{self._format_time(current_ms)} / {self._format_time(length_ms)}")
                    if length_ms > 0:
                        self.is_seeking = True
                        self.seek_slider.set((current_ms / length_ms) * 100.0)
                        self.is_seeking = False
                    if self.engine.is_finished():
                        finished = self.queue.finish_current()
                        self.player_state.update({"url": "", "paused": False, "stopped": False, "time": 0})
                        if finished:
                            log("PLAYER", f"Завершено: {finished.title}")
                        self.refresh_queue()
                        if not self.queue.items and self._background_paused_by_player:
                            background_music.pause_toggle()
                            self._background_paused_by_player = False
                            log("BACKGROUND MUSIC", "Фоновая музыка продолжена после окончания очереди.")
                        if not self.queue.items and self._yandex_paused_by_player and bool(self.config.get("auto_resume_yandex", True)):
                            try:
                                yandex_music.play_pause()
                                self._yandex_paused_by_player = False
                            except Exception:
                                pass
                        self.after(350, self.start_next_if_needed)
                elif self.queue.current is None:
                    self.time_label.configure(text="00:00 / 00:00")
                    self.seek_slider.set(0)
                    self.start_next_if_needed()
        except Exception as exc:
            log("PLAYER UI", f"Ошибка цикла плеера: {exc}")
        self.after(500, self._update_loop)

    def shutdown(self) -> None:
        """Корректно останавливает VLC и OBS-источник, сохраняя очередь и позицию."""
        if self._shutdown_done:
            return
        self._shutdown_done = True

        position = 0.0
        if self.engine:
            try:
                position = self.engine.time_ms() / 1000.0
            except Exception:
                position = self.queue.resume_position_seconds

        try:
            self.queue.save_state(
                position_seconds=position,
                paused=bool(self.player_state.get("paused", False)),
                stopped=bool(self.player_state.get("stopped", False)),
                force=True,
            )
        except Exception:
            self.queue.save_state(force=True)

        # Очищаем только состояние OBS. Текущий трек остаётся сохранён в player_state.json.
        self.player_state.update({"url": "", "paused": False, "stopped": True, "time": position})
        self.destroyed = True
        self._resolve_token += 1
        self.play_in_progress = False

        if self.engine:
            try:
                self.engine.stop()
            except Exception:
                pass
            self.engine.release()
            self.engine = None

        log("PLAYER", "Плеер остановлен, очередь и позиция сохранены.")

    def _on_destroy(self, event) -> None:
        if event.widget is self:
            self.shutdown()
