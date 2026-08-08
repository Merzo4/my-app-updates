import customtkinter as ctk
from ..core.bootstrap import mark_first_run_complete
class Welcome(ctk.CTkToplevel):
    def __init__(self,parent):
        super().__init__(parent); self.title('Добро пожаловать'); self.geometry('620x470'); self.transient(parent); self.grab_set()
        ctk.CTkLabel(self,text='MerzoStream Suite',font=('Arial',28,'bold')).pack(pady=(30,5))
        ctk.CTkLabel(self,text='Beta 0.0.2h',font=('Arial',16)).pack()
        text="Первая объединённая версия:\n\n• управление Twitch, YouTube, VK и Kick;\n• медиаплеер и очередь заказов;\n• Flask API для Streamer.bot;\n• браузерный источник для OBS;\n• общие настройки, авторизация и логи;\n• подготовленная модульная структура обновлений."
        ctk.CTkLabel(self,text=text,justify='left',wraplength=520,font=('Arial',14)).pack(padx=30,pady=25)
        ctk.CTkButton(self,text='Начать работу',height=42,command=self.close).pack(pady=15)
    def close(self): mark_first_run_complete(); self.destroy()
