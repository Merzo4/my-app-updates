import threading

import customtkinter as ctk
import requests

from ...core.config import save
from ...core.event_log import log
from ...core.paths import STREAM_CONFIG


class AITab(ctk.CTkFrame):
    def __init__(self, parent, cfg):
        super().__init__(parent, fg_color="transparent")
        self.cfg = cfg

        ctk.CTkLabel(self, text="🤖 AI Producer", font=("Arial", 26, "bold")).pack(anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            self,
            text="Опиши тему стрима — генератор предложит варианты названий.",
            font=("Arial", 13),
            text_color="#aeb8c4",
        ).pack(anchor="w", padx=24, pady=(0, 15))

        self.prompt = ctk.CTkEntry(self, height=44, placeholder_text="Например: SnowRunner, везу брёвна, застреваю в грязи")
        self.prompt.pack(fill="x", padx=24, pady=8)

        self.generate_button = ctk.CTkButton(
            self,
            text="✨ Сгенерировать 25 названий",
            height=44,
            font=("Arial", 14, "bold"),
            command=self.generate,
        )
        self.generate_button.pack(fill="x", padx=24, pady=8)

        self.results = ctk.CTkTextbox(self, font=("Segoe UI Emoji", 14))
        self.results.pack(fill="both", expand=True, padx=24, pady=(10, 24))

    def generate(self):
        prompt = self.prompt.get().strip()
        key = self.cfg.get("groq_key", "").strip()
        if not prompt:
            log("AI", "Введите тему стрима.")
            return
        if not key:
            log("AI", "В разделе Авторизация не заполнен Groq API Key.")
            return

        save(STREAM_CONFIG, self.cfg)
        self.generate_button.configure(state="disabled", text="ИИ генерирует...")
        threading.Thread(target=self._request, args=(prompt, key), daemon=True).start()

    def _request(self, prompt, key):
        try:
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Ты продюсер русскоязычных стримов. Выдай строго 25 коротких названий, "
                            "каждое с новой строки, без нумерации. Используй 1-2 подходящих эмодзи."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.75,
            }
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
                timeout=25,
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            self.after(0, lambda: self._show(text))
            log("AI", "Названия сгенерированы.")
        except Exception as exc:
            log("AI", f"Ошибка генерации: {exc}")
        finally:
            self.after(0, lambda: self.generate_button.configure(state="normal", text="✨ Сгенерировать 25 названий"))

    def _show(self, text):
        self.results.delete("1.0", "end")
        self.results.insert("1.0", text)
