import customtkinter as ctk


class AboutTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        ctk.CTkLabel(self, text="MerzoStream Suite", font=("Arial", 30, "bold")).pack(pady=(70, 6))
        ctk.CTkLabel(self, text="Beta 0.0.2f", font=("Arial", 16, "bold"), text_color="#70b7ff").pack()
        ctk.CTkLabel(
            self,
            text=(
                "Единое приложение для управления трансляциями, медиаплеером заказов, "
                "авторизациями, логами и будущими обновлениями."
            ),
            wraplength=650,
            justify="center",
            font=("Arial", 14),
            text_color="#aeb8c4",
        ).pack(padx=40, pady=24)
        ctk.CTkLabel(self, text="Автор проекта: Merzo4", font=("Arial", 13, "bold")).pack(pady=5)
