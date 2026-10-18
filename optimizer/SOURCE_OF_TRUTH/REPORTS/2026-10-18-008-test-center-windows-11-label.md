# REPORT 008 — Correct Windows 11 naming in Test Center environment card

Date: 2026-10-18.
SOT Repo: Merzo4/my-app-updates.
SOT branch: mwo-r57-safe-background-actions.
HEAD before: 85fe37083ba3d6c6a6a59122ed4d67962db11418; after: exact commit including report (verify GitHub).
Separate Test Center infrastructure prior: a6f2cd3fcd31a9b10c994333a00ae5ca3b05b1d3 (0.1.8); updated: 00f0484cbff48380a205410da1ebf208c7f63de6 (0.1.9).
Scope: read-only user-interface label and installer BAT pin; no Optimizer code/registry mutation/installer/public release.

## Owner observation
Windows Settings screenshots show **Windows 11 Pro 25H2 OS build 26200.9457**. Test Center 0.1.8 Environment card displays "Windows 10.0.26200.0". The string in GUI was generated directly by `[Environment]::OSVersion.Version`, which is the NT kernel version (10.0) retained by Windows 11, not marketing/product OS name.

## Changes
- mwo-local-test-center@00f0484cbff48380a205410da1ebf208c7f63de6 — GUI helper reads Registry Windows NT CurrentVersion Product EditionID, DisplayVersion, UBR and build with fallbacks; classify OS family on build >=22000; display two short lines Windows 11 Pro, 25H2 + 26200.9457; no machine name in card. 0.1.8 -> 0.1.9 profile. README.
- optimizer/BOOTSTRAP/INSTALL_TEST_CENTER.bat pinned from a6f2cd3fcd31a9b10c994333a00ae5ca3b05b1d3 to 00f0484cbff48380a205410da1ebf208c7f63de6, version 0.1.9.
- SOT status/handoff/sequence/map/live ledger updated, Report/Checkpoint 008 appended.

## Gates
PASS: exact source code references inspected, GitHub commit and modified branch tree tracked; label behavior designed.
NOT RUN: Windows PowerShell script parser, real Test Center 0.1.9 installation/GUI version label, R57 Diagnostics retest and subsequent Sync/Quick/FullSafe; no unearned pass.
R57 last evidence: auto GitHub Diagnostics FAIL Inno Setup 6. No newest evidence of correction yet.
No changes to protected production installed optimizer.

## EXACT NEXT EXECUTION
Owner closes Test Center 0.1.8 GUI; runs D:\MerzoOptimizer-LocalLab\UPDATE-TEST-CENTER.bat (uses updated infra bootstrap) or downloads pinned 0.1.9 BAT. Confirm Windows 11 Pro 25H2 version displayed. Ensure Inno Setup 6 and Diagnostics PASS. Next Source Sync → QUICK → FULL SAFE with actual logged evidence. No GAME/RESTORE on owner PC.
