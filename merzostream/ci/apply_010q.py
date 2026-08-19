import base64
import hashlib
import lzma
import os
import pathlib
import subprocess

repo = pathlib.Path(__file__).resolve().parents[2]
root = pathlib.Path(os.environ["MERZO_SRC"])
tmp = pathlib.Path(os.environ.get("RUNNER_TEMP", str(root.parent)))
ALPHABET = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

CHUNK_SHAS = [
    "ceaad4f136807fb61e327f056f13c5bfe014029f2d6bce4ef8cef8318042d7b6",
    "35c36c093e300171d04396d711ed6190ac0117a648df7589bfe067d00c1d5fd5",
    "06ad53860ec510e41da5a68e80bd165e4189df872e67bd77f183075e03cb9fc5",
    "d00f63b223ae68987239d3bdf181e3fc4e9308cf31d57634ea64bf22dab2b072",
    "53009dda83efc187b1677a45e2c6657ba17c5bad355196231a229441e493ddc5",
    "09ebd61fdabbf6cfbb518b0cab74b568f7fa962b30e55b4a6a0384240890c8e9",
    "9832612fa46201bd5dfde1b4f4dcc55f1b4242b0d45f6a5d9b2c5bf1bdb5a721",
    "c7b06559a78d2123d35f01f0f8985c760935ed4616f343c3d51341424e3c3bee",
    "ff764f9701fa55312225dd370c3dd9e79502e53b0511fc3046e3cbff2e281f06",
]
XZ_SHA = "7d63046278e7ab0400958fabca88c30de00ea325fa25329e91db62d1555d3d74"
RAW_SHA = "223079939f2c93d592ae12516b2d2403824b6d8bc3f07aa228686bbba7d03a11"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def recover_one_symbol(raw: bytes, expected: str, label: str) -> bytes:
    actual = sha(raw)
    if actual == expected:
        return raw
    print(f"{label} SHA differs: {actual}; searching one Base64 substitution")
    work = bytearray(raw)
    for pos, old in enumerate(raw):
        if old not in ALPHABET:
            continue
        for repl in ALPHABET:
            if repl == old:
                continue
            work[pos] = repl
            if sha(work) == expected:
                print(f"{label} EXACT REPAIR pos={pos} {chr(old)!r}->{chr(repl)!r} sha={expected}")
                return bytes(work)
        work[pos] = old
    raise SystemExit(f"{label} SHA mismatch and exact one-symbol repair failed: {actual} != {expected}")

parts = repo / "merzostream" / "ci" / "010q-b64"
encoded = []
for i, expected in enumerate(CHUNK_SHAS):
    p = parts / f"chunk{i:02d}.txt"
    if not p.exists():
        raise SystemExit(f"0.1.0q chunk missing: {p.name}")
    raw = recover_one_symbol(p.read_bytes(), expected, f"0.1.0q {p.name}")
    encoded.append(raw.decode("ascii").strip())

xz = base64.urlsafe_b64decode("".join(encoded))
actual_xz = sha(xz)
if actual_xz != XZ_SHA:
    raise SystemExit(f"0.1.0q XZ SHA mismatch: {actual_xz} != {XZ_SHA}")
patch = lzma.decompress(xz)
actual_raw = sha(patch)
if actual_raw != RAW_SHA:
    raise SystemExit(f"0.1.0q raw SHA mismatch: {actual_raw} != {RAW_SHA}")

patch_path = tmp / "merzostream-010q.patch"
patch_path.write_bytes(patch)
subprocess.run(["git", "apply", "--check", "--binary", str(patch_path)], cwd=root, check=True)
subprocess.run(["git", "apply", "--binary", str(patch_path)], cwd=root, check=True)
print("0.1.0q TEXT PATCH PASS", RAW_SHA, "xz", XZ_SHA, "chunks", len(CHUNK_SHAS))
print("0.1.0q CUMULATIVE APPLY PASS")
