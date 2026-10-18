# 03 — DEVELOPMENT RULES v1.0

## A. Достоверность и граница проектов
- Вся утверждённая документация Optimizer — optimizer/SOURCE_OF_TRUTH/ ветки mwo-r57-safe-background-actions, пока отдельным Decision не назначена новая.
- Репозиторий содержит чужие продукты. Не менять merzostream/, root README, общие release assets, StreamCenter/QUVELIO; изменения только в явно определённом Optimizer scope.
- Перед действием получить реальные HEAD/SHA, status/gate и последнее evidence. Никогда не подставлять SHA из памяти.
- Считать статусами: PROPOSED, APPROVED, IMPLEMENTED, TESTED, CONFIRMED, ACCEPTED, RELEASED; отдельные результаты PASS, FAIL, BLOCKED, PARTIAL, NOT RUN, PENDING. IMPLEMENTED не означает TESTED; TESTED не обязательно CONFIRMED на пользовательском ПК.

## B. Регрессии и риски
- Не переписывать принятое ради рефакторинга. Если риск/контракт расширяется — Decision + план миграции + нужные регрессионные тесты.
- Функции Windows mutation отделять от read-only diagnosis и selection-only UI.
- Запрет случайного process kill, отключения неизвестных служб и драйверов, сброса сети/реестра без подтверждения, обхода встроенной защиты, удалений без доказуемого отката.
- Defender, Windows Update, Store, IPv6 и pagefile — защищены; Core helper использует allow-list и минимально необходимые права.
- EXTREME / LAB — отдельное explicit consent / recovery preflight, destructive testing только в disposable lab.
- PUBLISHED/Stable, merge/risk expansion и изменение критичной политики только с owner approval.

## C. Тесты и evidence
- В каждом отчёте обязательны ветка + SHA продукта, версия, environment/OS, сборка, режим SAFE/EXTREME, risk boundary, шаги и результаты.
- Проводить структурные/static проверки, SelfTest, real-window startup, installer, update, rollback/RestoreAll по соответствующему gate. Нельзя считать одно другим.
- PASS старого SHA не переписывать и не переносить молча на изменённый код. Документальное изменение может сохранить кодовый baseline, но новый HEAD всё равно должен быть указан как новый HEAD.
- При блокирующей ошибке STOP, описать причину, новый шаг и retest лишь изменённого риска.
- NO REPEAT: пройденные SAME CODE SHA + SAME risk/environment tests не повторять без записанной причины; новый чат — не причина.
- Не публиковать CI артефакт без сквозной проверки опубликованного exact SHA/digest.

## D. EVERY ACTION IS RECORDED — обязательно
После каждого существенного рабочего цикла записать:
1. REPORTS/YYYY-MM-DD-...md — читаемый owner/report + все изменённые файлы, почему, что проверено.
2. EXECUTION_LEDGER/YYYY-MM-DD-NNN-...md — новый immutable checkpoint с подробным последовательным ACTION LOG (включая мелкие исправления и отрицательные гипотезы).
3. 06_LIVE_EXECUTION_LEDGER.md — указатель на последний checkpoint, последние evidence и DO NOT REPEAT.
4. 02_CURRENT_STATUS.md и 05_ACTIVE_WORK_HANDOFF.md — синхронизировать, если изменился status, next, branch, blocker или gate.
5. 08_EXECUTION_SEQUENCE.md / 04_PRODUCT_ROADMAP.md / 13_FEATURE_MATRIX.md — обновлять при изменении этапа, планов, состава функций.
6. Новое архитектурное/продуктовое исключение — отдельный append-only DECISIONS/ file.

Один checkpoint может охватывать цельный цикл; отдельный checkpoint на каждую строку не нужен. Лог обязан содержать последовательность действий/фактов. Служебная запись самого отчёта/указателя не требует бесконечного рекурсивного checkpoint.

## E. Что писать в checkpoint
- DATE, ACTOR, objective, read authority files;
- expected SHA/code SHA before; actual HEAD before/after (если доступен);
- risk boundary, gates, run IDs, OS, logs/links;
- ACTION LOG (ordered): read/patch/build/test/results/decisions/writes;
- DONE; PASS / FAIL / PENDING / NOT RUN (ничего не выдумывать);
- discovered defects / limitations; DO NOT REPEAT;
- EXACT NEXT EXECUTION;
- no-release/no-destructive constraints;
- перечень синхронизированных live-files.

Checkpoint никогда не редактировать задним числом. Ошибки исправлять новым checkpoint с ссылкой на предшественника. Чувствительные токены, пути пользователя, персональные сведения в логах санитизировать; ZIP не публиковать автоматически.

## F. Рабочий цикл нового ИИ
Полное чтение согласно 00 -> сверка live HEAD -> определить один основной блок -> выполнить только разрешённые действия -> реальные проверки -> запись REPORT/LEDGER/live status до финального отчёта пользователю. Фразы «продолжай» и «отчет отправлен» не создают PASS сами по себе.

## Resident Guardian safety boundary (Decision 002)
Long-running agent must default OFF/monitor-only, be per-user interactive with visible tray/exit/uninstall, low sampling overhead, bounded audit logs, user-defined action policies and no hidden SYSTEM privilege. A critical threshold never grants process kill authority. Unattended actions must be exact identity-checked, separately consented, stateless, gracious close only, with no unsaved work, persistent exclusions, cooldown and fail-closed semantics. No arbitrary cache clearing or false RAM/FPS claims. Do not implement before R57 gate sequence authorizes future block.

## Source patching hazard noted at Test Center 0.2.0
Text transformations must never use replacement strings with unescaped JavaScript `$'`, `$&`, `$1` substitution patterns when authored source contains PowerShell-dollar variables and regex strings. Use index-based splice or replace-function callbacks; assert exact anchors and no duplicated root functions/terminators; run authoritative PowerShell Parser.ParseFile and C# compilation on Windows before marking PASS. Source corruption in v0.1.9 persisted to v0.2.0 because the parser gate correctly blocked owner installation — **DO NOT DISABLE THIS GATE**. A missing test cannot be papered over with source-only PASS.
