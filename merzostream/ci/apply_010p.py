import base64
import hashlib
import lzma
import os
import pathlib
import subprocess

RAW_SHA="aaf9102abda5cdec25eb8e70663e0dfd5d44891cfc3de4b99207739e6124eb15"
XZ_SHA="21d74b200a3d8e6ff98cf611da2c3e9b10f18db49d1726ef7af9792ee5c36aaa"
CHUNK_SHA=[
    "56c96146ba47af47607a08915281fe9ff901ac5390cfb30e5f77e98415e0c986",
    "07aab0ec7474605c92200e7223f2683b0badac6678901c4d2f7aa0c04975ac74",
    "d4a28c764ff7cc791f682c2424e3989515eb64483801606d694316afa38d213e",
    "d10153ea7e245ab209db15ae99444016c0412160856b72cf9e86578ef73931b6",
    "efce472661e1125debc3be45d8a084c9aed432e5f5b5fae5309b1e9680ff34af",
]
repo=pathlib.Path(__file__).resolve().parents[2]
parts=repo/"merzostream"/"ci"/"010p-b64"
encoded=[]
for i,expected in enumerate(CHUNK_SHA):
    p=parts/f"chunk{i:02d}.txt"
    if not p.exists(): raise SystemExit(f"0.1.0p chunk missing: {p.name}")
    raw=p.read_bytes(); actual=hashlib.sha256(raw).hexdigest()
    if actual!=expected: raise SystemExit(f"0.1.0p chunk SHA mismatch: {p.name} {actual}")
    encoded.append(raw.decode("ascii").strip())
xz=base64.urlsafe_b64decode("".join(encoded)); actual_xz=hashlib.sha256(xz).hexdigest()
if actual_xz!=XZ_SHA: raise SystemExit(f"0.1.0p xz SHA mismatch: {actual_xz}")
patch=lzma.decompress(xz); actual_raw=hashlib.sha256(patch).hexdigest()
if actual_raw!=RAW_SHA: raise SystemExit(f"0.1.0p raw patch SHA mismatch: {actual_raw}")
root=pathlib.Path(os.environ["MERZO_SRC"]); out=pathlib.Path(os.environ.get("RUNNER_TEMP",str(root.parent)))/"merzostream-010p.patch"; out.write_bytes(patch)
subprocess.run(["git","apply","--check","--binary",str(out)],cwd=root,check=True); subprocess.run(["git","apply","--binary",str(out)],cwd=root,check=True)
print("0.1.0p CUMULATIVE PATCH PASS",RAW_SHA,"xz",XZ_SHA,"chunks",len(CHUNK_SHA))
