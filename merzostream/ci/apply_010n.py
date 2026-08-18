import base64
import hashlib
import lzma
import os
import pathlib
import subprocess

PATCH_SHA = "63fc4bfbade986c51e07cb0cd2703b526125f622167ac254532ad48a0d65507b"
XZ_SHA = "120ad1b2fd1100a8d231e5b0e9ae74ff72e9249c0a737faf10c4fd7d08bc8803"
PART_SHA = [
    "8c083b646764cd5472231f9f863c7378a1e5cc180483e20459a756e45c53bfd8",
    "828cc351ecbb5849122539beb9607814dbfad3155c9c469c65c343f7ee0b56b6",
    "f32ec22c5a4dc75a68a54f9bf422c4e509b70cb2fa33c3cff08062f0c15e9dab",
    "05828d89d1919e974fc5a754c26813d7538c8c908e8dd0212b9153b981980431",
]

repo = pathlib.Path(__file__).resolve().parents[2]
parts_dir = repo / "merzostream" / "ci" / "010n-patch"
parts = [parts_dir / f"part{i:02d}.b64" for i in range(len(PART_SHA))]
for i, part in enumerate(parts):
    if not part.exists():
        raise SystemExit(f"0.1.0n patch part missing: {part.name}")
    actual = hashlib.sha256(part.read_bytes()).hexdigest()
    if actual != PART_SHA[i]:
        raise SystemExit(f"0.1.0n patch part SHA mismatch: {part.name} {actual}")
encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
xz = base64.b64decode(encoded)
if hashlib.sha256(xz).hexdigest() != XZ_SHA:
    raise SystemExit("0.1.0n xz SHA mismatch")
patch = lzma.decompress(xz)
if hashlib.sha256(patch).hexdigest() != PATCH_SHA:
    raise SystemExit("0.1.0n patch SHA mismatch")
root = pathlib.Path(os.environ["MERZO_SRC"])
out = pathlib.Path(os.environ.get("RUNNER_TEMP", str(root.parent))) / "merzostream-010n.patch"
out.write_bytes(patch)
subprocess.run(["git", "apply", "--check", "--ignore-space-change", str(out)], cwd=root, check=True)
subprocess.run(["git", "apply", "--ignore-space-change", str(out)], cwd=root, check=True)

# C# compiler fix: foreach iteration variables in the chained if/else subscription block
# must have distinct names because the statements share the enclosing scope.
sb = root / "src" / "MerzoStream.Foundation" / "Services" / "StreamerBotService.cs"
sb_text = sb.read_text(encoding="utf-8-sig")
fixes = [
    ('foreach (var name in new[] { "ChatMessage", "PresentViewers", "ViewerCountUpdate" }) if (names.Contains(name)) wanted.Add(name);', 'foreach (var twitchEvent in new[] { "ChatMessage", "PresentViewers", "ViewerCountUpdate" }) if (names.Contains(twitchEvent)) wanted.Add(twitchEvent);'),
    ('foreach (var name in new[] { "Message", "PresentViewers", "StatisticsUpdated" }) if (names.Contains(name)) wanted.Add(name);', 'foreach (var youtubeEvent in new[] { "Message", "PresentViewers", "StatisticsUpdated" }) if (names.Contains(youtubeEvent)) wanted.Add(youtubeEvent);'),
    ('foreach (var name in new[] { "ChatMessage", "PresentViewers", "ViewerCountUpdate" }) if (names.Contains(name)) wanted.Add(name);', 'foreach (var kickEvent in new[] { "ChatMessage", "PresentViewers", "ViewerCountUpdate" }) if (names.Contains(kickEvent)) wanted.Add(kickEvent);'),
    ('foreach (var name in names)\n                if (AlertEventTokens.Any(token => name.Contains(token, StringComparison.OrdinalIgnoreCase))) wanted.Add(name);', 'foreach (var eventName in names)\n                if (AlertEventTokens.Any(token => eventName.Contains(token, StringComparison.OrdinalIgnoreCase))) wanted.Add(eventName);'),
]
for old, new in fixes:
    if old not in sb_text:
        raise SystemExit(f"0.1.0n Streamer.bot compiler marker missing: {old[:50]}")
    sb_text = sb_text.replace(old, new, 1)
sb.write_text(sb_text, encoding="utf-8", newline="\n")

print("0.1.0n PATCH PASS", PATCH_SHA, "xz", XZ_SHA, "parts", len(parts), "compiler-fix=aligned")
