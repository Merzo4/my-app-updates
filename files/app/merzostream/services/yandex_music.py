from __future__ import annotations
import ctypes, subprocess
VK_MEDIA_PLAY_PAUSE=0xB3; VK_MEDIA_NEXT_TRACK=0xB0; VK_MEDIA_PREV_TRACK=0xB1

def _press(vk:int):
    ctypes.windll.user32.keybd_event(vk,0,0,0); ctypes.windll.user32.keybd_event(vk,0,2,0)
def play_pause(): _press(VK_MEDIA_PLAY_PAUSE)
def next_track(): _press(VK_MEDIA_NEXT_TRACK)
def previous_track(): _press(VK_MEDIA_PREV_TRACK)
def launch(): subprocess.Popen(['cmd','/c','start','','yandexmusic://'],shell=False)
