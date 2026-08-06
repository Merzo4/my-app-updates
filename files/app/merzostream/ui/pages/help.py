from __future__ import annotations

import customtkinter as ctk

SECTIONS = {
"Быстрый старт": """1. Авторизуй нужные площадки во вкладке «Авторизация».\n2. В «Управлении трансляцией» выбери площадки, название и игру.\n3. Для заказов добавь в Streamer.bot адрес /add.\n4. Для видео в OBS создай Browser Source с адресом /player.\n5. Для фоновой музыки создай второй Browser Source с адресом /music.""",
"Управление трансляцией": """Меняет название и категорию на Twitch, YouTube, VK Video и Kick. Галочки определяют, какие площадки участвуют. Авторизация хранится в AppData и не сбрасывается при обновлении программы.""",
"Заказы зрителей": """Streamer.bot отправляет запрос на http://127.0.0.1:5000/add?user=%userName%&query=%rawInput%. Очередь хранит имя зрителя, название и ссылку. Правая кнопка по заказу позволяет удалить или заблокировать пользователя/видео.""",
"OBS — видео заказов": """Создай Browser Source с адресом http://127.0.0.1:5000/player. Это источник только для клипов и видеозаказов. При закрытии программы источник очищается.""",
"OBS — фоновая музыка": """Создай отдельный Browser Source с адресом http://127.0.0.1:5000/music. У этого источника нет изображения — только звук. В свойствах OBS включи «Управлять аудио через OBS», чтобы получить отдельный аудиоканал и не смешивать музыку с клипами.""",
"Фоновая музыка": """Добавляй локальные MP3/WAV во вкладке «Фоновая музыка». Лучше использовать YouTube Audio Library. Для треков с обязательной атрибуцией заполни автора и текст — программа соберёт готовый блок для описания YouTube.""",
"Настройки": """Разделы настроек раскрываются по нажатию. Кулдаун задаётся в минутах, минимальная длительность — в секундах, максимальная — в минутах. Изменения правил применяются к новым заказам.""",
"Файлы программы": """Настройки и авторизации находятся в %LOCALAPPDATA%\\MerzoStreamSuite. Фоновая музыка: music\\youtube_safe. История: data\\merzostream.db. Логи: logs. Эти данные не должны удаляться при обновлении приложения.""",
}

class HelpPage(ctk.CTkFrame):
    def __init__(self, parent, context):
        self.colors=context["theme"]["colors"]
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text="📘 Инструкция по MerzoStream Suite", font=("Arial", 22, "bold"), text_color=self.colors["text"]).grid(row=0,column=0,columnspan=2,sticky="w",padx=12,pady=(10,8))
        self.search=ctk.CTkEntry(self, placeholder_text="Поиск по инструкции"); self.search.grid(row=1,column=0,sticky="new",padx=(12,6),pady=6); self.search.bind("<KeyRelease>", lambda _e:self.refresh())
        self.nav=ctk.CTkScrollableFrame(self, width=230, fg_color=self.colors.get("card","#20242b")); self.nav.grid(row=2,column=0,sticky="nsew",padx=(12,6),pady=(0,12))
        self.body=ctk.CTkTextbox(self, wrap="word", font=("Arial",14)); self.body.grid(row=1,column=1,rowspan=2,sticky="nsew",padx=(6,12),pady=(6,12))
        self.current=next(iter(SECTIONS)); self.refresh()
    def refresh(self):
        query=self.search.get().strip().lower()
        for child in self.nav.winfo_children(): child.destroy()
        matches=[]
        for title,text in SECTIONS.items():
            if not query or query in title.lower() or query in text.lower(): matches.append((title,text))
        for title,_ in matches:
            ctk.CTkButton(self.nav,text=title,anchor="w",fg_color="transparent",command=lambda t=title:self.show(t)).pack(fill="x",pady=2)
        if query:
            self.body.configure(state="normal"); self.body.delete("1.0","end")
            self.body.insert("end","\n\n".join(f"{t}\n{'─'*len(t)}\n{x}" for t,x in matches) or "Ничего не найдено."); self.body.configure(state="disabled")
        else:self.show(self.current)
    def show(self,title):
        self.current=title; self.body.configure(state="normal"); self.body.delete("1.0","end"); self.body.insert("end",f"{title}\n\n{SECTIONS[title]}"); self.body.configure(state="disabled")
