# IMMUTABLE CHECKPOINT 016 — Inno Setup 6 current-user file exists

Date: 2026-10-18.
Repo Merzo4/my-app-updates.
SOT branch HEAD before: 9834354abbd1264f571fca15be71155d1ab83913; after: commit containing this checkpoint.
Prev immutable checkpoint: EXECUTION_LEDGER/2026-10-18-015-inno6-user-scope-detection.md.
TC source f0044e15c1952482c65b6d3d85afa982bab4deb5 v0.2.4.
Scope: screenshot analysis, GitHub verification, documentation only, no user PC operations.

## Ordered ACTION LOG
1. User sent Windows PowerShell screenshot of `Test-Path (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')`, returning `True`.
2. Classified PASS narrowly to physical compiler file existence in expected current-user location; winget v6.7.3 registration corroborates product version but file embedded metadata still unchecked.
3. Fetched current GitHub SOT/Test Center/evidence branch HEADs. SOT before 9834354abbd1264f571fca15be71155d1ab83913; Test Center pinned 0.2.4; remote evidence last 0.2.3 Diagnostics FAIL. No new Test Center 0.2.4 local run yet.
4. Re-read mandatory 00_READ_FIRST, SOT current status, handoff, live-ledger/latest checkpoint and execution sequence; next action unchanged.
5. Recorded screenshot evidence in REPORTS/2026-10-18-016-inno6-file-existence-user-proof.md and this immutable checkpoint; appended current/handoff/sequence and moved live ledger pointer to 016.
6. No executable/source edits, installer run, registry change, publication or GAME testing.

## Results
PASS: expected Inno 6 compiler file exists, read-only PowerShell output user-provided.
NOT RUN: Test Center 0.2.4 Diagnostics/AutoEvidence acceptance, actual compiler version resource, R57 Source/QUICK/FULL SAFE.
FAIL HISTORIC: previous Test Center 0.2.3 Inno 6 discovery.
DO NOT REPEAT: R56 old exact build passes; old Test Center installs; Inno Setup reinstall.
NO RELEASE / NO DESTRUCTIVE test on owner PC.

## EXACT NEXT EXECUTION
User updates Lab if currently older than 0.2.4; runs 0.2.4 Diagnostics and waits for automatic GitHub evidence; if PASS, Source Sync -> QUICK -> FULL SAFE with exact new SHA; stop at FAIL, no GAME/RESTORE on main PC.
