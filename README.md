# MerzoStream Suite — Central Update Repository

This repository is the control point for **Central Update Engine 5.0**.

## What lives in the Git repository

- `cloud_public_config.json` — public GitHub OAuth Client ID for MerzoStream Cloud. **Never put a client secret here.**
- `CHANGELOG.md` — human-readable release history.
- `.gitignore` — prevents accidentally committing release ZIPs, logs and local secrets.

## What does NOT live in the Git tree anymore

Application files are no longer committed one-by-one under `files/`.
Every application version is published as a **GitHub Release asset**:

- `MerzoStreamSuite-<version>.zip`
- `MerzoStreamSuite-<version>.sha256`

The launcher reads the Releases API, downloads one ZIP only when a newer version exists, validates it, installs it into `versions/<version>`, and keeps the previous working version for rollback.

## Release tags

Use tags like `v0.0.4z`, `v0.0.5z`, etc.
Beta builds may be marked **Pre-release**. Engine 5 beta channel accepts both pre-releases and regular published releases; stable channel ignores pre-releases.

Do not modify an already published version package. If anything changes, publish a new version/tag.
