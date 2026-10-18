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
