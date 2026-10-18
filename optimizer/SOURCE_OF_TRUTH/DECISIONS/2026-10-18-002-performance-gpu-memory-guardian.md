# DECISION 002 — GPU, memory and resident Guardian expansion

Date: 2026-10-18.
Product: Merzo Windows Optimizer; owner requested GPU tuning, boot/background RAM reduction and always-on critical system health response.
Status: **PRODUCT DIRECTION APPROVED; DESIGN RECORDED; IMPLEMENTATION NOT STARTED; TESTS NOT RUN**.
Prior SOT branch/HEAD: mwo-r57-safe-background-actions@ef423e7791c4aa6879dccc364036488f2c55a989.
Binding scope: ONLY the Optimizer product; do not alter StreamCenter, QUVELIO or MerzoStream.

## Three connected product centers
1. **GPU Optimization Center** — supported NVIDIA, AMD and Intel capabilities, device/driver identity and per-game recommendations; capability-gated reversible Windows and, where supported, vendor graphics preferences.
2. **Memory & Background Center** — accurate RAM/commit/available/standby/cached accounting, late-starting processes and autostart source attribution; allowlisted, reversible reduction of truly unwanted background workloads, with before/after proof.
3. **Merzo Guardian** — separate, optional, low-overhead user-session/tray monitoring process, locally sampling memory pressure/CPU/disk/GPU where supported, with alerts and cautiously opt-in automated SAFE responses.

## RAM target truth
Owner wants to lower observed Windows boot consumption from 6–8 GB toward 2–3 GB. This is an **aspirational device/workload-dependent goal**, NOT a guaranteed Windows 11 target and not feasible when all user apps necessarily consume more RAM. "Used" Windows RAM can include useful/reclaimable cached and standby pages; never manipulate counters merely for screenshots. Optimize available memory, boot latency, paging and foreground performance under comparable workloads.

## Authority / threat boundaries
- Guardian **OFF by default**; after enable, monitoring/notifications only by default.
- Per-user interactive autostart, visible tray, pause/exit/disable-startup, uninstall cleanup. No stealth persistence, SYSTEM service, hidden elevation or driver injection.
- Critical pressure must be sustained and corroborated by available physical memory, commit/paging/foreground impact. Neither 80% RAM nor momentary CPU spike alone permits mutation.
- A separate opt-in **Auto SAFE** grants permission only for exact, positively identified, previously reviewed and demonstrably stateless user applications; check signer/path/user/session, current process start identity/PID reuse, activity and process tree. Fail CLOSED on unknown, unsaved-work dialogs and failed checks.
- Unattended action can request **graceful close only**; NO force kill, taskkill /F, service/system process killing, or blanket process-name rules. Closing a process is *not reversible*: Snapshot does not restore unsaved data. If permission or safety proof absent, log SKIPPED, alert user.
- Always protect security and Windows core (Defender, Update, Store, services, drivers, pagefile), Explorer, users' work, games, OBS/recording/streaming, browser sessions, calls/Discord/audio, backup/sync/OneDrive, downloads, unknown WebView2 and peripherals. Never interfere with active workload automatically.
- No automated standby-list emptying, working-set trimming, SysMain/pagefile blanket disabling, OC/undervolt, GPU voltage/fan/power changes, undocumented driver registry hacks, or generic "FPS boost" claims.
- Existing Snapshot->Apply->Verify->Undo catalog remains authority for reversible Windows changes; do not duplicate mutation engine.
- Data stays local by default. Bounded telemetry and local sanitized journal, alert rate limits, cooldown/hysteresis, CPU/RAM overhead limits, no always-on network requirement.

## Phase/sequence
R57 P4 Local FULL SAFE remains PRIMARY, with Test Center 0.1.8 owner-visible GUI confirmation still PENDING. This decision authorizes **future scope**, not immediate product coding nor bypass of R57 gates. Future implementation phases are gated F0 read-only contract, F1 telemetry and GPU/memory inventory, F2 tray monitor and synthetic pressure, F3 notifications, F4 narrowly reviewed Auto SAFE, F5 test/release acceptance. Separate owner consent remains required for risk expansion, destructive lab trials and Stable/public release.

## References
- FEATURES/GPU_OPTIMIZATION_CENTER.md
- FEATURES/MEMORY_BACKGROUND_CENTER.md
- FEATURES/MERZO_GUARDIAN.md
