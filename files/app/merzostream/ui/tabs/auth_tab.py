import customtkinter as ctk, webbrowser
from ...core.config import save
from ...core.paths import STREAM_CONFIG, YOUTUBE_TOKEN, KICK_TOKEN
class AuthTab(ctk.CTkScrollableFrame):
    def __init__(self,parent,cfg):
        super().__init__(parent,fg_color='transparent'); self.cfg=cfg
        ctk.CTkLabel(self,text='🔐 Авторизация и API',font=('Arial',24,'bold')).pack(pady=15)
        self.fields={}
        for key,label,secret in [('twitch_client_id','Twitch Client ID',False),('twitch_oauth_token','Twitch OAuth Token',True),('vk_token','VK Access Token',True),('kick_client_id','Kick Client ID',False),('kick_client_secret','Kick Client Secret',True),('groq_key','Groq API Key',True)]:
            ctk.CTkLabel(self,text=label).pack(anchor='w',padx=30)
            e=ctk.CTkEntry(self,show='*' if secret else ''); e.insert(0,cfg.get(key,'')); e.pack(fill='x',padx=30,pady=(2,10)); self.fields[key]=e
        ctk.CTkButton(self,text='💾 Сохранить',command=self.save).pack(pady=8)
        ctk.CTkLabel(self,text=lambda:'').pack()
        ctk.CTkLabel(self,text=f"YouTube token: {'есть' if YOUTUBE_TOKEN.exists() else 'нет'}\nKick token: {'есть' if KICK_TOKEN.exists() else 'нет'}").pack(pady=10)
        ctk.CTkButton(self,text='Получить VK токен',command=lambda:webbrowser.open('https://auth.live.vkvideo.ru/app/oauth2/authorize?client_id=lmn3one57wbvnwyo&response_type=token&scope=channel:stream:settings&redirect_uri=http://localhost')).pack(pady=5)
    def save(self):
        for k,e in self.fields.items(): self.cfg[k]=e.get().strip()
        save(STREAM_CONFIG,self.cfg)
