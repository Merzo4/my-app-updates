# GPU Optimization Center — planned feature
Status: APPROVED FUTURE SCOPE; NOT IMPLEMENTED; TESTS NOT RUN.
Decision: ../DECISIONS/2026-10-18-002-performance-gpu-memory-guardian.md

## Read-only overview
Identify NVIDIA/AMD/Intel (including several adapters), exact driver/version and output/monitor ownership, dedicated/shared VRAM, utilization and supported thermal/power telemetry, current Windows/game settings. Label unsupported sensors as N/A instead of making up readings. Prefer documented DXGI/Windows PnP/graphics APIs with capability-negotiated vendor adapters.

## Future per-app settings
Show supported game/app graphics routing, power-vs-performance tradeoff, Windows graphics options (Game Mode, windowed optimizations, HAGS, VRR/HDR where available); recommend driver per-program features only through supported interfaces. Not all options improve games or are writable programmatically; otherwise use guided official settings page. Respect recording/streaming overlays and users' chosen drivers. Only exact compatible reversible settings go through Snapshot->Apply->Verify->Undo; no mutation from Scan/Recommend.

## Exclusions and acceptance
No blind global "Prefer Maximum Performance", OC/voltage/fan curve changes, DDU, driver swap, TDR hacks, forced realtime priority or FPS promises.
Verify on real GPU/driver/Windows tuple, single and multiple GPU, same-game repeatable average FPS/1% lows/frame time/thermal measurements. No benchmark = no gain claim.
