from __future__ import annotations

import requests

from .common import ServiceResult


class GroqService:
    def __init__(self, config: dict):
        self.config = config

    def generate_titles(self, prompt: str) -> tuple[list[str], ServiceResult]:
        key = self.config.get("groq_key", "").strip()
        if not key:
            return [], ServiceResult.error("Не заполнен Groq API Key.")
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Ты продюсер русскоязычных игровых стримов. Выдай строго 25 "
                                "коротких цепляющих названий, каждое с новой строки, без нумерации. "
                                "Допускается 1-2 подходящих эмодзи."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.8,
                },
                timeout=30,
            )
            response.raise_for_status()
            raw = response.json()["choices"][0]["message"]["content"]
            titles = []
            for line in raw.splitlines():
                cleaned = line.strip().lstrip('0123456789.-*)#[]"\' ')
                if len(cleaned) > 4:
                    titles.append(cleaned)
            return titles[:25], ServiceResult.success(f"Сгенерировано вариантов: {min(len(titles), 25)}")
        except Exception as exc:
            return [], ServiceResult.error(str(exc))
