import customtkinter as ctk
from ...player.engine import PlayerEngine
from ...player.queue_manager import QueueManager
from ...player.web_server import PlayerWebServer
from ...core.paths import NOW_PLAYING
from ...core.event_log import log

class PlayerTab(ctk.CTkFrame):
    def __init__(self,parent,cfg):
        super().__init__(parent,fg_color='transparent'); self.cfg=cfg; self.state={'url':'','paused':False,'stopped':False,'time':0}
        body=ctk.CTkFrame(self,fg_color='transparent'); body.pack(fill='both',expand=True,padx=8,pady=8)
        left=ctk.CTkFrame(body); left.pack(side='left',fill='both',expand=True,padx=5)
        right=ctk.CTkFrame(body,width=330); right.pack(side='right',fill='y',padx=5)
        self.canvas=ctk.CTkCanvas(left,bg='black',highlightthickness=0); self.canvas.pack(fill='both',expand=True,padx=8,pady=8)
        controls=ctk.CTkFrame(left); controls.pack(fill='x',padx=8,pady=8)
        ctk.CTkButton(controls,text='⏯ Пауза',command=self.pause).pack(side='left',padx=5,pady=8)
        ctk.CTkButton(controls,text='⏹ Стоп',command=self.stop).pack(side='left',padx=5)
        ctk.CTkButton(controls,text='⏭ Скип',command=self.skip).pack(side='left',padx=5)
        self.vol=ctk.CTkSlider(controls,from_=0,to=100,command=lambda v:self.engine.volume(v)); self.vol.set(30); self.vol.pack(side='right',padx=10)
        ctk.CTkLabel(right,text='📋 Очередь',font=('Arial',18,'bold')).pack(pady=10)
        self.queue_box=ctk.CTkTextbox(right,width=330); self.queue_box.pack(fill='both',expand=True,padx=8,pady=8)
        self.status=ctk.CTkLabel(right,text=f"OBS: http://127.0.0.1:{cfg.get('port',5000)}/player",wraplength=300); self.status.pack(pady=8)
        self.queue=QueueManager(cfg); self.engine=PlayerEngine(lambda:self.canvas.winfo_id()); self.web=PlayerWebServer(self.queue,cfg,self.state,self.refresh); self.web.start()
        self.after(1000,self.tick)
    def refresh(self):
        self.queue_box.delete('1.0','end')
        if self.queue.current: self.queue_box.insert('end',f"▶ {self.queue.current['title']}\n@{self.queue.current['user']}\n\n")
        for i,x in enumerate(self.queue.items,1): self.queue_box.insert('end',f"#{i} {x['title']}\n@{x['user']}\n\n")
    def pause(self): self.engine.pause_toggle(); self.state['paused']=not self.state['paused']
    def stop(self): self.engine.stop(); self.state['stopped']=True
    def skip(self): self.engine.stop(); self.queue.current=None; self.state.update({'url':'','stopped':False,'paused':False}); self.refresh()
    def tick(self):
        if self.queue.current is None and self.queue.items:
            self.queue.current=self.queue.pop(); self.state.update({'url':self.queue.current['url'],'stopped':False,'paused':False}); self.engine.play(self.queue.current['url']); NOW_PLAYING.write_text(self.queue.current['title'],encoding='utf-8'); self.refresh(); log('Player',f"Запущено: {self.queue.current['title']}")
        t,l=self.engine.time_info(); self.state['time']=max(0,t/1000)
        self.after(1000,self.tick)
