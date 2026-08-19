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


def recover_one_symbol(raw: bytes, expected: str, label: str) -> bytes:
    actual = hashlib.sha256(raw).hexdigest()
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
            if hashlib.sha256(work).hexdigest() == expected:
                print(f"{label} EXACT REPAIR pos={pos} {chr(old)!r}->{chr(repl)!r} sha={expected}")
                return bytes(work)
        work[pos] = old
    raise SystemExit(f"{label} SHA mismatch and one-substitution repair failed: {actual} != {expected}")


def load_payload(folder, chunk_shas, xz_sha, raw_sha, label):
    parts = repo / "merzostream" / "ci" / folder
    encoded = []
    for i, expected in enumerate(chunk_shas):
        p = parts / f"chunk{i:02d}.txt"
        if not p.exists():
            raise SystemExit(f"{label} chunk missing: {p.name}")
        raw = recover_one_symbol(p.read_bytes(), expected, f"{label} {p.name}")
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
        "5d60127eb45f941814c20c0d2af96229b73357b5c55abc60f7a98b4521b12858",
        "3b71e1114a152557003c8bf4082fbd8383efd8c3e5444c017d3c6c1bfa0682ab",
        "5a627051e2813220f753b57ad8fe5d18f9cd81afd113522fae55e34c8c328def",
        "6994a33828d312a6f4dff9bf2d0679868ae2e0369bed2177e191ff8143ca5c88",
    ],
    "228b39335117327606216e7c3620043169e246273b2d9c4310c12d18fc63b1ba",
    "03c828620e2749f86863af95db9ebc64a0bd059d160cc05d68551fe105662a1f",
    "0.1.0p FINAL",
)
apply_patch(final_patch, "merzostream-010p-final.patch", "0.1.0p FINAL")
print("0.1.0p TWO-STAGE CUMULATIVE PATCH PASS")
