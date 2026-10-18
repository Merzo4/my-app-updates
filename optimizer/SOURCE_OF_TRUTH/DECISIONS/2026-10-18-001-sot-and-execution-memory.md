# DECISION 001 — Dedicated Optimizer Source of Truth and Execution Memory

Date: 2026-10-18
Status: APPROVED BY OWNER REQUEST (create SOT files, work journals, reports comparable to other projects).
Repo: Merzo4/my-app-updates
Adoption branch: mwo-r57-safe-background-actions
Pre-documentation source baseline: f9e63b0c57faab592ba17344943021cc7adbc123

## Decision
Use optimizer/SOURCE_OF_TRUTH/ as canonical, product-scoped documentation inside shared repository. Keep 00–14 root authority, immutable EXECUTION_LEDGER, REPORTS, append-only DECISIONS and NEW_CHAT_BOOTSTRAP.

## Reason
Existing root README/RELEASE_POLICY document MerzoStream; optimizer has many patch/status/workflow assets but lacks a unified product concept, current-state pointer, mandatory handoff, and durable all-actions history.

## Invariants
- No code/runtime/Windows changes by this decision.
- Do not modify root shared-product README or switch the shared main's behavior.
- Owner controls stable/public release, destructive actions and product contract expansion.
- No retroactive fabricated evidence; R57 remains PENDING real Windows local test.
- Reports and checkpoint every substantive work cycle; immutable historical records.
- Move SOT to separate branch/repository only through later explicit change decision that preserves history and pointers.

## Adoption acceptance
Verify all SOT files exist at one GitHub commit; 06 points to the new checkpoint; 02 and 05 point to R57 P4 and exact prior source SHA. Record verification outcome in next checkpoint if actual verification is not available at commit creation.
