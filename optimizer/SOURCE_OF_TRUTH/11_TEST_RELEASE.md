# 11 — TESTING AND RELEASE PROTOCOL

## Обязательная идентичность
Every result requires repo, branch, source SHA, code/content SHA if docs-only differs, version, test run, OS/environment, scope/risk, artifact hash and exact command or workflow.

## Gates
1. Prebuild: validate source reconstruct, patch anchor, XAML parse, SAFE reviewed tweak IDs, no second mutation surface.
2. Build: production DLL/EXE, compilation/SelfTest and versions all identical.
3. Runtime: real main WPF window; no startup error window and no fresh crash log.
4. Package: Inno installer + portable with exact SHA-256, install under Program Files.
5. Local FULL SAFE on Windows: non-destructive UI and diagnosis; selection-only R57, no direct Windows mutation.
6. Dedicated LAB: GAME/EXTREME, service/network/OneDrive and RestoreAll safety with explicit scoped permission.
7. OTA upgrade on real installed baseline, digest/timeout/rollback.
8. Owner Windows 11 acceptance and, when desired, repeatable before-after measurements.

## Правила результата
- PENDING: ожидается; NOT RUN: не выполнялось; PREPARED: код/скрипт только подготовлен.
- PASS: exact run artefact succeeded; FAIL: falsifying evidence; BLOCKED: prerequisites unmet; PARTIAL: only subset.
- RUN FAIL не перезаписывать. Исправление -> новый SHA и новый отдельный run; установить причинность.
- Не смешивать Windows Server 2025 disposable-lab PASS и настраиваемый домашний Windows 11 owner acceptance.

## Release gate
Before stable tag publish: exact reproducible artifact, full risk coverage, dependency/Windows tests, docs/ledger current, issue list/known limitations, owner confirmation, immutable release tag/assets. Не пересобирать код молча между tested artifact и published artifact.
