# REPORT 007 — automated Test Center evidence PASS; Diagnostics FAIL for missing Inno 6

Date: 2026-10-18
Repo/branch: Merzo4/my-app-updates / mwo-r57-safe-background-actions
HEAD before: 46c03b70bf1fe213f3b230c50d95c493298939d9; after: commit containing this report.
Scope: documentation/status only; no PC/toolchain installs or product code changes.

## Source of evidence
User screenshot shows Test Center 0.1.8, Diagnostics FAIL and `EVIDENCE_PUBLISHED`.
Fetched live GitHub evidence branch commit 22030119a4af17803fd83ce3950f2041d400b761 and `LOCAL_LAB_EVIDENCE/LATEST_EVENT/EVENT.json`, `Current.log`. Exact event: `20261018T072321769Z-profile.Diagnostics-7cd11a93`. Auto-upload is confirmed GitHub-side; user does not need to click Send Report after such success.

## Test status
- PASS: D: available, Git, PowerShell 7.6.7, .NET 10 SDK, D: lab-only location, protected Program Files, D: free ~288.2 GB.
- FAIL: Inno Setup 6 / `ISCC.exe` absent from hardcoded standard paths.
- PASS: automatic event published to `mwo-local-lab-evidence` with zero GitHub Actions minutes.
- NOT RUN: Source Sync/QUICK/FULL SAFE, R57 compiled program/installer and actual R57 acceptance.
- Source branch/commit fields in this event are empty; expected since Sync not yet run.

## New privacy observation
Actual published event contains local username and computer identifier. This is insufficient sanitization. Log as scoped Test Center privacy hardening defect; avoid republishing raw identifiers in new SOT or public messages. Requires separate follow-up change with exact Test Center code/risk review; no automatic historical deletion.

## Exact next
Owner installs official **Inno Setup 6** (not 7) at standard install path; reruns Diagnostics. If PASS continue Source Sync → QUICK → FULL SAFE; if FAIL stop and report new event. No destructive GAME/RESTORE on workstation. Then update SOT ledger/hand-off based on live evidence.
