import customtkinter as ctk

from ...core.content import load_dashboard
from ...core.paths import CLIENT_SECRET, KICK_TOKEN, YOUTUBE_TOKEN


class HomePage(ctk.CTkScrollableFrame):
    def __init__(self, parent, context):
        app_cfg = context["app_cfg"]
        stream_cfg = context["stream_cfg"]
        player_cfg = context["player_cfg"]
        super().__init__(parent, fg_color="transparent")
        self.grid_columnconfigure((0, 1), weight=1)
        dashboard = load_dashboard()
        colors = context["theme"]["colors"]

        ctk.CTkLabel(self, text=dashboard.get("heading", "MerzoStream Suite"), font=("Arial", 26, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(self, text=dashboard.get("subtitle", ""), font=("Arial", 14), text_color=colors["muted_text"]).grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 20))

        values = {
            "game": stream_cfg.get("game", "Just Chatting"),
            "port": player_cfg.get("port", 5000),
            "auth_summary": self._auth_summary(),
        }
        cards = dashboard.get("cards", [])
        for index, card_data in enumerate(cards):
            row, col = 2 + index // 2, index % 2
            card = ctk.CTkFrame(self, fg_color=colors["card"], corner_radius=14)
            card.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)
            template = card_data.get("value_template", "")
            try:
                value = template.format(**values)
            except (KeyError, ValueError):
                value = template
            ctk.CTkLabel(card, text=card_data.get("title", ""), font=("Arial", 18, "bold")).pack(anchor="w", padx=18, pady=(18, 6))
            ctk.CTkLabel(card, text=value, font=("Arial", 14), text_color=colors["accent_text"]).pack(anchor="w", padx=18)
            ctk.CTkLabel(card, text=card_data.get("detail", ""), font=("Arial", 12), text_color=colors["muted_text"], wraplength=430, justify="left").pack(anchor="w", padx=18, pady=(5, 18))

        notice_row = 2 + (len(cards) + 1) // 2
        note = ctk.CTkFrame(self, fg_color=colors.get("notice", "#1f2c3a"), corner_radius=12)
        note.grid(row=notice_row, column=0, columnspan=2, sticky="ew", padx=10, pady=(18, 10))
        ctk.CTkLabel(note, text=dashboard.get("notice", ""), font=("Arial", 13, "bold"), text_color=colors.get("notice_text", "#dbeafe"), wraplength=900, justify="left").pack(anchor="w", padx=18, pady=18)

    @staticmethod
    def _auth_summary():
        youtube = "YouTube ✓" if YOUTUBE_TOKEN.exists() else "YouTube —"
        kick = "Kick ✓" if KICK_TOKEN.exists() else "Kick —"
        secret = "client_secret ✓" if CLIENT_SECRET.exists() else "client_secret —"
        return f"{youtube}  •  {kick}  •  {secret}"
