# Merzo Windows Optimizer — R44 FUNCTION EXPANSION

Status: IN DEVELOPMENT
Base: published R43 / 0.1.43 TRUE FULL UI

## Non-negotiable baseline
- Keep R43 shell/layout and 1000x600 window contract.
- No return to R40/R42 page layout.
- Do not remove or rename existing commands/bindings without compatibility aliases.
- Preserve Snapshot -> Apply -> Verify -> Log -> Undo/Restore.
- Preserve R40 NetworkProgress OneWay fix.
- No destructive Appx removal until a guaranteed restore path exists.
- No automatic update install; user confirmation remains required.

## R44 scope
### 1. Smart Audit 2.0
- One consolidated audit result split into Privacy / Performance / Gaming / Startup / Services / Cleanup.
- Show already optimized, available, unsupported and attention-needed counts.
- Generate a personalized recommendation based on the actual machine state.
- Add a pre-apply plan summary instead of immediately changing Windows.

### 2. Profiles 2.0
- LIGHT / STANDARD / MAXIMUM / GAMING remain reversible.
- Before Apply show counts for tweaks, startup items, services/tasks and optional cleanup.
- Recommendation badges are driven by audit state, not hardcoded.
- Existing profile tags remain compatible.

### 3. Privacy / Telemetry Center 2.0
- Summarize documented privacy policies plus telemetry services/tasks already present in the catalog.
- Separate SAFE / STRICT / MAXIMUM.
- Show current state, applicable state and items already disabled.
- Never claim a setting is disabled unless the underlying scan confirms it.

### 4. Startup Manager 2.0
- Keep current startup engine and extend presentation with manageable / protected / already-disabled classification.
- Add impact/recommendation summary based on available metadata; no invented boot-time numbers.
- Preserve individual reversible actions.

### 5. Debloat 2.0
- Categorize audited Appx entries into Recommended / Optional / System-protected presentation groups.
- Keep removal disabled in R44 unless guaranteed package restore is implemented and tested.
- Explain why an app is safe/optional/protected instead of only listing package names.

## Release gates
- Build: 0 warnings / 0 errors.
- Core SelfTest PASS.
- R43 visual baseline contract PASS.
- 12 top-level pages preserved.
- Existing VM command regression gate PASS.
- Smart Audit 2.0 calculations tested with synthetic states.
- Privacy counts must be derived from actual tweak/service/task state.
- Startup/Debloat classifications must not enable new destructive actions by accident.
- XAML well-formedness PASS.
- Dispatcher + Network runtime smoke PASS.
- Full EXE startup PASS.
- Installer + portable + SHA-256 PASS.

Target release: 0.1.44 / R44 FUNCTION EXPANSION
