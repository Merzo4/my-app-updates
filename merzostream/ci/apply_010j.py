import base64
import hashlib
import lzma
import os
import pathlib
import subprocess

PATCH_SHA = "5d21bead829401e92f63164641161da29ade3a8add979a28d49eb906ca9399c9"
XZ_SHA = "3c4e984a847478b9c0578dc1a3ee33b1c03bec8be5fa703fa89a9aeb8542e185"
PART_SHA = [
    "ee8e5cdf5de2a7c40eba12907a153fcbab182712951710c61ca3cf9bd19936be",
    "a488b81f0a3cd1762455c949d918c763b09569c46f374c9e33a50a157c25a857",
    "75eac070d82d7708df8b02151ea11bfb750b67d267fa286abc786dd7cc5dc0a9",
    "3dad2740e745eb3a95ed51149fc5840b69c818451125d5f15f21ffbca5eff5c1",
]

repo = pathlib.Path(__file__).resolve().parents[2]
parts_dir = repo / "merzostream" / "ci" / "010j-patch"
parts = [parts_dir / f"part{i:02d}.b64" for i in range(4)]
for i, part in enumerate(parts):
    if not part.exists():
        raise SystemExit(f"0.1.0j patch part missing: {part.name}")
    actual = hashlib.sha256(part.read_bytes()).hexdigest()
    if actual != PART_SHA[i]:
        raise SystemExit(f"0.1.0j patch part SHA mismatch: {part.name} {actual}")

encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
xz = base64.b64decode(encoded)
actual_xz = hashlib.sha256(xz).hexdigest()
if actual_xz != XZ_SHA:
    raise SystemExit(f"0.1.0j xz SHA mismatch: {actual_xz}")
patch = lzma.decompress(xz)
actual_patch = hashlib.sha256(patch).hexdigest()
if actual_patch != PATCH_SHA:
    raise SystemExit(f"0.1.0j patch SHA mismatch: {actual_patch}")

root = pathlib.Path(os.environ["MERZO_SRC"])

# The normalized patch was generated against LF versions of these text files.
# RELEASE_NOTES_0.1.0i.md intentionally stays untouched until git apply deletes it.
normalize = [
    "06_BUILD_RUNTIME_RELEASE.ps1",
    "08_BUILD_BRANDED_SETUP.ps1",
    "SELFTEST_PURE_DOTNET_STATIC.ps1",
    "content/app_info.json",
    "release/GITHUB_ACTIONS_MERZOSTREAM_RUNTIME.yml",
    "src/MerzoStream.Foundation/Services/LocalPlayerServer.cs",
    "src/MerzoStream.Foundation/Services/UpdateService.cs",
    "src/MerzoStream.Foundation/State/AppSettings.cs",
    "src/MerzoStream.Host/DotNetBackend.cs",
    "src/MerzoStream.Host/MainForm.cs",
    "src/MerzoStream.Setup/Program.cs",
    "tools/MerzoStream.Foundation.SelfTest/Program.cs",
    "ui/web/app.js",
    "ui/web/app_info.json",
    "ui/web/concept.css",
    "ui/web/concept.js",
    "ui/web/index.html",
    "ui/web/splash.html",
    "ui/web/styles.css",
]
for rel in normalize:
    p = root / rel
    if not p.exists():
        raise SystemExit(f"0.1.0j normalize target missing: {rel}")
    text = p.read_bytes().decode("utf-8-sig")
    p.write_bytes(text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))

out = pathlib.Path(os.environ.get("RUNNER_TEMP", str(root.parent))) / "merzostream-010j.patch"
out.write_bytes(patch)
subprocess.run(["git", "apply", "--check", str(out)], cwd=root, check=True)
subprocess.run(["git", "apply", str(out)], cwd=root, check=True)

notes_src = repo / "merzostream" / "ci" / "010j-release-notes.md"
notes_dst = root / "RELEASE_NOTES_0.1.0j.md"
if not notes_src.exists():
    raise SystemExit("0.1.0j release notes source missing")
notes_dst.write_text(notes_src.read_text(encoding="utf-8-sig"), encoding="utf-8", newline="\n")

print("0.1.0j PATCH PASS", PATCH_SHA, "xz", XZ_SHA, "parts", len(parts))
