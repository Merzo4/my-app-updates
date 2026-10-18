# Memory & Background Center — planned feature
Status: APPROVED FUTURE SCOPE; NOT IMPLEMENTED; TESTS NOT RUN.
Decision: ../DECISIONS/2026-10-18-002-performance-gpu-memory-guardian.md

## Measurements
Separate physical installed/usable RAM, in-use, available, standby/cache, compressed, commit/limit, paged/nonpaged kernel pools and page pressure; process private bytes and working sets overlap, so don't sum them into a made-up physical RAM total. T+2/5/15 minutes after login, source-attributed startup, service/task/process family, driver/system/unknown categories, top resident consumers, opened apps and disk/CPU workload. Cache is not automatically waste.

## Safe reduction
Reuse existing startup/catalog and R56/R57 Process Intelligence once accepted. Suggest disabling **unwanted** app autoruns/background tasks only on reviewed allowlist, after user choice and reversible state snapshot. Protect OS/security, Store/Update, pagefile, OneDrive, sync, backups, drivers, peripherals and unknown WebView2. No blanket kill or periodic cache-clearing.

## Goal and verification
Lower avoidable boot RAM/CPU/disk and improve usable available memory/latency/paging. 2–3 GB is *a conditional best-case goal*, not guaranteed on a Windows 11 PC with real applications already running. Compare same hardware/driver/workload after consistent reboot at 2/5/15 min, quantify before/after and side effects. Link measured results to Guardian alerts via shared read-only model.
