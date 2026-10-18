# NEW CHAT BOOTSTRAP — Merzo Windows Optimizer

Продолжи Merzo Windows Optimizer с последнего записанного GitHub checkpoint. НЕ начинай программу заново.

Repository: Merzo4/my-app-updates
Active working/SOT branch at adoption: mwo-r57-safe-background-actions
Canonical docs: optimizer/SOURCE_OF_TRUTH/

Before any work, completely read 00_READ_FIRST.md and all mandatory files in its specified order. Read latest immutable EXECUTION_LEDGER checkpoint pointed to by 06_LIVE_EXECUTION_LEDGER.md. Then verify current branch HEAD and active R57 status/evidence in GitHub.

Facts as at 2026-10-18 (must be revalidated):
- Latest public optimizer: mwo-v0.1.55.1.
- R56 code candidate: 0.1.56; build run 32479505374 PASS; installed + GAME Recovery run 32480404145 PASS; NOT PUBLIC.
- R57: prepared SAFE background actions and local release controller; optimizer/R57_LOCAL_TEST_STATUS.json says ready-for-local-full-safe, publicRelease false, GitHub Actions for R57 false.
- Pre-documentation R57 code SHA: f9e63b0c57faab592ba17344943021cc7adbc123; DO NOT assume same as current HEAD after docs commit.
- R57 Windows FULL SAFE: NOT RUN. Dedicated-lab destructive GAME->RestoreAll: NOT RUN.

DO NOT repeat R56 gates at same exact SHA/risk, do not touch other products in shared repo, do not claim tests or publication not evidenced, do not do destructive operations on normal workstation. Follow 08_EXECUTION_SEQUENCE.

At end of substantial cycle: write REPORTS report; append immutable EXECUTION_LEDGER checkpoint with full sequential ACTION LOG, PASS/FAIL/NOT RUN, SHA/env/risk/evidence; move 06 pointer; synchronize 02 status/05 handoff and affected roadmap. New binding design decision -> DECISIONS append-only. BEFORE replying with claimed completion, confirm files in GitHub.

EXACT NEXT EXECUTION: R57 Windows Local Test Center FULL SAFE run, then separate dedicated-lab destructive acceptance only if gated/authorized; publish stable only on explicit owner approval.

## Copy/paste starter for owner
A directly pasteable Russian message exists at `optimizer/BOOTSTRAP/NEW_CHAT_PROMPT.txt`. It is a shortcut only; the assistant must still read all authority and live GitHub SHA before working. Separate installers exist in `optimizer/BOOTSTRAP/`.

## Live user issue after BAT distribution
Test Center 0.1.7 produced an invisible GUI on first launch and an «already running» second-launch dialog. Test Center 0.1.8 infrastructure launcher hotfix is `mwo-local-test-center@3523eaabba8461aa63ec80a3da9d7270180ffd3a` with GUI visibility marker; user Windows confirmation is PENDING. The latest `optimizer/BOOTSTRAP/INSTALL_TEST_CENTER.bat` pins the fixed commit and offers a scoped old-GUI restart. Check last checkpoint and owner feedback before declaring PASS. R57 product gate remains NOT RUN.

 
### Final pinned Test Center hotfix SHA / parser-safety correction
Final Test Center 0.1.8 source is `mwo-local-test-center@a6f2cd3fcd31a9b10c994333a00ae5ca3b05b1d3` (supersedes earlier infrastructure hotfix commit 3523eaabba8461aa63ec80a3da9d7270180ffd3a ONLY for the installer source pin). This is a minimal parse-safe native Console Add-Type adjustment; 0.1.8 **WINDOWS NOT RUN/PENDING**. Updated pinned BAT uses this exact immutable SHA. Prior checkpoint 003 is kept unchanged as historical.
