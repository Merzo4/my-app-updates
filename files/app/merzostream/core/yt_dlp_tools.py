from __future__ import annotations
import subprocess, sys

def current_version()->str:
    try:
        import yt_dlp
        return str(yt_dlp.version.__version__)
    except Exception:return 'не установлен'

def update()->tuple[bool,str]:
    try:
        p=subprocess.run([sys.executable,'-m','pip','install','--upgrade','yt-dlp'],capture_output=True,text=True,timeout=180)
        text=(p.stdout or p.stderr or '').strip()
        return p.returncode==0, text[-1500:] if text else ('Обновлено' if p.returncode==0 else 'Ошибка')
    except Exception as exc:return False,str(exc)
