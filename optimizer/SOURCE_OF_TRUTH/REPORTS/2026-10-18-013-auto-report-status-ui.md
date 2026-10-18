# REPORT 013 — native Test Center automatic report status

Date: 2026-10-18
Repo: Merzo4/my-app-updates, active SOT branch mwo-r57-safe-background-actions.
SOT HEAD before: 3a76e4ac13284bb7f2e59f97cd7f5583f9c8238b; after: exact GitHub commit containing this report.
Separate Test Center code revision: a205879fdf1d4d84ee35cd8b26411855a73318fc, version 0.2.3.
Risk: Lab GUI and upload status only, no changes to Optimizer R57 runtime.

## Problem
Owner supplied Test Center v0.2.2 screenshot: Diagnostics FAIL because Inno Setup 6 was not detected; log showed EVIDENCE_PUBLISHED, which proves upload happened automatically. Permanent button Отправить отчёт made it look manual. Winget reports Inno package already installed, exact ISCC 6 path remains unresolved.

## Investigation
Inspected Run-Profile.ps1 and AUTO-REPORT.ps1: each profile already invokes publish automatically, including FAIL. PUBLISH-EVIDENCE.ps1 performs Git push and preserves queue on failure. No visible upload state in native Program.cs. Prior actual evidence event 20261018T080939838Z-profile.Diagnostics-660846e5 in GitHub branch mwo-local-lab-evidence@84778f7e5c390f3c3a6e5ad8ef60ad07eadaceaa supports previous upload PASS.

## Work completed in separate Test Center source
Native EXE v0.2.3: replace permanent upload button with АВТООТЧЁТ status, independently display sending/confirmed sent/deferred/queued; Повторить отправку appears if needed and never reruns Diagnostics. Publisher writes a local State/EvidencePublishStatus.json receipt only after Git push success or failure; receipt is local and contains no credentials. Existing logs support previous-version migration. Version bumped 0.2.3; Optimizer pinned bootstrap updated. Original backend tests and GAME restrictions not modified.

## Status
PASS: historical v0.2.2 automated GitHub upload, source files committed to GitHub.
IMPLEMENTED: new upload receipt, UI and conditional retry v0.2.3.
NOT RUN: Windows v0.2.3 build/GUI, offline retry, auto publication acceptance, R57 Source/Quick/FullSafe.
FAIL: last actual Diagnostics missing Inno Setup 6 ISCC.exe (not a report delivery FAIL).
KNOWN ISSUE: raw machine/user details still in report payload; privacy hardening not included in this scope.
NO Stable/public Optimizer release or destructive test.

## EXACT NEXT EXECUTION
Owner updates Test Center to 0.2.3 when idle via installed UPDATE-TEST-CENTER.bat, confirms auto status and evidence in GitHub. Verify Inno Setup 6 ISCC.exe path/version if installed despite diagnostic FAIL; after Diagnostics PASS, Source Sync, QUICK, FULL SAFE on Windows. Stop at first FAIL and preserve evidence.
