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
