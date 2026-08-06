import customtkinter as ctk
from ...core.event_log import subscribe
class LogsPage(ctk.CTkFrame):
    def __init__(self, parent, context):
        super().__init__(parent,fg_color='transparent'); self.box=ctk.CTkTextbox(self,font=('Consolas',12)); self.box.pack(fill='both',expand=True,padx=10,pady=10); subscribe(self.add)
    def add(self,line): self.after(0,lambda:(self.box.insert('end',line+'\n'),self.box.see('end')))
