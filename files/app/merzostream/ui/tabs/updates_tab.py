import customtkinter as ctk


class UpdatesTab(ctk.CTkFrame):
    def __init__(self, parent, app_cfg):
        super().__init__(parent, fg_color="transparent")
        ctk.CTkLabel(self, text="⬇️ Обновления", font=("Arial", 26, "bold")).pack(anchor="w", padx=24, pady=(20, 5))
        ctk.CTkLabel(
            self,
            text="Модуль обновлений будет подключён после проверки перенесённых функций.",
            text_color="#aeb8c4",
            font=("Arial", 13),
        ).pack(anchor="w", padx=24, pady=(0, 20))

        card = ctk.CTkFrame(self, fg_color="#24282f", corner_radius=14)
        card.pack(fill="x", padx=24, pady=10)
        ctk.CTkLabel(card, text="Текущая версия", font=("Arial", 14, "bold")).pack(anchor="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(card, text="Beta 0.0.2h", text_color="#70b7ff", font=("Arial", 20, "bold")).pack(anchor="w", padx=18)
        ctk.CTkLabel(card, text=f"Репозиторий: {app_cfg.get('github_repo', 'Merzo4/my-app-updates')}", text_color="#aeb8c4").pack(anchor="w", padx=18, pady=(6, 18))

        self.check_button = ctk.CTkButton(self, text="Проверить обновления — будет включено позже", state="disabled", height=44)
        self.check_button.pack(fill="x", padx=24, pady=10)
