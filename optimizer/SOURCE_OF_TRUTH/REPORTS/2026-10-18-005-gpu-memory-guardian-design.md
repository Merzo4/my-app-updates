# REPORT 005 — GPU/Memory/Guardian performance modules specification

Date: 2026-10-18.
Repository: Merzo4/my-app-updates.
Branch: mwo-r57-safe-background-actions.
HEAD before: ef423e7791c4aa6879dccc364036488f2c55a989; HEAD after: new commit containing this report.
Risk: documentation-only, no runtime/Windows mutation.

## Request
Owner asked for GPU optimization and real Windows memory reduction from perceived ~6–8 GB to 2–3 GB where feasible, plus ongoing system-health background agent with safe response to critical pressure.

## Findings and decisions
Read mandatory SOT documents and checkpoint 004. Existing R57 P4 FULL SAFE still PENDING and Test Center 0.1.8 owner GUI confirmation PENDING. Set a conditional measurable memory goal, no guaranteed 2–3 GB when user apps run. Approve future modules GPU/Memory/Guardian under Decision 002, guarded lifecycle, precise identity and user-consented graceful mitigation, no automatic kill of unknown/user-critical apps.

## Changed files
Added DECISIONS/2026-10-18-002-performance-gpu-memory-guardian.md and FEATURES/GPU_OPTIMIZATION_CENTER.md, MEMORY_BACKGROUND_CENTER.md, MERZO_GUARDIAN.md; appended master spec, status, rules, roadmap, execution sequence, handoff, architecture, tests, matrix and repository map; live ledger points to checkpoint 005.

## Evidence/outcome
PASS: fetched exact GitHub SOT/head and current gates for docs review.
DONE: proposed technical design/owner-approved product scope recorded; GitHub commit verification after write.
NOT RUN: new code/build, agent launch, Windows GPU/Memory measurements, 0.1.8 owner test, R57 FULL SAFE, GAME/RESTORE.
BLOCKED: future code implementation must wait for phase sequence or explicit new permission; no automatic destructive process closing.
No release.

## EXACT NEXT EXECUTION
Owner runs Test Center 0.1.8, confirms visible GUI and supplies results; then R57 QUICK/FULL SAFE and exact evidence/REPORT/LEDGER; later future read-only telemetry F0/F1 when phase authority permits.
