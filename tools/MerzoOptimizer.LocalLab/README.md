# Merzo Optimizer Local Test Center

Локальная Windows-лаборатория для **Merzo Windows Optimizer**, сделанная по тому же принципу, что и MerzoStream Test Center: основная масса проверок выполняется на локальном компьютере и **не расходует GitHub Actions minutes**.

## Главное правило

Test Center — это инфраструктура разработки, а не часть Merzo Windows Optimizer. Он не входит в installer продукта и не заменяет публичный release/OTA gate.

Корень лаборатории:

`D:\MerzoOptimizer-LocalLab`

Установленная рабочая программа защищена:

`C:\Program Files\Merzo Windows Optimizer`

Безопасные профили не устанавливают туда кандидат и обязаны доказать, что fingerprint Program Files не изменился.

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

Именно там разрешены `fetch`, `checkout`, `reset --hard` и `clean -fd` после проверки origin. Рабочие папки пользователя и установленный Optimizer не используются.

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

## Evidence

Каждый запуск перезаписывает:

- `D:\MerzoOptimizer-LocalLab\Results\Latest\LAB-RESULT.json`
- `D:\MerzoOptimizer-LocalLab\Results\Latest\REPORT.txt`
- `D:\MerzoOptimizer-LocalLab\Logs\Current.log`

Последние 20 коротких результатов хранятся в:

`D:\MerzoOptimizer-LocalLab\Results\history.jsonl`

Evidence ZIP создаётся командой:

```powershell
pwsh -File D:\MerzoOptimizer-LocalLab\App\PACK-EVIDENCE.ps1
```

Результат:

`D:\MerzoOptimizer-LocalLab\Results\MerzoOptimizer-Verify-Evidence.zip`

ZIP содержит только отчёт/лог/хэши и имеет лимит 25 MB. Большие installer/portable в evidence не дублируются.

## Установка

Из checkout ветки `mwo-local-test-center` запустить:

`tools\MerzoOptimizer.LocalLab\INSTALL-LOCAL-LAB-ON-D.bat`

Установщик создаёт ярлык **Merzo Optimizer Test Center** на рабочем столе.

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
