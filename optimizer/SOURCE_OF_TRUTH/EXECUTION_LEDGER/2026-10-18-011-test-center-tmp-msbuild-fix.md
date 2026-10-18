# IMMUTABLE CHECKPOINT 011 — Test Center 0.2.1 MSBuild TMP environment issue

Date: 2026-10-18.
Repository: Merzo4/my-app-updates.
SOT branch/head before: mwo-r57-safe-background-actions@59341fbc4a8ac208da5b07a1ab3dd3cb7a4c3590.
SOT HEAD after: commit containing this checkpoint.
Previous: EXECUTION_LEDGER/2026-10-18-010-test-center-parser-source-restoration.md.
TC infra previous `1db2b1d91ea699a84fd0a374b00867c185d9e8c9`, updated `39b17f00c7270bca7ee3a5df607e51420c4ae2fc`.
Risk: local Test Center installer/toolchain environment and scoped bootstrap only, no Optimizer executable mutations.

## Ordered ACTION LOG
1. User sent full native 0.2.1 Windows installation log: Parser PASS and legacy PS GUI Smoke PASS; native dotnet publish failed MSBUILD MSB1025 unable to create a temporary directory under ...Temp\INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat.
2. Read actual Test Center source and located update-launcher generator `set "TMP=%TEMP%\INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat"`. Diagnosed inherited reserved TMP pointing to an existing BAT file, blocking MSBuild temp folder creation.
3. Confirmed 0.2.1 original parser corruption no longer affects local script parser, but native C# not built or smoke-tested.
4. Patched Test Center source 0.2.2: generated updater uses dedicated `MWO_UPDATE_DOWNLOAD` variable; source root installer, Install-LocalLab and Build-NativeHost enforce valid Lab-owned TEMP/TMP process-local directory before launching .NET.
5. Committed Test Center source fix 39b17f00c7270bca7ee3a5df607e51420c4ae2fc (including CMD line endings normalization). Updated current Optimizer user BAT to pin 39b17f00c7270bca7ee3a5df607e51420c4ae2fc and restore safe TEMP/TMP even when launched from old updater.
6. Updated 02 status, 05 handoff, 08 sequence, 11 test policy, 14 repository map, 06 live ledger, REPORT 011 and this immutable checkpoint. Unmodified R57 app code/public release.
7. Did not run Windows build, native GUI or destructive tests in assistant environment.

## Results
PASS: old 0.2.1 local Parser and legacy GUI Smoke (owner-provided console), GitHub source root-cause verification.
FAIL: old 0.2.1 native dotnet publish MSB1025 (owner-provided console).
IMPLEMENTED/PREPARED: 0.2.2 TEMP/TMP correction; native Windows acceptance pending.
NOT RUN: 0.2.2 on Windows, native GUI/run, R57 QUICK/FULL SAFE, lab GAME/RestoreAll.
DO NOT REPEAT: R56 accepted exact work, R55.1 publication, unrelated products.
NO public Stable release or primary user-PC mutation.

## EXACT NEXT EXECUTION
Run updated 0.2.2 installer via existing `UPDATE-TEST-CENTER.bat` on owner Windows after closing Test Center. Verify temp preflight, local parser, native dotnet build/smoke, no-console WinForms UI and exact 0.2.2 version. If error send native-build.log + screenshot; if PASS resume R57 Diagnostics after installing Inno Setup 6; then Source, Quick, FULL SAFE. Record new SOT checkpoint from real owner evidence.
