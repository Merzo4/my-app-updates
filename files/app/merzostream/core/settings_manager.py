from __future__ import annotations

import json
import shutil
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from .paths import BACKUPS_DIR, SETTINGS_DIR

DEFAULTS: dict[str, dict[str, Any]] = {
    "app": {
        "version": "0.0.1-beta", "theme_id": "dark", "check_updates": False,
        "show_changelog": True, "github_repo": "Merzo4/my-app-updates", "developer_mode": False,
    },
    "stream": {
        "title": "", "game": "Just Chatting", "vk_token": "", "groq_key": "",
        "twitch_client_id": "gp762nuuoqcoxypju8c569th9wz7q5", "twitch_oauth_token": "",
        "kick_client_id": "", "kick_client_secret": "",
        "platforms": {"twitch": True, "youtube": True, "vk": True, "kick": False},
    },
    "player": {
        "port": 5000, "volume": 30,
        "min_duration_sec": 10, "max_duration_min": 10,
        "min_views": 0, "user_limit": 3, "global_limit": 20,
        "user_cooldown_min": 5, "search_results": 8, "search_timeout_sec": 12,
        "parallel_checks": 3,
        "allow_shorts": True, "allow_live": False, "allow_playlists": False,
        "allow_age_restricted": False, "skip_kids": False, "require_embeddable": False,
        "cookies_enabled": False, "cookies_browser": "chrome",
        "blocked_users": [], "blocked_videos": [], "blocked_words": [], "blocked_channels": [],
        "font_family": "Arial", "font_size": 13,
        "auto_pause_yandex": True, "auto_resume_yandex": True, "yandex_enabled": True,
    },
    "obs": {"browser_url": "http://127.0.0.1:5000/player", "clear_on_exit": True},
    "ui": {"scale": 1.0, "show_status_bar": True, "mode": "classic", "qt_theme_id": "merzostream_dark"},
    "developer": {"verbose_logging": False, "allow_unsigned_plugins": False},
}

FILE_NAMES = {
    "app": "app.json", "stream": "stream_control.json", "player": "media_player.json",
    "obs": "obs.json", "ui": "ui.json", "developer": "developer.json",
}

class SettingsManager:
    def __init__(self, settings_dir: Path = SETTINGS_DIR):
        self.settings_dir = settings_dir
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict[str, Any]] = {}

    def path_for(self, section: str) -> Path:
        if section not in FILE_NAMES: raise KeyError(f"Неизвестный раздел настроек: {section}")
        return self.settings_dir / FILE_NAMES[section]

    @staticmethod
    def _merge(defaults: Any, stored: Any) -> Any:
        if isinstance(defaults, dict):
            result = deepcopy(defaults)
            if isinstance(stored, dict):
                for key, value in stored.items():
                    result[key] = SettingsManager._merge(defaults[key], value) if key in defaults else value
            return result
        return deepcopy(defaults) if stored is None else stored

    def load(self, section: str, force: bool = False) -> dict[str, Any]:
        if not force and section in self._cache: return self._cache[section]
        path=self.path_for(section); stored={}
        if path.exists():
            try: stored=json.loads(path.read_text(encoding='utf-8'))
            except Exception:
                self.backup_file(path, 'broken'); stored={}
        data=self._merge(DEFAULTS[section], stored)
        self._normalize(section, data)
        self._cache[section]=data
        self.save(section, data)
        return data

    def _normalize(self, section: str, data: dict[str, Any]) -> None:
        if section == 'stream':
            if not str(data.get('twitch_client_id','')).strip(): data['twitch_client_id']=DEFAULTS['stream']['twitch_client_id']
            platforms=deepcopy(DEFAULTS['stream']['platforms'])
            if isinstance(data.get('platforms'),dict): platforms.update(data['platforms'])
            data['platforms']=platforms
        elif section == 'player':
            # migration from old seconds fields
            if 'max_duration_min' not in data or data.get('max_duration_min') is None:
                try: data['max_duration_min']=max(1, round(int(data.get('max_duration',600))/60))
                except Exception: data['max_duration_min']=10
            if 'min_duration_sec' not in data or data.get('min_duration_sec') is None:
                try: data['min_duration_sec']=int(data.get('min_duration',10))
                except Exception: data['min_duration_sec']=10
            ints={
                'port':5000,'volume':30,'min_duration_sec':10,'max_duration_min':10,'min_views':0,
                'user_limit':3,'global_limit':20,'user_cooldown_min':5,'search_results':8,
                'search_timeout_sec':12,'parallel_checks':3,'font_size':13,
            }
            for key,fallback in ints.items():
                try: data[key]=int(data.get(key,fallback))
                except Exception: data[key]=fallback
            data['port']=max(1,min(65535,data['port'])); data['volume']=max(0,min(100,data['volume']))
            data['min_duration_sec']=max(0,data['min_duration_sec']); data['max_duration_min']=max(1,data['max_duration_min'])
            data['search_results']=max(1,min(20,data['search_results'])); data['search_timeout_sec']=max(5,min(30,data['search_timeout_sec']))
            data['parallel_checks']=max(1,min(6,data['parallel_checks']))
            for key in ('blocked_users','blocked_videos','blocked_words','blocked_channels'):
                if not isinstance(data.get(key),list): data[key]=[]
        elif section=='ui':
            try: data['scale']=float(data.get('scale',1.0))
            except Exception: data['scale']=1.0
            if data.get('mode') not in {'classic','qt'}: data['mode']='classic'
            if not str(data.get('qt_theme_id','')).strip(): data['qt_theme_id']='merzostream_dark'

    def save(self, section: str, data: dict[str, Any] | None = None) -> None:
        payload=data if data is not None else self._cache.get(section,self.load(section))
        self._normalize(section,payload)
        path=self.path_for(section); path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix(path.suffix+'.tmp'); temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8'); temp.replace(path)
        self._cache[section]=payload

    def get(self, section:str,key:str,default:Any=None)->Any:
        data:Any=self.load(section)
        for part in key.split('.'):
            if not isinstance(data,dict) or part not in data: return default
            data=data[part]
        return data
    def get_int(self,section,key,default=0,minimum=None):
        try:value=int(self.get(section,key,default))
        except Exception:value=default
        return max(minimum,value) if minimum is not None else value
    def get_float(self,section,key,default=0.0):
        try:return float(self.get(section,key,default))
        except Exception:return default
    def get_bool(self,section,key,default=False):
        value=self.get(section,key,default)
        return value.strip().lower() in {'1','true','yes','on','да'} if isinstance(value,str) else bool(value)
    def set(self,section,key,value,save_now=True):
        data=self.load(section); cur=data; parts=key.split('.')
        for part in parts[:-1]:
            if not isinstance(cur.get(part),dict):cur[part]={}
            cur=cur[part]
        cur[parts[-1]]=value; self._normalize(section,data)
        if save_now:self.save(section,data)
    def backup_file(self,path:Path,suffix='backup'):
        if not path.exists(): return None
        BACKUPS_DIR.mkdir(parents=True,exist_ok=True); stamp=time.strftime('%Y%m%d-%H%M%S')
        target=BACKUPS_DIR/f'{path.stem}-{stamp}-{suffix}{path.suffix}'; shutil.copy2(path,target); return target
    def backup_all(self):
        stamp=time.strftime('%Y%m%d-%H%M%S'); target=BACKUPS_DIR/f'settings-{stamp}'; target.mkdir(parents=True,exist_ok=True)
        for section in FILE_NAMES:
            p=self.path_for(section)
            if p.exists(): shutil.copy2(p,target/p.name)
        return target
    def export_all(self,target:Path): target.write_text(json.dumps({s:self.load(s) for s in FILE_NAMES},ensure_ascii=False,indent=2),encoding='utf-8')
    def import_all(self,source:Path):
        payload=json.loads(source.read_text(encoding='utf-8'))
        if not isinstance(payload,dict): raise ValueError('Файл импорта должен содержать объект JSON')
        self.backup_all()
        for section in FILE_NAMES:
            if isinstance(payload.get(section),dict):
                data=self._merge(DEFAULTS[section],payload[section]); self._normalize(section,data); self.save(section,data)

settings=SettingsManager()
