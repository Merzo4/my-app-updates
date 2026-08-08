from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget


class HelpPage(QWidget):
    def __init__(self, theme: dict):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 26)
        title = QLabel("Инструкция")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        box = QTextEdit()
        box.setReadOnly(True)
        box.setPlainText(
            "ПОДСКАЗКИ\n"
            "Наведи курсор на кнопку, поле, список, ползунок или пункт навигации — программа объяснит его назначение.\n\n"
            "УПРАВЛЕНИЕ ТРАНСЛЯЦИЕЙ\n"
            "Название и категория отправляются в выбранные площадки.\n\n"
            "МЕДИАПЛЕЕР\n"
            "Streamer.bot Fetch URL:\nhttp://127.0.0.1:5000/add?user=%userName%&query=%rawInput%\n"
            "OBS Browser Source: http://127.0.0.1:5000/player\n\n"
            "ФОНОВАЯ МУЗЫКА\n"
            "OBS Browser Source: http://127.0.0.1:5000/music\n"
            "Можно добавить локальные файлы или вставить ссылку на один трек. Если сайт не даёт скачать автоматически, "
            "используй его официальный Download и затем добавь полученный файл.\n\n"
            "ЕДИНЫЙ ЧАТ\n"
            "OBS Browser Source: http://127.0.0.1:5001/chat\n"
            "Добавление сообщений: /chat/add?platform=Twitch&user=%userName%&message=%rawInput%\n\n"
            "ОБНОВЛЕНИЯ\n"
            "Открой раздел «Обновления», проверь GitHub, изучи список изменённых файлов и установи. "
            "Перед заменой Update Engine создаёт резервную копию."
        )
        layout.addWidget(box, 1)
