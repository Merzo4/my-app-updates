from __future__ import annotations

import threading

import customtkinter as ctk

from ...core.event_log import log
from ...services.stream import StreamManager


class AIProducerPage(ctk.CTkFrame):
    def __init__(self, parent, context):
        super().__init__(parent, fg_color="transparent")
        self.context = context
        self.cfg = context["stream_cfg"]
        self.manager = StreamManager(self.cfg)

        ctk.CTkLabel(self, text="🤖 AI Producer", font=("Arial", 26, "bold")).pack(anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            self,
            text="Опиши будущий стрим. Любой вариант можно сразу отправить в поле названия.",
            font=("Arial", 13),
            text_color=context["theme"]["colors"].get("muted", "#aeb8c4"),
        ).pack(anchor="w", padx=24, pady=(0, 14))

        self.prompt = ctk.CTkEntry(self, height=44, placeholder_text="Например: SnowRunner, Вашингтон, тяжёлые грузы и грязь")
        self.prompt.pack(fill="x", padx=24, pady=8)
        self.generate_button = ctk.CTkButton(
            self, text="✨ Сгенерировать 25 названий", height=44, font=("Arial", 14, "bold"), command=self.generate
        )
        self.generate_button.pack(fill="x", padx=24, pady=8)
        self.results = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.results.pack(fill="both", expand=True, padx=20, pady=(8, 20))

    def generate(self):
        prompt = self.prompt.get().strip()
        if not prompt:
            log("AI", "Введите тему стрима.")
            return
        self.generate_button.configure(state="disabled", text="🧠 ИИ думает...")

        def job():
            titles, result = self.manager.groq.generate_titles(prompt)
            log("AI", result.message)
            self.after(0, lambda: self._show_results(titles, result.message))

        threading.Thread(target=job, daemon=True).start()

    def _show_results(self, titles: list[str], message: str):
        for widget in self.results.winfo_children():
            widget.destroy()
        if not titles:
            ctk.CTkLabel(self.results, text=f"❌ {message}", wraplength=700).pack(pady=20)
        for title in titles:
            row = ctk.CTkFrame(self.results)
            row.pack(fill="x", padx=4, pady=3)
            ctk.CTkLabel(row, text=title, anchor="w", justify="left", wraplength=700).pack(side="left", fill="x", expand=True, padx=12, pady=9)
            ctk.CTkButton(row, text="ВЗЯТЬ", width=72, command=lambda value=title: self.use_title(value)).pack(side="right", padx=10)
        self.generate_button.configure(state="normal", text="✨ Сгенерировать 25 названий")

    def use_title(self, title: str):
        self.cfg["title"] = title
        stream_page = self.context["app"].reload_page("stream")
        self.context["app"].show_page("stream")
        if hasattr(stream_page, "title_entry"):
            stream_page.title_entry.delete(0, "end")
            stream_page.title_entry.insert(0, title)
