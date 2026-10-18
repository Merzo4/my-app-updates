# 00 — READ FIRST / обязательный вход

## Продукт и граница
Merzo Windows Optimizer. Repo Merzo4/my-app-updates — общий с другим продуктом; никогда не интерпретировать корневой README о MerzoStream как спецификацию Optimizer.
Рабочая и первоначальная SOT ветка: mwo-r57-safe-background-actions. SOT находится в optimizer/SOURCE_OF_TRUTH/. Перед любым действием подтвердить текущие ветку и SHA через GitHub.

## Полный обязательный порядок
1. 00_READ_FIRST.md (этот документ).
2. 01_MASTER_SPEC.md.
3. 02_CURRENT_STATUS.md.
4. 03_DEVELOPMENT_RULES.md.
5. 04_PRODUCT_ROADMAP.md.
6. 08_EXECUTION_SEQUENCE.md.
7. 05_ACTIVE_WORK_HANDOFF.md.
8. 06_LIVE_EXECUTION_LEDGER.md.
9. 07_CHANGE_POLICY.md.
10. Последний immutable checkpoint по указателю из 06.
11. Относящиеся к задаче: 09_ARCHITECTURE.md, 10_INSTALL_UPDATE_RECOVERY.md, 11_TEST_RELEASE.md, 12_USER_GUIDE.md, 13_FEATURE_MATRIX.md, 14_REPOSITORY_MAP.md, DECISIONS/ и REPORTS/.

NEW_CHAT_BOOTSTRAP.md помогает переходить между чатами, но не заменяет первичное чтение.

## Иерархия достоверности
1. Фактический GitHub SHA, исходники, run ID и файлы evidence для точной сборки.
2. Принятые решения в DECISIONS/ и действующая MASTER_SPEC.
3. Test/release gates и EXECUTION_SEQUENCE.
4. CURRENT_STATUS, HANDOFF, LIVE LEDGER и последний checkpoint.
5. ROADMAP, инструкции и исторические сведения.
6. История диалогов — контекст, но не доказательство тестов.

## Запреты
- Не путать опубликованный R55.1, проверенный технический кандидат R56 и подготовленный к локальным тестам R57.
- Не выводить PASS из наличия кода, Markdown, подготовленного script или старого PASS другого SHA.
- Не повторять DONE/PASS для неизменного SHA/границы риска без зафиксированной причины.
- Не изменять GAME, EXTREME, службы, задачи, OneDrive, сеть, Registry и recovery как побочный эффект документации.
- Никакой неконтролируемой очистки процессов, неизвестных служб, системной защиты, драйверов и файлов пользователя.
- Не выпускать публичный релиз, не выполнять потенциально разрушительные действия на рабочем ПК без явного разрешения владельца.
- Не редактировать прежний checkpoint; исправление — новым superseding checkpoint.

## EVERY ACTION IS RECORDED
Любой содержательный рабочий цикл завершается: отчёт REPORTS, новый append-only checkpoint EXECUTION_LEDGER, обновление указателя 06 и, если поменялась точка работы, 02/05/08/04. Записывать PASS, FAIL, BLOCKED, PARTIAL, NOT RUN, PENDING; SHA, среду, риск, причину, результат, дальнейший шаг.

## На данный момент
Публичный mwo-v0.1.55.1. R56 0.1.56 — CI/build/installed-candidate/GAME Recovery PASS, НЕ опубликован. R57 0.1.57 — код и локальный gate подготовлены, local FULL SAFE и отдельный lab destructive gate НЕ пройдены. Базовый R57 code SHA до документационного изменения: f9e63b0c57faab592ba17344943021cc7adbc123.
