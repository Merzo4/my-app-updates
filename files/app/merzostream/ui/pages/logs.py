from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ...core.database import database
from ...core.event_log import subscribe, unsubscribe


class LogsPage(ctk.CTkFrame):
    def __init__(self, parent, context):
        super().__init__(parent, fg_color="transparent")
        self.context = context
        self.theme = context["theme"]
        self.colors = self.theme["colors"]
        self._subscribed = True
        self._build()
        subscribe(self._on_live_line)
        self.refresh()

    def _build(self):
        toolbar = ctk.CTkFrame(self, fg_color=self.colors.get("card", self.colors["window"]))
        toolbar.pack(fill="x", padx=8, pady=(8, 5))
        self.search_var = ctk.StringVar()
        self.module_var = ctk.StringVar(value="Все модули")
        self.level_var = ctk.StringVar(value="Все уровни")
        self.search = ctk.CTkEntry(toolbar, textvariable=self.search_var, placeholder_text="Поиск по журналу...")
        self.search.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        self.module_menu = ctk.CTkOptionMenu(toolbar, variable=self.module_var, values=["Все модули"], width=150)
        self.module_menu.pack(side="left", padx=4)
        self.level_menu = ctk.CTkOptionMenu(toolbar, variable=self.level_var, values=["Все уровни"], width=135)
        self.level_menu.pack(side="left", padx=4)
        ctk.CTkButton(toolbar, text="Обновить", width=95, command=self.refresh).pack(side="left", padx=4)
        ctk.CTkButton(toolbar, text="Экспорт CSV", width=105, command=self.export_csv).pack(side="left", padx=4)
        ctk.CTkButton(toolbar, text="Очистить", width=85, fg_color="#9b3030", command=self.clear).pack(side="left", padx=(4, 8))
        self.search.bind("<Return>", lambda _event: self.refresh())

        self.box = ctk.CTkTextbox(self, font=("Consolas", 12), wrap="word")
        self.box.pack(fill="both", expand=True, padx=8, pady=(5, 8))

    def _filters(self):
        module = "" if self.module_var.get() == "Все модули" else self.module_var.get()
        level = "" if self.level_var.get() == "Все уровни" else self.level_var.get()
        return module, level, self.search_var.get().strip()

    def refresh(self):
        modules, levels = database.app_event_filters()
        self.module_menu.configure(values=["Все модули"] + modules)
        self.level_menu.configure(values=["Все уровни"] + levels)
        module, level, search = self._filters()
        rows = list(reversed(database.recent_app_events(1000, module, level, search)))
        self.box.delete("1.0", "end")
        for row in rows:
            stamp = datetime.fromtimestamp(float(row["created_at"])).strftime("%H:%M:%S")
            self.box.insert("end", f'[{stamp}] [{row["level"]}] [{row["module"]}] {row["message"]}\n')
        self.box.see("end")

    def _on_live_line(self, line):
        if not self.winfo_exists():
            return
        self.after(0, lambda value=line: self._append(value))

    def _append(self, line):
        module, level, search = self._filters()
        upper = line.upper()
        if module and f"[{module}]" not in upper:
            return
        if level and f"[{level}]" not in upper:
            return
        if search and search.lower() not in line.lower():
            return
        self.box.insert("end", line + "\n")
        self.box.see("end")

    def export_csv(self):
        module, level, search = self._filters()
        rows = database.recent_app_events(5000, module, level, search)
        target = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="MerzoStream_logs.csv")
        if not target:
            return
        with Path(target).open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(["Дата", "Уровень", "Модуль", "Сообщение"])
            for row in reversed(rows):
                writer.writerow([datetime.fromtimestamp(row["created_at"]).isoformat(sep=" ", timespec="seconds"), row["level"], row["module"], row["message"]])
        messagebox.showinfo("Экспорт логов", "Журнал успешно сохранён.")

    def clear(self):
        if messagebox.askyesno("Очистить журнал", "Удалить события из базы журнала?"):
            database.clear_app_events()
            self.refresh()

    def shutdown(self):
        if self._subscribed:
            unsubscribe(self._on_live_line)
            self._subscribed = False
