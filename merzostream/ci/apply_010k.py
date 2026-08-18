import base64
import hashlib
import lzma
import os
import pathlib
import subprocess

PATCH_SHA = "d1bb28d54d5afeba331efcc69569444f8bb256b239885aa1ecf525907a893061"
XZ_SHA = "d555a3e5dc924aa22d0654a1403d6b6c934e49703700a28fb72fb752aa4651da"
PART_SHA = ['6b688b4b9f8861bdd9b68e5e3f0d34709a91421feb74a30ad998b26a135d046c', 'dc89c6d88bfd49435699283ab903b2f884d03c843b47b0e33b0611adda7f3f79', '0db2d945d29b1ee68d30ada8ac4d7c37b508d5ab8da34662d442295328a5db9d', 'fc9c1075e8c9844d29266ca952ea4ac4be44bf22d58924796e52475e3b18da9a', '87656ca719c9b91f4171d2563ab629f43f4d48c9cebebbe463317f586e245a6b']
NORMALIZE = ['06_BUILD_RUNTIME_RELEASE.ps1', '08_BUILD_BRANDED_SETUP.ps1', 'SELFTEST_PURE_DOTNET_STATIC.ps1', 'content/app_info.json', 'release/GITHUB_ACTIONS_MERZOSTREAM_RUNTIME.yml', 'src/MerzoStream.Foundation/Services/LocalPlayerServer.cs', 'src/MerzoStream.Foundation/Services/MediaQueueService.cs', 'src/MerzoStream.Foundation/Services/MusicLibraryService.cs', 'src/MerzoStream.Foundation/Services/OnlineMusicService.cs', 'src/MerzoStream.Foundation/Services/StreamerBotService.cs', 'src/MerzoStream.Foundation/Services/UpdateService.cs', 'src/MerzoStream.Foundation/State/AppSettings.cs', 'src/MerzoStream.Host/DotNetBackend.cs', 'src/MerzoStream.Host/MainForm.cs', 'src/MerzoStream.Setup/Program.cs', 'tools/MerzoStream.Foundation.SelfTest/Program.cs', 'ui/web/app.js', 'ui/web/app_info.json', 'ui/web/concept.css', 'ui/web/concept.js', 'ui/web/index.html', 'ui/web/splash.html', 'ui/web/styles.css']

repo = pathlib.Path(__file__).resolve().parents[2]
parts_dir = repo / "merzostream" / "ci" / "010k-patch"
parts = [parts_dir / f"part{i:02d}.b64" for i in range(len(PART_SHA))]
for i, part in enumerate(parts):
    if not part.exists():
        raise SystemExit(f"0.1.0k patch part missing: {part.name}")
    actual = hashlib.sha256(part.read_bytes()).hexdigest()
    if actual != PART_SHA[i]:
        raise SystemExit(f"0.1.0k patch part SHA mismatch: {part.name} {actual}")

encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
xz = base64.b64decode(encoded)
actual_xz = hashlib.sha256(xz).hexdigest()
if actual_xz != XZ_SHA:
    raise SystemExit(f"0.1.0k xz SHA mismatch: {actual_xz}")
patch = lzma.decompress(xz)
actual_patch = hashlib.sha256(patch).hexdigest()
if actual_patch != PATCH_SHA:
    raise SystemExit(f"0.1.0k patch SHA mismatch: {actual_patch}")

root = pathlib.Path(os.environ["MERZO_SRC"])
for rel in NORMALIZE:
    p = root / rel
    if not p.exists():
        raise SystemExit(f"0.1.0k normalize target missing: {rel}")
    text = p.read_bytes().decode("utf-8-sig")
    p.write_bytes(text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8"))

out = pathlib.Path(os.environ.get("RUNNER_TEMP", str(root.parent))) / "merzostream-010k.patch"
out.write_bytes(patch)
subprocess.run(["git", "apply", "--check", str(out)], cwd=root, check=True)
subprocess.run(["git", "apply", str(out)], cwd=root, check=True)
print("0.1.0k PATCH PASS", PATCH_SHA, "xz", XZ_SHA, "parts", len(parts))
