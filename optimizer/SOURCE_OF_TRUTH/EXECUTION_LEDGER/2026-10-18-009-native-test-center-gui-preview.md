# IMMUTABLE CHECKPOINT 009 — native EXE Test Center interface

Date: 2026-10-18.
Repo: Merzo4/my-app-updates.
SOT branch before: mwo-r57-safe-background-actions@b62cf44b522be3fa46c99e579562c7c444964d22.
After: GitHub commit including this checkpoint.
Infrastructure Test Center source SHA: mwo-local-test-center@f8757abcfabf0780fcf891661e0e1596dc1ad96a.
Previous checkpoint: EXECUTION_LEDGER/2026-10-18-008-test-center-windows-11-label.md.
Scope/risk: Test Center UI & installer infrastructure only; no user Windows code run here.
R57 active gate: P4, Diagnostics last FAIL due to Inno Setup 6.

## Ordered ACTION LOG
1. Owner asks why PowerShell appears alongside Test Center, wants a simple standalone graphical EXE like their other lab.
2. Read live GitHub branches and Test Center GUI/installer/bootstraps; identified PowerShell WinForms-hosted UI + WScript pwsh launcher, even after console visibility mitigations.
3. Chose least-disruptive architecture: native WinForms C#/.NET10 WinExe UI; existing PowerShell 7 scripts remain safe hidden backend for tests and auto evidence. No R57 code modifications.
4. Authored separate NativeHost project and implementation of summary/cards/log view/profile actions, Windows version label, current-user singleton and lab safety gate in mwo-local-test-center.
5. Authored Build-NativeHost.ps1 local dotnet publish win-x64 self-contained, native smoke; updated installer for native shortcut and rollback START-TEST-CENTER-LEGACY.bat; bumped infrastructure version 0.2.0; committed Test Center at f8757abcfabf0780fcf891661e0e1596dc1ad96a.
6. Updated Optimizer pinned installer BAT to fetch exact infrastructure SHA and nested NativeHost C# sources; synchronized SOT master/status/handoff/sequence/architecture/install/test/repo map and this REPORT/LEDGER checkpoint.
7. Did not run native exe, dotnet publish, Windows tests, R57 FULL SAFE or destructive GAME; no release published.

## Outcomes
DONE: source-only native GUI and controlled installation design.
PASS: GitHub changes persisted (verify SHA).
NOT RUN: Windows compile/smoke/UI/auto-report tests; R57 candidate build and local FULL SAFE.
PENDING: owner validation and last Inno Setup 6 diagnostic prerequisite.
FAIL (historic): 0.1.7 invisible GUI; fixed 0.1.8 owner PASS; latest Diagnostics missing Inno 6.
DO NOT REPEAT: previously accepted R56 exact runs, unrelated product tests.
No installer/GUI release declared ready before Windows test.

## EXACT NEXT EXECUTION
On Windows close Test Center and ensure no active checks, run pinned 0.2.0 BAT or installed updater. Check native-build.log, native-smoke.log, EXE presence and actual GUI/PowerShell visibility. If build fails preserve old shortcut and use legacy GUI while diagnosing. Once native PASS, ensure Inno Setup 6 and Diagnostics PASS, then Sync->QUICK->FULL SAFE with GitHub evidence; no destructive GAME/RESTORE on owner PC.
