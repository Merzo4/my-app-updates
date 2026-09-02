# Merzo Optimizer Local Test Center

Локальная Windows-лаборатория для **Merzo Windows Optimizer**, сделанная по тому же принципу, что и MerzoStream Test Center: основная масса проверок выполняется на локальном компьютере и **не расходует GitHub Actions minutes**.

## Главное правило

Test Center — это инфраструктура разработки, а не часть Merzo Windows Optimizer. Он не входит в installer продукта и не заменяет публичный release/OTA gate.

Корень лаборатории:

`D:\MerzoOptimizer-LocalLab`

Установленная рабочая программа защищена:

`C:\Program Files\Merzo Windows Optimizer`

Безопасные профили не устанавливают туда кандидат и обязаны доказать, что fingerprint Program Files не изменился.

## Запуск без терминала

Рабочий ярлык **Merzo Optimizer Test Center** запускает `wscript.exe`, который создаёт скрытый `pwsh`-процесс. Пользователь видит только WinForms GUI. Видимый PowerShell/Windows Terminal не является частью нормального запуска, поэтому его нельзя случайно закрыть вместе с Test Center.

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
