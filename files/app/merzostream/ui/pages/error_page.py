import customtkinter as ctk

class ErrorPage(ctk.CTkFrame):
    def __init__(self, parent, context, page_id="unknown", error=""):
        super().__init__(parent, fg_color="transparent")
        ctk.CTkLabel(self, text="Страница не загрузилась", font=("Arial", 26, "bold"), text_color="#ff6b6b").pack(pady=(70, 10))
        ctk.CTkLabel(self, text=f"Модуль: {page_id}", font=("Consolas", 14)).pack(pady=4)
        ctk.CTkLabel(self, text=str(error), wraplength=800, justify="left", text_color="#aeb8c4").pack(padx=30, pady=12)
