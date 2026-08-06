import customtkinter as ctk
from ...core.config import save
from ...core.paths import PLAYER_CONFIG
class SettingsTab(ctk.CTkScrollableFrame):
    def __init__(self,parent,cfg):
        super().__init__(parent,fg_color='transparent'); self.cfg=cfg; self.entries={}
        ctk.CTkLabel(self,text='⚙️ Настройки медиаплеера',font=('Arial',24,'bold')).pack(pady=15)
        for k,l in [('port','Порт Flask'),('max_duration','Макс. длительность, сек'),('min_views','Мин. просмотров'),('user_limit','Лимит на зрителя'),('global_limit','Общий лимит'),('user_cooldown_min','Кулдаун, мин')]:
            ctk.CTkLabel(self,text=l).pack(anchor='w',padx=30); e=ctk.CTkEntry(self); e.insert(0,str(cfg.get(k,''))); e.pack(fill='x',padx=30,pady=(2,8)); self.entries[k]=e
        ctk.CTkButton(self,text='💾 Сохранить',command=self.save).pack(pady=15)
    def save(self):
        for k,e in self.entries.items():
            try:self.cfg[k]=int(e.get())
            except:pass
        save(PLAYER_CONFIG,self.cfg)
