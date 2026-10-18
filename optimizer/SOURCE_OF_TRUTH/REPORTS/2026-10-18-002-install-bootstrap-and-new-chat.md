# 2026-10-18-002 — Install bootstraps and new-chat instructions

Requested: Russian new-chat instruction and downloadable BAT launchers for separate Optimizer and Test Center setups.

Code branch: mwo-r57-safe-background-actions.
HEAD before: 0ac7ffb59e8c73c4e978ebf3518fd665e4988d3c.
Type: BOOTSTRAP / DOCUMENTATION ONLY, no app runtime code changes.
Code state R57: unchanged, still awaiting Local FULL SAFE.

## Existing sources inspected
- `mwo-local-test-center@edc83fca9f0f89fc895a0a30c7f58f81af143779`: existing INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat, Install-LocalLab.ps1, local-lab-profile.json (Test Center 0.1.7, target R57).
- Published GitHub `mwo-v0.1.55.1` release: installer asset exact SHA-256 `bda73f442a1726082372e8c4272668e0151c9d882df1350f417fadcc022a1035`.
- Source of Truth current 00/02/03/05/06 and initial checkpoint.

## Changes
- optimizer/BOOTSTRAP/INSTALL_TEST_CENTER.bat — pinned Test Center infrastructure with D: preflight, source scripts, setup GUI.
- optimizer/BOOTSTRAP/INSTALL_WINDOWS_OPTIMIZER.bat — pinned stable installer digest, failure fail-close, installed-version downgrade protection, interactive setup.
- optimizer/BOOTSTRAP/NEW_CHAT_PROMPT.txt — paste-in continuation instructions.
- optimizer/BOOTSTRAP/README.md — prerequisites and operating instructions.
- Update relevant SOT map/install/new-chat pointers, report, immutable checkpoint and live ledger pointer.

## Truthful test results
- PASS: GitHub source and official published digest verified via repository metadata.
- PASS: documentation/launcher paths committed and repository diff scoped (to be verified after commit).
- NOT RUN: BAT execution on Windows, UAC install, Test Center GUI install on actual PC, R57 local FULL SAFE.
- NOT DONE: any new public optimizer release or destructive GAME/RESTORE.

## EXACT NEXT EXECUTION
On Windows with D: and an appropriate developer toolchain, run Test Center installation and Diagnostics, then QUICK/FULL SAFE; capture result IDs, logs and screenshots, record a new checkpoint. Destructive tests only in dedicated lab, stable release by owner approval.
