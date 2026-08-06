import threading, json
import customtkinter as ctk
from ...core.config import save
from ...core.paths import STREAM_CONFIG, CONTENT_DIR
from ...core.event_log import log
from ...services.stream_services import StreamServices

class StreamTab(ctk.CTkFrame):
    def __init__(self,parent,cfg):
        super().__init__(parent,fg_color='transparent'); self.cfg=cfg; self.services=StreamServices(cfg)
        ctk.CTkLabel(self,text='📡 Управление трансляцией',font=('Arial',24,'bold')).pack(pady=15)
        self.title_e=ctk.CTkEntry(self,height=42,placeholder_text='Название трансляции'); self.title_e.insert(0,cfg.get('title','')); self.title_e.pack(fill='x',padx=30,pady=8)
        games=['Just Chatting','SnowRunner','Rust','World of Tanks','GTA 5 RP']
        try: games=list(json.loads((CONTENT_DIR/'games.json').read_text(encoding='utf-8')).keys())
        except Exception: pass
        self.game=ctk.CTkComboBox(self,values=games,height=38); self.game.set(cfg.get('game','Just Chatting')); self.game.pack(fill='x',padx=30,pady=8)
        row=ctk.CTkFrame(self,fg_color='transparent'); row.pack(pady=8)
        self.tw=ctk.CTkCheckBox(row,text='Twitch'); self.tw.select(); self.tw.pack(side='left',padx=10)
        self.yt=ctk.CTkCheckBox(row,text='YouTube'); self.yt.select(); self.yt.pack(side='left',padx=10)
        self.vk=ctk.CTkCheckBox(row,text='VK Video'); self.vk.select(); self.vk.pack(side='left',padx=10)
        self.ki=ctk.CTkCheckBox(row,text='Kick'); self.ki.select(); self.ki.pack(side='left',padx=10)
        ctk.CTkButton(self,text='🚀 ОБНОВИТЬ ВЕЗДЕ',height=55,font=('Arial',18,'bold'),command=self.run_all).pack(fill='x',padx=30,pady=15)
        ctk.CTkButton(self,text='🔑 Авторизовать Kick',command=lambda:self.services.authorize_kick(self)).pack(pady=5)
    def run_all(self):
        self.cfg['title']=self.title_e.get().strip(); self.cfg['game']=self.game.get().strip(); save(STREAM_CONFIG,self.cfg)
        def job():
            t,g=self.cfg['title'],self.cfg['game']
            if self.tw.get(): self.services.update_twitch(t,g)
            if self.yt.get(): self.services.update_youtube(t,g)
            if self.vk.get(): self.services.update_vk(t,g)
            if self.ki.get(): self.services.update_kick(t,g)
            log('Stream','Обновление платформ завершено.')
        threading.Thread(target=job,daemon=True).start()
