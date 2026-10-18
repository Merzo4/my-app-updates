# REPORT 022 — R57 QUICK fail proven Windows Python alias 9009, toolchain preflight v0.2.6

Date: 2026-10-18.
Product: Merzo Windows Optimizer.
Repo/branch: Merzo4/my-app-updates / mwo-r57-safe-background-actions.
SOT HEAD BEFORE: 4610321c35c270df17df8999b46e412349886ca6; AFTER: GitHub commit containing report.
TC infra: mwo-local-test-center@95c735c54ced62605e9c02cd98569b0b4d023665, source version 0.2.6.
Prior QUICK evidence mwo-local-lab-evidence@aa91d2d16a64e68a28910cc99118691b0d7fca13, event 20261018T130032723Z-profile.Quick-6d3cf2f4.
Scope: Test Center toolchain checks, pinned bootstrap, docs only; no R57 runtime source patch or OS mutation.

## User proof / root cause
After QUICK failed at R49's earliest Python patch r24_update_center.py, owner ran PowerShell commands: `python --version` printed only `Python`; `python exit=9009` documented, Windows App Installer Alias. `py -3 --version` command not found. This is positive evidence that there is **no usable Python 3 command** in the shell used for Test Center; calling `python` does not run the needed script. Root cause of first-patch failure is missing runtime, **not a demonstrated defect in r24_update_center.py**. Prior Diagnostics v0.2.5 8/8 PASS omitted this toolchain dependency; old PASS preserved for old stages but not complete prerequisites.

## Fix prepared in separate Test Center
0.2.6 adds read-only Test-Python3Runtime by executing literal `python -c`, verifying Python >=3.10 and exact sentinel, checking exit code zero. New env.python Diagnostics gate and fail-fast QUICK check before Sync/compilation, inherited by FULL SAFE. Test Center version bumped 0.2.6, pinned Optimizer bootstrap updated to its exact SHA; no automated Python installation, registry, alias changes or R57 patch changes.

## Classification
PASS: user screenshot proves Windows alias exit 9009 and missing py launcher; prior Sync and auto evidence.
FAIL: actual QUICK on existing exact SHA; old new-PC Python prerequisite.
IMPLEMENTED/PREPARED: Test Center 0.2.6 Python prerequisite in GitHub.
NOT RUN: user Python installation, 0.2.6 native Windows build, new Diagnostics Python stage, QUICK retry, FULL SAFE.
BLOCKED: R57 test/build and publication until Python present and explicit passes.
No GAME/RESTORE on owner main workstation.

## Exact next
Owner installs trusted Python 3 (WinGet package Python.Python.3.13 from winget source recommended), restarts shell and Test Center, confirms real `python -c "import sys; print(sys.version)"` returns 3.x exit 0. Resolve App Execution Alias priority if still 9009. Then update Test Center to 0.2.6 via existing D: updater, run Diagnostics (new Python stage must PASS), QUICK, then FULL SAFE only after QUICK PASS, with auto remote evidence and new checkpoint.
