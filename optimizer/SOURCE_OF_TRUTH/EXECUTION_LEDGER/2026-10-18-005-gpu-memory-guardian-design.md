# IMMUTABLE CHECKPOINT 005 — GPU/Memory/Guardian design

Date: 2026-10-18; actor: ChatGPT with owner product direction.
Repo/branch: Merzo4/my-app-updates / mwo-r57-safe-background-actions.
HEAD before: ef423e7791c4aa6879dccc364036488f2c55a989. HEAD after: exact GitHub commit containing this file.
Previous: EXECUTION_LEDGER/2026-10-18-004-test-center-parser-safe-bootstrap-pin.md.
Risk: SOT documentation-only; no application executable change, no OS process changes.
Primary: R57 P4 Local FULL SAFE pending; Test Center 0.1.8 owner visible GUI pending.

## ACTION LOG (sequential)
1. Owner asked to optimize video cards and reduce perceived Windows RAM 6–8 GB toward 2–3 GB.
2. Clarified that cached/standby RAM is not automatically waste and 2–3 GB with open user programs cannot be promised.
3. Owner requested permanent background watchdog that detects critical resource constraints and frees resources/closes unnecessary processes.
4. Fetched exact GitHub HEAD and all mandatory SOT authority docs, latest checkpoint 004 and related architecture/tests.
5. Established threat model: resident optional per-user tray monitor OFF by default, monitor/alert first; no blanket process kills, no kernel/security modification, exact per-app user opt-in only with stateless identity and graceful close, deny on unknown/unsaved/active game/OBS/call/sync; no standby clearing.
6. Authored Decision 002 and three feature contracts (GPU, Memory & Background, Guardian); defined gated future phase.
7. Synced master, status, development rules, roadmap, phase sequence, handoff, architecture, test rules, feature matrix, repository map, live pointer and report 005.
8. No code, app build, local Windows test, destructive test or release performed. GitHub commit is the documentation checkpoint.

## RESULTS
DONE: future scope and guardrails approved/recorded.
PASS: authority read and documentation authoring (GitHub write verification follows).
NOT RUN: Guardian binary, GPU/RAM runtime, 0.1.8 owner Windows UI, R57 FULL SAFE.
PENDING: current R57 gate.
DO NOT REPEAT: R56 green runs, R55.1 published release, fixed Test Center 0.1.8 bootstrap prior work.
NO RELEASE, NO DESTRUCTIVE USER-PC EXPERIMENT.

## EXACT NEXT EXECUTION
Verify Test Center 0.1.8 owner visible window, obtain R57 FULL SAFE evidence and record a new checkpoint. Only when phase sequence permits proceed to future GPU/Memory/Guardian read-only implementation and separate risk-gated tests.
