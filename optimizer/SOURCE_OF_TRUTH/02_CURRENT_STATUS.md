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

## Owner Local Test Center Diagnostics 0.1.8 — verified auto-report FAIL (2026-10-18)
GitHub evidence branch `mwo-local-lab-evidence` current event `20261018T072321769Z-profile.Diagnostics-7cd11a93` shows `outcome=FAIL`, `message="Inno Setup 6: ISCC.exe"` and `sourceBranch/sourceCommit` empty because no Sync yet. Other checked preflight gates: D: PASS, Git PASS, PowerShell 7.6.7 PASS, .NET 10 SDK PASS, D: protection/production PASS, D: free 288.2 GB PASS. **Auto-report PUBLISHED PASS (actual GitHub commit 22030119a4af17803fd83ce3950f2041d400b761)**. This is NOT an R57 build/runtime FAIL. Stop Quick/FullSafe until Inno Setup 6 is installed/detected and Diagnostics PASS, then Sync->Quick->FullSafe. The published event includes raw Windows username/machine identifiers; report privacy sanitization needs review, do not repost raw fields in owner-facing docs.

## Test Center 0.1.9 visual-only Windows 11 label fix
Owner screenshot: Windows Settings reports Windows 11 Pro 25H2 build 26200.9457 but Test Center 0.1.8 environment card says "Windows 10.0.26200.0". Root cause: direct display of `[Environment]::OSVersion.Version` (Windows 11 kernel retains major version 10). Fixed only in separate Test Center infra branch commit `00f0484cbff48380a205410da1ebf208c7f63de6`: Product Windows 11 is inferred for builds >=22000, edition/DisplayVersion/CurrentBuildNumber/UBR read from Windows NT CurrentVersion registry; machine identity removed from card display. Test Center version now **0.1.9, SOURCE IMPLEMENTED, WINDOWS RUNTIME NOT RUN**. Active R57 and its status remain unchanged, last verified GitHub evidence is Diagnostics FAIL Inno 6 at `mwo-local-lab-evidence@22030119a4af17803fd83ce3950f2041d400b761`.

## Test Center 0.2.0 EXE frontend — source implemented / Windows NOT RUN
Owner asked why PowerShell window appeared together with the Lab UI and requested standalone EXE like other project Test Lab. Root cause: legacy GUI itself was `MerzoOptimizer.LocalLab.ps1` with WinForms and wscript/pwsh launcher. A native C#/.NET 10 WinForms WinExe frontend has been added in separate `mwo-local-test-center@f8757abcfabf0780fcf891661e0e1596dc1ad96a`: standalone EXE via dotnet publish self-contained win-x64, desktop shortcut targets EXE after local native smoke, legacy PowerShell GUI remains fallback. Profiles/auto GitHub evidence still use hidden PowerShell backend. **CURRENT STATUS: IMPLEMENTED IN SOURCE, WINDOWS BUILD/INSTALL/RUNTIME NOT RUN**. Do not call this PASS until owner's exact local Test Center installation confirms EXE opens and evidence still uploads. R57 P4 Diagnostics last FAIL (Inno Setup 6) remains; Source/QUICK/FULL SAFE NOT RUN.

## Test Center 0.2.0 source corruption / 0.2.1 hotfix
User screenshot of the 0.2.0 native installer: **FAIL** at `Install-LocalLab.ps1:30`, `TEST CENTER PARSER FAIL MerzoOptimizer.LocalLab.ps1`; the legacy PowerShell GUI source had been malformed by prior 0.1.9 Windows label text insertion. Root-cause GitHub examination: damaged script 1538 lines, duplicate full source sections (~5x), disrupted registry regex and unterminated statements; original 0.1.8 clean file was 498 lines. New Test Center 0.2.1 source `mwo-local-test-center@1db2b1d91ea699a84fd0a374b00867c185d9e8c9` restores original known-good file + a carefully inserted read-only Windows 11 display helper (531 lines, single GUI definition). **HOTFIX IMPLEMENTED; WINDOWS PARSER/EXE BUILD NOT RUN**. User R57 diagnostics still last known FAIL for missing Inno Setup 6; Source/Quick/FullSafe NOT RUN. The installer must still enforce parser gate before native build, no silent bypass.

## Test Center 0.2.1 local .NET build FAIL (user log); v0.2.2 source fix
The user ran Test Center 0.2.1 installer: **LOCAL_TEST_CENTER_LOCAL_PARSER_GATE_PASS**, **LOCAL_TEST_CENTER_GUI_SMOKE_TEST_PASS**, followed by **MSBUILD MSB1025 FAIL**: `Cannot create '...\Temp\INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat' because a file or directory with the same name already exists`. Root cause verified in GitHub: old locally generated `UPDATE-TEST-CENTER.bat` contained `set "TMP=%TEMP%\INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat"`, clobbering reserved Windows temporary-directory variable and propagating it via CALL into `dotnet publish`. No GPU/Optimizer failure and no native EXE created/validated by that run. New Test Center 0.2.2 source `mwo-local-test-center@39b17f00c7270bca7ee3a5df607e51420c4ae2fc` fixes both generator and inherited environment in root BAT, Install-LocalLab and native build helper. **SOURCE FIX IMPLEMENTED; Windows installer/native smoke PENDING.** Prior R57 Diagnostics FAIL (Inno 6) remains the last actual profile evidence.

## Test Center 0.2.2 opened on owner Windows, live Diagnostics auto-upload verified (2026-10-18)
Owner explicitly reports GUI opened after 0.2.2 installation. **OWNER GUI VISIBLE: PASS (reported)**. The exact desktop shortcut native EXE path/no-console behaviour has not been independently attested with screenshot/process identity; don't extend GUI PASS to every native GUI feature. New GitHub evidence `mwo-local-lab-evidence@84778f7e5c390f3c3a6e5ad8ef60ad07eadaceaa` EVENT `20261018T080939838Z-profile.Diagnostics-660846e5` shows Test Center version **0.2.2** executing `profile.Diagnostics`, `outcome=FAIL`, `message="Inno Setup 6: ISCC.exe"`; automatic upload **PASS**. D:, Git, PowerShell 7.6.7, .NET10, protected Program Files and D: storage checks **PASS**. R57 Source Sync / QUICK / FULL SAFE **NOT RUN**; this is a toolchain prerequisite failure, not R57 runtime failure. Install official Inno Setup **6** (`JRSoftware.InnoSetup`; 6.7.3 current listed vendor release), rerun Diagnostics and only continue sequentially on PASS. No software code/product release modified by this owner observation.

## 0.2.3 Test Center upload UI / source only
Owner provided 0.2.2 screenshot with GitHub EVIDENCE_PUBLISHED confirming automatic upload of Diagnostics FAIL, but permanent manual-send button was misleading. Test Center v0.2.3 source a205879fdf1d4d84ee35cd8b26411855a73318fc replaces it with АВТООТЧЁТ delivery status, backed by persisted SENDING/PUBLISHED/DEFERRED local receipt, with retry available only when delivery is pending. PASSED old 0.2.2 auto evidence (SHA 84778f7e5c390f3c3a6e5ad8ef60ad07eadaceaa); v0.2.3 code IMPLEMENTED, Windows build/GUI/offline retry NOT RUN. R57 candidate runtime unchanged, R57 Source/Quick/FullSafe still NOT RUN, current Diagnostics FAIL Inno Setup 6. Existing outbound event/report privacy exposure is a known separate issue.

## New owner Test Center 0.2.3 Windows Diagnostics / auto-report evidence (2026-10-18)
Owner reports updated and ran Diagnostics; report sent. Verified actual GitHub mwo-local-lab-evidence HEAD dc1ac24ed1a85a2ce0dd7d1965e31ad936e5b328, new event 20261018T083407111Z-profile.Diagnostics-ec944325 at 2026-10-18T08:34:07Z, Test Center version **0.2.3**, profile=Diagnostics, outcome **FAIL** solely `Inno Setup 6: ISCC.exe`. Other env/safety checks **PASS**: D:, Git, PowerShell 7.6.7, .NET10 SDK, protected Program Files, lab-only D:, free disk 286.8 GB. Auto GitHub report transport **PASS** (remote EVENT.json and latest LAB-RESULT verified); user-visible upload receipt display and offline/deferred retry behaviour are **NOT independently verified** (no new UI screenshot). Source checkout, Quick, Full Safe R57 remain **NOT RUN/BLOCKED**. Owner's prior winget command found JRSoftware.InnoSetup already installed: determine whether that is major 6 or 7 and the actual ISCC.exe path; Test Center currently scans only standard Inno Setup 6 directories; do not blindly reinstall without checking.

## 2026-10-18 — Inno Setup 6.7.3 installed via Winget; Test Center 0.2.4 source correction
Owner provided screenshot: `winget list --id JRSoftware.InnoSetup -e` returns Inno Setup **6.7.3**. Previous PowerShell Program Files ISCC glob returns nothing. Actual EXE location not yet observed; likely per-user installation under LocalAppData. Test Center 0.2.3 Diagnostics FAIL Inno 6 is therefore **known false negative candidate**; cannot assert real compiler exists until found. New `mwo-local-test-center@f0044e15c1952482c65b6d3d85afa982bab4deb5` **0.2.4 source IMPLEMENTED, Windows NOT RUN** — read-only major-6-verified compiler discovery in user/system paths and registry, shared Diagnostics/QUICK and env handoff. Optimizer active cumulative R56/R57 builder scripts now accept only verified MWO_INNO6_ISCC path in addition to historical standard paths (toolchain-only change; R56 historic checks not transferred to this newer script). R57 local FULL SAFE still **NOT RUN**. Owner update Test Center 0.2.4, rerun Diagnostics; only on proven PASS proceed Source -> QUICK -> FULL SAFE. No public release.

## User confirms per-user ISCC.exe physical existence (2026-10-18)
Owner's PowerShell screenshot shows `Test-Path (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')` returned **True**. Combined with prior `winget list ...` v6.7.3 result, this substantiates the expected current-user installation path and explains prior 0.2.3 standard-Program-Files-only false negative. **Physical file presence: PASS (owner observation).** Exact compiler FileVersion metadata and resolver acceptance: NOT RUN/NOT REPORTED. New Test Center 0.2.4 Diagnostics evidence not yet in GitHub (last evidence branch HEAD dc1ac24ed1a85a2ce0dd7d1965e31ad936e5b328, 0.2.3 Diagnostics FAIL). R57 Source/QUICK/FULL SAFE NOT RUN. Do not reinstall Inno Setup. Next confirm Test Center 0.2.4 installed then Diagnostics; on PASS proceed R57 P4 gated sequence.

## Test Center v0.2.4 real Diagnostics — GitHub evidence, 2026-10-18
Actual latest auto-published event in `mwo-local-lab-evidence@ca858f12ccc66a6bee2086a8d9e7738ab446763b`: `20261018T093622014Z-profile.Diagnostics-48622cba`, 14:36 local, profile Diagnostics, version 0.2.4, conclusion **FAIL** solely `Inno Setup 6: ISCC.exe not found; inspect install location`; D:, Git, PowerShell 7.6.7, .NET 10, D: lab boundary and Program Files protection PASS, 286.8 GB free. **Auto-upload PASS** (new remote event). Previous owner's `Test-Path` in `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe` returned True and winget listed 6.7.3. New resolver returned null despite file existence: **root cause not confirmed**. Possible actual embedded EXE version metadata mismatch or resolver execution/identity issue; DO NOT declare cause or modify validation on guess. Exact next owner read-only query: FileVersion, ProductVersion, match to 6.x from Get-Item in same user session; do not upload full user path. Diagnostics PASS still BLOCKED, R57 Source/QUICK/FULL SAFE NOT RUN. No reinstall or bypass of compiler verification.
