import base64, hashlib, lzma, os, pathlib, subprocess

PATCH_SHA = "a89506c6028496514400803f9c5d5605f4fef69b09cacf4e8c276ceece43cd34"
XZ_SHA = "9623499da6245ea757a6378d7a80501753f517ed7bbfb9ed36f32f70adb2c33a"
parts_dir = pathlib.Path(__file__).resolve().parent / "010i-patch"
parts = sorted(parts_dir.glob("part*.b64"))
if not parts:
    raise SystemExit(f"0.1.0i patch parts missing: {parts_dir}")
encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
xz = base64.b64decode(encoded)
if hashlib.sha256(xz).hexdigest() != XZ_SHA:
    raise SystemExit("0.1.0i xz SHA mismatch")
patch = lzma.decompress(xz)
if hashlib.sha256(patch).hexdigest() != PATCH_SHA:
    raise SystemExit("0.1.0i patch SHA mismatch")
root = pathlib.Path(os.environ["MERZO_SRC"])
out = pathlib.Path(os.environ.get("RUNNER_TEMP", ".")) / "merzostream-010i.patch"
out.write_bytes(patch)
subprocess.run(["git", "apply", "--check", str(out)], cwd=root, check=True)
subprocess.run(["git", "apply", str(out)], cwd=root, check=True)
print("0.1.0i PATCH PASS", PATCH_SHA, len(patch), "parts", len(parts))
