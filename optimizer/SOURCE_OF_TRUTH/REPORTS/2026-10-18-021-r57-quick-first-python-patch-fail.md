# REPORT 021 — New-PC R57 QUICK FAIL at earliest cumulative Python patch

Date: 2026-10-18.
Product: Merzo Windows Optimizer.
Repo/branch: Merzo4/my-app-updates / mwo-r57-safe-background-actions.
SOT HEAD before: 1329f6cd887faa3fe85f701c988609e7aa4f16f4; after: GitHub checkpoint commit.
Test Center exact infra: mwo-local-test-center@7626f1fd28d931620b9a255a3d88672a9192578b (v0.2.5).
Actual evidence: mwo-local-lab-evidence@aa91d2d16a64e68a28910cc99118691b0d7fca13, event 20261018T130032723Z-profile.Quick-6d3cf2f4.
Risk: analysis and documentation-only, no OS mutations, code patch, release or lab destructive actions.

## User and evidence
Owner sent "отчет отправлен" after starting QUICK. Live GitHub EVENT.json reports profile Quick, outcome FAIL, message "Локальная cumulative сборка: controller exit=1", version 0.2.5, source branch mwo-r57-safe-background-actions, exact SHA 1329f6cd887faa3fe85f701c988609e7aa4f16f4. Latest LAB-RESULT contains source.sync PASS and quick.build FAIL; first causal failure "Build controller failed: 1". Current.log shows successful fetch/reset and then PowerShell exception at D: Temp/Run/Current/r50_release_expanded.ps1 line 35, reporting "Patch failed: r24_update_center.py". This is the first Python patch in optimizer/scripts/r49_release.ps1, invoked through R50 cumulative baseline; no build or main window executed.

## Root cause investigation
Read exact R50/R49 script: R49 reconstructs immutable trusted R21 source from 29 parts then loops through patches beginning with r24_update_center.py via `python`; any nonzero exit throws a generic "Patch failed" error. Test Center 0.2.5 diagnostics only checks D:, Git, PowerShell 7, .NET10, Inno6, protected production and disk space; Python is NOT included. The GitHub log does not show inner Python version, stderr, alias status or script traceback. Missing Python/Windows Store alias on fresh PC is plausible, NOT proven; r24 patch-specific failure also possible. Do not assert Python absence.

## Status
PASS: historical Diagnostics 8/8, exact source Sync in current QUICK, GitHub automatic transport.
FAIL: cumulative QUICK first Python patch exit through controller=1, SHA 1329f6cd887faa3fe85f701c988609e7aa4f16f4.
NOT RUN/BLOCKED: QUICK later gates, R56/R57 patch/build, app GUI/installer, FULL SAFE and separate destructive lab.
No Windows/Linux tool executed by assistant, no stable release and no product source code changed. No raw machine or user identifiers reproduced.

## EXACT NEXT EXECUTION
Owner runs read-only `python --version` and `py -3 --version` in PowerShell, capturing exit codes (avoid local account pathname). If no genuine Python 3, install trusted official version with approval/guide and add test preflight; if Python is present, collect exact stderr from isolated r24 invocation under controlled D: lab or add narrow diagnostics logging first. Do not press QUICK/FULL SAFE until cause known and correction in GitHub. On fresh verified QUICK PASS, FULL SAFE next, without GAME/RESTORE on workstation.
