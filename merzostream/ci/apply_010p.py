import base64
import hashlib
import lzma
import os
import pathlib
import subprocess

RAW_SHA="e71b8a71b15cfd74c1813123bf0d2594f6a4b0b26d22758aadb7317523a8e3ea"
XZ_SHA="e9b7593ff43c4b2f9058ebadb944301ca7d67a985a1c09dc8e1b179e4729ee35"
CHUNK_SHA=[
    "8625aa715465c35c6af07db878c41d23dbb3609abfe5c1e1c436aaec289e8754",
    "a1319ae42f5e7430e36ce535698660402dc45d1ff57d4ecabf14784ace402caf",
    "a48ad994aad560c35d706b3b9a3fa3bf448f1d3b108bddc68ca3a7bda6431e8f",
    "b32eab18a63deda574c32ee069752e48208bfe06f520071a14ca13f3e2645be6",
]
ALPHABET=b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

def repair_one_substitution(raw: bytes, expected: str, name: str) -> bytes:
    actual=hashlib.sha256(raw).hexdigest()
    if actual==expected:
        return raw
    print(f"0.1.0p {name} SHA differs: {actual}; searching one Base64 substitution")
    buf=bytearray(raw)
    for pos,old in enumerate(buf):
        if old not in ALPHABET:
            continue
        for new in ALPHABET:
            if new==old:
                continue
            buf[pos]=new
            if hashlib.sha256(buf).hexdigest()==expected:
                print(f"0.1.0p {name} EXACT REPAIR pos={pos} {chr(old)!r}->{chr(new)!r} sha={expected}")
                return bytes(buf)
        buf[pos]=old
    raise SystemExit(f"0.1.0p full chunk SHA mismatch and one-substitution repair failed: {name} {actual} len={len(raw)}")

repo=pathlib.Path(__file__).resolve().parents[2]
parts=repo/"merzostream"/"ci"/"010p-full-b64-r2"
encoded=[]
for i,expected in enumerate(CHUNK_SHA):
    p=parts/f"chunk{i:02d}.txt"
    if not p.exists(): raise SystemExit(f"0.1.0p full chunk missing: {p.name}")
    raw=repair_one_substitution(p.read_bytes(),expected,p.name)
    encoded.append(raw.decode("ascii").strip())
xz=base64.urlsafe_b64decode("".join(encoded)); actual_xz=hashlib.sha256(xz).hexdigest()
if actual_xz!=XZ_SHA: raise SystemExit(f"0.1.0p xz SHA mismatch: {actual_xz}")
patch=lzma.decompress(xz); actual_raw=hashlib.sha256(patch).hexdigest()
if actual_raw!=RAW_SHA: raise SystemExit(f"0.1.0p raw patch SHA mismatch: {actual_raw}")
root=pathlib.Path(os.environ["MERZO_SRC"]); out=pathlib.Path(os.environ.get("RUNNER_TEMP",str(root.parent)))/"merzostream-010p-full-r2.patch"; out.write_bytes(patch)
subprocess.run(["git","apply","--check","--binary",str(out)],cwd=root,check=True)
subprocess.run(["git","apply","--binary",str(out)],cwd=root,check=True)
print("0.1.0p FULL CUMULATIVE PATCH PASS",RAW_SHA,"xz",XZ_SHA,"chunks",len(CHUNK_SHA))
