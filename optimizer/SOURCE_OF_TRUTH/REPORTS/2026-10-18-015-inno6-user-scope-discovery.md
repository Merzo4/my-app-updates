# REPORT 015 — Inno Setup 6 installed but detection missed per-user compiler

Date: 2026-10-18.
Repo: Merzo4/my-app-updates.
Branch mwo-r57-safe-background-actions; HEAD BEFORE 3458b69743ed71c91b432a9f38879d6a0cfc53d7.
HEAD AFTER: commit containing this report (retrieve exact GitHub SHA).
Test Center infrastructure: mwo-local-test-center@f0044e15c1952482c65b6d3d85afa982bab4deb5, version 0.2.4.
Risk: read-only toolchain discovery and toolchain-path propagation; no Windows registry writes, no optimizer feature mutations, no public release.

## User evidence
Owner sent Windows PowerShell screenshot showing `winget list --id JRSoftware.InnoSetup -e` -> Inno Setup version **6.7.3** already installed. PowerShell Get-ChildItem for C:\Program Files\Inno Setup *\ISCC.exe and Program Files (x86) yielded no result. Last auto GitHub Test Center 0.2.3 Diagnostics shows only Inno 6 ISCC.exe FAIL. A WinGet packaging issue confirms a known per-user installation path in LOCALAPPDATA\Programs\Inno Setup 6, which old scripts did not check. The screenshot alone does NOT prove actual compiler exists; version listing might refer to a broken installation or nonstandard folder.

## Root cause
- tools/MerzoOptimizer.LocalLab/Run-Profile.Core.ps1 Diagnostics checked only two Program Files hard-coded paths, not per-user scope or registered install metadata.
- optimizer/scripts/r56_baseline_process_intelligence_release.ps1 (cumulative baseline) and r57_safe_background_actions_release.ps1 ALSO selected only those paths for EXE installer compilation. Merely changing Diagnostics would give an invalid green gate that still failed during QUICK.

## Code change
- Separate Test Center v0.2.4 `mwo-local-test-center@f0044e15c1952482c65b6d3d85afa982bab4deb5`: `Resolve-InnoSetup6Compiler` checks system Program Files, per-user LocalAppData programs, PATH, Windows App Paths, scoped Inno Setup 6 uninstall registry, and targeted installed WinGet package. Requires actual ISCC.exe and FileVersion/ProductVersion major 6, returns null on failure. Diagnostics stores result as local env variable without user path in stage summaries; QUICK reuses resolver and exports the same process-scoped env var.
- Active Optimizer branch: minimal selection updates in cumulative R56 & R57 release controller scripts. New path accepted from MWO_INNO6_ISCC (verified again for EXE name/version) or old standard paths. No product mutation changed and no public release.
- Pinned optimizer/BOOTSTRAP/INSTALL_TEST_CENTER.bat points to v0.2.4 source; SOT live status/handoff/sequence/tests/map updated, report 015 and immutable checkpoint 015 added.

## Evidence status
PASS: GitHub sources inspected, change commits written.
IMPLEMENTED: source-only compiler detection and controller toolchain handoff.
NOT RUN: PowerShell Parser on Windows, Test Center 0.2.4 native build, physical Inno 6 path verification, live new Diagnostics, R57 Sync/QUICK/FULL SAFE, install/recovery/OTA.
FAIL (historical): Test Center 0.2.3 Diagnostics missing ISCC from standard paths.
R56 historical PASS does NOT carry to modified R56 toolchain controller.
No destructive GAME/RESTORE.

## EXACT NEXT EXECUTION
Owner closes Test Center when idle, updates via UPDATE-TEST-CENTER.bat to v0.2.4, executes Diagnostics and automatically sends evidence. If FAIL, locate exact physical ISCC file in per-user local path and inspect Windows registry installation path before further source work. On Diagnostics PASS, safely perform Source Sync → QUICK → FULL SAFE, stop on first FAIL and record latest evidence. Never force OS process changes or publish release without owner.
