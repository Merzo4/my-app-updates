# Merzo Optimizer Local Test Center

Локальная Windows-лаборатория для **Merzo Windows Optimizer**, сделанная по тому же принципу, что и MerzoStream Test Center: основная масса проверок выполняется на локальном компьютере и **не расходует GitHub Actions minutes**.

## Главное правило

Test Center — это инфраструктура разработки, а не часть Merzo Windows Optimizer. Он не входит в installer продукта и не заменяет публичный release/OTA gate.

Корень лаборатории:

`D:\MerzoOptimizer-LocalLab`

Установленная рабочая программа защищена:

`C:\Program Files\Merzo Windows Optimizer`

Безопасные профили не устанавливают туда кандидат и обязаны доказать, что fingerprint Program Files не изменился.

## Fix 0.1.8: invisible window on first launch

Previous 0.1.7 used `WScript.Shell.Run(..., 0)` to hide pwsh; that may also suppress the visible WinForms main window, while the mutex still blocks a second launch. Version 0.1.8 starts with a normal window style and hides ONLY the host console after the WinForms Shown event. A GUI-shown marker is written to `D:\\MerzoOptimizer-LocalLab\\State\\gui-shown.json`; installer waits for it and fails rather than claiming that an invisible UI is working.

If an old hidden GUI owns the mutex, use the scoped `optimizer/BOOTSTRAP/RECOVER_TEST_CENTER_WINDOW.bat` from active Optimizer branch before reinstall. It must not stop other PowerShell processes or other programs.

## Запуск без терминала

Рабочий ярлык **Merzo Optimizer Test Center** запускает `wscript.exe`, который создаёт скрытый `pwsh`-процесс. Пользователь видит WinForms GUI. В версии 0.1.8 консоль может кратковременно появиться до события Shown; затем скрывается сама консоль, а не окно UI. Видимый PowerShell/Windows Terminal не является частью нормального запуска, поэтому его нельзя случайно закрыть вместе с Test Center.

`START-TEST-CENTER.bat` также только передаёт запуск в `wscript.exe` и сразу завершается.

## Что проверяется локально

### Диагностика

Не собирает продукт и не меняет Windows:
- D: доступен;
- Git доступен;
- PowerShell 7;
- .NET 10 SDK;
- Inno Setup 6;
- Local Lab находится только на D:;
- production Program Files не является test target;
- dedicated Source имеет правильный Git origin.

### Обновить Source

Test Center владеет только:

`D:\MerzoOptimizer-LocalLab\Source`

Именно там разрешены `fetch`, `checkout`, `reset --hard` и `clean -fdx` после проверки origin. Рабочие папки пользователя и установленный Optimizer не используются.

### QUICK

- получает exact target branch;
- запускает текущий cumulative build controller из `local-lab-profile.json`;
- выполняет все встроенные acceptance/SelfTest/startup gates этого controller;
- собирает installer + portable локально;
- staging выполняется в `TestBuild\Quick`;
- проверяется fingerprint установленной production-программы;
- QUICK не делает GAME/служебные мутации Windows.

### FULL SAFE

Включает QUICK и дополнительно:
- запускает exact staged EXE;
- требует настоящее окно Merzo Windows Optimizer;
- отклоняет startup-error;
- проверяет bounded runtime stability;
- только после полного PASS продвигает build в `TestBuild\Current`.

Это основной профиль для ежедневной разработки на обычном компьютере.

### GAME → RESTORE

**По умолчанию заблокирован.**

Он разрешается только на отдельной лабораторной Windows/тестовом ПК через:

```powershell
pwsh -File D:\MerzoOptimizer-LocalLab\App\ENABLE-DESTRUCTIVE-LAB.ps1 -DedicatedLabOnly
```

Маркер привязан к имени конкретной машины. Профиль требует Administrator и запускает текущий production GAME/Restore acceptance из profile JSON.

Не включать этот режим на основном рабочем Windows только ради уменьшения числа процессов.

## Автоматический evidence / отчёты

Ручная отправка больше не является обязательной.

После каждого профиля `Диагностика`, `Обновить Source`, `QUICK`, `FULL SAFE`, `GAME → RESTORE` Test Center автоматически создаёт событие PASS/FAIL и пытается отправить его в изолированную ветку:

`mwo-local-lab-evidence`

Startup/GUI/utility ошибки также автоматически создают события. Для каждого события сохраняются тип, PASS/FAIL/WARN/INFO, сообщение, машина, версия Test Center, версия продукта, branch/SHA если они уже известны, и bounded log.

Если GitHub недоступен или авторизация на push временно не работает, событие **не теряется**. Оно остаётся в локальной очереди:

`D:\MerzoOptimizer-LocalLab\State\EvidenceQueue`

При следующем автоотчёте/ручной отправке очередь снова пытается уйти в GitHub. Элементы удаляются из очереди только после успешного push или когда подтверждено, что exact event уже есть в evidence-ветке.

Evidence branch намеренно не содержит `.github/workflows`, поэтому обычный `git push` отчётов **не расходует GitHub Actions minutes**.

Локальные основные файлы:
- `D:\MerzoOptimizer-LocalLab\Results\Latest\LAB-RESULT.json`
- `D:\MerzoOptimizer-LocalLab\Results\Latest\REPORT.txt`
- `D:\MerzoOptimizer-LocalLab\Logs\Current.log`
- `D:\MerzoOptimizer-LocalLab\Results\history.jsonl`

Ручная кнопка **«Отправить отчёт»** остаётся как резервная команда для принудительного flush очереди.

Evidence ZIP создаётся командой:

```powershell
pwsh -File D:\MerzoOptimizer-LocalLab\App\PACK-EVIDENCE.ps1
```

Результат:

`D:\MerzoOptimizer-LocalLab\Results\MerzoOptimizer-Verify-Evidence.zip`

ZIP содержит только отчёт/лог/хэши и имеет лимит 25 MB. Большие installer/portable в evidence не дублируются.

## Установка

Рекомендуемый bootstrap в корне ветки:

`INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat`

Он сам ставит/находит PowerShell 7, выполняет parser gate и реальный GUI smoke gate, обновляет файлы на D: и заменяет ярлык.

Первый запуск:

1. `Диагностика`
2. `Обновить Source`
3. `QUICK`
4. при необходимости `FULL SAFE`
5. `Открыть тестовую`

## Что остаётся на GitHub Actions

Actions больше не нужны для каждой промежуточной сборки. Их оставляем для редких независимых ворот:
- финальный immutable release candidate;
- публичный OTA со старой опубликованной версии на новую;
- release asset/digest verification;
- проверки, которые принципиально требуют чистой disposable Windows и которые мы не хотим выполнять на рабочем ПК.

Обычные source/build/startup/SelfTest/diagnostic проверки выполняются Local Test Center локально.

## Обновление на следующую версию

Сам Test Center не привязан к R56. Для R57/R58 меняется прежде всего `local-lab-profile.json`:
- target branch;
- version;
- build controller;
- generated root/dist paths;
- destructive acceptance script.

GUI и Local Lab layout остаются прежними.

 
## Fix 0.1.9: truthful Windows edition/build display
The Environment card used to print `[Environment]::OSVersion.Version` and thus looked like "Windows 10.0.26200.0" on Windows 11, because Windows 11 still uses kernel version 10.0. Version 0.1.9 reads the **Windows NT CurrentVersion registry properties** `CurrentBuildNumber`, `UBR`, `DisplayVersion`, `EditionID` for clear display. Build >= 22000 is labelled "Windows 11"; Professional is labelled "Pro". For example Windows 11 Pro 25H2 build 26200.9457 shows as two rows `Windows 11 Pro` and `25H2 | 26200.9457`. A fallback uses only the available kernel information rather than crashing the GUI if the registry read fails. The machine name is omitted from this visible environment card.

This is **display-only**; no change to Windows compatibility checks, registry writes, safety gates, runtime profile executions, user programs or the product. The 0.1.9 parser/GUI/owner Windows retest remains PENDING until observed. Test Center 0.1.8 is already owner GUI PASS. Updating the Test Center should not require R57 build verification to be repeated.

 
## 0.2.0 Native Windows GUI EXE (source-only until local Windows verification)
New `NativeHost/` is a WinForms C#/.NET 10 `WinExe`. Installer compiles a self-contained x64 EXE on the Windows developer machine via `Build-NativeHost.ps1`, tests actual native WinForms smoke, only then redirects desktop shortcut to `D:\MerzoOptimizer-LocalLab\App\Native\MerzoOptimizer.TestCenter.exe`. The native GUI does not open or require a visible PowerShell console.

Diagnostics, Sync, Quick, FullSafe and the automatic evidence push still execute the existing `Run-Profile.ps1` runner in child pwsh processes without console windows. The source/risk/checkpoint contracts, production Program Files protection, no Actions minutes and GAME->RestoreAll dedicated-lab gate are unchanged.

If native compilation/smoke fails, the installer stops before shortcut replacement. `START-TEST-CENTER-LEGACY.bat` opens the previous PowerShell GUI as backup; `START-TEST-CENTER.bat` uses native EXE. Installer waits for State/native-gui-shown.json. Source authored, Windows compile/runtime **NOT RUN** until the owner updates.

**Do not confuse EXE GUI with conversion of all backend scripts:** PowerShell 7 still powers build and reporting behind the scenes, and can appear in Task Manager during an active test.

## 0.2.1 — critical parser restoration
The 0.1.9 display-only change accidentally corrupted the old PowerShell WinForms script by copying parts of the file multiple times into a registry lookup and left invalid PowerShell syntax; installation 0.2.0 stopped at TEST CENTER PARSER FAIL before native EXE build. Restored the **exact known-good 0.1.8 script** and inserted the new Windows 11 OS display helper via safe source slicing (no replacement-template expansion). The parser gate is deliberately kept **before** installing native GUI so source errors fail closed. 0.2.1 source fixed; native Windows build and end-to-end verification still require owner's local run. Prior installer and user settings/reports remain preserved. Rollback: use previously functioning 0.1.8 GUI until fresh installation confirms success.

 
## Test Center 0.2.2 — inherited TEMP/TMP bug fixed
Owner's native 0.2.1 installer passed Parser and PS GUI Smoke, but the .NET WinForms EXE `dotnet publish` failed: `MSBUILD : error MSB1025 ... Cannot create ...Temp\\INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat because a file or directory with the same name already exists`. Root cause: the **previously installed** `UPDATE-TEST-CENTER.bat` generated `set "TMP=%TEMP%\\INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat"`, thus poisoning the Windows `TMP` environment variable for all subsequent `call` / PowerShell / MSBuild descendants.

Fix in 0.2.2: new generator uses `MWO_UPDATE_DOWNLOAD`, never a reserved OS temp variable; both downloadable root bootstrap and `Install-LocalLab.ps1` repair **process-scoped** `TEMP/TMP` before starting the .NET toolchain. The native build helper separately enforces `D:\\MerzoOptimizer-LocalLab\\Temp\\ToolchainTemp` so direct invocation is also safe. Temp directory creation uses only dedicated Lab-owned directories on D:; it does NOT remove user temp, does not alter global Windows environment, and does NOT modify the main Optimizer. Local source checks passed; actual Windows build/GUI/runtime is still **NOT RUN** after the fix.

Even when running the **old installed updater once more**, the fetched 0.2.2 bootstrap repairs inherited TMP in its own batch scope, and successful installation replaces the old updater with the corrected generator. Keep the old GUI untouched until native exe build/smoke succeeds.

## 0.2.3 — automatic evidence delivery indicator
The native GUI now displays an **АВТООТЧЁТ** status in the left navigation instead of an always-active "Отправить отчёт" button. Backend behavior is unchanged: profile Diagnostics/Sync/Quick/FullSafe automatically calls AUTO-REPORT and PUBLISH-EVIDENCE, even when the profile outcome is FAIL. PUBLISH-EVIDENCE records a local durable receipt `D:\MerzoOptimizer-LocalLab\State\EvidencePublishStatus.json` with independent states `SENDING`, `PUBLISHED` or `DEFERRED`, update time and queue count; the GUI reads this and checks `State\EvidenceQueue\*.json`. It shows sent only after GitHub push success or an already-current clean queue, never from the product test PASS/FAIL. If a network/authorization error preserves queued events, the GUI shows the queue and an explicit **Повторить отправку** button; no re-run of product tests needed. Status/marker writes are local and do not use GitHub Actions minutes.

The updater still compiles the WinForms host locally on Windows and smoke-checks it. Current 0.2.3 source is PREPARED, actual Windows runtime PENDING. Last real profile evidence before the update was Test Center 0.2.2 Diagnostics FAIL because `ISCC.exe` (Inno Setup 6) was not discovered; the automatic GitHub upload itself succeeded. Note: privacy hardening for user/machine fields in the **existing** event publisher remains separately tracked; UI status does not imply published reports are fully anonymized.

## 0.2.4 — Inno Setup 6 user-scope registry/path discovery
Owner Windows 11 winget listed Inno Setup 6.7.3, while Program Files wildcards and Diagnostics failed to locate ISCC.exe. Run-Profile.Core.ps1 now checks system and current-user installed paths, PATH, App Paths and scoped Inno 6 uninstall registry, and the dedicated winget Inno package directory. It accepts only an actual ISCC.exe with Windows version resource major 6, does not scan disks globally, and does not upload the local executable path as a stage detail.
The exact same resolver is used by Diagnostics and Quick/FullSafe, forwarding a process-local MWO_INNO6_ISCC variable to the cumulative R56/R57 build controllers (which must support and verify it). Code prepared; Windows local results PENDING. If compiler is missing physically, reinstall may still be necessary, but do not reinstall based on winget registration alone.

## 0.2.5 Inno6 zero-resource version detection
Owner's user-scope ISCC.exe has FileVersion and ProductVersion both 0.0.0.0, despite winget installed Inno Setup 6.7.3. New Test-Inno6CompilerIdentity first checks file resources for major 6 and rejects explicit major 7. If no major version is present it runs a fixed official /? help invocation with redirected streams and a six-second timeout; a strict Inno Setup 6 Command-Line Compiler banner is required. No file writes or any Windows optimization actions in the test. Both Diagnostics and Quick share that resolver; the R56/R57 release controllers must use matching validation. Source prepared, Windows parser/compiler/real-user success NOT RUN.
