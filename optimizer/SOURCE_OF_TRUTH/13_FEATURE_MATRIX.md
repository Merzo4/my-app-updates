# 13 — FEATURE AND VERIFICATION MATRIX

Date: 2026-10-18. Status column distinguishes available public from candidate/prepared. «Published» означает опубликованную реализацию по release notes, а не доказательство на любом ПК.

| Feature | Earliest evidence/example | Status |
|---|---|---|
| WPF dark 12-page shell / UI | mwo-v0.1.43 / R50–R52 UX fixes | Published |
| Smart Audit 2.0 | mwo-v0.1.44 | Published |
| Profiles LIGHT/STANDARD/MAXIMUM/GAMING | R44/R47/R49 releases | Published |
| GAME SAFE/PERFORMANCE/EXTREME/LAB | mwo-v0.1.39, R49–R54 | Published; destructive lab condition |
| Privacy / Telemetry Center 2.0 | mwo-v0.1.44 | Published |
| Startup Manager / Services / Scheduled Tasks | mwo-v0.1.44; R34 | Published |
| Debloat Appx allow-list and conditional removal | mwo-v0.1.53–R54 | Published; recovery safety boundary |
| Process Reduction / baseline / TOP-50 | mwo-v0.1.34 | Published |
| 0/1/5/10/15 minute process audit | mwo-v0.1.55.1 | Published |
| Persistent background at 15 min / live-vs-saved | R56 run 32479505374 and 32480404145 | Technical candidate PASS, NOT PUBLIC |
| Diagnostics -> prepared SAFE tweak cards | R57 source and static/test scripts | IMPLEMENTED/PREPARED; FULL SAFE NOT RUN |
| Repair/Network & SAFE gaming network | R37–R39 | Published |
| Snapshot/Undo/RestoreAll | R34–R56 tested release family | Published; verify exact scenarios |
| OneDrive protection/recovery | R49/R54.2/R55.1/R56 | Published; strong restrictions |
| User feedback/crash report | mwo-v0.1.34 | Published |
| Built-in Update Center/release integrity | R32/R46/R48/R54 | Published; fresh target acceptance required |
| Program Files installer / portable | mwo-v0.1.54.2 / R56 gate | Published + R56 verified |
| Code obfuscation without runtime regression | R33 history, R57 skip | Deferred/unresolved |
| Digital signing certificate | no confirmed certified signer | NOT CONFIRMED |
| Full owner Windows 11 R57 acceptance | no verified result | PENDING |

Rule: edit this matrix with exact evidence and release gate; do not overwrite previous historical failure or promote a draft.
