# 04 — PRODUCT ROADMAP

Roadmap не равен release notes. Статусы из GitHub на 2026-10-18.

## HISTORICAL COMPLETED / зафиксировано
- R34–R55.1: каталог настроек, профили, Gaming/Network, Process Reduction, Undo, feedback/diagnostics, UI, установщик, OTA improvements и 15-минутный аудит. Публичный R55.1.
- R56: baseline process intelligence, read-only «Постоянный фон», разделение live/saved audit, уточнённая классификация. Exact CI + installed/restore PASSED; NOT PUBLIC.

## NOW: R57 SAFE BACKGROUND ACTIONS — PENDING WINDOWS ACCEPTANCE
R57 mappings Edge/Chrome/Widgets -> existing reversible SAFE cards. Unknown WebView2 owner/OneDrive не отключать. Вкладка «Выбранное», НЕ прямое применение.
Gates: static acceptance -> .NET build/SelfTest -> real WPF window -> installer/portable -> non-destructive Windows acceptance. Имеющийся файл R57_LOCAL_TEST_STATUS обозначает ready-for-local-full-safe, а не PASS.

## NEXT: LAB GAME/RESTOREALL
Лишь disposable lab, точное имя артефакта и SHA; full GAME apply/verify -> full RestoreAll/recovery evidence. На рабочей машине запрещено без отдельного разрешения.

## NEXT: DISTRIBUTION
Проверить installed upgrade R55.1 -> целевой релиз, timeout handling, restart/UAC, payload integrity, uninstaller, clean reinstall, rollback and repeated updates, данные пользователя. Старое OTA timeout evidence не скрывать.

## NEXT: USER ACCEPTANCE
Проверки в реальной Windows 11, различные DPI/мониторы, авторизация, обычный vs администратор, Smart Audit, GAME safe, OneDrive protection, startup/drivers; метрики RAM/process delta без гарантированных чисел.

## LATER: HARDENING
Безопасная защита/обфускация runtime без regressions generic/async; code-signing certificate по решению владельца; accessibility, help, performance benchmarks, maintainable source build pipeline. Не обещать дату или измерения без evidence.

## Release definition of done
Полное exact code/evidence, no critical defects, recovery/installer/update accepted, changelog/docs актуальны, owner approves Stable/public release. Никакой автоматической публикации на основании лишь сборки.
