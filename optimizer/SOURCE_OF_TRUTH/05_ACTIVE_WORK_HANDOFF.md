# 05 — ACTIVE WORK HANDOFF

Date: 2026-10-18.
Primary block: R57 SAFE BACKGROUND ACTIONS, **local FULL SAFE gate awaiting actual Windows run**.
Repo: Merzo4/my-app-updates.
Code branch: mwo-r57-safe-background-actions.
Last known pre-documentation R57 source SHA: f9e63b0c57faab592ba17344943021cc7adbc123. Новый HEAD устанавливать по GitHub при начале работы.
Public release: mwo-v0.1.55.1. Last fully green candidate: R56 (0.1.56), build 32479505374, exact verification 32480404145.
R57_LOCAL_TEST_STATUS.json: ready-for-local-full-safe; publicRelease false; githubActionsUsedForR57 false; localTestCenterVersion 0.1.7.

## Implemented in R57 branch
- optimizer/patches/r57_safe_background_actions.py — mapping diagnosed permanent background families to existing SAFE cards.
- optimizer/scripts/r57_safe_background_actions_release.ps1 — cumulative R56 controller + R57 patch + build/SelfTest/installer.
- optimizer/scripts/r57_safe_background_actions_acceptance.ps1 — static contract checker.
- optimizer/scripts/r57_game_recovery_acceptance.ps1 — separate inherited GAME/RestoreAll lab gate.
- optimizer/R57_LOCAL_TEST_STATUS.json — prepared, never claim accepted.

## Conditions / blocked
- Windows full local build/runtime/test NOT RUN for R57.
- Destructive GAME/production RestoreAll for R57 NOT RUN on dedicated lab.
- R57 CI/public release NOT RUN; public release remains R55.1.
- R55.1 historical OTA timeout was later followed by separate staged OTA PASS; final upgrade path requires new acceptance on exact release.

## EXACT NEXT EXECUTION
1. Read authority docs and immutable checkpoint.
2. Fetch actual branch HEAD and separate it from last code SHA before docs.
3. On a suitable Windows environment run **Local Test Center FULL SAFE** on the R57 candidate: cumulative build -> R57 static acceptance -> SelfTest -> real UI window -> installer/portable; no GAME apply or other destructive actions.
4. Attach run ID, logs, OS, SHA, exact artifacts, and PASS/FAIL to a new REPORT + immutable checkpoint.
5. Only if above is successful, prepare separate disposable-lab GAME->production RestoreAll verification.
6. Follow 08_EXECUTION_SEQUENCE and get owner approval before Stable/public release.

## DO NOT REPEAT
R56 run 32479505374 and exact run 32480404145 for unchanged SHA/risk; do not reconstruct R55.1 publication again; do not redo unrelated MerzoStream tests.

## Working restrictions
Do not modify root README for another product, release public assets, process kill behavior, power/OneDrive/GAME policies, or user Windows. Docs-only setup is not a new test result.

## Test Center blocker discovered after documentation/bootstrap checkpoint
Owner reported first 0.1.7 GUI launch invisible and second «already running» modal. **FAIL (visible GUI UX)**, R57 product test still PENDING. Test Center infrastructure hotfix 0.1.8 commit `3523eaabba8461aa63ec80a3da9d7270180ffd3a` changes process launching to show WinForms first and hide only its own console afterwards, emits State/gui-shown.json marker and installer waits for it. **Hotfix is implemented, not Windows-validated.** Updated user BAT at optimizer/BOOTSTRAP/INSTALL_TEST_CENTER.bat offers scoped close of matching GUI pwsh processes after explicit confirmation, fetches pinned hotfix commit. Backup recovery BAT launches GUI with visible console for diagnostics.
EXACT NEXT OWNER STEP: close any active Test Center tests, run patched Test Center BAT, then confirm actual GUI visible and send sanitized D:\MerzoOptimizer-LocalLab\Logs\startup-error.log / gui-visibility-error.log if not. Record owner PASS/FAIL in next checkpoint. Only then run R57 QUICK/FULL SAFE, no GAME/RESTORE on workstation.

 
### Final pinned Test Center hotfix SHA / parser-safety correction
Final Test Center 0.1.8 source is `mwo-local-test-center@a6f2cd3fcd31a9b10c994333a00ae5ca3b05b1d3` (supersedes earlier infrastructure hotfix commit 3523eaabba8461aa63ec80a3da9d7270180ffd3a ONLY for the installer source pin). This is a minimal parse-safe native Console Add-Type adjustment; 0.1.8 **WINDOWS NOT RUN/PENDING**. Updated pinned BAT uses this exact immutable SHA. Prior checkpoint 003 is kept unchanged as historical.

## Future feature scope, not a switch of PRIMARY
Decision 002 + FEATURES/ approved GPU optimization, Memory & Background and user-session Merzo Guardian monitoring with opt-in allowlisted graceful mitigation. No Guardian binary or Windows process deployed. Current P4 EXACT NEXT EXECUTION unchanged: verify Test Center 0.1.8 visible GUI on owner Windows then R57 QUICK/FULL SAFE, evidence; future F0 only when sequence permits. Do not repeat R56 accepted tests or conflate new docs SHA with new validated product code.

## Latest owner Windows evidence — Test Center GUI recovered
Owner reports Test Center 0.1.8 installed and main GUI opened. Set GUI visibility issue: **PASS / OWNER OBSERVATION** (prior 0.1.7 FAIL preserved); test run logs/smoke gates **NOT VERIFIED**. Exact next instruction for owner: run **Диагностика**, check each stage PASS and available free D:; if PASS press **Обновить Source**, then **QUICK**, then **FULL SAFE**. Stop at first FAIL and send LAB-RESULT.json, REPORT.txt, Current.log (sanitize system/user details). Test Center local profile targets R57 mwo-r57-safe-background-actions and has 0.1.8; live source HEAD after docs may differ from R57 code SHA. Test Center re-syncs a dedicated D: checkout and SAFE run verifies production Program Files fingerprint.
**DO NOT PRESS GAME → RESTORE** on normal workstation. After actual test results, commit report/immutable checkpoint, exact OS/run/SHA/artifacts; release unchanged R55.1.

## New blocking evidence — Diagnostics auto upload verified
Owner screenshot of Test Center 0.1.8 shows auto-report `EVIDENCE_PUBLISHED ... queued=1 actionsMinutes=0`, while Diagnostics is **FAIL** for missing `ISCC.exe` (Inno Setup 6). GitHub `mwo-local-lab-evidence` latest event `20261018T072321769Z-profile.Diagnostics-7cd11a93`, evidence SHA 22030119a4af17803fd83ce3950f2041d400b761 confirms automatic upload. Source still absent (expected prior to Sync). Exact next: user installs **Inno Setup 6 (not 7)** from official vendor `https://jrsoftware.org/isdl.php` or winget `winget install --id JRSoftware.InnoSetup -e -s winget -i`; then restart Test Center if needed, rerun Diagnostics and stop on FAIL. If PASS proceed Sync -> Quick -> FullSafe. Don't manually send reports when EVIDENCE_PUBLISHED present. Evidence payload itself currently exposes user/machine identifiers: sanitize in future Test Center bugfix under distinct scoped gate.

## Latest Test Center UX correction 0.1.9
Test Center 0.1.8 incorrectly shows "Windows 10.0.26200.0" on owner Windows 11 Pro 25H2 build 26200.9457; display-only fix committed in infrastructure `mwo-local-test-center@00f0484cbff48380a205410da1ebf208c7f63de6`, new 0.1.9 user BAT pin in optimizer/BOOTSTRAP. NOT a newly tested optimizer version. When convenient, owner closes Test Center GUI and updates via `D:\MerzoOptimizer-LocalLab\UPDATE-TEST-CENTER.bat` (or current GitHub pinned INSTALL_TEST_CENTER.bat), then confirms proper Environment label. No need to rerun unrelated R56 tests. Highest-priority R57 gate: ensure Inno Setup 6 detected (previous Diagnostics FAIL), then on PASS Sync → QUICK → FULL SAFE. The current Test Center GUI version 0.1.8 installation was previously confirmed.

## Active local infrastructure change — Test Center 0.2.0 native EXE preview
User requested no separate visible PowerShell/terminal at GUI launch. Separate Test Center code branch `mwo-local-test-center@f8757abcfabf0780fcf891661e0e1596dc1ad96a` contains C#/.NET 10 WinForms EXE frontend + local self-contained build/smoke in installer. Optimizer branch pinned `optimizer/BOOTSTRAP/INSTALL_TEST_CENTER.bat` to exact commit with NativeHost sources. Installer should preserve old desktop launcher until compilation + native smoke succeed; `START-TEST-CENTER-LEGACY.bat` remains as rollback. Native GUI launch + profile executor + auto-report on owner Windows are **NOT RUN / PENDING**.
**EXACT NEXT:** close Test Center 0.1.9 while no profile runs; launch latest pinned BAT or UPDATE-TEST-CENTER.bat; watch build log. Confirm desktop shortcut target is `D:\MerzoOptimizer-LocalLab\App\Native\MerzoOptimizer.TestCenter.exe`, UI opens without PowerShell console, Diagnostics and auto report still work. If failure, send `Logs/native-build.log`, `native-smoke.log` and `native-gui-error.log` (if exists). After passing update, install/check Inno Setup 6 then Diagnostics PASS -> Source -> Quick -> FullSafe R57. Destructive GAME only disposable lab.
