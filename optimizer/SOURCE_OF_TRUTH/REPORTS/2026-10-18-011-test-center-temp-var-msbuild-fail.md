# Report 011 — Test Center native EXE build MSB1025 (TMP assigned to BAT)

Date: 2026-10-18.
Repo/branch: Merzo4/my-app-updates / mwo-r57-safe-background-actions.
SOT HEAD before: 59341fbc4a8ac208da5b07a1ab3dd3cb7a4c3590, after: GitHub commit containing report.
Test Center prior: mwo-local-test-center@1db2b1d91ea699a84fd0a374b00867c185d9e8c9 (0.2.1).
Test Center fixed source: mwo-local-test-center@39b17f00c7270bca7ee3a5df607e51420c4ae2fc (0.2.2).
Scope: Test Center installer and toolchain environment only; no R57 Optimizer source or OS mutation.

## User Windows evidence (from pasted console log)
- `LOCAL_TEST_CENTER_LOCAL_PARSER_GATE_PASS` — PASS.
- `LOCAL_TEST_CENTER_GUI_SMOKE_TEST_PASS` — PASS (old WinForms PS GUI).
- `MSBUILD : error MSB1025`, .NET IOException: `Cannot create ...\Temp\INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat because a file or directory with the same name already exists` — FAIL.
- Native `MerzoOptimizer.TestCenter.exe` publish, smoke, shortcut, owner-visible native UI — NOT RUN/BLOCKED.
- Multiple temporary path errors are symptoms of inherited invalid TMP, not Windows 11 kernel mismatch.

## Root cause confirmed by GitHub source
`Install-LocalLab.ps1` generated `UPDATE-TEST-CENTER.bat` setting `TMP` to `%TEMP%\INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat` then `call "%TMP%"`. This persists `TMP=<BAT file>` in the child environment, and .NET/MSBuild tries to create a temporary folder at that path. No global Windows setting is wrong.

## Fix
1. In separate Test Center 0.2.2 code, generate `set MWO_UPDATE_DOWNLOAD=<downloaded BAT>` instead of `set TMP`.
2. In new root bootstrap and PowerShell Install-LocalLab + Build-NativeHost, set process-local `TEMP`/`TMP` to an existing dedicated Lab directory `D:\MerzoOptimizer-LocalLab\Temp\ToolchainTemp`. This repairs inherited environment even when owner uses the existing stale updater one last time.
3. In Optimizer pinned bootstrap, use same safe local temp guard and pin infrastructure SHA 39b17f00c7270bca7ee3a5df607e51420c4ae2fc.
4. Keep existing PS parser and GUI smoke gates; native C# publish+smoke and owner GUI acceptance still mandatory. 0.2.2 not yet tested on Windows.

## Result classification
PASS: source investigation + exact old-updater bug identification; GitHub fixes committed.
FAIL: prior 0.2.1 native .NET publish on user machine.
NOT RUN: 0.2.2 Windows compile, smoke, EXE visible launch, R57 Source/QUICK/FULL SAFE.
PENDING: Inno Setup 6 preflight for R57. No public release or destructive test.

## EXACT NEXT EXECUTION
Owner closes Test Center when idle and reruns `D:\MerzoOptimizer-LocalLab\UPDATE-TEST-CENTER.bat` (old updater downloads current bootstrap, which normalizes temp). Confirm native exe compilation, smoke and GUI visible. If FAIL send `D:\MerzoOptimizer-LocalLab\Logs\native-build.log` and console output. Once PASS continue Diagnostics (Inno 6), Sync, Quick, FullSafe with automatic evidence.
