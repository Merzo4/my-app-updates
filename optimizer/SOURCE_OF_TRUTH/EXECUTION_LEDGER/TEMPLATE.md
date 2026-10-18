# IMMUTABLE EXECUTION CHECKPOINT TEMPLATE

Create new file YYYY-MM-DD-NNN-slug.md; never modify a previously committed checkpoint.

Timestamp/date:
Objective:
Authority docs read:
Repo/branch:
HEAD BEFORE:
HEAD AFTER (if known; otherwise resolve through GitHub commit):
CODE SHA / artefact digest:
OS / runner:
Risk boundary:
Sequence phase + gate:
Previous checkpoint:
Evidence references:

## ACTION LOG (ordered)
1. READ / observation.
2. CHANGE / reason.
3. BUILD / TEST / evidence outcome.
4. DECISION / blocked or accepted.
5. RECORD / report + status/handoff/ledger synchronization.

## RESULT MATRIX
DONE:
PASS:
FAIL:
BLOCKED:
PARTIAL:
NOT RUN / PENDING:

## DO NOT REPEAT
Exact SHA + same risk/environment gates already accepted.

## DEFECTS / RISKS
Evidence and owner-only decisions.

## EXACT NEXT EXECUTION
Exact next command, environment, expected result, stop condition.

## Publication restrictions
No public release or destructive test without required authorization.
