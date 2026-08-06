import shutil
from .paths import CLIENT_SECRET, RESOURCES_DIR, FIRST_RUN_FLAG
from .config import load_app, load_stream, load_player

def bootstrap():
    load_app(); load_stream(); load_player()
    bundled = RESOURCES_DIR / "client_secret.json"
    if bundled.exists() and not CLIENT_SECRET.exists():
        shutil.copy2(bundled, CLIENT_SECRET)
    return not FIRST_RUN_FLAG.exists()

def mark_first_run_complete():
    FIRST_RUN_FLAG.write_text("ok", encoding="utf-8")
