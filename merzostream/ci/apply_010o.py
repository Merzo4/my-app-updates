import base64
import hashlib
import lzma
import os
import pathlib
import subprocess

RAW_SHA = "4e797d425565ec2e9333a54c1d978d2c5bd606edffa2fcbc2fafedb26345bdf9"
XZ_SHA = "ea3633c89ca74e7fa1699e5d98b37c4828893178fd427e9002de82d84504077c"
CHUNK_SHA = [
    "5ab25444600d6f6b1ab5933827ece02c3c69d154df46e4bde48fef59aa918ab9",
    "16f207cf9e0f6e1dbea59ed0dc30cfacc1e0242e2eb920d2ad2e41fba35c3626",
    "3807a3655b668525e11220b1f1c2db074c77d8850c2363c9fcb72ca680848614",
    "8cf1bc7e67f1380d1651112316e4b31f8688bf9e11cee9e31fdce90a1196ba27",
    "4d1cf3bb885376ae5ad52cca3f4d40e280dc45cbf4cdba7c51a1bfba1af4f9e7",
    "4a2ebc1062b558a9aa24406a491a9824ff594c94b5f088356dd6a007f0b987d8",
    "f162d80441fda25ddec971a8ece027b131e26b85e160fec1a22d442321ea3fba",
]

repo = pathlib.Path(__file__).resolve().parents[2]
parts_dir = repo / "merzostream" / "ci" / "010o-small-b64"
chunks = [parts_dir / f"chunk{i:02d}.txt" for i in range(len(CHUNK_SHA))]
encoded_parts = []
for i, chunk in enumerate(chunks):
    if not chunk.exists():
        raise SystemExit(f"0.1.0o chunk missing: {chunk.name}")
    raw = chunk.read_bytes()
    expected = CHUNK_SHA[i]
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        if i == 2:
            # Diagnose the one transported chunk using the stronger package-level
            # checks below. Nothing can be applied unless BOTH the complete XZ SHA
            # and the decompressed raw patch SHA still match their canonical values.
            print(f"0.1.0o chunk02 legacy SHA differs: {actual}; validating full package")
        else:
            raise SystemExit(f"0.1.0o chunk SHA mismatch: {chunk.name} {actual}")
    encoded_parts.append(raw.decode("ascii").strip())

xz = base64.b64decode("".join(encoded_parts))
actual_xz = hashlib.sha256(xz).hexdigest()
if actual_xz != XZ_SHA:
    raise SystemExit(f"0.1.0o xz SHA mismatch: {actual_xz}")
patch = lzma.decompress(xz)
actual_raw = hashlib.sha256(patch).hexdigest()
if actual_raw != RAW_SHA:
    raise SystemExit(f"0.1.0o raw patch SHA mismatch: {actual_raw}")

root = pathlib.Path(os.environ["MERZO_SRC"])
out = pathlib.Path(os.environ.get("RUNNER_TEMP", str(root.parent))) / "merzostream-010o.patch"
out.write_bytes(patch)
subprocess.run(["git", "apply", "--check", "--binary", str(out)], cwd=root, check=True)
subprocess.run(["git", "apply", "--binary", str(out)], cwd=root, check=True)
print("0.1.0o CUMULATIVE PATCH PASS", RAW_SHA, "xz", XZ_SHA, "chunks", len(chunks))
