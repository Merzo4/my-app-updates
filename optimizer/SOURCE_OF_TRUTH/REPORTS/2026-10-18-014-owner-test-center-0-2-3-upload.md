# REPORT 014 — Test Center 0.2.3 auto-upload confirmed remotely; Diagnostics FAIL Inno Setup 6

Date: 2026-10-18.
Repository Merzo4/my-app-updates; SOT branch mwo-r57-safe-background-actions.
SOT HEAD BEFORE: cee2562c7043085bd7cd22bef36111df67f45a74; AFTER: GitHub commit containing this report.
Infrastructure source SHA: mwo-local-test-center@a205879fdf1d4d84ee35cd8b26411855a73318fc.
Evidence branch SHA: mwo-local-lab-evidence@dc1ac24ed1a85a2ce0dd7d1965e31ad936e5b328.
Event ID: 20261018T083407111Z-profile.Diagnostics-ec944325.
Scope: Evidence verification and status log only, no code, user Windows modification or release.

## User action and verification
Owner confirmed Test Center updated, ran Diagnostics, and report sent. Live GitHub evidence branch was fetched and its newest event/LATEST LAB-RESULT.json inspected. Event version **0.2.3**, timestamp **08:34:07Z**, profile Diagnostics FAIL "Inno Setup 6: ISCC.exe". All other checks in evidence PASS: Git, PowerShell 7.6.7, .NET10, D drive, app protection, D free 286.8 GB. The event is newly published and distinct from prior v0.2.2 evidence. Auto GitHub publication **PASS** as fact, independent of actual diagnostics FAIL.

## Remaining scope and warnings
Native new UI is running Test Center 0.2.3, but visual display "АВТООТЧЁТ Отправлено" not independently evidenced via fresh screenshot; simulated no-network queue/retry remains NOT RUN. Outbound evidence still includes raw local machine/user labels in private evidence branch; this ongoing privacy deficiency is tracked, no further personal identifiers reproduced here. Source Sync/QUICK/FULL SAFE remain NOT RUN, not a product FAIL.

Prior owner's winget command stated JRSoftware.InnoSetup package installed, but no installed version shown. Current Diagnostics checks only paths under C:\Program Files\Inno Setup 6 and C:\Program Files (x86)\Inno Setup 6. Need inspect actual package major version and location of ISCC.exe before reinstalling. Inno Setup 7 is not a substitute for required Inno 6.

## EXACT NEXT EXECUTION
Ask owner to execute two read-only PowerShell commands displaying installed winget package version and candidate ISCC.exe paths/file versions, redacting user/profile details. Then choose either Inno 6 side-by-side install (if absent) or a narrow Test Center detection fix (if Inno 6 present in non-standard path). Once Diagnostics PASS, run Source Sync -> QUICK -> FULL SAFE in sequence with automatic GitHub evidence. Never GAME/RESTORE on main PC.
