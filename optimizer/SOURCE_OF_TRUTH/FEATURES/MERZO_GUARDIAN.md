# Merzo Guardian — planned resident system monitor and SAFE reaction

Status: APPROVED FUTURE SCOPE; NOT IMPLEMENTED; NOT TESTED; NO BACKGROUND PROCESS DEPLOYED.
Decision: ../DECISIONS/2026-10-18-002-performance-gpu-memory-guardian.md

## Lifecycle
Optional per-user Windows interactive-session agent, OFF by default, enabled with separate consent. Visible system tray icon and compact panel; statuses IDLE/MONITOR/WARNING/CRITICAL/AUTO SAFE/PAUSED. Startup registration only on consent, uninstall cleanly removes registration; minimal privileges; singleton per user; fail-safe restart and no hidden SYSTEM service. Tray controls Open, Pause, Resume, disable autostart, Exit, Review log.

## What it watches
Use bounded low-overhead sampling (proposed 5–15 s intervals; tune after profiling): physical available/in-use, memory pressure/commit/paging, high sustained CPU/disk usage and lack of disk space; GPU only when sensors support it. Window/smoothing 30–60s, more than one independent indicator to classify resource exhaustion. Differentiate normal temporary game load from real crisis. Never treat cached standby RAM as emergency; log actual reason and confidence.
Privacy: local retention/rotation and optional sanitized export; no compulsory remote telemetry.

## Four response stages
1. HEALTHY: read-only.
2. WARNING: journal + optional tray notification.
3. CRITICAL: explain culprit and propose safe manual recovery, no implicit elevation or process kill.
4. AUTO SAFE (separately opt-in): only exact reviewed, safe, stateless user app identity; user configures every app and authorized response. If activity/unsaved state cannot be ruled out, **SKIPPED + alert**. Do not use unattended TerminateProcess or taskkill /F, never bypass a Save prompt. Automatically applying Windows configuration changes is prohibited unless supported by the existing reversible action catalog under separately approved policy.

## Protected classes
No termination of system/driver/security, game, OBS/streaming/recording/capture, Discord/call/audio, browser with valuable tabs, document/editor, backup/cloud/OneDrive, active download, Windows shell, hardware utility, elevated/user-unknown app, unknown publisher or process not positively allowlisted. Check path + signer + session/user + process-start identity and recheck immediately before a graceful Close. Process names/PIDs alone are insufficient, including recycled PIDs. Protect active foreground, child processes and in-progress work.

## Fail-safe design
User may pause or uninstall. Cooldown, action ceiling, hysteresis, no repeated closing on every tick. On failure/no candidate, notify only. Per-app close is irreversible with respect to unsaved user data; label it accurately; no invented Undo. Record each action and result, no excessive overhead or disruption during sleep/resume/sign-out or Windows updates.

## Test gates
Synthetic false low-RAM alarms, high used cache/available memory, PID reuse, spoofed process, Save-dialog refusal, active game/OBS/call, overnight uptime, sleep/resume, multiuser, uninstall cleanly removes autostart, CPU/RAM overhead and notification cooldown. Tests that might terminate apps or stress OS only on disposable lab. R57 FULL SAFE and Test Center GUI recovery stay the current prerequisite.
