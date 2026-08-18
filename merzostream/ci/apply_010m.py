import base64
import hashlib
import lzma
import os
import pathlib
import subprocess

PATCH_SHA = "ffeed6da5f22fa5afbddc47ec14dc78d1a35056cbbd30667cdac725a7ef1fc87"
XZ_SHA = "6edee4233030686bc3cb701b533550e94cc18a7bee14ace092537aba432cd688"
PART_SHA = [
    "e96afaeb2bef3da58fb77f3572ba8227d612b0482f7f9d4a475ce274ef2e7161",
    "5a07dc2cc973c3401ef84ab13fdf08bfff57c881b03e13c59936f796a87bdfa7",
    "a35a1395c9c42f806d95de404c72b1c6a325cd8a7bf3e48456ba1c1d5e518cf8",
    "60c922c2f941ee2544feabe0d7c20aea2506df4d44975d4db86a09c1cb304b16",
    "b8300c43de06fa1db2636611d8a7fd47aa2d7ee5aad981242dd0d3919c3c8716",
    "5145413df3482062828b822d368516984f4413443155d6624081007584a8f6da",
    "60fc5034ecdd3dacf977e33ecb9b4dc5dd7ace550e92a2eb3e17112a0b3afc53",
    "9d9927b306be86d6f03d94300ca4b3a983babc63b326ffb0f27b8f17e4aaaca7",
    "87ab90fda120191cbbc01f64089caa41a6b517fb004797d93d3cbbc175d5118a",
    "bd7d48c5683a86816bf51a5d0ad41230bd52c23c72c72627a9b2f9bca85ffeba",
    "a55360c44560054c6343b0f3f67b3710e4931f0b50bb5d02cfc17f849be0c662",
    "87522b1978672d5d227fc77740c91716798af0a2b82703ce639fcc0fe57cf0fa",
    "a65b72c88eb40a0eb0c013cdf46eb6be92c3e58ba8d9e09f749c00677b1fce2d",
]

repo = pathlib.Path(__file__).resolve().parents[2]
parts_dir = repo / "merzostream" / "ci" / "010m-patch"
parts = [parts_dir / f"part{i:02d}.b64" for i in range(len(PART_SHA))]
for i, part in enumerate(parts):
    if not part.exists():
        raise SystemExit(f"0.1.0m patch part missing: {part.name}")
    actual = hashlib.sha256(part.read_bytes()).hexdigest()
    if actual != PART_SHA[i]:
        raise SystemExit(f"0.1.0m patch part SHA mismatch: {part.name} {actual}")

encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
xz = base64.b64decode(encoded)
actual_xz = hashlib.sha256(xz).hexdigest()
if actual_xz != XZ_SHA:
    raise SystemExit(f"0.1.0m xz SHA mismatch: {actual_xz}")
patch = lzma.decompress(xz)
actual_patch = hashlib.sha256(patch).hexdigest()
if actual_patch != PATCH_SHA:
    raise SystemExit(f"0.1.0m patch SHA mismatch: {actual_patch}")

root = pathlib.Path(os.environ["MERZO_SRC"])
out = pathlib.Path(os.environ.get("RUNNER_TEMP", str(root.parent))) / "merzostream-010m.patch"
out.write_bytes(patch)
subprocess.run(["git", "apply", "--check", str(out)], cwd=root, check=True)
subprocess.run(["git", "apply", str(out)], cwd=root, check=True)

# The frameless splash was intentionally resized to 620x370 in 0.1.0m.
# Keep the static contract aligned with the actual MainForm instead of the older 600x330 value.
selftest = root / "SELFTEST_PURE_DOTNET_STATIC.ps1"
text = selftest.read_text(encoding="utf-8-sig")
old = "ClientSize = new Size(600, 330)"
new = "ClientSize = new Size(620, 370)"
if old not in text:
    raise SystemExit("0.1.0m selftest splash-size marker missing")
selftest.write_text(text.replace(old, new), encoding="utf-8", newline="\n")

print("0.1.0m PATCH PASS", PATCH_SHA, "xz", XZ_SHA, "parts", len(parts), "splash-contract=620x370")
