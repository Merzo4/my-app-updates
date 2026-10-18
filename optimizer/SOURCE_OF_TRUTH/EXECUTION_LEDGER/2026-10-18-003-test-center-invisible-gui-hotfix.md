# IMMUTABLE CHECKPOINT 003 — Local Test Center invisible GUI

Date: 2026-10-18. Owner requested fix for invisible Test Center 0.1.7 GUI. 
SOT repository: Merzo4/my-app-updates
SOT branch: mwo-r57-safe-background-actions
SOT HEAD BEFORE: 3bd3d7a0e878b7f2475b4e9b0e30426872ac41fb; after: actual GitHub commit containing this checkpoint.
Test Center separate branch: mwo-local-test-center@3523eaabba8461aa63ec80a3da9d7270180ffd3a; prior: edc83fca9f0f89fc895a0a30c7f58f81af143779.
R57 product runtime/code SHA: unchanged by this cycle.
Prior checkpoint: EXECUTION_LEDGER/2026-10-18-002-user-bootstrap-bat-installers.md
Risk boundary: Test Center launch process/user diagnostic tooling ONLY.

## Ordered ACTION LOG
1. Inspected owner-provided desktop shortcut and duplicate-launch dialog screenshots; recorded first launch invisible / second already-running.
2. Verified exact Test Center and active Optimizer GitHub SHA.
3. Read full local Test Center GUI controller, Install-LocalLab.ps1, Start-TestCenter.ps1, profile and bootstrap.
4. Located hidden VBS Shell.Run(...,0) launcher and mutex-before-ShowDialog, GUI smoke test bypasses visibility; formed causal hypothesis, not yet owner-confirmed.
5. Patched isolated mwo-local-test-center code: version 0.1.8, normal launch style, form Shown event, hide console after visibility only, marker/log and installer marker wait. GitHub commit 3523eaabba8461aa63ec80a3da9d7270180ffd3a.
6. Authored updated pinned Test Center installer/recovery diagnostic BATs; explicit consent before terminating only specifically matched Test Center GUI pwsh command lines; no kill of unrelated PowerShell/Windows processes.
7. Updated Optimizer SOT current status/handoff, record, installers documentation and new-chat instructions; report 003 and this immutable checkpoint.
8. GitHub presence/commit file scope verification is a later verification step; no new Windows result claimed.

## Results
FAIL: user-observed invisible 0.1.7 GUI launch (main UI absent).
IMPLEMENTED: 0.1.8 launcher fix, visibility marker and bootstrap diagnostics.
NOT RUN: actual Windows 0.1.8 GUI, batch installers, PowerShell parser, R57 Local FULL SAFE, dedicated-lab GAME/RestoreAll.
DO NOT REPEAT: already accepted R56 exact runs, unrelated MerzoStream work.
BLOCKER: owner Windows GUI visibility acceptance for fixed Test Center.
OWNER-ONLY: no public release/destructive change.

## EXACT NEXT EXECUTION
Run updated Test Center 0.1.8 BAT on owner's Windows after closing active tests; verify actual GUI window, inspect marker/log. If failed run RECOVER BAT with visible console and capture evidence. If pass record new immutable checkpoint; then resume R57 Local FULL SAFE. No destructive GAME/RESTORE on main workstation.
