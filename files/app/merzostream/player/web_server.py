from __future__ import annotations

import logging
import threading
from typing import Callable, Any

from flask import Flask, jsonify, render_template_string, request, send_from_directory

from ..core.event_log import log
from ..core.database import database
from .queue_manager import QueueItem, QueueManager
from .youtube_resolver import YouTubeResolver
from .background_music import MUSIC_DIR, background_music


PLAYER_HTML = r"""
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<style>
html,body{width:100%;height:100%;margin:0;background:transparent;overflow:hidden}
#wrap{width:100%;height:100%;opacity:0;transition:opacity .35s ease}
video{width:100%;height:100%;object-fit:contain}
</style>
</head>
<body>
<div id="wrap"><video id="player" autoplay></video></div>
<script>
const player=document.getElementById('player');
const wrap=document.getElementById('wrap');
let currentUrl='';
let failedPolls=0;
function clearPlayer(){
  wrap.style.opacity='0';
  if(currentUrl || player.getAttribute('src')){
    player.pause();
    player.removeAttribute('src');
    player.load();
    currentUrl='';
  }
}
setInterval(async()=>{
  try{
    const response=await fetch('/video_data',{cache:'no-store'});
    const data=await response.json();
    failedPolls=0;
    if(!data.url || data.stopped){
      clearPlayer();
      return;
    }
    wrap.style.opacity='1';
    if(data.url!==currentUrl){
      currentUrl=data.url;
      player.src=currentUrl;
      player.play().catch(()=>{});
    }
    if(data.paused && !player.paused) player.pause();
    if(!data.paused && player.paused) player.play().catch(()=>{});
    const remoteTime=Number(data.time||0);
    if(Math.abs(remoteTime-player.currentTime)>5) player.currentTime=remoteTime;
  }catch(_error){
    failedPolls+=1;
    if(failedPolls>=2) clearPlayer();
  }
},1000);
</script>
</body>
</html>
"""


MUSIC_HTML = r"""
<!doctype html><html lang="ru"><head><meta charset="utf-8">
<style>html,body{margin:0;background:transparent;overflow:hidden}audio{display:none}</style></head>
<body><audio id="music" autoplay></audio>
<script>
const audio=document.getElementById('music'); let current=''; let lastSeek=0;
async function control(action,value=''){try{await fetch('/music_control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,value})});}catch(e){}}
audio.addEventListener('ended',()=>control('ended'));
setInterval(async()=>{
 try{const r=await fetch('/music_status',{cache:'no-store'}); const d=await r.json();
 const t=d.current; if(!t||!d.playing){audio.pause();audio.removeAttribute('src');current='';return;}
 const wanted='/music_file/'+encodeURIComponent(t.filename);
 if(wanted!==current){current=wanted;audio.src=wanted;audio.currentTime=Number(d.position||0);audio.play().catch(()=>{});}
 audio.volume=Math.max(0,Math.min(1,Number(d.volume||35)/100));
 if(d.paused&&!audio.paused)audio.pause(); if(!d.paused&&audio.paused)audio.play().catch(()=>{});
 const pos=Number(d.position||0); if(Math.abs(audio.currentTime-pos)>6){audio.currentTime=pos;}
 }catch(e){}
},800);
setInterval(()=>{if(current&&!audio.paused)control('position',audio.currentTime)},5000);
</script></body></html>
"""


class PlayerWebServer:
    def __init__(
        self,
        queue: QueueManager,
        config: dict[str, Any],
        player_state: dict[str, Any],
        on_queue_changed: Callable[[], None],
    ):
        self.queue = queue
        self.config = config
        self.player_state = player_state
        self.on_queue_changed = on_queue_changed
        self.app = Flask("merzostream_player")
        self._started = False
        self._register_routes()

    def _register_routes(self) -> None:
        @self.app.get("/add")
        def add_request():
            query = request.args.get("query", "").strip()
            user = request.args.get("user", "Зритель").strip() or "Зритель"
            log("PLAYER API", f"Запрос от @{user}: {query}")

            if not query:
                return jsonify({"message": f"❌ @{user}, укажите ссылку или название.", "status": 400})

            try:
                result = YouTubeResolver(self.config, status=lambda message: log("PLAYER SEARCH", message)).resolve(query)
                if result.info is None:
                    database.add_media_event(title=query, user=user, result="rejected", reason=result.reason)
                    return jsonify({"message": f"❌ @{user}, {result.reason}", "status": 400})

                info = result.info
                video_id = str(info.get("id", ""))
                duration = int(info.get("duration") or 0)
                view_count = int(info.get("view_count") or 0)
                allowed, error_message = self.queue.validate_request(user, video_id, duration, view_count)
                if not allowed:
                    database.add_media_event(
                        video_id=video_id, title=str(info.get("title", "Без названия")), user=user,
                        webpage_url=str(info.get("webpage_url", "")), duration=duration,
                        view_count=view_count, result="rejected", reason=error_message
                    )
                    return jsonify({"message": error_message, "status": 400})

                item = QueueItem(
                    id=video_id,
                    url=str(info.get("url", "")),
                    webpage_url=str(info.get("webpage_url", "")),
                    title=str(info.get("title", "Без названия")),
                    user=user,
                    duration=duration,
                    view_count=view_count,
                )
                position = self.queue.add(item)
                self.on_queue_changed()
                log("PLAYER API", f"Добавлено: {item.title} — @{user}")

                if self.queue.current is None and position == 1:
                    message = f"🎵 @{user} заказал: {item.title}. Ожидает запуска."
                else:
                    message = f"✅ @{user} заказал: {item.title}. Позиция в очереди: {position}."
                return jsonify({"message": message, "status": 200, "position": position})
            except Exception as exc:
                log("PLAYER API", f"Ошибка обработки заказа: {exc}")
                return jsonify({"message": f"❌ @{user}, видео не найдено или недоступно.", "status": 400})

        @self.app.get("/status")
        def status():
            snapshot = self.queue.snapshot()
            current = snapshot["current"]
            if current:
                message = (
                    f"🎶 Сейчас играет: {current['title']} "
                    f"(заказал @{current['user']}). В очереди: {snapshot['queue_length']}."
                )
            else:
                message = f"📭 Сейчас ничего не играет. В очереди: {snapshot['queue_length']}."
            return jsonify({"message": message, "status": 200, **snapshot})

        @self.app.get("/queue")
        def queue_state():
            return jsonify({"status": 200, **self.queue.snapshot()})

        @self.app.get("/video_data")
        def video_data():
            return jsonify(dict(self.player_state))

        @self.app.get("/player")
        def player_page():
            return render_template_string(PLAYER_HTML)

        @self.app.get("/music")
        def music_page():
            return render_template_string(MUSIC_HTML)

        @self.app.get("/music_status")
        def music_status():
            return jsonify(background_music.snapshot())

        @self.app.get("/music_file/<path:filename>")
        def music_file(filename: str):
            return send_from_directory(MUSIC_DIR, filename, conditional=True)

        @self.app.post("/music_control")
        def music_control():
            data = request.get_json(silent=True) or {}
            action = str(data.get("action", ""))
            value = data.get("value")
            if action == "play": background_music.play()
            elif action == "pause": background_music.pause_toggle()
            elif action == "stop": background_music.stop()
            elif action == "next": background_music.next()
            elif action == "previous": background_music.previous()
            elif action == "ended": background_music.ended()
            elif action == "position":
                try: background_music.set_position(float(value))
                except Exception: pass
            elif action == "volume":
                try: background_music.set_volume(float(value))
                except Exception: pass
            return jsonify({"ok": True, **background_music.snapshot()})

        @self.app.get("/health")
        def health():
            return jsonify({"ok": True, "service": "MerzoStreamSuite Player API"})

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        port = int(self.config.get("port", 5000))
        logging.getLogger("werkzeug").setLevel(logging.ERROR)

        def run_server() -> None:
            try:
                self.app.run(
                    host="127.0.0.1",
                    port=port,
                    threaded=True,
                    use_reloader=False,
                )
            except OSError as exc:
                log("PLAYER API", f"Не удалось запустить порт {port}: {exc}")
            except Exception as exc:
                log("PLAYER API", f"Сервер завершился с ошибкой: {exc}")

        threading.Thread(target=run_server, name="MerzoPlayerAPI", daemon=True).start()
        log("PLAYER API", f"Сервер запускается: http://127.0.0.1:{port}")
