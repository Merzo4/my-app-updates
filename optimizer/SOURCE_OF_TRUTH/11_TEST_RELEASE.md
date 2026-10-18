# 11 — TESTING AND RELEASE PROTOCOL

## Обязательная идентичность
Every result requires repo, branch, source SHA, code/content SHA if docs-only differs, version, test run, OS/environment, scope/risk, artifact hash and exact command or workflow.

## Gates
1. Prebuild: validate source reconstruct, patch anchor, XAML parse, SAFE reviewed tweak IDs, no second mutation surface.
2. Build: production DLL/EXE, compilation/SelfTest and versions all identical.
3. Runtime: real main WPF window; no startup error window and no fresh crash log.
4. Package: Inno installer + portable with exact SHA-256, install under Program Files.
5. Local FULL SAFE on Windows: non-destructive UI and diagnosis; selection-only R57, no direct Windows mutation.
6. Dedicated LAB: GAME/EXTREME, service/network/OneDrive and RestoreAll safety with explicit scoped permission.
7. OTA upgrade on real installed baseline, digest/timeout/rollback.
8. Owner Windows 11 acceptance and, when desired, repeatable before-after measurements.

## Правила результата
- PENDING: ожидается; NOT RUN: не выполнялось; PREPARED: код/скрипт только подготовлен.
- PASS: exact run artefact succeeded; FAIL: falsifying evidence; BLOCKED: prerequisites unmet; PARTIAL: only subset.
- RUN FAIL не перезаписывать. Исправление -> новый SHA и новый отдельный run; установить причинность.
- Не смешивать Windows Server 2025 disposable-lab PASS и настраиваемый домашний Windows 11 owner acceptance.

## Release gate
Before stable tag publish: exact reproducible artifact, full risk coverage, dependency/Windows tests, docs/ledger current, issue list/known limitations, owner confirmation, immutable release tag/assets. Не пересобирать код молча между tested artifact и published artifact.

## Decision 002 future regression gate
GPU: vendor/driver/OS support, multi-GPU routing, game/video recording compatibility, measured baseline/after. Memory: in-use/available/standby/commit correctness, comparable boot profile and paging/latency. Guardian: monitor overhead, synthetic pressure, no action from ordinary used RAM alone, PID reuse/cross-session/exclusions, unsaved-work dialog, gaming/OBS/voice protection, cooldown, pause, uninstall/autostart removal, long-run and sleep/resume. No background closure on normal workstation or claims of Windows acceptance without run ID/exact SHA.

## Local Test Center evidence publication + privacy issue
Actual `profile.Diagnostics` event at `20261018T072321769Z-profile.Diagnostics-7cd11a93` auto published to GitHub evidence branch (report 007), showing toolchain FAIL for Inno 6. Treat auto upload PASS separately from diagnostic FAIL. Current auto event JSON contains unsanitized local Windows user/machine fields; backlog privacy defect: replace with pseudonymous opt-in IDs and avoid uploading local sensitive data unless explicitly approved. Do not erase historic evidence or infer all fields safe because described as 'sanitized'. Source Sync/QUICK/FULL SAFE remain not run.

## Native Test Center 0.2.0 acceptance required before owner signoff
New C# frontend is NOT an R57 product build. Test: actual dotnet publish win-x64, smoke launch with clean mutex, user desktop EXE direct launch without PowerShell console, no duplicate GUI windows, Windows 11 edition/build card, Diagnostics missing Inno6 reports FAIL accurately, auto evidence published (when authorized), GUI controls, Source/QUICK/FULL SAFE parity after prerequisites, ProcessExit/Stop and profile logging, evidence utility dialogs, dedicated lab-only destructive action blocked on owner PC, rollback to legacy GUI. Inspect relevant Logs/native-build.log/native-smoke.log/native-gui-error.log. No code signing/Windows runtime PASS inferred from the GitHub source commit.

## Test Center 0.2.0 parser regression evidence
0.2.0 failed ParseFile on owner's Windows with repeated pasted PowerShell source sections. Requirements for future GUI/bootstrap changes: parser gate PASS before native compile, invariant count of root definitions/GUI entry exactly once, native dotnet publish smoke, launcher no-console behavior, rollback preservation; mark corrected code as IMPLEMENTED only until owner installs 0.2.1 and captures logs. This was test of infrastructure, not the R57 runtime.

## Test Center Native EXE MSBuild temp regression
Test Center 0.2.1 exposed environment misuse: updater `set TMP=<downloaded BAT file>` corrupts MSBuild temporary directory, error MSB1025. Future bootstrap tests must simulate poisoned TEMP/TMP inherited from legacy/updater, run parser gate, real C# publish/smoke, create shortcut only on success and verify temp cleanup confined to Lab. Test Center 0.2.2 code attempts fail-safe scoped correction; no actual Windows re-run yet. Record original FAIL, don't relabel as .NET SDK corruption.

## Test Center auto report verification contract v0.2.3
On real Windows verify that Diagnostics FAIL can still auto-publish and indicator shows Отправлено only with actual GitHub push. Simulate offline/failed Git push using a disposable isolated test environment, ensure queue persists and shows Повторить отправку, no rerun of product test needed; retry transitions to uploaded only on success. Verify legacy log receipt fallback and app restart state. Existing publisher may include raw username/machine and latest test report, so do not claim full sanitization; separate privacy fix required. None of these new 0.2.3 runtime tests performed.

## Toolchain-only Inno Setup 6 source change acceptance
Tests for v0.2.4: PowerShell Parser.ParseFile of modified Run-Profile.Core and both modified R56/R57 release controllers; simulate Inno 6 x86 machine install vs per-user LocalAppData install vs app uninstall registry vs Winget packages; reject nonexistent ISCC and non-6 major/attacker-controlled file, no general-disk scan, diagnostic log no user path. On owner Windows verify real 6.7.3 file, local Diagnostics PASS, then Source Sync/QUICK/FULL SAFE build Inno installer using exact resolved path. GitHub static persistence PASS only; **no Windows 0.2.4 test performed yet**. Changing previously tested R56 baseline controller for toolchain compatibility does not turn older R56 checks green at modified SHA.

## v0.2.5 ISCC zero-version fallback test gate
PowerShell parser preflight on changed Test Center Core and R56/R57 controllers required. Expected positive: present ISCC.exe with file/product 0.0.0.0, official `/?` banner identifies Inno Setup 6 Command-Line Compiler. Negative: wrong major Inno 7, missing ISCC, wrong banner, CLI hanging beyond six seconds, arbitrary process/injection, missing file, nonstandard path. Do not call PASS without actual Windows native runner evidence; the user must rerun Diagnostics/QUICK at exact new SHA. The CLI probe must not create installers, edit Windows settings or upload full user paths. Latest known automated GitHub evidence is v0.2.4 Inno FAIL; v0.2.5 **NOT RUN**.
