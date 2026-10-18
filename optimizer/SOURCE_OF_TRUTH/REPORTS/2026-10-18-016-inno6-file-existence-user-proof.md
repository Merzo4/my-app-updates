# REPORT 016 — Physical per-user Inno Setup 6 compiler confirmed

Date: 2026-10-18.
Repo: Merzo4/my-app-updates; active SOT branch mwo-r57-safe-background-actions.
HEAD before: 9834354abbd1264f571fca15be71155d1ab83913, HEAD after: GitHub commit containing this report.
Scope: read-only user screenshot evidence and SOT bookkeeping; no source/executable change or OS action.
Test Center code baseline: mwo-local-test-center@f0044e15c1952482c65b6d3d85afa982bab4deb5 (v0.2.4).
Last remote evidence: mwo-local-lab-evidence@dc1ac24ed1a85a2ce0dd7d1965e31ad936e5b328 (0.2.3 Diagnostics FAIL).

## Owner-provided verification
Screenshot shows read-only command:
`Test-Path (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')`
Result: **True**. Prior owner screenshot shows `winget list --id JRSoftware.InnoSetup -e` version 6.7.3. Actual compiler file presence in expected per-user directory **PASS**. Its embedded product/version resource and new v0.2.4 resolver behavior have not yet been verified, so do not mark actual Diagnostics PASS.

## Conclusion
Previous Test Center 0.2.3 false-negative likely stemmed from hard-coded system-wide Program Files directories, while WinGet deployed to current-user app folder. Test Center v0.2.4 code already addresses it, and active cumulative R56/R57 builders accept a verified process-scoped Inno 6 path. No reinstall of Inno Setup needed.
No new evidence run; last GitHub event remains old Diagnostics FAIL.
No change to toolchain or product source in this report cycle.

## Status
PASS: physical file exists (owner observed), historical auto evidence transport.
NOT RUN: local Test Center 0.2.4 Diagnostics, file embedded major-version verification, R57 Source Sync/QUICK/FULL SAFE.
BLOCKED: R57 P4 until current Diagnostics PASS.
No destructive GAME/RESTORE or public release.

## EXACT NEXT EXECUTION
Owner ensures Test Center 0.2.4 (update only if older), runs Diagnostics and waits for auto-upload. Check GitHub event and Inno 6 stage. If PASS perform Source Sync, QUICK, FULL SAFE in order, stop on first FAIL and record source SHA/results with next report/checkpoint. If Inno FAIL, inspect reported failure before further changes.
