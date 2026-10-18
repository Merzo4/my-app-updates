# 09 — ARCHITECTURE / проверенная карта

## Что известно из исходников и cumulative release controllers
Стек: .NET / C# / WPF (XAML + ViewModel). Слои MerzoOptimizer.App, MerzoOptimizer.Core, MerzoOptimizer.Windows и отдельный elevated helper; .NET SelfTest; Inno Setup installer. Production scripts собирают полный исходный root из исторического базового source/patch chain, а не напрямую из root main. Конкретные имена файлов ниже проверены в r57 script.

- src/MerzoOptimizer.App/MainWindow.xaml — видимая оболочка; protected OneWay bindings.
- src/MerzoOptimizer.App/ViewModels/MainWindowViewModel.cs — команды UI и workflow выбора SAFE tweak.
- src/MerzoOptimizer.Core/Audit/ProcessStabilityModels.cs — модели анализа процессов.
- src/MerzoOptimizer.Windows/Processes/WindowsProcessStabilityAnalyzer.cs — аудит 0/1/5/10/15 мин, классификация и management mapping.
- data/tweaks.json — идентификаторы уже reviewed tweak; R57 не изобретает второй mutation engine.
- installer/MerzoWindowsOptimizer.iss — Inno Setup production installer.
- build/Build-Production.ps1 — сборка полученного cumulative source root.
- MerzoOptimizer.SelfTest — контрактная проверка .NET.

## Семантика безопасности
Диагностика/read-only -> пользовательский план/selection-only -> Snapshot -> Apply -> Verify -> Log -> Undo/RestoreAll. Выбор рекомендаций сам по себе не меняет Windows. Elevated-helper и service control должны соблюдать allow-list. Защищённые/system/driver/unknown классификации — не кандидаты на прямое disable/kill.

## Идентичность и delivery
- Ветка mwo-r57-safe-background-actions содержит patch + controller + tests + history.
- R57 controller начинает с cumulative R56 baseline, применяет R57 patch, проверяет версии 0.1.57.0 и собирает installer/portable.
- R56 success не наследуется как доказательство R57 runtime.
- Release assets находятся в GitHub Releases с тегами mwo-v*, не путать с MerzoStream assets.

## Непроверенное
Полная карта зависимостей каждого класса/сервиса, обещания о complete source migration и всех конфигурациях Windows не утверждаются без отдельного исходного аудита. Этот файл обновлять только с указанием SHA и фактов, не гипотез.

## Proposed architecture only — Guardian and performance centers
Future separate least-privileged per-user agent with tray, singleton/current-session opt-in autorun, bounded telemetry loop, local policy and action journal; existing WPF main app views and existing process-audit/selected-tweak/operation state shared via safe IPC. No second mutation engine, driver, SYSTEM service or unattended elevation. GPU feature-detected vendor adapters; Memory normalized memory-manager counters. Guardian itself may only read/alert by default, never auto kill; any reversible changes must use existing Snapshot->Apply->Verify->Undo. Not coded.

## Test Center 0.2.0 native GUI frontend (infra code only)
Separate `mwo-local-test-center/tools/MerzoOptimizer.LocalLab/NativeHost` contains WinForms C#/.NET10 WinExe with single-user mutex, four summary cards, test profiles, log tail/result view, Windows 11 display, user interaction, Pause/Stop, safe LAB-only gate. The original `Run-Profile.ps1`, `Run-Profile.Core.ps1`, `AUTO-REPORT.ps1`, evidence branch and sandbox/protected Program Files checks remain backend. UI launches them via hidden child pwsh. Native build/publish/smoke path in `Build-NativeHost.ps1` + `Install-LocalLab.ps1`; fallback `START-TEST-CENTER-LEGACY.bat`. Source implementation not Windows-verified.
