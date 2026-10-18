# REPORT 009 — Standalone native EXE frontend for Merzo Optimizer Test Center

Date: 2026-10-18.
Repo/branch: Merzo4/my-app-updates / mwo-r57-safe-background-actions.
SOT HEAD before: b62cf44b522be3fa46c99e579562c7c444964d22; after: new GitHub commit containing this report.
Separate Test Center active commit: mwo-local-test-center@f8757abcfabf0780fcf891661e0e1596dc1ad96a.
Risk boundary: Test Center developer infrastructure only, not Optimizer executable/Windows mutations.

## User request
PowerShell window is displayed or briefly flashes while starting Test Center GUI. Owner wants an app that runs directly like another project Test Lab.

## Root cause
Test Center 0.1.9 GUI is hosted in PowerShell WinForms script with wscript launcher; hiding the console after WinForms Shown prevents invisibility but may show PowerShell briefly. PowerShell is a hosting dependency of the UI rather than only a test backend.

## Changes
- Added `NativeHost/MerzoOptimizer.TestCenter.csproj` and `Program.cs` (native WinForms WinExe), active version 0.2.0.
- Added `Build-NativeHost.ps1` to locally dotnet publish self-contained win-x64 and run WinForms smoke; installer copies built EXE to separate D: App/Native and adjusts desktop shortcut only if native build/smoke succeeds.
- Updated Test Center installer/bootstrap to download C# files, publish EXE, keep VBS/pwsh GUI via START-TEST-CENTER-LEGACY.bat.
- Native GUI invokes exactly existing PowerShell 7 Run-Profile and evidence scripts *as hidden background children*, preserving Diagnostics, Sync, Quick, FullSafe, protected Program Files and auto GitHub upload.
- Re-pinned active Optimizer `optimizer/BOOTSTRAP/INSTALL_TEST_CENTER.bat` to exact separate Test Center commit and updated SOT spec/status/handoff, phases, architecture, installation, tests, map, ledger pointer.

## Verification matrix
PASS: GitHub commit existence/branch origin/changed path evidence once verified.
IMPLEMENTED/PREPARED: C# source, local build script and installer integration.
NOT RUN: actual Windows .NET publish, compiler/static analysis, native EXE smoke, Test Center 0.2.0 UI real launch, automatic report parity in native frontend, R57 product full SAFE.
FAIL remains: last owner Diagnostics Inno Setup 6 missing in evidence event (unless new pass later uploaded).
NO public product release, no destructive user machine activity.

## Rollback and exact next
On Windows close GUI, no profile active; run updated pinned BAT (or installed UPDATE-TEST-CENTER.bat), wait for native EXE build. If fails, previous shortcut should remain intact; inspect D:\MerzoOptimizer-LocalLab\Logs\native-build.log/native-smoke.log. If PASS inspect actual launched EXE/shortcut and no PowerShell window. Then Diagnostics (requires Inno Setup 6), Sync, Quick, FullSafe. Owner GAME/RESTORE remains blocked.
