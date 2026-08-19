import base64
import hashlib
import lzma
import os
import pathlib
import subprocess

repo = pathlib.Path(__file__).resolve().parents[2]
root = pathlib.Path(os.environ["MERZO_SRC"])
tmp = pathlib.Path(os.environ.get("RUNNER_TEMP", str(root.parent)))


def load_payload(folder, chunk_shas, xz_sha, raw_sha, label):
    parts = repo / "merzostream" / "ci" / folder
    encoded = []
    for i, expected in enumerate(chunk_shas):
        p = parts / f"chunk{i:02d}.txt"
        if not p.exists():
            raise SystemExit(f"{label} chunk missing: {p.name}")
        raw = p.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != expected:
            raise SystemExit(f"{label} chunk SHA mismatch: {p.name} {actual} != {expected}")
        encoded.append(raw.decode("ascii").strip())
    xz = base64.urlsafe_b64decode("".join(encoded))
    actual_xz = hashlib.sha256(xz).hexdigest()
    if actual_xz != xz_sha:
        raise SystemExit(f"{label} XZ SHA mismatch: {actual_xz} != {xz_sha}")
    patch = lzma.decompress(xz)
    actual_raw = hashlib.sha256(patch).hexdigest()
    if actual_raw != raw_sha:
        raise SystemExit(f"{label} raw SHA mismatch: {actual_raw} != {raw_sha}")
    print(label, "PAYLOAD PASS", raw_sha, "xz", xz_sha, "chunks", len(chunk_shas))
    return patch


def apply_patch(patch, filename, label):
    out = tmp / filename
    out.write_bytes(patch)
    subprocess.run(["git", "apply", "--check", "--binary", str(out)], cwd=root, check=True)
    subprocess.run(["git", "apply", "--binary", str(out)], cwd=root, check=True)
    print(label, "APPLY PASS")


base_patch = load_payload(
    "010p-b64",
    [
        "56c96146ba47af47607a08915281fe9ff901ac5390cfb30e5f77e98415e0c986",
        "07aab0ec7474605c92200e7223f2683b0badac6678901c4d2f7aa0c04975ac74",
        "d4a28c764ff7cc791f682c2424e3989515eb64483801606d694316afa38d213e",
        "d10153ea7e245ab209db15ae99444016c0412160856b72cf9e86578ef73931b6",
        "efce472661e1125debc3be45d8a084c9aed432e5f5b5fae5309b1e9680ff34af",
    ],
    "21d74b200a3d8e6ff98cf611da2c3e9b10f18db49d1726ef7af9792ee5c36aaa",
    "aaf9102abda5cdec25eb8e70663e0dfd5d44891cfc3de4b99207739e6124eb15",
    "0.1.0p BASE",
)
apply_patch(base_patch, "merzostream-010p-base.patch", "0.1.0p BASE")

final_patch = load_payload(
    "010p-final4k",
    [
        "adc87a74d2237f9b4f4706ab3bbb2b91f9d34e20f718afe25a85740760c31d9b",
        "24a126261d0e4e439989e14606f775f5de4377525c3fcadab619a294c83b70c3",
        "fbd166f51f5ad2380141cbbead486ba33845682e496fc7e955c13cc4720c610c",
        "d04b916df423ac2db0f410266ad878bcfdbf8bb0276f86dca2e2186508d9ebc5",
    ],
    "8110a63f2cd821927ab3baab90917ce77190364ae50ee430a70f9f1fb7cd05bc",
    "af502e9380053471a48b8c5fcaee06ec5f89aa82229b4d618b57ff7a2fa8dd14",
    "0.1.0p FINAL",
)
apply_patch(final_patch, "merzostream-010p-final.patch", "0.1.0p FINAL")
print("0.1.0p TWO-STAGE CUMULATIVE PATCH PASS")
