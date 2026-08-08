from __future__ import annotations

import json
import threading
import urllib.parse
import urllib.request
import webbrowser

from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QSlider, QVBoxLayout, QWidget

from ...core.event_log import log
from ...player.engine import PlayerEngine
from ..runtime import get_runtime


class _Signals(QObject):
    message=Signal(str)
    queue_changed=Signal()


class MediaPlayerPage(QWidget):
    def __init__(self, theme: dict):
        super().__init__(); self.theme=theme; self.runtime=get_runtime(); self.queue=self.runtime.queue; self.config=self.runtime.player_config; self.port=int(self.config.get('port',5000)); self.engine=None; self.signals=_Signals(self); self.signals.message.connect(self._status); self.signals.queue_changed.connect(self.refresh_queue); self.runtime.subscribe_queue(self._queue_notice)
        root=QVBoxLayout(self); root.setContentsMargins(28,22,28,26); root.setSpacing(10)
        title=QLabel("Медиаплеер заказов"); title.setObjectName("pageTitle"); sub=QLabel("Очередь, VLC и API Streamer.bot работают в новом интерфейсе."); sub.setObjectName("pageSubtitle"); root.addWidget(title); root.addWidget(sub)
        top=QHBoxLayout(); self.server=QLabel(f"● API: 127.0.0.1:{self.port}"); self.server.setObjectName("cardText"); top.addWidget(self.server); top.addStretch(1)
        for text,url in (("API /status",f"http://127.0.0.1:{self.port}/status"),("OBS /player",f"http://127.0.0.1:{self.port}/player")):
            b=QPushButton(text); b.clicked.connect(lambda _=False,u=url:webbrowser.open(u)); top.addWidget(b)
        root.addLayout(top)
        body=QHBoxLayout(); body.setSpacing(12)
        left=QFrame(); left.setObjectName("heroCard"); ll=QVBoxLayout(left); ll.setContentsMargins(14,14,14,14)
        self.video=QFrame(); self.video.setObjectName("videoFrame"); self.video.setMinimumHeight(280); ll.addWidget(self.video,1)
        self.now=QLabel("Сейчас ничего не играет"); self.now.setObjectName("heroTitle"); self.user=QLabel("Очередь ожидает заказов"); self.user.setObjectName("cardText"); ll.addWidget(self.now); ll.addWidget(self.user)
        self.seek=QSlider(Qt.Horizontal); self.seek.setRange(0,1000); self.seek.sliderReleased.connect(self.seek_release); ll.addWidget(self.seek)
        controls=QHBoxLayout(); play=QPushButton("▶ Следующий"); play.setObjectName("primaryButton"); play.clicked.connect(self.play_next); pause=QPushButton("⏯ Пауза"); pause.clicked.connect(self.pause); stop=QPushButton("⏹ Стоп"); stop.clicked.connect(self.stop); skip=QPushButton("⏭ Скип"); skip.clicked.connect(self.skip)
        for b in (play,pause,stop,skip):controls.addWidget(b)
        controls.addWidget(QLabel("🔊")); self.volume=QSlider(Qt.Horizontal); self.volume.setRange(0,100); self.volume.setValue(int(self.config.get('volume',30))); self.volume.valueChanged.connect(self.set_volume); controls.addWidget(self.volume); ll.addLayout(controls)
        addrow=QHBoxLayout(); self.user_in=QLineEdit("Merzo4"); self.query=QLineEdit(); self.query.setPlaceholderText("Ссылка YouTube или название"); add=QPushButton("Добавить"); add.clicked.connect(self.add_order); addrow.addWidget(self.user_in); addrow.addWidget(self.query,1); addrow.addWidget(add); ll.addLayout(addrow)
        self.result=QLabel(""); self.result.setWordWrap(True); self.result.setObjectName("cardText"); ll.addWidget(self.result); body.addWidget(left,3)
        right=QFrame(); right.setObjectName("contentCard"); rl=QVBoxLayout(right); rl.setContentsMargins(14,14,14,14); h=QLabel("Очередь заказов"); h.setObjectName("cardTitle"); rl.addWidget(h); self.list=QListWidget(); rl.addWidget(self.list,1)
        qr=QHBoxLayout(); rem=QPushButton("Удалить"); rem.clicked.connect(self.remove); clear=QPushButton("Очистить"); clear.clicked.connect(self.clear); refresh=QPushButton("Обновить"); refresh.clicked.connect(self.refresh_queue); qr.addWidget(rem); qr.addWidget(clear); qr.addWidget(refresh); rl.addLayout(qr)
        api=QLabel(f"Streamer.bot:\nhttp://127.0.0.1:{self.port}/add?user=%userName%&query=%rawInput%"); api.setWordWrap(True); api.setObjectName("cardText"); rl.addWidget(api); body.addWidget(right,2); root.addLayout(body,1)
        self.timer=QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(700); QTimer.singleShot(300,self.init_engine); self.refresh_queue()

    def _queue_notice(self): self.signals.queue_changed.emit()
    def init_engine(self):
        try:
            self.engine=PlayerEngine(int(self.video.winId()),int(self.config.get('volume',30))); self._status("VLC подключён." if self.engine.available else "VLC недоступен: "+self.engine.last_error)
        except Exception as e:self._status("VLC: "+str(e))
    def refresh_queue(self):
        self.list.clear(); snap=self.queue.snapshot(); cur=snap.get('current')
        for i,item in enumerate(snap.get('queue',[]),1):self.list.addItem(f"{i}. {item.get('title','Без названия')} — @{item.get('user','Зритель')}")
        if cur:self.now.setText(cur.get('title','Без названия')); self.user.setText("Заказал @"+cur.get('user','Зритель'))
        else:self.now.setText("Сейчас ничего не играет"); self.user.setText(f"В очереди: {snap.get('queue_length',0)}")
    def play_next(self):
        if not self.engine or not self.engine.available:return self._status("VLC не готов.")
        if self.queue.current is not None:self.queue.finish_current()
        item=self.queue.pop_next()
        if not item:return self._status("Очередь пуста.")
        if self.engine.play(item.url):
            self.runtime.player_state.update({'url':item.url,'paused':False,'stopped':False,'time':0}); self.refresh_queue(); self._status("▶ "+item.title)
        else:self._status("Не удалось запустить видео. Возможно, ссылка устарела — добавь заказ заново.")
    def pause(self):
        if self.engine and self.engine.available:
            paused=self.engine.toggle_pause(); self.runtime.player_state['paused']=paused; self._status("Пауза" if paused else "Продолжено")
    def stop(self):
        if self.engine:self.engine.stop()
        self.runtime.player_state.update({'url':'','paused':False,'stopped':True,'time':0}); self.queue.save_state(stopped=True,force=True); self._status("Остановлено")
    def skip(self):
        if self.engine:self.engine.stop()
        self.queue.finish_current(); self.play_next()
    def set_volume(self,v):
        if self.engine:self.engine.set_volume(v)
        self.config['volume']=int(v)
    def seek_release(self):
        if self.engine and self.engine.available:self.engine.set_position_percent(self.seek.value()/10)
    def tick(self):
        if self.engine and self.engine.available:
            length=self.engine.length_ms(); pos=self.engine.time_ms(); self.runtime.player_state['time']=pos//1000
            if length>0 and not self.seek.isSliderDown():self.seek.setValue(int(pos*1000/length))
            if self.engine.is_finished():self.queue.finish_current(); self.play_next()
        self.refresh_queue()
    def add_order(self):
        user=self.user_in.text().strip() or 'Merzo4'; query=self.query.text().strip()
        if not query:return self._status("Введите ссылку или название.")
        self._status("Ищу видео…")
        url=f"http://127.0.0.1:{self.port}/add?"+urllib.parse.urlencode({'user':user,'query':query})
        def job():
            try:
                with urllib.request.urlopen(url,timeout=35) as r:data=json.loads(r.read().decode('utf-8'))
                self.signals.message.emit(str(data.get('message','Готово'))); self.signals.queue_changed.emit()
            except Exception as e:self.signals.message.emit("Ошибка добавления: "+str(e))
        threading.Thread(target=job,daemon=True).start()
    def remove(self):
        i=self.list.currentRow()
        if i>=0:self.queue.remove(i); self.refresh_queue()
    def clear(self):
        if QMessageBox.question(self,"Очередь","Очистить очередь?")==QMessageBox.Yes:self.queue.clear(); self.refresh_queue()
    def _status(self,text): self.result.setText(text); log('PLAYER QT',text)
    def shutdown(self):
        self.runtime.unsubscribe_queue(self._queue_notice)
        if self.engine:self.engine.release()
