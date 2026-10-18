# 02 — CURRENT STATUS

Дата сверки: 2026-10-18. Продукт: Merzo Windows Optimizer.
Репозиторий: Merzo4/my-app-updates.
Активная dev/SOT ветка: mwo-r57-safe-background-actions.
Исходный code checkpoint до документального коммита: f9e63b0c57faab592ba17344943021cc7adbc123.
После документальных изменений HEAD станет другим; ВСЕГДА проверять живой GitHub HEAD, не повторять старый SHA как HEAD.

## Три разных состояния
- **PUBLIC / RELEASED:** mwo-v0.1.55.1, опубликован 2026-08-21, с реальной проверкой главного окна и исправленным ProcessStabilityProgress OneWay.
- **R56 / EXACT TECHNICAL GREEN CANDIDATE (NOT PUBLISHED):** 0.1.56, Build run 32479505374, installed + GAME/production RestoreAll verification run 32480404145; файлы optimizer/R56_CI_STATUS.json, R56_INSTALLED_CANDIDATE_STATUS.json, R56_GAME_RECOVERY_STATUS.json. Не переносить автоматически на R57.
- **R57 / PREPARED, NOT TESTED FULL SAFE:** версия 0.1.57; Python patch, cumulative release controller, static acceptance, separate GAME Recovery gate добавлены. optimizer/R57_LOCAL_TEST_STATUS.json: state ready-for-local-full-safe; publicRelease=false; githubActionsUsedForR57=false; localTestCenterVersion=0.1.7.

## Активный блок
R57 SAFE BACKGROUND ACTIONS: выбор уже существующих SAFE tweaks по данным permanent background без прямого применения. Никакой реальной Windows мутации в новом R57 bridge.

## Последний подтверждённый технический результат
R56 CI и installed-candidate + GAME Recovery PASS на точной версии; опубликован по-прежнему R55.1.
R55.1 public OTA v2 старый прогон завершился failure «OTA installer timeout»; отдельно staged OTA direct-single-runner позднее PASS. Не стирать отрицательное evidence, проверить актуальный full update path перед новым релизом.

## Открытые условия
1. Local Test Center FULL SAFE для R57 на Windows: cumulative R56 -> R57 patch -> static gate -> .NET build/SelfTest -> real WPF main window -> installer/portable.
2. Отдельный destructive GAME -> production RestoreAll на выделенной lab-машине, не обычной рабочей станции.
3. Непротиворечивые SHA/артефакты, installed/update/rollback сценарий и пользовательское подтверждение, где требуется.
4. Новая публичная публикация только после полного acceptance и явного согласия владельца.
5. Проверка поддержки реальной целевой Windows 11 и честных before/after метрик остаётся необходимой.

## Evidence
- https://github.com/Merzo4/my-app-updates/releases/tag/mwo-v0.1.55.1
- https://github.com/Merzo4/my-app-updates/actions/runs/32479505374
- https://github.com/Merzo4/my-app-updates/actions/runs/32480404145
- optimizer/R57_LOCAL_TEST_STATUS.json в активной ветке.

## EXACT NEXT EXECUTION
Вначале сверить живой HEAD и checkpoint, затем выполнить R57 Local Test Center FULL SAFE на Windows в строго неразрушительном режиме; если PASS — отдельно подготовить испытание GAME/RestoreAll только на выделенной лабораторной машине. Никаких автоматических destructive действий на рабочем ПК. Крупное изменение требует нового checkpoint.
 
## User-reported Local Test Center defect / infrastructure hotfix (2026-10-18)
Owner screenshots: first launch of installed Test Center 0.1.7 shows no visible main UI; second launch says «уже запущен». This is **FAIL (owner UX)** on Test Center launcher, not an R57 product test failure. Source indicates WScript.Shell.Run with windowStyle=0 while mutex considers any running process an active GUI; precise causal sufficiency still **PENDING Windows retest**.
Patch-only Test Center 0.1.8 prepared at `mwo-local-test-center@3523eaabba8461aa63ec80a3da9d7270180ffd3a`: visible style=1 launch; hide console only after WinForms Shown; GUI-shown marker + installer gate. Test Center 0.1.8 on user PC = **NOT RUN / PENDING**. User should run updated `optimizer/BOOTSTRAP/INSTALL_TEST_CENTER.bat` (or visible RECOVER BAT); no R57 FAST/FULL SAFE PASS claimed and no product code changed.

 
### Final pinned Test Center hotfix SHA / parser-safety correction
Final Test Center 0.1.8 source is `mwo-local-test-center@a6f2cd3fcd31a9b10c994333a00ae5ca3b05b1d3` (supersedes earlier infrastructure hotfix commit 3523eaabba8461aa63ec80a3da9d7270180ffd3a ONLY for the installer source pin). This is a minimal parse-safe native Console Add-Type adjustment; 0.1.8 **WINDOWS NOT RUN/PENDING**. Updated pinned BAT uses this exact immutable SHA. Prior checkpoint 003 is kept unchanged as historical.

## Approved future scope (Decision 002) — not active implementation
GPU Optimization Center, Memory & Background Center and Merzo Guardian have been specified at owner's request. **STATUS: APPROVED FUTURE SCOPE; CODE NOT IMPLEMENTED; TESTS NOT RUN.** Current R57 P4 and Test Center 0.1.8 owner-visible window confirmation unchanged and still PENDING. No background monitor deployed, no automatic process closing enabled.

## Test Center 0.1.8 — owner visible GUI confirmation (2026-10-18)
The owner explicitly reported: "тест центр установлен открылся 0.1.8". **PASS (owner-observed visible GUI/installed Test Center)** for the previously broken 0.1.7 startup symptom. This confirms only that 0.1.8 opens visibly on owner's Windows, **NOT** that Diagnostics, Sync, QUICK, FULL SAFE, R57 product runtime, or automatic GitHub evidence upload passed. No new Windows logs/screenshots were supplied; installer parser/smoke internals remain unverified independently. R57 P4 remains PENDING.
