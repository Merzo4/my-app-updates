import importlib
import os
import subprocess
import sys
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from .core.bootstrap import bootstrap
from .core.config import load_app, load_player, load_stream
from .core.content import load_app_info, load_navigation, load_texts, load_theme
from .core.event_log import log
from .core.paths import bundle_root
from .core.settings_manager import settings
from .core.database import database
from .core.module_manager import module_manager
from .core.plugin_manager import plugin_manager
from .core.update_manager import update_manager
from .ui.pages.error_page import ErrorPage
from .ui.text_editing import install_text_editing
from .ui.welcome import Welcome
from .ui.widgets.system_monitor import SystemMonitorPanel
from .chat.server import ChatWebServer
from .chat.manager import chat_manager


class App(ctk.CTk):
    def __init__(self, first_run: bool):
        super().__init__()
        self.app_cfg = load_app()
        self.theme_id = self.app_cfg.get("theme_id", "dark")
        self.app_info = load_app_info()
        self.theme = load_theme(self.theme_id)
        self.navigation = load_navigation()
        self.texts = load_texts()
        colors = self.theme["colors"]
        layout = self.theme["layout"]

        self.title(self.app_info["window_title"])
        self.geometry(f'{layout["window_width"]}x{layout["window_height"]}')
        self.minsize(layout["min_width"], layout["min_height"])
        self.configure(fg_color=colors["window"])
        install_text_editing(self)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.stream_cfg = load_stream()
        self.player_cfg = load_player()
        self.chat_server = ChatWebServer(chat_manager, port=5001)
        self.chat_server.start()
        self.page_context = {
            "app": self, "app_cfg": self.app_cfg, "stream_cfg": self.stream_cfg,
            "player_cfg": self.player_cfg, "theme": self.theme,
            "app_info": self.app_info, "texts": self.texts,
            "settings": settings, "database": database,
            "module_manager": module_manager, "plugin_manager": plugin_manager,
            "update_manager": update_manager,
            "chat_manager": chat_manager, "chat_port": 5001,
        }
        self.pages = {}
        self.nav_buttons = {}
        self.nav_titles = {}
        self.page_specs = {}
        self.current_page = ""
        self._background_image = None
        self._background_label = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.sidebar = ctk.CTkFrame(self, width=layout["sidebar_width"], corner_radius=0, fg_color=colors["sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=colors["window"])
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        self.system_monitor = SystemMonitorPanel(self, self.theme)
        self.system_monitor.grid(row=0, column=2, sticky="nsew")

        self.status_bar = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color=colors.get("header", colors["window"]))
        self.status_bar.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.status_bar.grid_propagate(False)
        self.status_text = ctk.CTkLabel(self.status_bar, text=f"MerzoStream Suite • {self.app_info['channel']} {self.app_info['version']} • GitHub Update Engine 2.0", font=("Arial", 10), text_color=colors.get("muted_text", colors["text"]))
        self.status_text.pack(side="left", padx=12, pady=4)

        self._build_sidebar()
        self._build_content_shell()
        initial_page = "home" if "home" in self.page_specs else next(iter(self.page_specs), "")
        if initial_page:
            self.show_page(initial_page)
        if first_run:
            self.after(350, lambda: Welcome(self))

    def _build_sidebar(self):
        colors = self.theme["colors"]
        layout = self.theme["layout"]
        ctk.CTkLabel(self.sidebar, text=self.app_info["sidebar_brand"], font=("Arial", 23, "bold"), text_color=colors["text"]).pack(padx=20, pady=(26, 0), anchor="w")
        ctk.CTkLabel(self.sidebar, text=self.app_info["sidebar_subtitle"], font=("Arial", 11, "bold"), text_color=colors["accent_text"]).pack(padx=22, pady=(2, 24), anchor="w")
        enabled_items = [item for item in self.navigation.get("items", []) if item.get("enabled", True)]
        previous_group = None
        for item in enabled_items:
            group = item.get("group", "main")
            if previous_group is not None and group != previous_group and self.navigation.get("show_group_separators", True):
                ctk.CTkFrame(self.sidebar, height=1, fg_color=colors.get("border", "#353941")).pack(fill="x", padx=18, pady=8)
            previous_group = group
            key = item["id"]
            title = item.get("title", key)
            self.page_specs[key] = item
            button = ctk.CTkButton(
                self.sidebar, text=f'{item.get("icon", "")}  {title}'.strip(),
                height=layout["nav_button_height"], anchor="w", corner_radius=layout["nav_corner_radius"],
                fg_color="transparent", hover_color=colors["hover"], text_color=colors["nav_text"],
                font=("Arial", 13, "bold"), command=lambda page=key: self.show_page(page),
            )
            button.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = button
            self.nav_titles[key] = title
        self.status_label = ctk.CTkLabel(self.sidebar, text=self.texts.get("status_running", "● Приложение запущено"), text_color=colors["success"], font=("Arial", 11, "bold"))
        self.status_label.pack(side="bottom", anchor="w", padx=20, pady=20)

    def _build_content_shell(self):
        colors = self.theme["colors"]
        header = ctk.CTkFrame(self.content, height=72, corner_radius=0, fg_color=colors["header"])
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)
        self.page_title = ctk.CTkLabel(header, text="", font=("Arial", 22, "bold"), text_color=colors["text"])
        self.page_title.grid(row=0, column=0, sticky="w", padx=28, pady=22)
        ctk.CTkLabel(header, text=f'{self.app_info["channel"]} {self.app_info["version"]}', font=("Arial", 12, "bold"), text_color=colors["accent_text"]).grid(row=0, column=1, sticky="e", padx=28)

        overlay = self.theme.get("layout", {}).get("content_overlay", colors["window"])
        self.page_host = ctk.CTkFrame(self.content, corner_radius=0, fg_color=overlay)
        self.page_host.grid(row=1, column=0, sticky="nsew")
        self.page_host.grid_columnconfigure(0, weight=1)
        self.page_host.grid_rowconfigure(0, weight=1)
        self._install_background()

    def _install_background(self):
        relative = self.theme.get("backgrounds", {}).get("main", "")
        if not relative:
            return
        path = bundle_root() / Path(relative)
        if not path.exists():
            log("THEME", f"Фон темы не найден: {path}")
            return
        try:
            image = Image.open(path)
            self._background_image = ctk.CTkImage(light_image=image, dark_image=image, size=(1200, 800))
            self._background_label = ctk.CTkLabel(self.page_host, text="", image=self._background_image)
            self._background_label.grid(row=0, column=0, sticky="nsew")
            self.page_host.bind("<Configure>", self._resize_background)
        except Exception as exc:
            log("THEME", f"Не удалось загрузить фон: {exc}")

    def _resize_background(self, event):
        if self._background_image and event.width > 20 and event.height > 20:
            self._background_image.configure(size=(event.width, event.height))

    def _load_page(self, key):
        if key in self.pages:
            return self.pages[key]
        spec = self.page_specs[key]
        module_name = spec.get("module")
        class_name = spec.get("class")
        try:
            if not module_name or not class_name:
                raise ValueError("В navigation.json не указаны module и class")
            module = importlib.import_module(module_name)
            page_class = getattr(module, class_name)
            page = page_class(self.page_host, self.page_context)
        except Exception as exc:
            log("UI", f"Не удалось загрузить страницу {key}: {exc}")
            page = ErrorPage(self.page_host, self.page_context, key, exc)

        # Новая страница создаётся скрытой. Показывает её только show_page().
        # Это важно для CTkScrollableFrame: одного tkraise() недостаточно,
        # иначе внутренний Canvas предыдущей страницы может остаться сверху.
        self.pages[key] = page
        return page

    def _hide_all_pages(self):
        """Надёжно убирает все страницы из grid перед показом выбранной."""
        for page in self.pages.values():
            try:
                page.grid_remove()
            except Exception:
                pass

    def reload_page(self, key):
        page = self.pages.pop(key, None)
        if page is not None:
            page.destroy()
        if self.current_page == key:
            self.current_page = ""
        return self._load_page(key)

    def show_page(self, key):
        if key not in self.page_specs:
            return

        # Сначала полностью скрываем старую страницу, затем размещаем новую.
        # Так страницы не накладываются и содержимое вкладок не смешивается.
        self._hide_all_pages()
        page = self._load_page(key)
        page.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
        page.tkraise()

        # Фоновая картинка всегда должна оставаться под активной страницей.
        if self._background_label is not None:
            try:
                self._background_label.lower()
            except Exception:
                pass

        self.current_page = key
        self.page_title.configure(text=self.nav_titles.get(key, key))
        colors = self.theme["colors"]
        for name, button in self.nav_buttons.items():
            button.configure(
                fg_color=colors["selected"] if name == key else "transparent",
                text_color="#ffffff" if name == key else colors["nav_text"],
            )

    def _on_close(self):
        """Даёт модулям корректно сохранить состояние и остановить фоновые процессы."""
        log("APP", "Закрытие приложения")
        for page in list(self.pages.values()):
            shutdown = getattr(page, "shutdown", None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception as exc:
                    log("APP", f"Ошибка завершения модуля {type(page).__name__}: {exc}")
        try:
            self.system_monitor.shutdown()
        except Exception:
            pass
        self.destroy()

    def restart_application(self):
        log("APP", "Перезапуск для применения темы")
        for page in list(self.pages.values()):
            shutdown = getattr(page, "shutdown", None)
            if callable(shutdown):
                try:
                    shutdown()
                except Exception as exc:
                    log("APP", f"Ошибка завершения модуля {type(page).__name__}: {exc}")
        args = [sys.executable] + sys.argv
        subprocess.Popen(args, cwd=str(Path.cwd()))
        try:
            self.system_monitor.shutdown()
        except Exception:
            pass
        self.destroy()


def run():
    app_cfg = load_app()
    theme = load_theme(app_cfg.get("theme_id", "dark"))
    ctk.set_appearance_mode(theme.get("appearance", "dark"))
    ctk.set_default_color_theme(theme.get("default_color_theme", "blue"))
    first_run = bootstrap()
    App(first_run).mainloop()
