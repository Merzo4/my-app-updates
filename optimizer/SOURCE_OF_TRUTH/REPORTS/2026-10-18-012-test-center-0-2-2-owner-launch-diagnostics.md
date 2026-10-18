# REPORT 012 — Test Center 0.2.2 opens and sends Diagnostics FAIL

Date: 2026-10-18.
Repo/branch: Merzo4/my-app-updates / mwo-r57-safe-background-actions.
SOT HEAD before: 2735ce9c28211351d0cbaf36eecaf89c978ac879; after: GitHub commit containing this report.
Risk: evidence/status bookkeeping only, no Windows process mutation or product release.

## Owner observation
Owner states Test Center opens after attempted 0.2.2 installation. GUI visible PASS by owner report. No direct shortcut target/process screenshot or proof that PowerShell terminal no longer appears; do not claim those unobserved details.

## Verified GitHub evidence
Branch mwo-local-lab-evidence SHA 84778f7e5c390f3c3a6e5ad8ef60ad07eadaceaa; event `20261018T080939838Z-profile.Diagnostics-660846e5`, profile Diagnostics, version 0.2.2, result **FAIL** only Inno Setup 6 (`ISCC.exe`). All shown other preflight stages PASS (Git, PowerShell 7.6.7, .NET 10, D: and Program Files protection), automatic GitHub event upload PASS. This does not test R57 code.

## State
GUI visible: PASS owner-observed.
Diagnostics: FAIL — missing standard Inno Setup 6 executable.
Auto evidence: PASS, event pushed to GitHub.
Source Sync: NOT RUN.
QUICK: NOT RUN.
FULL SAFE: NOT RUN.
GAME/RESTORE: BLOCKED on owner main workstation.
Published Optimizer remains mwo-v0.1.55.1.

## Next
Owner installs official Inno Setup 6 (JRSoftware.InnoSetup) and reruns Diagnostics, checking expected `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` or `C:\Program Files\Inno Setup 6\ISCC.exe`. If PASS, run Update Source → QUICK → FULL SAFE, stop on first FAIL. Record new live evidence and checkpoint without raw user/machine identifiers. If Inno 6 is already installed, inspect exact installation path before reinstalling anything.
