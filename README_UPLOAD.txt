MerzoStream Suite 0.0.2i — FIXED GitHub paths

Исправлено: файлы Python для автообновления лежат в files/app/merzostream, потому что Update Engine принимает логический путь app/merzostream и сам переводит его в src/merzostream при запуске из исходников.

Скопировать manifest.json и папку files в корень репозитория my-app-updates с заменой, Commit, Push origin.
