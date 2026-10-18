# Report 010 — Fix Test Center 0.2.0 PowerShell parser failure

Date: 2026-10-18.
SOT repo/branch: Merzo4/my-app-updates / mwo-r57-safe-background-actions.
SOT HEAD before: 54d99032ca7d2ca9463a3c26b038f72ccf97efb7; HEAD after: commit containing report (verify GitHub).
Test Center before: `mwo-local-test-center@f8757abcfabf0780fcf891661e0e1596dc1ad96a` (0.2.0).
Test Center fixed source: `mwo-local-test-center@1db2b1d91ea699a84fd0a374b00867c185d9e8c9` (0.2.1).
Scope: developer Test Center infrastructure and pinned bootstrap; no Optimizer code, R57 runtime mutation or release.

## Screenshot/failure
Owner ran native 0.2.0 installer, got `TEST CENTER PARSER FAIL MerzoOptimizer.LocalLab.ps1` in Install-LocalLab.ps1:30, with unexpected LAB/using/DllImport tokens, unmatched script constructs. Parser gate stopped installation before native C# build. Additional cmd path warning near temporary BAT is visible but primary blocking failure is the parser; investigate if persists after parser fix.

## Root cause
GitHub source inspection: 0.1.9 Windows 11 label replacement inadvertently expanded a JavaScript-style string replacement marker `$'` inside a regex in injected PowerShell text, duplicating the tail of source repeatedly. Healthy pre-change script: 498 lines (0.1.8). Broken: 1538 lines with multiple duplicate Shown/showDialog blocks. Later 0.2.0 installer downloaded the broken script faithfully and correctly failed.

## Fix
Restored exact known-good 0.1.8 base GUI from commit a6f2cd3fcd31a9b10c994333a00ae5ca3b05b1d3; inserted human-readable Windows 11 label function with safe index-based splice, no substitution-template expansion. Corrected source: 531 lines, one `Refresh-Cards` and one `ShowDialog`. Test Center version 0.2.1 and native host assembly version set to 0.2.1. Installer still parses all PowerShell scripts before building native EXE and preserves old shortcut until native smoke. Optimizer pinned BAT exact fixed source. SOT status/handoff/rules/sequence/tests/map/ledger updated.

## Evidence
PASS: GitHub source branch update, structural invariants on restored PS file (one root UI and source trailer) and original source provenance.
NOT RUN: real Windows PowerShell Parser.ParseFile after repair; native .NET compiler/publish and smoke, real GUI, auto evidence parity, R57 QUICK/FULL SAFE.
FAIL: prior owner 0.2.0 install, preserved as history. Latest separate Diagnostics failed Inno Setup 6 before Sync.
No OS changes/public release.

## EXACT NEXT
Owner reruns updated `UPDATE-TEST-CENTER.bat` when no active test. Observe Parser gate, native EXE compile/smoke and show marker. If build fails, provide screenshot and relevant log. If pass confirm only EXE UI displays. Then install/detect Inno Setup 6, rerun Diagnostics PASS, Sync, Quick, FullSafe on normal workstation. Never run GAME/RESTORE.
