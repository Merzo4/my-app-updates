# REPORT 004 — Test Center 0.1.8 parser-safe pin correction

Date: 2026-10-18.
Product: Merzo Windows Optimizer; Test Center infrastructure only.
SOT branch: mwo-r57-safe-background-actions.
HEAD BEFORE: aaa11c7e917d2a64e31f1a41eea6e72e8c0b24a9; HEAD AFTER: commit containing this report.
Test Center previous infrastructure hotfix: 3523eaabba8461aa63ec80a3da9d7270180ffd3a.
Test Center final 0.1.8 infrastructure SHA: a6f2cd3fcd31a9b10c994333a00ae5ca3b05b1d3.

## Causal change
After source inspection, the native Win32 interop Add-Type here-string was made parser-neutral by assigning to `$nativeSource` then calling `Add-Type -TypeDefinition $nativeSource -ErrorAction Stop`. This avoids an ambiguous here-string terminator followed by parameters. A descriptive comment in Install-LocalLab.ps1 was synchronized. No changes to WinForms logic, mutex, R57 code or previous test results.

## Installed user entrypoint
`optimizer/BOOTSTRAP/INSTALL_TEST_CENTER.bat` re-pinned to a6f2cd3fcd31a9b10c994333a00ae5ca3b05b1d3; the manual `RECOVER_TEST_CENTER_WINDOW.bat` remains an alternative for visible console diagnostics. Version 0.1.8; user Windows run still NOT RUN.

## Tests
PASS: exact source and branch revisions saved to GitHub, expected pinned SHA after update.
NOT RUN: Windows parser/GUI Test Center 0.1.8; R57 FULL SAFE; destructive GAME/RESTORE.
Do not claim bug solved on Windows until actual owner observation.

## EXACT NEXT EXECUTION
Owner runs current fixed Test Center BAT, checks real window and evidence, sends errors if any. If visible window PASS, continue R57 Local FULL SAFE as planned.
