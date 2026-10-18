# REPORT 018 — Inno Setup 6 EXE version resources are zero, fix detection

Date: 2026-10-18.
Repo: Merzo4/my-app-updates, SOT branch mwo-r57-safe-background-actions.
HEAD BEFORE SOT: 31d22512d77eb42d8dc9064711d8dbd2be58b7f0; after: the commit containing this report.
Test Center SOURCE SHA: mwo-local-test-center@7626f1fd28d931620b9a255a3d88672a9192578b v0.2.5.
Previous live evidence: mwo-local-lab-evidence@ca858f12ccc66a6bee2086a8d9e7738ab446763b, v0.2.4 Diagnostics FAIL.
Risk scope: read-only compiler identity check, Test Center installation pin and cumulative compiler scripts, no product runtime mutation or public release.

## Owner evidence and root cause
User screenshot shows genuine path exists: `Get-Item (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')`; FileVersion `0.0.0.0`, ProductVersion `0.0.0.0`, Version6Found False. Prior WinGet listing identifies installed Inno Setup 6.7.3 but does not by itself authenticate the EXE. Previous Test Center 0.2.4 resolver checked only major-six EXE file resource and rejected zero metadata. This mismatch **causes the documented 0.2.4 false negative**. Actual ISCC runtime banner not yet supplied.

## Implementation
Separate Test Center 0.2.5 code implements `Test-Inno6CompilerIdentity`: accepts explicit major6 resource, rejects explicit major7, otherwise performs read-only fixed `/?` on already-discovered ISCC.exe through .NET ProcessStartInfo with redirected stdout/err and 6-second timeout, requires documented Inno Setup 6 Command-Line Compiler banner. Diagnostics and Quick share this resolver. Optimizer active R56 and R57 cumulative installer controllers use the exact same helper, so green Diagnostics cannot be immediately contradicted by old hardcoded metadata validation. Pinned user BAT updated to exact Test Center SHA. No actual Windows test here, no registry/Program Files mutations, no stable release.

## Verification statuses
PASS: owner actual file metadata zero demonstrated; GitHub inspected/committed source and pin consistency (verify new HEAD).
IMPLEMENTED: read-only compiler banner fallback in Test Center and cumulative R56/R57.
NOT RUN: PowerShell parser/runtime on owner Windows, compiler `/?` banner verification, Test Center 0.2.5 Windows install/native GUI, Diagnostics/auto evidence, R57 Source/QUICK/FULL SAFE or installer runtime.
FAIL preserved: previous v0.2.4 Diagnostics Inno 6 metadata-only; automatic upload PASS.
No destructive test on owner's main workstation. No R56 prior PASS transferred to new compiler-controller SHA.

## EXACT NEXT EXECUTION
Owner closes Test Center when idle and runs existing `D:\MerzoOptimizer-LocalLab\UPDATE-TEST-CENTER.bat` to get v0.2.5. After visible native GUI opens, run Diagnostics and await auto-report. If PASS proceed Update Source -> QUICK -> FULL SAFE sequentially; if FAIL collect event and safe /? banner output without local paths, diagnose before another patch. Never GAME/RESTORE on main workstation.
