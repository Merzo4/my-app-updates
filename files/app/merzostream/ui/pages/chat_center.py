from __future__ import annotations

import datetime as dt
import threading
import urllib.parse
import urllib.request
import webbrowser

import customtkinter as ctk
from tkinter import messagebox

from ...chat.manager import chat_manager
from ...core.event_log import log


PLATFORMS = ["all", "twitch", "youtube", "vk", "kick", "rutony", "streamerbot", "other"]


class ChatCenterPage(ctk.CTkFrame):
    def __init__(self, parent, context):
        self.context = context
        self.colors = context["theme"]["colors"]
        self.port = int(context.get("chat_port", 5001))
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.platform_var = ctk.StringVar(value="all")
        self._build_header()
        self._build_feed()
        self._build_test_tools()
        chat_manager.subscribe(self._on_message)
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.refresh()

    def _card(self) -> str:
        return self.colors.get("card", self.colors.get("panel", "#20242b"))

    def _build_header(self) -> None:
        frame = ctk.CTkFrame(self, fg_color=self._card())
        frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 5))
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text="Единый чат", font=("Arial", 20, "bold"), text_color=self.colors["text"]).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(frame, text="Twitch • YouTube • VK • Kick • RutonyChat • Streamer.bot", text_color=self.colors.get("muted_text", self.colors["text"])).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))
        buttons = ctk.CTkFrame(frame, fg_color="transparent")
        buttons.grid(row=0, column=1, rowspan=2, sticky="e", padx=12)
        ctk.CTkButton(buttons, text="Открыть OBS-чат", command=lambda: webbrowser.open(f"http://127.0.0.1:{self.port}/chat")).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Обновить", width=90, command=self.refresh).pack(side="left", padx=4)

    def _build_feed(self) -> None:
        frame = ctk.CTkFrame(self, fg_color=self._card())
        frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=5)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        tools = ctk.CTkFrame(frame, fg_color="transparent")
        tools.grid(row=0, column=0, sticky="ew", padx=12, pady=10)
        ctk.CTkLabel(tools, text="Площадка:", text_color=self.colors["text"]).pack(side="left", padx=(0, 6))
        ctk.CTkComboBox(tools, values=PLATFORMS, variable=self.platform_var, width=150, command=lambda _v: self.refresh()).pack(side="left")
        ctk.CTkButton(tools, text="Очистить экран", width=120, command=self.clear_screen).pack(side="right", padx=4)
        ctk.CTkButton(tools, text="Очистить историю", width=130, fg_color="#a33a3a", hover_color="#7f2f2f", command=self.clear_history).pack(side="right", padx=4)
        self.feed = ctk.CTkTextbox(frame, font=("Consolas", 13), state="disabled")
        self.feed.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _build_test_tools(self) -> None:
        frame = ctk.CTkFrame(self, fg_color=self._card())
        frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(5, 8))
        frame.grid_columnconfigure(2, weight=1)
        self.test_platform = ctk.CTkComboBox(frame, values=PLATFORMS[1:], width=130)
        self.test_platform.set("twitch")
        self.test_platform.grid(row=0, column=0, padx=(12, 5), pady=12)
        self.test_user = ctk.CTkEntry(frame, width=140)
        self.test_user.insert(0, "Merzo4")
        self.test_user.grid(row=0, column=1, padx=5, pady=12)
        self.test_message = ctk.CTkEntry(frame, placeholder_text="Тестовое сообщение")
        self.test_message.grid(row=0, column=2, sticky="ew", padx=5, pady=12)
        ctk.CTkButton(frame, text="Добавить", width=90, command=self.add_test).grid(row=0, column=3, padx=(5, 12), pady=12)
        info = (
            f"OBS Browser Source: http://127.0.0.1:{self.port}/chat\n"
            f"Streamer.bot/RutonyChat: http://127.0.0.1:{self.port}/chat/add?platform=Twitch&user=%userName%&message=%rawInput%"
        )
        ctk.CTkLabel(frame, text=info, justify="left", anchor="w", font=("Consolas", 11), wraplength=1050, text_color=self.colors.get("muted_text", self.colors["text"])).grid(row=1, column=0, columnspan=4, sticky="w", padx=12, pady=(0, 12))

    def _on_message(self, _payload: dict) -> None:
        try:
            self.after(0, self.refresh)
        except Exception:
            pass

    def refresh(self) -> None:
        selected = self.platform_var.get()
        platforms = None if selected == "all" else {selected}
        items = chat_manager.snapshot(200, platforms)
        lines = []
        for item in items:
            stamp = dt.datetime.fromtimestamp(float(item["created_at"])).strftime("%H:%M:%S")
            lines.append(f"[{stamp}] [{item['platform'].upper():11}] {item['user']}: {item['message']}")
        self.feed.configure(state="normal")
        self.feed.delete("1.0", "end")
        self.feed.insert("1.0", "\n".join(lines) if lines else "Сообщений пока нет.")
        self.feed.see("end")
        self.feed.configure(state="disabled")

    def add_test(self) -> None:
        try:
            chat_manager.add(self.test_platform.get(), self.test_user.get(), self.test_message.get())
            self.test_message.delete(0, "end")
        except Exception as exc:
            messagebox.showerror("Единый чат", str(exc))

    def clear_screen(self) -> None:
        chat_manager.clear(False)
        self.refresh()

    def clear_history(self) -> None:
        if messagebox.askyesno("Единый чат", "Удалить всю сохранённую историю чата?"):
            chat_manager.clear(True)
            self.refresh()

    def _on_destroy(self, event) -> None:
        if event.widget is self:
            chat_manager.unsubscribe(self._on_message)

    def shutdown(self) -> None:
        chat_manager.unsubscribe(self._on_message)
