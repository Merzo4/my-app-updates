from __future__ import annotations

import datetime
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ...core.content import load_theme_index
from ...core.database import database
from ...core.settings_manager import settings
from ...core.yt_dlp_tools import current_version, update as update_ytdlp
from ...player.background_music import MUSIC_DIR


class AccordionSection(ctk.CTkFrame):
    def __init__(self, parent, title: str, subtitle: str, colors: dict, opened: bool = False):
        super().__init__(parent, fg_color=colors.get("card", "#20242b"), corner_radius=14,
                         border_width=1, border_color=colors.get("border", "#353941"))
        self.colors = colors
        self.opened = opened
        self.button = ctk.CTkButton(self, text="", anchor="w", height=54, corner_radius=12,
                                    fg_color="transparent", hover_color=colors.get("hover", "#2b3038"),
                                    text_color=colors.get("text", "#fff"), font=("Arial", 16, "bold"),
                                    command=self.toggle)
        self.button.pack(fill="x", padx=6, pady=6)
        self.subtitle = subtitle
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self._refresh()

    def _refresh(self):
        arrow = "▼" if self.opened else "▶"
        self.button.configure(text=f"{arrow}  {self.button.cget('text').split('  ',1)[-1] if '  ' in self.button.cget('text') else ''}")
        if self.opened:
            self.body.pack(fill="x", padx=12, pady=(0, 12))
        else:
            self.body.pack_forget()

    @classmethod
    def create(cls, parent, title, subtitle, colors, opened=False):
        obj = cls(parent, title, subtitle, colors, opened)
        obj.title = title
        obj.button.configure(text=("▼" if opened else "▶") + "  " + title)
        if subtitle:
            ctk.CTkLabel(obj.body, text=subtitle, justify="left", wraplength=950,
                         text_color=colors.get("muted_text", colors.get("text", "#fff"))).pack(fill="x", anchor="w", padx=6, pady=(0, 8))
        return obj

    def toggle(self):
        self.opened = not self.opened
        self.button.configure(text=("▼" if self.opened else "▶") + "  " + self.title)
        if self.opened: self.body.pack(fill="x", padx=12, pady=(0, 12))
        else: self.body.pack_forget()


class SettingsPage(ctk.CTkScrollableFrame):
    def __init__(self, parent, context):
        self.context=context; self.app=context["app"]; self.app_cfg=settings.load("app"); self.player_cfg=settings.load("player")
        self.theme=context["theme"]; self.colors=self.theme["colors"]
        super().__init__(parent, fg_color="transparent")
        self.entries={}; self.switches={}; self.textboxes={}
        ctk.CTkLabel(self, text="⚙ Настройки", font=("Arial",24,"bold"), text_color=self.colors.get("text","#fff")).pack(anchor="w",padx=20,pady=(12,4))
        ctk.CTkLabel(self, text="Нажимай на заголовок раздела, чтобы раскрыть его. Под каждой группой есть пояснение.",
                     text_color=self.colors.get("muted_text",self.colors.get("text","#fff"))).pack(anchor="w",padx=20,pady=(0,12))
        self._build_theme(); self._build_limits(); self._build_search(); self._build_blocks(); self._build_yandex(); self._build_background(); self._build_history(); self._build_backup()

    def _section(self,title,subtitle,opened=False):
        sec=AccordionSection.create(self,title,subtitle,self.colors,opened); sec.pack(fill="x",padx=20,pady=6); return sec.body

    def _entry(self, card, key, label, value, help_text=""):
        ctk.CTkLabel(card,text=label,text_color=self.colors.get("text","#fff")).pack(anchor="w",padx=8,pady=(8,2))
        e=ctk.CTkEntry(card); e.insert(0,str(value)); e.pack(fill="x",padx=8,pady=(0,2)); self.entries[key]=e
        if help_text: ctk.CTkLabel(card,text=help_text,justify="left",wraplength=920,text_color=self.colors.get("muted_text",self.colors.get("text","#fff")),font=("Arial",11)).pack(anchor="w",padx=8,pady=(0,4))

    def _switch(self,card,key,label,value,help_text=""):
        var=ctk.BooleanVar(value=bool(value)); self.switches[key]=var
        ctk.CTkSwitch(card,text=label,variable=var,text_color=self.colors.get("text","#fff")).pack(anchor="w",padx=8,pady=(7,1))
        if help_text: ctk.CTkLabel(card,text=help_text,justify="left",wraplength=920,text_color=self.colors.get("muted_text",self.colors.get("text","#fff")),font=("Arial",11)).pack(anchor="w",padx=8,pady=(0,4))

    def _build_theme(self):
        card=self._section("🎨 Оформление","Выбор темы меняет цвета, фон и вид интерфейса. После применения программа перезапускается.",True)
        themes=load_theme_index().get("themes",[]); self.theme_map={i.get("title",i.get("id")):i.get("id","dark") for i in themes} or {"Тёмная":"dark"}
        current=str(self.app_cfg.get("theme_id","dark")); current_title=next((t for t,i in self.theme_map.items() if i==current),next(iter(self.theme_map)))
        self.theme_var=ctk.StringVar(value=current_title); ctk.CTkComboBox(card,values=list(self.theme_map),variable=self.theme_var,width=320).pack(anchor="w",padx=8,pady=8)
        ctk.CTkButton(card,text="Применить тему",command=self.apply_theme).pack(anchor="w",padx=8,pady=(0,8))

    def _build_limits(self):
        card=self._section("🎵 Очередь и лимиты","Здесь задаются ограничения заказов. Кулдаун и максимальная длительность указываются в минутах.")
        for key,label,fallback,help_text in [
            ("port","Порт Flask",5000,"Менять только если порт 5000 занят другой программой."),
            ("min_duration_sec","Минимальная длительность, секунд",10,"Слишком короткие ролики будут отклоняться."),
            ("max_duration_min","Максимальная длительность, минут",10,"Ролики длиннее этого значения не попадут в очередь."),
            ("min_views","Минимум просмотров",0,"0 отключает проверку популярности."),
            ("user_limit","Заказов на зрителя",3,"Сколько активных заказов одного зрителя допускается одновременно."),
            ("global_limit","Максимум в очереди",20,"Общее число ожидающих заказов."),
            ("user_cooldown_min","Кулдаун зрителя, минут",5,"Через сколько минут пользователь сможет сделать следующий заказ."),
            ("volume","Громкость VLC, %",30,"Громкость клипов и заказов зрителей."),]: self._entry(card,key,label,self.player_cfg.get(key,fallback),help_text)
        ctk.CTkButton(card,text="Сохранить",command=self.save_player).pack(anchor="w",padx=8,pady=10)

    def _build_search(self):
        card=self._section("🔎 YouTube и поиск","Поиск перебирает несколько результатов и пропускает недоступные ролики. Cookies обычно не нужны.")
        for key,label,fallback,help_text in [
            ("search_results","Результатов для проверки",8,"Чем больше число, тем выше шанс найти рабочий ролик, но поиск может идти дольше."),
            ("search_timeout_sec","Максимальное время поиска, секунд",12,"После этого запрос завершается ошибкой, чтобы бот не зависал."),
            ("parallel_checks","Параллельных проверок",3,"2–4 обычно оптимально."),]: self._entry(card,key,label,self.player_cfg.get(key,fallback),help_text)
        for key,label,fallback,help_text in [
            ("allow_shorts","Разрешить Shorts",True,"Разрешает короткие вертикальные ролики."),
            ("allow_live","Разрешить прямые эфиры",False,"Эфиры могут быть бесконечными, поэтому обычно выключено."),
            ("allow_playlists","Разрешить плейлисты",False,"Если выключено, из ссылки будет обработан только отдельный ролик."),
            ("allow_age_restricted","Разрешить 18+",False,"Такие ролики часто требуют cookies и могут не воспроизводиться."),
            ("require_embeddable","Требовать разрешение на встраивание",False,"Полезно для OBS, но иногда отбрасывает рабочие ролики."),
            ("cookies_enabled","Использовать cookies браузера",False,"Включай только для роликов, которые открываются в браузере, но не запускаются в программе."),]: self._switch(card,key,label,self.player_cfg.get(key,fallback),help_text)
        self._entry(card,"cookies_browser","Браузер cookies",self.player_cfg.get("cookies_browser","chrome"),"Допустимо: chrome, edge или firefox.")
        row=ctk.CTkFrame(card,fg_color="transparent"); row.pack(fill="x",padx=8,pady=10)
        ctk.CTkButton(row,text="Сохранить поиск",command=self.save_player).pack(side="left")
        self.ytdlp_label=ctk.CTkLabel(row,text=f"yt-dlp: {current_version()}",text_color=self.colors.get("text","#fff")); self.ytdlp_label.pack(side="left",padx=12)
        ctk.CTkButton(row,text="Обновить yt-dlp",command=self.update_ytdlp).pack(side="left")

    def _build_blocks(self):
        card=self._section("🚫 Чёрные списки","Каждая строка — отдельное правило. Списки зрителей и видео также пополняются через правую кнопку в очереди.")
        for key,label in [("blocked_words","Запрещённые слова"),("blocked_channels","Заблокированные каналы"),("blocked_users","Заблокированные зрители"),("blocked_videos","Заблокированные ID видео")]:
            ctk.CTkLabel(card,text=label,text_color=self.colors.get("text","#fff")).pack(anchor="w",padx=8,pady=(8,2)); box=ctk.CTkTextbox(card,height=75); box.insert("1.0","\n".join(map(str,self.player_cfg.get(key,[])))); box.pack(fill="x",padx=8); self.textboxes[key]=box
        ctk.CTkButton(card,text="Сохранить списки",command=self.save_player).pack(anchor="w",padx=8,pady=10)

    def _build_yandex(self):
        card=self._section("🎧 Яндекс Музыка","Управляет отдельным приложением Яндекс Музыки и может ставить его на паузу во время заказов.")
        for key,label,fallback,help_text in [
            ("yandex_enabled","Показывать управление Яндекс Музыкой",True,"Добавляет кнопки управления во вкладку медиаплеера."),
            ("auto_pause_yandex","Ставить на паузу при заказе",True,"Чтобы две композиции не играли одновременно."),
            ("auto_resume_yandex","Продолжать после очереди",True,"Возобновляет Яндекс Музыку, когда очередь заказов закончилась."),]: self._switch(card,key,label,self.player_cfg.get(key,fallback),help_text)
        ctk.CTkButton(card,text="Сохранить",command=self.save_player).pack(anchor="w",padx=8,pady=10)

    def _build_background(self):
        card=self._section("🎼 Фоновая музыка для YouTube","Это отдельный аудио-источник OBS без видео. Добавляй лицензированные MP3/WAV во вкладке «Фоновая музыка».")
        ctk.CTkLabel(card,text=f"Папка музыки:\n{MUSIC_DIR}\n\nOBS Browser Source:\nhttp://127.0.0.1:{self.player_cfg.get('port',5000)}/music",
                     justify="left",font=("Consolas",12),text_color=self.colors.get("text","#fff")).pack(anchor="w",padx=8,pady=8)
        ctk.CTkLabel(card,text="В OBS включи «Управлять аудио через OBS». Тогда музыка будет отдельным аудиоканалом и не смешается с видеоклипами.",wraplength=900,justify="left",text_color=self.colors.get("muted_text",self.colors.get("text","#fff"))).pack(anchor="w",padx=8,pady=(0,8))

    def _build_history(self):
        card=self._section("📚 История заказов","Показывает последние принятые, проигранные и отклонённые заказы.")
        self.history=ctk.CTkTextbox(card,height=180); self.history.pack(fill="x",padx=8,pady=8); self.refresh_history()
        ctk.CTkButton(card,text="Обновить историю",command=self.refresh_history).pack(anchor="w",padx=8,pady=(0,8))

    def _build_backup(self):
        card=self._section("💾 Резервные копии и обслуживание","Экспорт сохраняет все настройки в один JSON. Импорт создаёт резервную копию перед заменой.")
        row=ctk.CTkFrame(card,fg_color="transparent"); row.pack(fill="x",padx=8,pady=10)
        ctk.CTkButton(row,text="Создать копию",command=self.backup_settings).pack(side="left",padx=4)
        ctk.CTkButton(row,text="Экспорт JSON",command=self.export_settings).pack(side="left",padx=4)
        ctk.CTkButton(row,text="Импорт JSON",command=self.import_settings).pack(side="left",padx=4)

    def apply_theme(self): settings.set("app","theme_id",self.theme_map.get(self.theme_var.get(),"dark")); self.app.restart_application()
    def save_player(self):
        errors=[]; int_keys={"port","min_duration_sec","max_duration_min","min_views","user_limit","global_limit","user_cooldown_min","volume","search_results","search_timeout_sec","parallel_checks"}
        for key,e in self.entries.items():
            raw=e.get().strip()
            if key in int_keys:
                try:self.player_cfg[key]=int(raw)
                except Exception:errors.append(key)
            else:self.player_cfg[key]=raw
        for key,v in self.switches.items():self.player_cfg[key]=bool(v.get())
        for key,b in self.textboxes.items():self.player_cfg[key]=[x.strip() for x in b.get("1.0","end").splitlines() if x.strip()]
        settings.save("player",self.player_cfg)
        messagebox.showwarning("Настройки","Проверь числа: "+", ".join(errors)) if errors else messagebox.showinfo("Настройки","Сохранено. Новые правила применятся к следующим заказам.")
    def update_ytdlp(self):
        self.ytdlp_label.configure(text="yt-dlp: обновление...")
        def worker():ok,msg=update_ytdlp(); self.after(0,lambda:self._finish_update(ok,msg))
        threading.Thread(target=worker,daemon=True).start()
    def _finish_update(self,ok,msg): self.ytdlp_label.configure(text=f"yt-dlp: {current_version()}"); (messagebox.showinfo if ok else messagebox.showerror)("yt-dlp",msg)
    def refresh_history(self):
        rows=database.recent_media(50); lines=[]
        for r in rows:
            stamp=datetime.datetime.fromtimestamp(r["created_at"]).strftime("%d.%m %H:%M"); line=f"{stamp} | @{r['requested_by']} | {r['action']} | {r['title']}"; line+=f" | {r['reason']}" if r.get("reason") else ""; lines.append(line)
        self.history.delete("1.0","end"); self.history.insert("1.0","\n".join(lines) if lines else "История пока пуста.")
    def backup_settings(self): messagebox.showinfo("Резервная копия",f"Сохранено:\n{settings.backup_all()}")
    def export_settings(self):
        f=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("JSON","*.json")]);
        if f: settings.export_all(Path(f)); messagebox.showinfo("Экспорт","Готово")
    def import_settings(self):
        f=filedialog.askopenfilename(filetypes=[("JSON","*.json")]);
        if not f:return
        try:settings.import_all(Path(f)); messagebox.showinfo("Импорт","Готово. Приложение будет перезапущено."); self.app.restart_application()
        except Exception as exc:messagebox.showerror("Импорт",str(exc))
