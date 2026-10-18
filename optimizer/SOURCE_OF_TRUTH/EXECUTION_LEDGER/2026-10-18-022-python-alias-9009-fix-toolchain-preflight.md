# IMMUTABLE CHECKPOINT 022 — Python execution alias 9009, missing prerequisite for QUICK

Date: 2026-10-18.
Repo: Merzo4/my-app-updates; working SOT branch mwo-r57-safe-background-actions.
Before HEAD 4610321c35c270df17df8999b46e412349886ca6; after commit containing this immutable checkpoint.
Previous: EXECUTION_LEDGER/2026-10-18-021-test-center-025-quick-first-python-patch-fail.md.
Test Center code: mwo-local-test-center@95c735c54ced62605e9c02cd98569b0b4d023665, version 0.2.6.
Risk: developer toolchain readiness, documentation; no Windows mutations, R57 runtime patch or release.

## Ordered ACTION LOG
1. User uploaded native PowerShell screenshot after QUICK FAIL showing `python --version` = bare "Python", `$LASTEXITCODE=9009`; `py -3 --version` CommandNotFoundException.
2. Correlated owner proof with previous real GitHub evidence QUICK FAIL at first R49 cumulative Python patch r24_update_center.py. Identified missing functional Python interpreter as root cause. Avoid blaming R57 source.
3. Confirmed live GitHub Test Center and Optimizer HEADs, read actual Test Center Run-Profile.Core.ps1 and mandatory SOT, most recent checkpoint 021, release scripts, and toolchain environment contracts.
4. Verified official Microsoft Windows guidance that App Installer python.exe alias returns error when Python is not installed and must not be considered a runnable interpreter.
5. Patched separate Test Center source v0.2.6, adds real interpreter Diagnostics gate `env.python` and pre-Quick functional check (minimum Python 3.10, exact `python -c` sentinel and exit=0) rejecting 9009 store alias; no automatic install.
6. Committed Test Center change 95c735c54ced62605e9c02cd98569b0b4d023665; updated pinned optimizer BAT and SOT status, handoff, ledger, sequence, testing, repo map; wrote REPORT 022 and this immutable checkpoint.
7. No Python installed on owner PC by assistant; no Windows run of v0.2.6, QUICK retry or FullSafe; no stable release.

## Results
PASS: observed local alias exit 9009 / missing py, verified missing toolchain prerequisite; previous Sync/auto upload.
FAIL: existing QUICK controller exit 1 at r24 first Python patch (new evidence unchanged).
IMPLEMENTED: new Test Center v0.2.6 source Python toolchain check; Windows not tested.
NOT RUN: owner Python install, 0.2.6 native build, Diagnostics, QUICK rerun or FULL SAFE.
BLOCKED: R57 full safe, destructive tests/public release.
DO NOT REPEAT: R56 historical test PASS on changed source; don't rerun old Quick without fixing prerequisite.

## EXACT NEXT EXECUTION
Owner installs Python.Python.3.13 (official winget source), closes/reopens shell & Test Center, verifies working python -c/exit 0, updates Test Center to 0.2.6, runs Diagnostics then QUICK; only if QUICK PASS run FULL SAFE. Report evidence; never GAME/RESTORE on main PC.
