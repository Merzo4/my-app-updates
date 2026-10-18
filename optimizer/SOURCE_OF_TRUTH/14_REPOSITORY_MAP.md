# 14 — REPOSITORY MAP AND OWNERSHIP

## Important
merzo-windows-optimizer work is in a **shared** Merzo4/my-app-updates repository, not a standalone repo. Root README, CHANGELOG.md and RELEASE_POLICY.md currently describe the MerzoStream suite; they are not the optimizer's authoritative design instructions.

## Optimizer code/test paths
- optimizer/source/ and optimizer/source-min/: archived/chunked historical bootstrap source, NOT a simple up-to-date full source checkout.
- optimizer/patches/: ordered release patches r24...r57; R57 safe_background_actions.py.
- optimizer/scripts/: cumulative release controllers, exact accepted test routines and safety gates.
- optimizer/Rxx_*_STATUS.json: machine-generated build/install/update/recovery statuses, some contain historic FAIL.
- optimizer/snapshots/: preserved baseline contracts.
- optimizer/triggers/: historical CI trigger markers.
- .github/workflows/build-mwo-*.yml and verify-mwo-*.yml: automated builds/tests for optimizer.
- GitHub Releases mwo-v*: public optimizer installers; other tags may belong to MerzoStream.
- optimizer/SOURCE_OF_TRUTH/: new canonical docs, decisions, immutable checkpoints, reports, next execution.

## Exact R57 important paths
- optimizer/patches/r57_safe_background_actions.py.
- optimizer/scripts/r57_safe_background_actions_release.ps1.
- optimizer/scripts/r57_safe_background_actions_acceptance.ps1.
- optimizer/scripts/r57_game_recovery_acceptance.ps1.
- optimizer/R57_LOCAL_TEST_STATUS.json.

## Branches
- main: shared release repository (not the current optimizer source-of-truth).
- mwo-r55-1-startup-binding-hotfix: public 0.1.55.1 provenance.
- mwo-r56-baseline-process-intelligence: last exact green technical candidate.
- mwo-r57-safe-background-actions: current active code branch + SOT at bootstrapping date.
Other historical optimizer branches are evidence/history, NOT current active authority without new decision.

## Rules of ownership
Never silently alter MerzoStream files, public release tags, shared updater resources, or other products. Any source-tree relocation or branch migration requires binding DECISIONS record and exact CI/Windows tests.

## User install / new-chat bootstraps
`optimizer/BOOTSTRAP/` — version-pinned user-facing BATs for Test Center and publicly released Optimizer; also README and NEW_CHAT_PROMPT. Do not confuse them with product compilation scripts in optimizer/scripts. See REPORTS/2026-10-18-002-install-bootstrap-and-new-chat.md.
 
Test Center separate infrastructure `mwo-local-test-center@3523eaabba8461aa63ec80a3da9d7270180ffd3a` has 0.1.8 hotfix. The active Optimizer branch contains the pinned repair installer and scoped `optimizer/BOOTSTRAP/RECOVER_TEST_CENTER_WINDOW.bat` for troubleshooting. Source of Test Center is NOT bundled into optimizer/SOURCE_OF_TRUTH and not merged into Optimizer product code.

## Decision 002 planned feature contracts
`optimizer/SOURCE_OF_TRUTH/FEATURES/GPU_OPTIMIZATION_CENTER.md`, `MEMORY_BACKGROUND_CENTER.md`, `MERZO_GUARDIAN.md` and `DECISIONS/2026-10-18-002-performance-gpu-memory-guardian.md` are source-of-truth specifications for planned modules, **not implementation files**. No new GPU/Guardian binary or driver in optimizer source.

## Current Test Center infrastructure display fix
`mwo-local-test-center@00f0484cbff48380a205410da1ebf208c7f63de6` holds v0.1.9 read-only Windows 11 environment display correction. `optimizer/BOOTSTRAP/INSTALL_TEST_CENTER.bat` pins this exact source SHA; installed `D:\MerzoOptimizer-LocalLab\UPDATE-TEST-CENTER.bat` fetches latest Lab bootstrap from infra branch. No Optimizer executable source changed.

## Native Lab GUI code
Separate `mwo-local-test-center` now stores `tools/MerzoOptimizer.LocalLab/NativeHost/{MerzoOptimizer.TestCenter.csproj,Program.cs}`, `Build-NativeHost.ps1`, updated `Install-LocalLab.ps1` and Test Center profile 0.2.0. Optimizer branch contains only pinned user BAT and SOT documentation; Optimizer R57 binary/source unchanged. No need to migrate all PowerShell runner scripts to a new process engine to achieve native standalone GUI.
