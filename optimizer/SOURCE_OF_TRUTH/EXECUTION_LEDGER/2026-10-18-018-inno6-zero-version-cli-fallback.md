# IMMUTABLE CHECKPOINT 018 — Inno Setup 6 binary zero-version metadata fallback

Date: 2026-10-18.
Repo Merzo4/my-app-updates; SOT branch mwo-r57-safe-background-actions.
HEAD before: 31d22512d77eb42d8dc9064711d8dbd2be58b7f0; after: actual commit containing this file.
Previous: EXECUTION_LEDGER/2026-10-18-017-inno6-0-2-4-diagnostics-still-fail.md.
Test Center branch mwo-local-test-center@7626f1fd28d931620b9a255a3d88672a9192578b, version 0.2.5.
Risk: read-only compiler help-banner identity and toolchain selection, no optimizer Windows operations/release.

## ACTION LOG
1. Received owner screenshot of actual per-user ISCC.exe Get-Item: FileVersion 0.0.0.0, ProductVersion 0.0.0.0, version6 regex result False.
2. Correlated with earlier Inno6.7.3 winget package and Test Center 0.2.4 real Diagnostics FAIL / auto-report PASS; conclusively identified metadata-only validation as source of reject, though CLI compiler identity itself is not yet verified.
3. Read current GitHub SHA for SOT/Test Center, required 00/01/02/03/04/08/05/06/07 and checkpoint 017; inspected exact Core resolver and cumulative R56/R57 release controllers.
4. Consulted external Inno command compiler documentation: official ISCC accepts /? and modern 6 series prints a major-six compiler usage banner.
5. Modified separate Test Center code (v0.2.5) with Test-Inno6CompilerIdentity accepting resources major 6 or a bounded, strict, read-only /? major-6 compiler banner fallback; accepts no non-ISCC EXE and explicitly rejects known major7. This same helper was added to both Optimizer cumulative R56/R57 compiler controllers, without changing GAME, RESTORE, product runtime or updater settings.
6. Updated Optimizer pinned Test Center bootstrap SHA, master current status, rules, handoff, sequence, testing, repository map, Report 018 and this immutable checkpoint; moved live ledger pointer.
7. No user PC Windows execution, native Test Center source build, compiler banner invocation in owner runtime, R57 QUICK/FULL SAFE or stable release performed in assistant environment.

## Results
PASS: exact owner zero-version observation, GitHub source persistence and invariant checks.
IMPLEMENTED: 0.2.5 CLI banner fallback and R56/R57 toolchain consistency.
NOT RUN: Windows parser, GUI/source download, CLI banner, local Diagnostics, Quick/FullSafe, installer and OTA.
FAIL (historic): Test Center 0.2.4 Inno compiler detection; auto GitHub report prior PASS.
No destructive main-PC testing, no public release.
Do not repeat accepted old R56 tests on changed new SHA.

## EXACT NEXT EXECUTION
Close Test Center when idle; update to v0.2.5 using installed updater; verify native GUI and run Diagnostics, wait for auto GitHub event. If PASS Source Sync -> QUICK -> FULL SAFE in order, stop at any FAIL. If Inno identity still FAIL, request read-only compiler /? output (redacted), no blind reinstall or disabled validation. Game/Extreme/Restore still lab-only.
