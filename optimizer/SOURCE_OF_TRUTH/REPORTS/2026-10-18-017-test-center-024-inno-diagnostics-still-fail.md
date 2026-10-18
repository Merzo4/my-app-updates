# REPORT 017 — Test Center v0.2.4 Diagnostics Inno6 false-negative investigation

Date: 2026-10-18.
Repo: Merzo4/my-app-updates, SOT branch mwo-r57-safe-background-actions.
HEAD BEFORE: 269cc056a33e771224ef03b4e0b1c87a569bb98d, AFTER: commit containing report.
TC branch SHA f0044e15c1952482c65b6d3d85afa982bab4deb5, version 0.2.4.
Remote evidence branch mwo-local-lab-evidence SHA ca858f12ccc66a6bee2086a8d9e7738ab446763b; Event 20261018T093622014Z-profile.Diagnostics-48622cba.
Risk: GitHub read/checkpoint only; no code/PC action, no release.

## Verified new owner test result
User: "отчет отправлен". Queried GitHub evidence HEAD, LATEST_EVENT/EVENT.json, Current.log, and LATEST/LAB-RESULT.json. v0.2.4 Diagnostics **FAIL** only Inno Setup 6 (`ISCC.exe not found; inspect install location`). PASS D:, Git, PowerShell 7.6.7, .NET 10, D: lab boundary, production Program Files protection, disk capacity. Actual automatic upload **PASS** (new evidence commit), distinct from diagnostics result. Source not prepared and R57 Quick/FullSafe NOT RUN.

## Differential diagnosis
The screenshot in prior checkpoint 016 proves `Test-Path (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')` returned True, and winget earlier displayed package v6.7.3. v0.2.4 Run-Profile.Core contains a resolver which adds that per-user path and checks the embedded FileVersion/ProductVersion for major 6. Null resolution despite known file existence could mean metadata mismatch or another resolver runtime/environment issue; actual cause NOT PROVEN by GitHub log. Do not reinstall Inno or disable compiler verification prematurely.

## Test outcomes
PASS: remote auto-upload v0.2.4, all listed non-Inno checks, GitHub source investigation.
FAIL: Inno Setup 6 test gate at v0.2.4 exact runtime.
PENDING: EXE embedded FileVersion/ProductVersion and resolver discrepancy.
NOT RUN: Source Sync, QUICK, FULL SAFE, product installer, destructive lab, auto retry offline.
No public Optimizer release.

## EXACT NEXT
Owner runs a read-only PowerShell command returning only ISCC.exe Name, FileVersion, ProductVersion and whether either matches a 6.x version. No full user path in response. If metadata 6.x but Test Center fails, diagnose resolver safely with non-sensitive stage telemetry and a focused fix. If metadata absent/non6, design supported compiler identity verification with no bypass. Preserve immutable report and checkpoint sequence.
