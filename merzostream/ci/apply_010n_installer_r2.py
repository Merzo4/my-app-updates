import base64
import hashlib
import lzma
import os
import pathlib
import subprocess

PATCH_SHA = "fb00375e21a4c8b9bd9e203aa27a8f39663f176530cc3495001e42d2ba45d9b7"
XZ_SHA = "68d1142670be7138337ba2ec82e8c341f1e62362fb9a9a28be90fdedb361f712"
PART_SHA = [
    "58ba3aeb87e5c98d520f05e073d80e804fce0b68ca631e238d75b7c0015ae3e6",
    "c2b014fc130c3018874cf8514492f584ca8d6a8e81b2cf26c9082c9d70d90de0",
    "474f876b237867da83bae9cc395b50362a2ec645a496f9f9862cb34ec60aada4"
]

repo = pathlib.Path(__file__).resolve().parents[2]
parts_dir = repo / "merzostream" / "ci" / "010n-installer-r2-patch"
parts = [parts_dir / f"part{i:02d}.b64" for i in range(len(PART_SHA))]
for i, part in enumerate(parts):
    if not part.exists():
        raise SystemExit(f"installer R2 patch part missing: {part.name}")
    actual = hashlib.sha256(part.read_bytes()).hexdigest()
    if actual != PART_SHA[i]:
        raise SystemExit(f"installer R2 patch part SHA mismatch: {part.name} {actual}")
encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
xz = base64.b64decode(encoded)
if hashlib.sha256(xz).hexdigest() != XZ_SHA:
    raise SystemExit("installer R2 xz SHA mismatch")
patch = lzma.decompress(xz)
if hashlib.sha256(patch).hexdigest() != PATCH_SHA:
    raise SystemExit("installer R2 patch SHA mismatch")
root = pathlib.Path(os.environ["MERZO_SRC"])
out = pathlib.Path(os.environ.get("RUNNER_TEMP", str(root.parent))) / "merzostream-010n-installer-r2.patch"
out.write_bytes(patch)
subprocess.run(["git", "apply", "--check", "--binary", str(out)], cwd=root, check=True)
subprocess.run(["git", "apply", "--binary", str(out)], cwd=root, check=True)
print("0.1.0n INSTALLER R2 PATCH PASS", PATCH_SHA, "parts", len(parts))
