# Release policy — Engine 5

1. Every published tag is immutable in practice: never replace the ZIP under the same version.
2. Build a full version package, not a patch chain.
3. Upload both `MerzoStreamSuite-<version>.zip` and `MerzoStreamSuite-<version>.sha256` to the GitHub Release.
4. The ZIP must contain `release_manifest.json` at its root.
5. The launcher validates the GitHub asset SHA-256 (API digest when available, `.sha256` fallback), then validates every file against the internal manifest.
6. A new version is installed into a separate folder and becomes trusted only after its UI writes a startup health marker.
7. On failed health-check, the launcher automatically rolls back to the previous working version.
