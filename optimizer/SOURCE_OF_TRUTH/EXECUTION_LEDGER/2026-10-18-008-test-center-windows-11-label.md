# IMMUTABLE CHECKPOINT 008 — Test Center Windows 11 display fix

Date: 2026-10-18.
SOT branch/HEAD before: mwo-r57-safe-background-actions@85fe37083ba3d6c6a6a59122ed4d67962db11418.
HEAD after: commit containing this checkpoint (verify live GitHub).
Test Center infra before: a6f2cd3fcd31a9b10c994333a00ae5ca3b05b1d3, after: 00f0484cbff48380a205410da1ebf208c7f63de6.
Previous checkpoint: EXECUTION_LEDGER/2026-10-18-007-diagnostics-fail-auto-evidence-published.md.
Risk: read-only GUI label and bootstrap pin change; no Windows mutation or R57 product code change.

## Ordered ACTION LOG
1. Owner supplied Windows Settings screenshot confirming 11 Pro, 25H2, build 26200.9457, contrasted with Test Center "Windows 10.0.26200.0".
2. Explained distinction between NT kernel major 10 and Windows 11 product naming; diagnosed precise GUI line `$cardEnv.Text="Windows $([Environment]::OSVersion.Version)..."`.
3. Verified Test Center branch SHA a6f2cd3fcd31a9b10c994333a00ae5ca3b05b1d3, active SOT SHA 85fe37083ba3d6c6a6a59122ed4d67962db11418, previous remote Diagnostics failure and current test phases.
4. Patched only separate Test Center GUI's read-only OS caption: Windows 11 if build >=22000, fetch EditionID/DisplayVersion/CurrentBuildNumber/UBR, show human label instead of kernel version and computer name, fallback if registry unavailable.
5. Bumped Test Center profile version to 0.1.9 and documented expected label; GitHub Test Center commit 00f0484cbff48380a205410da1ebf208c7f63de6.
6. Re-pinned Optimizer BAT to exact Test Center commit 00f0484cbff48380a205410da1ebf208c7f63de6, amended CURRENT_STATUS, HANDOFF, execution sequence, repo map, updated live ledger and Report 008; appended this checkpoint.
7. NO user PC commands, no R57 code builds, no stable release.

## Outcomes
IMPLEMENTED: Test Center 0.1.9 display-only label fix, infrastructure GitHub commit.
PASS: source code inspection and GitHub repository persistence (verify commit).
PENDING/NOT RUN: actual Windows 0.1.9 GUI/install/parser, Inno Setup 6 corrected Diagnostics and subsequent R57 tests.
DO NOT REPEAT: prior R56 exact green, previously confirmed Test Center 0.1.8 visible GUI tests for unchanged behavior.
LATEST FAIL: Inno Setup 6 missing in last remote Diagnostics event; unrelated to display fix.
RELEASE: not authorized/none.

## EXACT NEXT EXECUTION
Owner updates Test Center to 0.1.9 after closing running GUI; validates Windows caption; installs/detects Inno Setup 6 if needed, runs Diagnostics then Sync → QUICK → FULL SAFE only if previous gate PASS. Separate lab destructive GAME/RESTORE remains blocked on main PC.
