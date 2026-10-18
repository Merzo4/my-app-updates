# 2026-10-18-003 — Test Center invisible GUI owner bug, patch prepared

Date: 2026-10-18.
Scope: Local Test Center infrastructure + user bootstrap files + documentation. Merzo Windows Optimizer R57 executable/runtime code unchanged.
Optimizer SOT branch HEAD BEFORE: 3bd3d7a0e878b7f2475b4e9b0e30426872ac41fb.
Infrastructure Test Center branch previous SHA: edc83fca9f0f89fc895a0a30c7f58f81af143779, hotfix SHA: 3523eaabba8461aa63ec80a3da9d7270180ffd3a.
No public release and no destructive mutation.

## User evidence
Owner screenshot 1: modal «Merzo Optimizer Test Center уже запущен». Screenshot 2: shortcut on Windows desktop. Owner reports first launch with no visible main window, then duplicate modal. **Confirmed owner-observed launcher UX FAIL** for installed 0.1.7, not proof of R57 product failure.

## Code inspection and hypothesis
In tools/MerzoOptimizer.LocalLab/Install-LocalLab.ps1 the generated VBS uses `WScript.Shell.Run cmd,0,False`, hiding the pwsh process. MerzoOptimizer.LocalLab.ps1 takes a named mutex before constructing GUI; subsequent launches show duplicate dialog independent of actual UI visibility. GUI SmokeTest only constructs and disposes controls before ShowDialog, so cannot assert actual visible window. Most likely WScript hidden startup inherited by WinForms; causal confirmation pending Windows retest.

## Changes
- Test Center 0.1.8 source branch SHA 3523eaabba8461aa63ec80a3da9d7270180ffd3a: VBS start style 1, managed shortcut switch, WinForms Add_Shown explicitly activates UI, hides only its host console after showing, writes gui-shown.json marker; installer waits for new marker or fails after 20 sec.
- Separate `optimizer/BOOTSTRAP/INSTALL_TEST_CENTER.bat` now pins infrastructure SHA 3523eaabba8461aa63ec80a3da9d7270180ffd3a; explicit owner consent and narrow process-commandline filter to stop only old Test Center GUI pwsh processes.
- Separate `RECOVER_TEST_CENTER_WINDOW.bat` starts GUI with visible console for diagnosing any remaining failure.
- Updated current status/handoff/ledger/docs; checkpoint 003 appended.

## Validation
- PASS: read/check source and confirmed original WScript 0 + mutex mechanism.
- PASS: infrastructure hotfix and docs commits created in GitHub.
- NOT RUN: Windows syntax/parser, GUI visible run, 0.1.8 installer/shortcut, R57 FULL SAFE, GAME Restore.
- PENDING: root-cause confirmation and owner-visible 0.1.8 UI acceptance.
- NO: optimizer executable/install state change, public release, destructive test.

## Exact next execution
Owner closes active tests and runs updated Test Center BAT; confirms real GUI, checks State/gui-shown.json. If FAIL, launches RECOVER BAT console, sends Logs/startup-error.log or Logs/gui-visibility-error.log; do not rerun unchanged other projects. Once visible PASS, perform R57 QUICK -> FULL SAFE and record exact OS/run/SHA.
