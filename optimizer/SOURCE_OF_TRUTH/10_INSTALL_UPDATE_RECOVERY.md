# 10 — INSTALL / UPDATE / RECOVERY

## Известный контракт
- Установка: C:\Program Files\Merzo Windows Optimizer\MerzoWindowsOptimizer.exe (installed candidate R56 подтверждён).
- UI работает asInvoker, повышение полномочий только отдельным helper для разрешённых операций.
- Установщик Inno Setup и portable win-x64; соответствие version/EXE/DLL и SHA-256 проверяется.
- По опубликованным release notes обновление из программы проверяет официальный GitHub release источник, exact installer name, size/digest, SHA sidecar и только после решения пользователя запускает установку.
- Program Files содержит бинарные файлы; данные, состояние, логи — отдельно; массовое удаление данных при переустановке не допустимо без consent.

## Известное evidence
- R55.1 public release подтверждён; installed-candidate успешен.
- R55.1 исторический public OTA test — FAIL: installer timeout. Более поздний direct staged OTA прошёл SUCCESS. Оба факта хранить; текущий exact upgrade тестировать снова на новом кандидате.
- R56 fresh Program Files installed candidate / main window / uninstall registration PASS в run 32480404145.
- R56 GAME -> production RestoreAll там же PASS, с риском и средой того exact прогона.

## Required acceptance до следующего public release
1. Clean install; launch non-error window; no crash log.
2. Upgrade from published version through real Update Center; data/config preserved, correct destination path and payload digest.
3. Uninstall registration; optional keep/remove data choices; retry installation.
4. Failure handling and rollback; no multiple installed copies or mixed DLL version.
5. Explicit user consent on mutation/update; recovery package for risky actions.
6. Dedicated lab for destructive GAME/EXTREME/RestoreAll; no automatic test on owner workstation.

## Security
Никаких секретов в client/source/public reports, fake code-signing claims или обходов подписи. Пока безопасная обфускация не восстановлена, production scripts выполняют SkipObfuscation; certificate не зафиксирован.

## New-pc BAT entrypoints (added 2026-10-18)
See `optimizer/BOOTSTRAP/README.md`, `INSTALL_WINDOWS_OPTIMIZER.bat`, `INSTALL_TEST_CENTER.bat`. The stable launcher pins public version 0.1.55.1 and its exact SHA; it is not a R57 release. The Test Center launcher pins infrastructure commit `edc83fca9f0f89fc895a0a30c7f58f81af143779` for Test Center 0.1.7, requires D:, installs independently. BATs are NOT yet run on owner Windows. Do not move destructive lab tests to main workstation.
