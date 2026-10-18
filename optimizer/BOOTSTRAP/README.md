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

## Native Test Center EXE — 0.2.0 (Windows acceptance pending)
Pinned updater `optimizer/BOOTSTRAP/INSTALL_TEST_CENTER.bat` now downloads the separate Test Center infrastructure SHA `f8757abcfabf0780fcf891661e0e1596dc1ad96a` and two `NativeHost/` C#/.NET 10 files, then compiles/publishes a self-contained win-x64 `MerzoOptimizer.TestCenter.exe` on the local Windows machine and performs a WinForms smoke check **before redirecting the desktop shortcut**. Native source is in branch `mwo-local-test-center`; full local artifacts at `D:\MerzoOptimizer-LocalLab\App\Native\`. **This conversion has not been run on owner's PC; PENDING**.

After a successful build, desktop icon opens EXE directly: no visible PowerShell GUI or terminal. PowerShell 7 remains internally for Diagnostics/QUICK/FULL SAFE and auto GitHub evidence (invisible child process). To recover older GUI, use `D:\MerzoOptimizer-LocalLab\START-TEST-CENTER-LEGACY.bat`. A failed native build should preserve previous launcher and report Logs/native-build.log. Do not run update while active profiles execute. Preflight .NET 10 SDK already passed on owner's diagnostics; Inno Setup 6 still required for R57 product builds, independently.

## 0.2.1 critical parser repair of native EXE installation
Previous 0.2.0 installer failed at `Install-LocalLab.ps1:30` with `TEST CENTER PARSER FAIL MerzoOptimizer.LocalLab.ps1`. Source was accidentally duplicated during the 0.1.9 Windows 11 label change, not due to owner OS. Separate `mwo-local-test-center@1db2b1d91ea699a84fd0a374b00867c185d9e8c9` restores original proven 0.1.8 498-line PS GUI and safely inserts exactly one OS display function, now 531 lines, and bumps profile/native host to 0.2.1. Owner machine new installation Windows result pending. This file pins exact repaired source. As before .NET 10 SDK is needed to locally compile native EXE and PowerShell 7 remains an invisible backend. On failed build or smoke, previous desktop shortcut should remain intact.

## 0.2.2 — inherited TMP-as-file fix
Owner's 0.2.1 log shows Parser PASS, legacy WinForms GUI Smoke PASS, native `dotnet publish` FAIL (`MSB1025`) because Windows `TMP` inherited `...\Temp\INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat` which was **a file**. The existing installed `UPDATE-TEST-CENTER.bat` assigned `TMP` to its downloaded BAT path. This is a launcher environment bug, not .NET or Windows corruption. New infrastructure SHA `39b17f00c7270bca7ee3a5df607e51420c4ae2fc` v0.2.2: generated updater now uses `MWO_UPDATE_DOWNLOAD`; standalone root bootstrap, Install-LocalLab.ps1, and Build-NativeHost.ps1 each enforce valid process-scoped `TEMP/TMP` under `D:\MerzoOptimizer-LocalLab\Temp\ToolchainTemp`. Pinned user BAT also resets them for legacy updater compatibility. No machine-global environment, user files or optimizer production executable are modified. New native runtime on Windows NOT RUN after fix.
