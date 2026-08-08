# MerzoStream Suite — Changelog

## 0.0.4z — Central Update Engine 5.0

- Full cumulative application baseline from the 0.0.2k → 0.0.4z development line.
- PySide6 stability, Designer 2.0, adaptive UI and weak-PC optimizations.
- Stream Control PRO: per-platform fields, YouTube descriptions, thumbnails, history and profiles.
- OBS Center PRO, platform live statuses, viewers/likes where APIs expose them.
- Hotkey Manager, media-key priority mode, Automation/Macros and Service Manager.
- Encrypted MerzoStream Cloud with portable/device/secret settings separation.
- Clean runtime layout: user data, logs, cache and update staging stay in `%LOCALAPPDATA%`.
- **Central Update Engine 5.0**: GitHub Releases, one ZIP per version, SHA-256, safe extraction, isolated version folders, background download and first-start health-check with automatic rollback.
- Shared Python venv: dependencies are installed only when `requirements.txt` changes.
- VLC installer moved to a shared one-time resource, so normal future Release ZIPs stay much smaller.
