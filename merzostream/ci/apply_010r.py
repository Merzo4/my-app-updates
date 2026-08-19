import base64, hashlib, lzma, os, pathlib, subprocess

root = pathlib.Path(os.environ['MERZO_SRC'])
tmp = pathlib.Path(os.environ.get('RUNNER_TEMP', str(root.parent)))
CHUNK_SHAS = [
    '606e10fdc2cdfe4b6b20385be19cf6b5b2cdec969406255df345657162b21053',
    '37017d459847bdcf36db2e8ea110ea33d8287306c0119da684d5661a14787e7e',
    '58f19611697aeae7a2a2ece3d0624433e9b7f7de75cd596f45f68a70819f7068',
]
XZ_SHA = '017999221d52c582fc667ac3f9adb4253cde7fbe875d7744aa6bfb085a95a1cc'
RAW_SHA = '26ad5886e14eb164f7482fea607eee937b68712cdb0b69ca72e3a5fc657a9b45'

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

parts_dir = pathlib.Path(__file__).resolve().parent / '010r-b64'
encoded = []
for i, expected in enumerate(CHUNK_SHAS):
    p = parts_dir / f'chunk{i:02d}.txt'
    raw = p.read_bytes().strip()
    actual = sha(raw)
    if actual != expected:
        raise SystemExit(f'0.1.0r {p.name} SHA mismatch: {actual} != {expected}')
    encoded.append(raw.decode('ascii'))

xz = base64.urlsafe_b64decode(''.join(encoded))
if sha(xz) != XZ_SHA:
    raise SystemExit(f'0.1.0r XZ SHA mismatch: {sha(xz)} != {XZ_SHA}')
patch = lzma.decompress(xz)
if sha(patch) != RAW_SHA:
    raise SystemExit(f'0.1.0r raw SHA mismatch: {sha(patch)} != {RAW_SHA}')

patch_path = tmp / 'merzostream-010r.patch'
patch_path.write_bytes(patch)
subprocess.run(['git', 'apply', '--check', '--binary', str(patch_path)], cwd=root, check=True)
subprocess.run(['git', 'apply', '--binary', str(patch_path)], cwd=root, check=True)
print('0.1.0r RECOVERY PATCH PASS', RAW_SHA, 'xz', XZ_SHA, 'chunks', len(CHUNK_SHAS))
