MerzoStream Suite Bootstrap Installer

Файл:
  MerzoStreamSetup.exe

Назначение:
  Полная установка MerzoStream Suite на чистый Windows x64 компьютер.

Что делает установщик:
  - запрашивает UAC;
  - устанавливает программу в C:\Program Files\MerzoStreamSuite;
  - хранит настройки/Cloud/логи отдельно в %LOCALAPPDATA%\MerzoStreamSuite;
  - получает список GitHub Releases Merzo4/my-app-updates;
  - выбирает самую новую версию с тегом v0.0.x;
  - скачивает MerzoStreamSuite-<version>.zip;
  - проверяет SHA-256;
  - безопасно распаковывает ZIP;
  - проверяет каждый файл по release_manifest.json;
  - при необходимости скачивает официальный Python 3.12 runtime;
  - создаёт изолированное окружение и устанавливает зависимости;
  - создаёт ярлыки рабочего стола и меню Пуск;
  - регистрирует MerzoStream Suite в списке установленных приложений;
  - запускает первый health-check через Central Launcher.

Повторный запуск:
  Кнопка «Обновить / восстановить» заново проверит и восстановит файлы программы,
  не удаляя пользовательские настройки и Cloud.

Удаление:
  Windows → Установленные приложения → MerzoStream Suite → Удалить.
  Пользовательские настройки и Cloud при обычном удалении сохраняются.

Важно:
  Этот bootstrap не привязан к конкретной версии MerzoStream Suite.
  Он всегда выбирает самый новый опубликованный GitHub Release формата v0.0.x.

Лог установки:
  %LOCALAPPDATA%\MerzoStreamSuite\logs\setup.log
