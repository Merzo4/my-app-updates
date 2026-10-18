# IMMUTABLE CHECKPOINT 017 — 0.2.4 auto report PASS and Inno compiler detect FAIL

Date: 2026-10-18.
Product: Merzo Windows Optimizer only.
SOT Repo: Merzo4/my-app-updates.
Branch: mwo-r57-safe-background-actions.
SOT HEAD BEFORE: 269cc056a33e771224ef03b4e0b1c87a569bb98d; AFTER: new GitHub commit containing this checkpoint.
Previous: EXECUTION_LEDGER/2026-10-18-016-inno6-current-user-file-confirmed.md.
Latest separate Test Center SHA: f0044e15c1952482c65b6d3d85afa982bab4deb5, version 0.2.4.
Latest auto evidence: mwo-local-lab-evidence@ca858f12ccc66a6bee2086a8d9e7738ab446763b; event 20261018T093622014Z-profile.Diagnostics-48622cba.
Scope: status/report bookkeeping only, no code changes or Windows operations.

## Ordered ACTION LOG
1. Owner reported newly automated Test Center diagnostics sent.
2. Verified live Test Center, SOT, and evidence branch HEADs; new evidence 20261018T093622014Z profile.Diagnostics, version 0.2.4.
3. Read EVENT.json, Current.log and latest LAB-RESULT.json from GitHub. Diagnostics FAIL only `Inno Setup 6: ISCC.exe not found; inspect install location`, seven other stages PASS. Remote auto-upload PASS.
4. Re-read SOT 00, status, handoff, live ledger, latest immutable checkpoint 016 and 08 execution sequence. Prior owner per-user ISCC physical presence True and winget v6.7.3 remain established; no evidence of actual embedded exe version or why resolver rejected it.
5. Inspected active Test Center Resolve-InnoSetup6Compiler: it checks path and embedded FileVersion/ProductVersion major6. A missing version match is one hypothesis, not yet confirmed root cause. Keep fail-closed, do not silently mark Diagnostics PASS.
6. Updated 02 status, 05 handoff, 08 sequence, 06 latest checkpoint pointer, Report 017 and this immutable checkpoint.
7. Did not build/execute a new EXE, alter owner Windows, or publish any stable release.

## Results
PASS: 0.2.4 remote GitHub auto upload and non-Inno prerequisites.
FAIL: Inno 6 resolver in live 0.2.4 Diagnostics.
PENDING: exact cause; first request real executable embedded version info (safe redacted).
NOT RUN/BLOCKED: R57 Source Sync, QUICK, FULL SAFE, dedicated lab destructive tests.
NO RELEASE: R55.1 remains published stable.
DO NOT REPEAT: R56 exact accepted tests, Inno Setup reinstall, prior Test Center repair rounds without new evidence.

## EXACT NEXT EXECUTION
Owner runs read-only PowerShell metadata inspection for the existing ISCC.exe: Name/FileVersion/ProductVersion/version-6-match. If it matches, isolate runtime resolver mismatch; otherwise design reliable official compiler validation and only then change code. Do not bypass safety gates or run GAME/RESTORE on primary machine.
