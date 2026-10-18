# IMMUTABLE CHECKPOINT 015 — WinGet-installed Inno Setup 6 compiler resolution

Date: 2026-10-18.
Repo: Merzo4/my-app-updates.
SOT branch HEAD BEFORE: 3458b69743ed71c91b432a9f38879d6a0cfc53d7; AFTER: commit containing this checkpoint.
Latest previous: EXECUTION_LEDGER/2026-10-18-014-owner-0-2-3-diagnostics-auto-upload.md.
Separate Test Center source: mwo-local-test-center@f0044e15c1952482c65b6d3d85afa982bab4deb5, version 0.2.4.
Risk boundary: read-only toolchain discovery, process-local env path to compiler, installer scripting only. No user machine tests performed in assistant environment; no public product release.

## Ordered ACTION LOG
1. Owner screenshot: winget JRSoftware.InnoSetup reports 6.7.3, but default Program Files Get-ChildItem paths return nothing. Confirms package registration but NOT where actual ISCC.exe resides.
2. Verified GitHub active SOT/TC/evidence branch HEAD and latest checkpoint 014; read required SOT, testing rules, exact legacy code.
3. Inspected Test Center Run-Profile.Core Diagnostics and cumulative Optimizer R56/R57 release scripts: all hard-code Program Files 6 paths. Determined source of false-negative and subsequent Quick failure risk. External WinGet issue corroborates LOCALAPPDATA per-user default.
4. Patched separate Test Center to v0.2.4: read-only Inno 6 resolver checks local user/system paths, App Paths/uninstall registry, targeted Winget package; validates physical compiler ISCC.exe major 6 version metadata. Same result used by Diagnostics and Quick; process-local MWO_INNO6_ISCC exported, without raw path in remote diagnostic stage.
5. Committed Test Center source SHA f0044e15c1952482c65b6d3d85afa982bab4deb5. Updated active Optimizer cumulative R56/R57 controller scripts to accept and independently verify the env-provided compiler plus standard locations (toolchain compatibility only).
6. Updated pinned user Test Center BAT, status/handoff/sequence/test rules/repo map, report 015, this checkpoint and live-ledger pointer. Historical immutable checkpoints unchanged.
7. No code compiled, physical ISCC location confirmed, Windows Test Center updated, R57 product test executed or release published in this assistant environment. Any Windows PASS still awaits owner evidence.

## Outcomes
DONE: toolchain discovery and handoff source implemented, GitHub commits.
PASS: direct source inspection and repository persistence.
FAIL (historical): v0.2.3 Inno diagnostic only.
NOT RUN: v0.2.4 on Windows, physical compiler availability, Diagnostics rerun, Source/QUICK/FULL SAFE and separate destructive lab.
BLOCKED: R57 local P4 until Diagnostics verified PASS.
NO REPEAT: R56 historical exact code PASS has separate SHA; new R56 controller revision must be checked with new build path, not reuse it.
NO RELEASE, NO GAME/RESTORE on main user PC.

## EXACT NEXT EXECUTION
Owner updates Test Center 0.2.4 via installed updater, confirms GUI, runs Diagnostics. If PASS proceed Sync -> QUICK -> FULL SAFE; else collect new GitHub evidence then request read-only local ISCC path/version check. Keep automation report delivery distinct from Diagnostics result.
