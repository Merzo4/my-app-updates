# IMMUTABLE CHECKPOINT 010 — native GUI parser source restoration

Date: 2026-10-18.
Repo: Merzo4/my-app-updates.
SOT branch before: 54d99032ca7d2ca9463a3c26b038f72ccf97efb7; after: actual commit containing checkpoint.
TC infra prior: f8757abcfabf0780fcf891661e0e1596dc1ad96a; corrected: 1db2b1d91ea699a84fd0a374b00867c185d9e8c9.
Previous checkpoint: EXECUTION_LEDGER/2026-10-18-009-native-test-center-gui-preview.md.
Risk: documentation + Test Center UI/bootstrap only; no R57 app source or Windows mutation.

## Sequential ACTION LOG
1. Received screenshot of owner Test Center native 0.2.0 installation showing parse errors in `MerzoOptimizer.LocalLab.ps1`, error thrown from `Install-LocalLab.ps1:30`.
2. Inspected exact GitHub source 0.2.0 and known-good 0.1.8 reference: corrupted 1538 vs good 498 lines; 5x duplicated WinForms blocks, malformed registry insertion. Identified earlier unsafe string replacement-expansion as source corruption.
3. Classified 0.2.0 installation **FAIL**, correctly caught before native EXE compilation; no claim of running R57 or native UI.
4. Restored known-good script and inserted Windows 11 product build label helper via substring splice, avoiding replacement template interpretation. Asserted unique GUI functions/trailer (531 lines).
5. Wrote separate TC infrastructure corrective commit 1db2b1d91ea699a84fd0a374b00867c185d9e8c9, bumped TC 0.2.1 in profile and NativeHost csproj/installer.
6. Updated Optimizer pinned Test Center BAT to new immutable SHA and 0.2.1 version, plus SOT current/handoff, rules, sequence, testing, repo map, report 010, and this append-only checkpoint.
7. Kept earlier 0.2.0 FAIL history; no operator Windows rerun, install, release or other product changes.

## RESULT
FAIL: native 0.2.0 installer PS parser on owner Windows.
IMPLEMENTED/PREPARED: 0.2.1 corrected source and pinned update.
PASS: exact GitHub recovery/ref/structural source checks.
NOT RUN: PowerShell runtime parser for new code on user Windows, .NET publish native GUI smoke, auto evidence, R57 local tests.
PENDING: user retest; Inno Setup 6 original prerequisite.
DO NOT REPEAT: R56 known-good exact builds/restore and other project work.
NO destructive GAME/RESTORE/public release.

## EXACT NEXT EXECUTION
Owner closes Test Center/no test active, runs installed `UPDATE-TEST-CENTER.bat` to fetch repaired v0.2.1. Observe parser gate, native publish, smoke, EXE desktop shortcut. If FAIL capture logs. If PASS run prerequisite Diagnostics (after Inno Setup 6), then R57 Sync/Quick/FULL SAFE. Preserve all statuses and record new checkpoint only after new evidence.
