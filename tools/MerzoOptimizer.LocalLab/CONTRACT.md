# MERZO OPTIMIZER LOCAL TEST CENTER — PERMANENT CONTRACT

**Status:** development infrastructure / local verification

## Purpose

Merzo Optimizer Local Test Center is the normal day-to-day verification path for Merzo Windows Optimizer. Its main purpose is to move repeated build, startup, SelfTest, diagnostic and owner-machine verification away from GitHub Actions.

GitHub Actions are reserved for rare independent release gates, especially immutable public release/OTA proof on disposable Windows.

## Canonical roots

Local laboratory:

`D:\MerzoOptimizer-LocalLab`

Protected installed product:

`C:\Program Files\Merzo Windows Optimizer`

Dedicated source checkout owned by Test Center:

`D:\MerzoOptimizer-LocalLab\Source`

Evidence checkout:

`D:\MerzoOptimizer-LocalLab\EvidenceRepo`

## Production protection

Safe profiles must never install over or replace the real Program Files application.

Before and after safe verification Test Center fingerprints the protected Program Files payload. A changed fingerprint is FAIL.

Source cleanup (`reset --hard`, `clean -fdx`, branch checkout) is allowed only in the dedicated Local Lab Source after repository-origin validation.

## Profiles

### Diagnostics

Non-mutating. Checks D:, Git, PowerShell 7, .NET 10, Inno Setup 6, repository origin and production-path isolation.

### Sync

Updates only the dedicated Source checkout to the target branch from `local-lab-profile.json` and records exact SHA.

### Quick

Runs the current cumulative product build controller locally, including the controller's own acceptance/SelfTest/startup gates, stages the exact build under `TestBuild\Quick`, and proves Program Files unchanged.

Quick never enables GAME/system mutation.

### Full Safe

Includes Quick plus an owner-machine real-window/stability smoke. Only whole Full Safe PASS is promoted to `TestBuild\Current`.

### GAME → RESTORE

Destructive and blocked by default. It may run only on a machine explicitly armed with `ALLOW-SYSTEM-MUTATION.json`, bound to that exact machine name, and requires Administrator.

The profile verifies the current product GAME mutation and production RestoreAll contract. It must not be enabled merely to reduce process counts on the owner's normal Windows installation.

## Evidence

Latest local result:

`D:\MerzoOptimizer-LocalLab\Results\Latest\LAB-RESULT.json`

Human-readable report:

`D:\MerzoOptimizer-LocalLab\Results\Latest\REPORT.txt`

Current log:

`D:\MerzoOptimizer-LocalLab\Logs\Current.log`

Bounded history: latest 20 summaries only.

Optional evidence ZIP:

`D:\MerzoOptimizer-LocalLab\Results\MerzoOptimizer-Verify-Evidence.zip`

## Zero-Actions evidence branch

Remote evidence branch:

`mwo-local-lab-evidence`

It intentionally contains no `.github/workflows` directory. Local Test Center may overwrite `LOCAL_LAB_EVIDENCE/LATEST/` with the latest small evidence files by ordinary Git push.

Evidence publishing failure never changes the already-determined product test PASS/FAIL.

## GitHub Actions policy

Do not use Actions for ordinary:
- source sync;
- restore/build;
- SelfTest;
- XAML/startup checks;
- process-audit/classification checks;
- local portable runtime smoke;
- local evidence generation.

Use hosted Actions only when an independent clean/disposable Windows proof materially adds value, especially final immutable release/public OTA verification.

## Version routing

The Test Center shell is version-independent. Product-specific routing lives in `local-lab-profile.json`.

When development advances to R57/R58/etc., update primarily:
- target branch;
- product version/file version;
- cumulative build controller;
- generated root/dist paths;
- destructive acceptance script.

Do not rewrite the whole Test Center for every product release.
