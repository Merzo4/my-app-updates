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
