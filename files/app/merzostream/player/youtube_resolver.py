from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from dataclasses import dataclass
from typing import Any, Callable
import time
import yt_dlp

class _SilentLogger:
    def debug(self, _msg): pass
    def warning(self, _msg): pass
    def error(self, _msg): pass

@dataclass(slots=True)
class ResolveResult:
    info: dict[str, Any] | None
    reason: str = ""

class YouTubeResolver:
    def __init__(self, config: dict[str, Any], status: Callable[[str],None] | None=None):
        self.config=config; self.status=status or (lambda _m:None)
    def _base_options(self,use_cookies=False):
        opts={
            'quiet':True,'no_warnings':True,'logger':_SilentLogger(),'noplaylist':not bool(self.config.get('allow_playlists',False)),
            'format':'best[ext=mp4]/best','socket_timeout':5,'retries':0,'extractor_retries':0,'skip_download':True,
            'ignoreerrors':False,'extractor_args':{'youtube':{'player_client':['android','web','tv']}},
        }
        if use_cookies and bool(self.config.get('cookies_enabled',False)):
            browser=str(self.config.get('cookies_browser','chrome') or 'chrome').strip().lower()
            if browser not in {'','none','off','нет'}: opts['cookiesfrombrowser']=(browser,)
        return opts
    def _search_options(self):
        o=self._base_options(False); o.update({'extract_flat':'in_playlist','format':None,'ignoreerrors':True}); return o
    @staticmethod
    def _is_url(q): return q.lower().strip().startswith(('http://','https://'))
    @staticmethod
    def _candidate_url(c):
        for k in ('webpage_url','original_url'):
            v=str(c.get(k) or '').strip()
            if v.startswith(('http://','https://')): return v
        vid=str(c.get('id') or '').strip()
        return f'https://www.youtube.com/watch?v={vid}' if vid else ''
    def _reject_reason(self,info):
        title=str(info.get('title','')); uploader=str(info.get('uploader') or info.get('channel') or '')
        duration=int(info.get('duration') or 0); views=int(info.get('view_count') or 0)
        live=str(info.get('live_status') or ''); age=int(info.get('age_limit') or 0); url=str(info.get('webpage_url') or '')
        hay=f'{title} {uploader}'.lower()
        for word in [str(x).lower().strip() for x in self.config.get('blocked_words',[]) if str(x).strip()]:
            if word in hay:return f'содержит запрещённое слово: {word}'
        blocked={str(x).lower().strip() for x in self.config.get('blocked_channels',[]) if str(x).strip()}
        if uploader.lower().strip() in blocked:return f'канал заблокирован: {uploader}'
        if live in {'is_live','is_upcoming','post_live'} and not self.config.get('allow_live',False):return 'прямые эфиры запрещены'
        if age>=18 and not self.config.get('allow_age_restricted',False):return 'возрастное ограничение'
        if '/shorts/' in url and not self.config.get('allow_shorts',True):return 'Shorts запрещены'
        if not bool(info.get('playable_in_embed',True)) and self.config.get('require_embeddable',False):return 'встраивание запрещено'
        min_sec=max(0,int(self.config.get('min_duration_sec',10) or 0)); max_sec=max(60,int(self.config.get('max_duration_min',10) or 10)*60)
        if duration and duration<min_sec:return f'короче {min_sec} сек.'
        if duration and duration>max_sec:return f'длиннее {max_sec//60} мин.'
        min_views=max(0,int(self.config.get('min_views',0) or 0))
        if views<min_views:return f'мало просмотров: {views}, требуется {min_views}'
        return ''
    def _extract_once(self,source,use_cookies=False):
        try:
            with yt_dlp.YoutubeDL(self._base_options(use_cookies)) as ydl:
                info=ydl.extract_info(source,download=False)
            return info if isinstance(info,dict) else None
        except Exception:return None
    def _extract_video(self,source):
        info=self._extract_once(source,False)
        if info is None and bool(self.config.get('cookies_enabled',False)): info=self._extract_once(source,True)
        return info
    def _validate(self,c):
        source=self._candidate_url(c); title=str(c.get('title') or c.get('id') or 'Без названия')
        if not source:return None,f'{title}: нет ссылки'
        info=self._extract_video(source)
        if info is None:return None,f'{title}: недоступно'
        reason=self._reject_reason(info)
        if reason:return None,f"{info.get('title',title)}: {reason}"
        if not info.get('url'):return None,f"{info.get('title',title)}: нет прямой ссылки"
        return info,''
    def resolve(self,query):
        query=query.strip()
        if not query:return ResolveResult(None,'пустой запрос')
        self.status('Поиск YouTube...')
        if self._is_url(query):
            info=self._extract_video(query)
            if info is None:return ResolveResult(None,'видео по ссылке недоступно')
            reason=self._reject_reason(info)
            return ResolveResult(None,reason) if reason else ResolveResult(info)
        count=max(1,min(20,int(self.config.get('search_results',8) or 8)))
        try:
            with yt_dlp.YoutubeDL(self._search_options()) as ydl: extracted=ydl.extract_info(f'ytsearch{count}:{query}',download=False)
        except Exception:return ResolveResult(None,'ошибка поиска YouTube')
        entries=extracted.get('entries') if isinstance(extracted,dict) else None
        candidates=[e for e in (entries or []) if isinstance(e,dict)]
        if not candidates:return ResolveResult(None,'YouTube не вернул результатов')
        self.status(f'Проверяю варианты: {len(candidates)}...')
        timeout=max(5,min(30,int(self.config.get('search_timeout_sec',12) or 12)))
        workers=max(1,min(6,int(self.config.get('parallel_checks',3) or 3)))
        reasons=[]; executor=ThreadPoolExecutor(max_workers=min(workers,len(candidates)),thread_name_prefix='youtube-check')
        futures=[executor.submit(self._validate,c) for c in candidates]
        try:
            for f in as_completed(futures,timeout=timeout):
                info,reason=f.result()
                if info is not None:
                    for p in futures:p.cancel()
                    executor.shutdown(wait=False,cancel_futures=True); self.status(f"Найдено: {info.get('title','Видео')}")
                    return ResolveResult(info)
                if reason:reasons.append(reason)
        except TimeoutError: pass
        finally:
            for p in futures:p.cancel()
            executor.shutdown(wait=False,cancel_futures=True)
        return ResolveResult(None,'подходящее видео не найдено: '+('; '.join(reasons[:3]) if reasons else f'таймаут {timeout} сек.'))
