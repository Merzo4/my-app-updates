"""Совместимый фасад. Новая реализация находится в services/stream/."""
from .stream import StreamManager


class StreamServices(StreamManager):
    pass
