from __future__ import annotations

import logging
import threading
from typing import Any

from flask import Flask, jsonify, render_template_string, request

from ..core.event_log import log
from .manager import ChatManager, chat_manager


CHAT_HTML = r"""
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--font-size:30px;--max-width:900px;--fade:22s}
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:transparent;font-family:Arial,sans-serif}
#chat{position:absolute;left:18px;right:18px;bottom:18px;display:flex;flex-direction:column;gap:10px;align-items:flex-start}
.msg{max-width:var(--max-width);padding:10px 14px;border-radius:14px;background:rgba(8,10,16,.72);color:#fff;font-size:var(--font-size);line-height:1.25;text-shadow:0 2px 3px #000;box-shadow:0 4px 18px rgba(0,0,0,.28);animation:enter .22s ease-out}
.platform{font-size:.58em;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:3px 7px;border-radius:999px;margin-right:8px;vertical-align:middle;background:#777}
.user{font-weight:800;margin-right:7px}.text{word-break:break-word}
.p-twitch{background:#9146ff}.p-youtube{background:#ff0033}.p-vk{background:#2787f5}.p-kick{background:#53fc18;color:#071007}.p-rutony{background:#ff8a00}.p-streamerbot{background:#1bb3a9}.p-other{background:#6b7280}
@keyframes enter{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
</style>
</head>
<body><div id="chat"></div>
<script>
const box=document.getElementById('chat');let lastId=0;let known=new Set();
const params=new URLSearchParams(location.search);
const maxMessages=Math.max(1,Math.min(30,Number(params.get('messages')||8)));
const lifetime=Math.max(3,Math.min(120,Number(params.get('lifetime')||22)))*1000;
const font=Math.max(14,Math.min(80,Number(params.get('font')||30)));
document.documentElement.style.setProperty('--font-size',font+'px');
function esc(v){const d=document.createElement('div');d.textContent=String(v??'');return d.innerHTML}
function add(m){if(known.has(m.id))return;known.add(m.id);lastId=Math.max(lastId,Number(m.id||0));const el=document.createElement('div');el.className='msg';el.dataset.id=m.id;el.innerHTML=`<span class="platform p-${esc(m.platform)}">${esc(m.platform)}</span><span class="user">${esc(m.user)}:</span><span class="text">${esc(m.message)}</span>`;box.appendChild(el);while(box.children.length>maxMessages)box.firstElementChild.remove();setTimeout(()=>{el.style.transition='opacity .5s';el.style.opacity='0';setTimeout(()=>el.remove(),520)},lifetime)}
async function poll(){try{const r=await fetch('/chat/messages?after='+lastId+'&limit=50',{cache:'no-store'});const d=await r.json();(d.messages||[]).forEach(add)}catch(e){}finally{setTimeout(poll,700)}}poll();
</script></body></html>
"""


class ChatWebServer:
    def __init__(self, manager: ChatManager | None = None, port: int = 5001) -> None:
        self.manager = manager or chat_manager
        self.port = int(port)
        self.app = Flask("merzostream_chat")
        self._started = False
        self._register_routes()

    def _register_routes(self) -> None:
        @self.app.route("/chat/add", methods=["GET", "POST"])
        def add_message():
            data: dict[str, Any] = request.get_json(silent=True) or {}
            source = data if request.method == "POST" else request.args
            try:
                payload = self.manager.add(
                    platform=str(source.get("platform", "other")),
                    user=str(source.get("user", source.get("username", "Зритель"))),
                    message=str(source.get("message", source.get("text", ""))),
                    color=str(source.get("color", "")),
                    badges=str(source.get("badges", "")),
                    avatar=str(source.get("avatar", "")),
                )
                return jsonify({"ok": True, "status": 200, "message": payload})
            except ValueError as exc:
                return jsonify({"ok": False, "status": 400, "error": str(exc)}), 400
            except Exception as exc:
                log("CHAT API", f"Ошибка добавления сообщения: {exc}", "ERROR")
                return jsonify({"ok": False, "status": 500, "error": "Внутренняя ошибка"}), 500

        @self.app.get("/chat/messages")
        def messages():
            limit = request.args.get("limit", 80, type=int) or 80
            after = request.args.get("after", 0, type=int) or 0
            platforms_raw = request.args.get("platforms", "")
            platforms = {x.strip() for x in platforms_raw.split(",") if x.strip()} or None
            items = self.manager.snapshot(limit=limit, platforms=platforms)
            if after:
                items = [item for item in items if int(item.get("id", 0)) > after]
            return jsonify({"ok": True, "messages": items, "count": len(items)})

        @self.app.post("/chat/clear")
        def clear():
            data = request.get_json(silent=True) or {}
            self.manager.clear(bool(data.get("history", False)))
            return jsonify({"ok": True})

        @self.app.get("/chat")
        def chat_overlay():
            return render_template_string(CHAT_HTML)

        @self.app.get("/health")
        def health():
            return jsonify({"ok": True, "service": "MerzoStreamSuite Chat API", "port": self.port})

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        logging.getLogger("werkzeug").setLevel(logging.ERROR)

        def run() -> None:
            try:
                self.app.run(host="127.0.0.1", port=self.port, threaded=True, use_reloader=False)
            except OSError as exc:
                log("CHAT API", f"Не удалось запустить порт {self.port}: {exc}", "ERROR")
            except Exception as exc:
                log("CHAT API", f"Сервер завершился с ошибкой: {exc}", "ERROR")

        threading.Thread(target=run, name="MerzoChatAPI", daemon=True).start()
        log("CHAT API", f"Единый чат: http://127.0.0.1:{self.port}/chat", "SUCCESS")
