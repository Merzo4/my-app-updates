# Merzo Windows Optimizer — bootstrap files

Папка для нового ПК и нового ChatGPT-чата. Продукт и Test Center устанавливаются **раздельно**.

- `INSTALL_WINDOWS_OPTIMIZER.bat` — скачивает точно опубликованный официальный **mwo-v0.1.55.1** из GitHub Releases, проверяет **фиксированный SHA-256** и запускает обычный установщик. Не устанавливает непроверенный R57. Не удаляет пользовательские данные; не допускает автоматического downgrade с более новой установленной версии. Перед установкой Windows может запросить UAC.
- `INSTALL_TEST_CENTER.bat` — скачивает версию **0.1.7** инфраструктуры из immutable commit `edc83fca9f0f89fc895a0a30c7f58f81af143779` ветки `mwo-local-test-center`; ставит отдельно в `D:\MerzoOptimizer-LocalLab`, запускает GUI и создаёт ярлык. Требует диск D:. В него может входить установка официального PowerShell 7 через UAC, если ещё нет. Для QUICK/FULL SAFE нужны Git, .NET 10 SDK и Inno Setup 6 (диагностика сообщит о недостающем).
- `NEW_CHAT_PROMPT.txt` — полный текст для вставки в новый чат.
 
## Рекомендованный порядок

1. На новом ПК дважды нажать `INSTALL_WINDOWS_OPTIMIZER.bat`; проверить UAC, завершить установку стабильной версии.
2. Проверить наличие диска D:, затем запустить `INSTALL_TEST_CENTER.bat`. Не выполнять GAME → RESTORE на рабочем ПК.
3. В Test Center: «Диагностика» → «Обновить Source» → QUICK → FULL SAFE. Обычная production установка в Program Files должна остаться неизменной.
4. В новом ChatGPT-чате вставить `NEW_CHAT_PROMPT.txt`. ИИ обязан самостоятельно открыть GitHub SOT и актуальный checkpoint.

## Provenance / Safety

- SHA-256 официального `MerzoWindowsOptimizerSetup-win-x64.exe` релиза 0.1.55.1: `bda73f442a1726082372e8c4272668e0151c9d882df1350f417fadcc022a1035`.
- Test Center bootstrap sources pinned к immutable commit, а не подвижному branch URL. Сам Test Center загружает последнюю R57 source-ветку и имеет автоотправку обезличенных диагностических событий в GitHub ветку `mwo-local-lab-evidence` при доступной GitHub авторизации.
- BAT выполняются только на Windows; здесь возможна статическая проверка содержимого, но реальное выполнение на ПК пользователя не проводилось.
- Для будущего стабильного релиза нужно обновить pin SHA/version в BAT после evidence/owner approval. Не использовать `latest` общих GitHub Releases — там также MerzoStream Suite.

## Windows GUI startup defect and fix (2026-10-18)
Reported 0.1.7: no visible Test Center on first click; second click says already running. Fix 0.1.8 in `mwo-local-test-center@3523eaabba8461aa63ec80a3da9d7270180ffd3a` is prepared. Updated `INSTALL_TEST_CENTER.bat` offers to stop only old matching Test Center GUI processes after confirmation and then pins 0.1.8; preserves App/Logs/Results and installed Optimizer. If still hidden, use `RECOVER_TEST_CENTER_WINDOW.bat` to start GUI with a visible diagnostic console. Send startup-error.log or gui-visibility-error.log if necessary. Test 0.1.8 installation on user Windows remains PENDING.

 
### Final pinned Test Center hotfix SHA / parser-safety correction
Final Test Center 0.1.8 source is `mwo-local-test-center@a6f2cd3fcd31a9b10c994333a00ae5ca3b05b1d3` (supersedes earlier infrastructure hotfix commit 3523eaabba8461aa63ec80a3da9d7270180ffd3a ONLY for the installer source pin). This is a minimal parse-safe native Console Add-Type adjustment; 0.1.8 **WINDOWS NOT RUN/PENDING**. Updated pinned BAT uses this exact immutable SHA. Prior checkpoint 003 is kept unchanged as historical.

## Test Center 0.1.9 Windows version label
Current installer BAT pins `mwo-local-test-center@00f0484cbff48380a205410da1ebf208c7f63de6` and updates Test Center 0.1.9 with a corrected "Windows 11 Pro / 25H2 / 26200.9457" environment label. Previous 0.1.8 was Windows owner-verified visibly launched; 0.1.9 itself is **NOT RUN on owner's Windows**. Existing installed Test Center has `D:\MerzoOptimizer-LocalLab\UPDATE-TEST-CENTER.bat`, which points to the separate infrastructure branch; close the GUI before updating to avoid singleton mutex conflict. Owner installation and diagnostics results remain separate from this visual-only code change.
