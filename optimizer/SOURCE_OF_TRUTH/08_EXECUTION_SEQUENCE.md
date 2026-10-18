# 08 — EXECUTION SEQUENCE / gate-controller

Документ определяет последовательность. Если активная техническая проверка блокирована — не перескакивать в следующий этап и не переименовывать FAIL в PASS.

| Фаза | Gate | Доказательство | Статус на 2026-10-18 |
|---|---|---|---|
| P0 | Public baseline R55.1 | GitHub release + CI/installer | RELEASED |
| P1 | R56 cumulative candidate build/real startup | run 32479505374 | PASS |
| P2 | R56 installed + GAME/RestoreAll exact test | run 32480404145 | PASS |
| P3 | R57 source/static gate | scripts + R57_LOCAL_TEST_STATUS | PREPARED, NOT RUN |
| P4 | R57 FULL SAFE local Windows build and UI test | new local evidence | PENDING |
| P5 | R57 GAME->RestoreAll on dedicated lab | new separate risk-boundary evidence | PENDING |
| P6 | R57 installed/OTA/update/rollback acceptance | exact artifact SHA | PENDING |
| P7 | user-facing Windows 11 regression and baseline | device/test evidence | PENDING |
| P8 | release approval and immutable asset publish | owner decision + release tag | NOT AUTHORIZED |

## Exit критерии
- P4: full source reconstruct, static acceptance, compilation/SelfTest, finished DLL version, real WPF non-error main window, finished installer/portable + SHA, no unintended mutation.
- P5: test ONLY disposable lab; OneDrive and protective checks, GAME mutation and production RestoreAll restoration each PASS; failing step blocks.
- P6: proven installed Program Files exact artifact; staged/public update path, UAC, rollback and file integrity; no untested replacement of live user data.
- P7: explicit owner-observed UX + logs, no claims of FPS/RAM without measurement.
- P8: all required evidence, owner explicitly approves release.

## Дисциплина
Технический PASS можно зафиксировать только для конкретных SHA/build/run/environment. Не переносить PASS R56 на R57; не тестировать risky gate на рабочем ПК. Перед выходом из этапа обновить current/handoff/ledger/roadmap. Отдельный документальный коммит не закрывает технологический gate.

## Future gated phases for Decision 002 — NOT YET AUTHORIZED TO START
F0 scope/risk/capabilities; F1 GPU+memory read-only measurement; F2 resident Guardian monitor-only lifecycle/tray; F3 critical-alert synthetic verification; F4 allowlisted Auto SAFE identity/graceful-close isolated-lab safety; F5 real hardware benchmarks, sleep/resume, recording/streaming, security, install/uninstall and owner acceptance. All FUTURE / NOT RUN. **Do not bypass current R57 P4–P8 prerequisites.** No public release or process-termination trials on normal owner workstation.

## R57 P4 subgate progress — Test Center visible GUI (owner, 2026-10-18)
Environment entry gate **P4.0 Test Center 0.1.8 visible GUI: OWNER OBSERVED PASS** after 0.1.7 failure, no independent log furnished. The remaining required P4 steps are **P4.1 Diagnostics NOT RUN**, **P4.2 Sync NOT RUN**, **P4.3 QUICK NOT RUN**, **P4.4 FULL SAFE NOT RUN**, plus follow-up exact logs/review. Run in that order, stop on failure; Test Center FULL SAFE internally repeats QUICK by design. This does not modify P5 lab-only safety, P6 OTA or P8 release authority.

## Real P4 diagnostics result, 2026-10-18
P4.0 Test Center GUI owner PASS. **P4.1 Diagnostics FAIL: Inno Setup 6 ISCC.exe missing**, published automatically to `mwo-local-lab-evidence` SHA 22030119a4af17803fd83ce3950f2041d400b761. P4.2 Source Sync, P4.3 QUICK, P4.4 FULL SAFE = NOT RUN / BLOCKED on prerequisite. The fix is a developer-toolchain install, NOT a code change to R57. Recheck Diagnostics until PASS; no program tests or release implied.

## Test Center UI label diagnostic subtask, 2026-10-18
Test Center 0.1.9 Windows 11 Edition/DisplayVersion/UBR label fix **IMPLEMENTED at source SHA 00f0484cbff48380a205410da1ebf208c7f63de6; NOT RUN on Windows**. Cosmetic, separate from R57 P4. Owner may update Test Center to check display label, but this is not a substitute for Diagnostics PASS and R57 Sync/Quick/FullSafe. Prior P4 Diagnostics FAIL Inno Setup 6 remains latest remote evidence; no new remote PASS found.

## Test Center infrastructure subgate: native EXE UI migration
Native Lab 0.2.0 source and local builder PREPARED at `mwo-local-test-center@f8757abcfabf0780fcf891661e0e1596dc1ad96a`; real Windows build/smoke and owner GUI verification **PENDING**, must not be called PASS. Restore point is existing 0.1.9 GUI and `START-TEST-CENTER-LEGACY.bat`. Validate native EXE start and close (no console), Diagnostics, auto evidence. Then fulfill R57 P4 Diagnostics prerequisites Inno 6, Source Sync, QUICK, FULL SAFE in existing safe sequence. Separate native test UI build is NOT R57 program acceptance and never authorizes GAME/RESTORE.

## Test Center Native EXE 0.2.1 unblocker
Test Center 0.2.0 local parser gate owner **FAIL**, before NativeHost compile. Restored PS source and pinned fixed Test Center 0.2.1 at `1db2b1d91ea699a84fd0a374b00867c185d9e8c9`: GitHub source corrected, native Windows parser/.NET build/GUI still **PENDING**. Reattempt local installer; stop on first FAIL, preserve logs and previous launcher. Once PASS, continue the R57 P4 sequence Diagnostics (requires Inno Setup 6), Sync, QUICK, FULL SAFE. This issue does not authorize bypass of parser gate or destructive modes.

## Test Center 0.2.1 -> 0.2.2 native build gate
Owner 0.2.1: PowerShell Parser PASS, legacy GUI Smoke PASS, native `dotnet publish` **FAIL** (MSB1025 inherited TEMP/TMP invalid); no native EXE Windows PASS. v0.2.2 source/generator/temp guards `39b17f00c7270bca7ee3a5df607e51420c4ae2fc` ready, next local install retest PENDING. Do not bypass parser, smoke or full error checks. R57 P4 remains blocked on Test Center native install and Inno Setup 6 preflight; Sync/Quick/FullSafe not run.

## Owner 0.2.2 environment gate update — 2026-10-18
Test Center 0.2.2 **GUI owner-visible PASS** and **profile.Diagnostics executed, AUTO EVIDENCE PASS**. Actual Diagnostics **FAIL** due missing Inno Setup 6 `ISCC.exe`; GitHub evidence `20261018T080939838Z-profile.Diagnostics-660846e5` SHA 84778f7e5c390f3c3a6e5ad8ef60ad07eadaceaa. Toolchain non-Inno checks PASS, source sync/Quick/FullSafe BLOCKED/PENDING. No need to repeat previous installer scripts when GUI already opens. Next blocker resolution Inno Setup **6**; retest Diagnostics exact run then Sync/Quick/FullSafe on PASS. Native EXE console visibility not explicitly confirmed; do not assume complete native frontend acceptance.

## Test Center 0.2.3 UI subgate
Test Center 0.2.3 source a205879fdf1d4d84ee35cd8b26411855a73318fc: auto GitHub receipt UI and retry for queued/deferred evidence, CODE IMPLEMENTED, Windows compiled/rendered/transport failure test NOT RUN. This is NOT an R57 product code gate and does not change destructive constraints. Diagnostics FAIL Inno Setup 6 remains latest evidence, Source/Quick/FullSafe blocked until prerequisite passes.

## Actual user 0.2.3 Diagnostics evidence, 2026-10-18
Remote `mwo-local-lab-evidence@dc1ac24ed1a85a2ce0dd7d1965e31ad936e5b328` event `20261018T083407111Z-profile.Diagnostics-ec944325`: auto GitHub upload **PASS**, Test Center 0.2.3 Diagnostics **FAIL** Inno Setup 6 `ISCC.exe` not found; other gates PASS. This does not assert native auto-report status indicator visual PASS nor offline retry. R57 P4 Source Sync, QUICK, FULL SAFE **NOT RUN**. Exact next subgate: inspect installed Inno Setup package version/path (winget already reports package installed) then resolve 6 detection, rerun Diagnostics PASS, only then gated R57 tests. No GAME/RESTORE on user workstation.

## R57 P4 preflight unblock — Inno 6 user-scope detection v0.2.4
Observed winget 6.7.3 installed but `ISCC.exe` absent from both Program Files globs, latest Test Center 0.2.3 Diagnostics FAIL. Source-only Test Center 0.2.4 adds local scope/uninstall registry resolution with compiler version major 6, same resolver for Diagnostics & Quick; exact compile path passed as process-local `MWO_INNO6_ISCC` and minimally supported in both cumulative R56 baseline and R57 build scripts. **P4 Diagnostics retest NOT RUN; Sync/Quick/FullSafe blocked**. Historic R56 tests are attached to old exact SHA and not transferred. First local Test Center update then Diagnostics PASS; thereafter complete exact P4 steps in order, stop on FAIL. No GAME/RestoreAll on ordinary workstation.

## 2026-10-18 — P4 prerequisite narrowed to real Test Center 0.2.4 Diagnostics
Confirmed by owner read-only PowerShell file existence check: current-user `Programs\Inno Setup 6\ISCC.exe` exists (PASS); `winget` earlier reports Inno 6.7.3. New v0.2.4 resolver is coded but not Windows-accepted; no new GitHub local-lab-evidence beyond v0.2.3. Do not reinstall toolchain or skip version verification. Next local 0.2.4 Diagnostics → on PASS Sync → QUICK → FULL SAFE. Preserve status segregation and auto reports; main-PC GAME/RESTORE prohibited.

## Actual 0.2.4 owner execution, 2026-10-18
P4.1 Diagnostics v0.2.4: **FAIL** Inno 6 `ISCC.exe not found; inspect install location` (GitHub evidence ca858f12ccc66a6bee2086a8d9e7738ab446763b); other diagnostics PASS, Auto-Report upload PASS. Previous compiler file presence True. Subreason of resolver rejection still unknown; obtain exact executable embedded version metadata, do not relax safety/version gate on assumption. P4.2 Sync, P4.3 Quick, P4.4 FullSafe remain NOT RUN/BLOCKED. R57 product source unchanged by this evidence-only cycle, no destructive testing on workstation.

## Test Center 0.2.5 major-six fallback — P4 prerequisite
Screenshot evidence shows local ISCC.exe metadata both 0.0.0.0 and v0.2.4 rejects by version resource; source fix 0.2.5 `7626f1fd28d931620b9a255a3d88672a9192578b` uses bounded read-only /? help banner for version6 as fallback. Both cumulative Optimizer R56/R57 scripts now use matching identity check. **IMPLEMENTED SOURCE; Windows Diagnostics NOT RUN**. Next owner update to v0.2.5 and Diagnostics PASS before R57 Sync -> QUICK -> FULL SAFE. Preserve prior FAIL and do not bypass gates or run destructive profiles.

## Current exact gate 2026-10-18 — P4.1 Diagnostics PASS (Test Center 0.2.5)
Remote evidence `mwo-local-lab-evidence@fe8b1f1da99770643cfeadfe0b8106a27febcb20`, Test Center 0.2.5, `profile.Diagnostics` 2026-10-18T12:50Z: **PASS 8/8**, including owner per-user Inno Setup 6 after strict compiler help-banner fallback. Auto-report transport PASS. P4.1 prerequisite now completed on user's Windows, old Inno detection blocker resolved. **P4.2 Source Sync NOT RUN (NEXT)**; **P4.3 QUICK NOT RUN**; **P4.4 FULL SAFE NOT RUN**. Gate logic remains strict, no R57 build/release accepted yet. Run Sync in D: sandbox, then Quick, then FullSafe, stopping at first fail. P5 dangerous lab-only, P8 release no authorization.

## Latest actual owner gate (2026-10-18) — P4.2 Source Sync PASS
`mwo-local-lab-evidence@7e9a8942dc87d16f5fc2b1642c5aeab56d7e57ee`, event `20261018T125650456Z-profile.Sync-d965463d`: Test Center 0.2.5 Source exact checkout **PASS** at `mwo-r57-safe-background-actions@1f1044bcf95bc54458dc60d53a6dc5242d35dd91`, source under `D:\MerzoOptimizer-LocalLab\Source`. P4.1 Diagnostics 8/8 PASS previously, P4.2 Source Sync PASS now. **P4.3 QUICK NOT RUN (NEXT)**; **P4.4 FULL SAFE NOT RUN**, hence R57 candidate not yet accepted. New docs-only HEAD changes are not product source changes; QUICK Sync must record the exact SHA that is actually built. On PASS proceed FullSafe; on FAIL stop/inspect latest evidence. GAME/RESTORE not allowed on primary workstation.

## Latest owner gate (2026-10-18) — QUICK FAIL, FULL SAFE BLOCKED
Actual GitHub `mwo-local-lab-evidence@aa91d2d16a64e68a28910cc99118691b0d7fca13`, `20261018T130032723Z-profile.Quick-6d3cf2f4`: Test Center 0.2.5 QUICK Source Sync PASS `mwo-r57-safe-background-actions@1329f6cd887faa3fe85f701c988609e7aa4f16f4`; cumulative build FAIL exit=1 at R50 expanded runner first Python patch `r24_update_center.py`, only later high-level error `Patch failed` captured. P4.1 Diagnostics previous PASS 8/8, P4.2 Source Sync PASS, **P4.3 QUICK FAIL**, **P4.4 FULL SAFE BLOCKED/NOT RUN**. Initial Diagnostics lacks Python availability probe. Root cause could be Python executable absent, bad App Execution Alias, or actual patch failure; DON'T GUESS. Obtain read-only Python 3 version and process exit codes before fix. Do not run GAME/RESTORE on normal PC, do not publish stable.

## Current next gate — resolve Python prerequisite after QUICK FAIL (2026-10-18)
Screenshot proves `python --version` returned alias `Python` with exit 9009, `py -3` not recognized. Cumulative build executes `python r24_update_center.py`, so functional Python 3 is missing. Test Center 0.2.6 SOURCE prepared `mwo-local-test-center@95c735c54ced62605e9c02cd98569b0b4d023665`, new env.python functional version check and pre-QUICK fail-fast. P4.1 previous Diagnostics v0.2.5 eight existing checks PASS, but new Python stage PENDING; P4.2 Source Sync PASS; P4.3 QUICK FAIL at SHA 1329f6c, P4.4 FULL SAFE BLOCKED. Next: owner install Python 3 from trusted publisher, refresh PATH, verify actual execution (not just alias), update Test Center v0.2.6, run Diagnostics and then QUICK; do not modify R57 patch on invalid toolchain. On QUICK PASS next FULL SAFE. No destructive workstation acceptance.

## Latest toolchain owner verification — 2026-10-18 checkpoint 023
Python 3.13.15 working in newly opened PowerShell, confirmed actual `-c` script and exit 0 (old Windows alias 9009 resolved). Python local environment gate PASS as a manual prerequisite, **not** as new Test Center Diagnostics. P4.1 prior Test Center 0.2.5 Diagnostics 8/8 PASS; P4.2 Sync PASS; P4.3 prior QUICK FAIL; current P4.3 retest NOT RUN, P4.4 FULL SAFE BLOCKED. Exact next Test Center **0.2.6** install/update -> real Diagnostics **9 stages** -> auto evidence; on all PASS run QUICK and only then FULL SAFE. No destructive workstation tests, no Stable publication.

## Current next gate after actual Test Center v0.2.6 Diagnostics 10/10 PASS
Live GitHub `mwo-local-lab-evidence@ddfd3bb8336789fd1122e8f4a120135886218d94` event `20261018T135421246Z-profile.Diagnostics-29054e0d` shows Test Center 0.2.6 completed **10/10 Diagnostics PASS** at 2026-10-18T13:54:21Z, including real Python 3.10+ execution, Inno Setup 6 and protected D: Lab environment; auto upload confirmed. Prior v0.2.5 eight stages PASS and the old Quick FAIL at first Python patch remain separate exact-run evidence; this corrected prereq makes **new P4.3 QUICK retry AUTHORIZED but NOT RUN**. Source origin stage is only identity check, not fresh checkout; QUICK itself Syncs source to exact new HEAD before cumulative build. **P4.4 FULL SAFE BLOCKED/NOT RUN until QUICK PASS.** No destructive GAME/RESTORE on primary workstation or release.
