# 01 — MASTER PRODUCT SPECIFICATION

## Назначение
Merzo Windows Optimizer — графическая Windows-программа диагностики, обратимых оптимизаций, игровых профилей, управления фоновыми источниками, конфиденциальностью, ремонтом сети и восстановления прежнего состояния ПК. Ценность измеряется фактическими состояниями ОС/потреблением ресурсов, а не «магическими ускорениями».

## Продукт/стек
- Desktop Windows; исходный проект C#/.NET с WPF UI (XAML, ViewModel, Core, Windows adapter, elevated helper).
- Installer/portable win-x64, Inno Setup; установка в Program Files, пользовательские данные/логи отдельно от программы.
- Репозиторий Merzo4/my-app-updates является одновременно release-host нескольких продуктов. Источник Optimizer — optimizer/, его GitHub Actions и отдельные mwo-v* releases. Корневой README — не Optimizer specification.
- Версии: опубликована 0.1.55.1, прошёл exact technical candidate 0.1.56, готовится 0.1.57. Не приравнивать эти статусы.

## Существующие продуктовые подсистемы (по GitHub releases; уточнить исполняемость на целевой Windows)
1. Smart Audit 2.0: Privacy, Performance, Gaming, Startup, Services, Cleanup; реальное сканирование и рекомендации.
2. Оптимизация поэлементно и профилями LIGHT, STANDARD, MAXIMUM, GAMING, специальные GAME/SAFE/PERFORMANCE/EXTREME/LAB уровни с оценкой риска.
3. Каталог registry/policy tweaks и classification SAFE/BALANCED/STRICT/EXPERT; выбранные действия до применения видны пользователю.
4. Контроль автозагрузки, Services Advisor, Scheduled Tasks Advisor; условные и защищённые источники остаются под контролем правил и allow-list.
5. Process Reduction/Performance Baseline и временной аудит процессов 0/1/5/10/15 минут; отдельная read-only вкладка «Постоянный фон» в R56.
6. Privacy/Telemetry и consumer/debloat (allow-listed Appx с условиями и требованиями восстановления).
7. Gaming Boost и Gaming Network с SAFE/EXTREME вариантами и baseline/restore адаптера.
8. Repair / Network: диагностика адаптера, DNS/DHCP/шлюза, допустимые ремонтные операции по согласию.
9. Power, очистка, история последних аудитов, подсказки после обновлений.
10. Operation Center с прогрессом Snapshot -> Apply -> Verify -> Log -> Undo/RestoreAll, отчётностью, crash/feedback.
11. Update Center: официальный источник, проверка URL/хэшей, скачивание, отображение/подтверждение обновления, установщик.
12. Фирменный UI 12 страниц, тёмная палитра и work-area/scrolling/DPI fixes.

## Текущий продуктовый срез R57
Новая функция только связывает выявленные семейства постоянного фона Edge/Chrome/Widgets с существующими обратимыми ID твиков и помещает предложения во вкладку «Выбранное». Она НЕ выполняет изменения Windows на этапе выбора. OneDrive и неизвестный владелец WebView2 не становятся автоматическими кандидатами; ОС/драйверы защищены. R57 НЕ подтверждён Windows local FULL SAFE.

## Безопасность как часть продукта
- Выполнять лишь явно разрешённые и проверенные действия, преимущественно обратимые.
- Защищать Defender, Windows Update, Microsoft Store, IPv6, pagefile, критические процессы/службы/драйверы.
- Не завершать процессы случайным PID и не обещать заданное число процессов/FPS.
- Перед изменением показать план и точный риск; Snapshot, Verify, Undo/RestoreAll там, где это применимо.
- EXTREME и сетевые рискованные операции — повышенный gate: Recovery Package/System Restore preflight и отдельная лабораторная проверка, не обычный desktop по умолчанию.
- Ни подтверждение сборки, ни наличие UI не заменяют реального Windows acceptance.
- Code signing/защита сборки НЕ завершены: прежний Obfuscar ломал generic/async runtime; до безопасного решения Production без него.

## Границы и не-обещания
Не заявлять автоматические FPS gain, абсолютные 60–80 процессов, гарантированную экономию RAM, поддерживаемость всех сборок Windows или «100% откат» без доказательств конкретного сценария. Состав функций сверять с 13_FEATURE_MATRIX.md; пожелания относятся к ROADMAP, а не DONE.

## Критерий готового продукта
Установщик, все предусмотренные основные пользовательские сценарии, отсутствие launch/crash регрессий, безопасный Update/Recovery, проверенный на целевой Windows UX и подтверждённые тестами отличия по рискам. Stable/public release — только после явного разрешения владельца.

## Future approved product direction: GPU / Memory / Merzo Guardian
Decision 002 authorizes the **future scope** of GPU Optimization Center, Memory & Background Center and optional resident Merzo Guardian. Read three FEATURES specifications. None of these has code, Windows test evidence or public availability as of this checkpoint. Guardian defaults to OFF / monitor-only and may only opt-in graceful-close positively verified stateless apps; no blanket killing, disabling system services, or 2–3 GB idle guarantee.

## Development infrastructure UX: Test Center native GUI
The separate Local Test Center 0.2.0 now has an **EXE-based C#/.NET 10 WinForms frontend** in `mwo-local-test-center` (native executable source implemented, Windows compilation/owner acceptance NOT RUN). This is developer test infrastructure only, not a new optimizer shipped feature. Test profiles and Auto Evidence still execute PowerShell 7 behind the scenes, without a visible console.
