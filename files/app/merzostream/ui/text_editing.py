from __future__ import annotations

import tkinter as tk


_EDITABLE_CLASSES = {"Entry", "TEntry", "Text", "Spinbox"}


def _editable_widget(widget) -> bool:
    try:
        return widget.winfo_class() in _EDITABLE_CLASSES
    except Exception:
        return False


def _emit(widget, sequence: str):
    try:
        widget.event_generate(sequence)
        return "break"
    except Exception:
        return None


def install_text_editing(root: tk.Misc) -> None:
    """Adds Ctrl hotkeys and a standard right-click menu to every text field."""

    def on_key(event):
        widget = event.widget
        if not _editable_widget(widget):
            return None

        ctrl = bool(event.state & 0x0004)
        if not ctrl:
            return None

        keysym = (event.keysym or "").lower()
        char = (event.char or "").lower()

        if keysym in ("c", "cyrillic_es") or char in ("c", "с", "\x03"):
            return _emit(widget, "<<Copy>>")
        if keysym in ("v", "cyrillic_em") or char in ("v", "м", "\x16"):
            return _emit(widget, "<<Paste>>")
        if keysym in ("x", "cyrillic_che") or char in ("x", "ч", "\x18"):
            return _emit(widget, "<<Cut>>")
        if keysym in ("a", "cyrillic_ef") or char in ("a", "ф", "\x01"):
            return _emit(widget, "<<SelectAll>>")
        if keysym in ("z", "cyrillic_ya") or char in ("z", "я", "\x1a"):
            return _emit(widget, "<<Undo>>")
        return None

    def popup(event):
        widget = event.widget
        if not _editable_widget(widget):
            return None

        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="Отменить", command=lambda: _emit(widget, "<<Undo>>"))
        menu.add_separator()
        menu.add_command(label="Вырезать", command=lambda: _emit(widget, "<<Cut>>"))
        menu.add_command(label="Копировать", command=lambda: _emit(widget, "<<Copy>>"))
        menu.add_command(label="Вставить", command=lambda: _emit(widget, "<<Paste>>"))
        menu.add_command(label="Удалить", command=lambda: _emit(widget, "<<Clear>>"))
        menu.add_separator()
        menu.add_command(label="Выделить всё", command=lambda: _emit(widget, "<<SelectAll>>"))
        try:
            widget.focus_set()
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass
        return "break"

    root.bind_all("<KeyPress>", on_key, add="+")
    root.bind_all("<Button-3>", popup, add="+")
