# 06 — LIVE EXECUTION LEDGER

This is a mutable pointer/summary, NOT the append-only checkpoint itself.

## Latest immutable checkpoint
EXECUTION_LEDGER/2026-10-18-005-gpu-memory-guardian-design.md

## Current authority
Repo: Merzo4/my-app-updates.
Source of Truth directory: optimizer/SOURCE_OF_TRUTH/ in mwo-r57-safe-background-actions.
Pre-documentation exact R57 code SHA: f9e63b0c57faab592ba17344943021cc7adbc123.
After documentation commit, read the current live HEAD from GitHub before testing.

## Current accepted evidence
- Public production: mwo-v0.1.55.1.
- R56 exact build PASS: 32479505374.
- R56 installed + GAME Recovery PASS: 32480404145.
- R57: PREPARED / local FULL SAFE NOT RUN / separate disposable lab GAME RestoreAll NOT RUN / not published.

## Current blocker
R57 lacks Windows FULL SAFE evidence; later lab/high-risk and update gates also pending.

## EXACT NEXT EXECUTION
Run only the next P4 gate from 08_EXECUTION_SEQUENCE.md in Windows Local Test Center; record exact code SHA, environment, outputs and exit status. Destructive GAME work must be isolated in dedicated disposable lab.

## DO NOT REPEAT
Previously accepted exact R56 runs for unchanged risk. Documentation bootstrap is not a rebuild or runtime PASS.

## Recording policy
Every substantial cycle: append REPORTS report + new EXECUTION_LEDGER checkpoint; move this pointer and synchronize 02/05 and 08/04/13 if state changed. Never edit prior immutable checkpoint.

## Bootstrap delivery (2026-10-18)
Two separate `optimizer/BOOTSTRAP/*.bat` files and `NEW_CHAT_PROMPT.txt` committed. Test Center uses immutable `mwo-local-test-center@edc83fca9f0f89fc895a0a30c7f58f81af143779`, program installer pinned to public R55.1 SHA-256. No Windows executable install/run performed in this documentation cycle. See REPORTS/2026-10-18-002-install-bootstrap-and-new-chat.md.
 
## Test Center UX defect / 0.1.8 infrastructure hotfix
Owner screenshots: invisible WinForms UI 0.1.7, second launch blocked by mutex. **Owner UX FAIL**. Test Center source fix `mwo-local-test-center@3523eaabba8461aa63ec80a3da9d7270180ffd3a` **IMPLEMENTED/PREPARED**, Windows smoke after fix **NOT RUN**. Updated installer + recovery BAT, no product code changed. See REPORTS/2026-10-18-003-test-center-invisible-gui-hotfix.md. First verify GUI visibly opens; only after that resume R57 Local FULL SAFE.

 
## Parser-safe final 0.1.8 infrastructure pin
Test Center 0.1.8 final source `mwo-local-test-center@a6f2cd3fcd31a9b10c994333a00ae5ca3b05b1d3`. Earlier 0.1.8 provisional commit 3523eaabba8461aa63ec80a3da9d7270180ffd3a remains as historical checkpoint evidence; pinned bootstrap updated. No owner Windows runtime PASS yet. Report 004.
 
## Decision 002 scope approved / Checkpoint 005
GPU Optimization Center + Memory & Background Center + Merzo Guardian design recorded. Implementation **NOT STARTED**, Windows tests **NOT RUN**; no process closing or public release. Primary remains owner Test Center 0.1.8 GUI verification then R57 P4 FULL SAFE. Details: REPORTS/2026-10-18-005-gpu-memory-guardian-design.md.
