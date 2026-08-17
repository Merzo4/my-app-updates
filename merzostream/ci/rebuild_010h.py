import base64, hashlib, lzma, os, pathlib, subprocess, sys, tarfile

repo = pathlib.Path.cwd()
root = pathlib.Path(os.environ['MERZO_SRC'])
root.mkdir(parents=True, exist_ok=True)
ref = 'origin/merzostream-010g-r5-ci'

def rd_git(path):
    return subprocess.check_output(['git','show',f'{ref}:{path}'], text=True).replace('\n','').replace('\r','').strip()

subprocess.check_call(['git','fetch','origin','merzostream-010g-r5-ci:refs/remotes/origin/merzostream-010g-r5-ci'])
c0=rd_git('merzostream/ci/010g-r5-csharp8/chunk00.b64')
c1=rd_git('merzostream/ci/010g-r5-csharp8/chunk01.b64')
p1=rd_git('merzostream/ci/010g-r5-csharp/part01.b64')
p2=rd_git('merzostream/ci/010g-r5-csharp/part02-correct.b64')
p3=rd_git('merzostream/ci/010g-r5-csharp/part02.b64')
p4=rd_git('merzostream/ci/010g-r5-csharp/part04.b64')
p5=rd_git('merzostream/ci/010g-r5-csharp/part05.b64')
p6=rd_git('merzostream/ci/010g-r5-csharp/part06.b64')
text=c0+c1+p1[2000:]+p2+p3+p4+p5+p6
assert len(text)==93332, len(text)
raw=base64.b64decode(text, validate=True)
want='b80d662f290bd5cddcbf33847a9b7fd8abbd141e714a7708560c9032a6e4eb6f'
got=hashlib.sha256(raw).hexdigest()
assert got==want,(got,want)
tgz=pathlib.Path(os.environ['RUNNER_TEMP'])/'r5.tar.gz'
tgz.write_bytes(raw)
with tarfile.open(tgz,'r:gz') as t:
    t.extractall(root)
assert (root/'MerzoStream.NetHost.sln').exists()
print('R5 BASELINE SHA PASS',got)

base=repo/'merzostream/ci/010h-r5-overlay'
fix=repo/'merzostream/ci/010h-r5-overlay-fix'
expected=[
'9048a8c09fc1aaf78c9070d6b1ef46fc5be4b8e8f232b02fb7f8b5c50733bc40',
'6822d4b36cc7baf3ed4cbb77b3952e7fc43cf5a8b389b858a87f7ad783ceac5a',
'71720d704b82977a71ccd917efffbae0e7b58eff7392f61b4ef69a7b4baca372',
'3aaba00d7721164e8d5e94784dc865b5aa9e218501e364d585f535634666d78b',
'064d48a39f4f6b3c86a9b7ccd09a5421d7e3b52ae1b9df6d33cde56fbbc3c885',
'70a68992e2b7718ee217149129381fe53419a6bac71141357f423d1d29543f0b',
'b1acc1f156b345299807f450920698eb0c7cd2076b9700a387090af6fc7ccac9',
'35ddba3257c0666f8e2a5710983792bd781e029ac0d47edb24426b124e8c964d',
'd4da55f49897999ec3e0b2650d56374317c2629bbdb4ca81fc85af819d6f1c9e',
'aca0138882b57d0a472955be3dc7ef2ca7154e1dab6f256b74e386fc1fbd0b92',
'141ebd4a18dcc42176b44c3445ddfe9f749cc7b4fd1a86f21509212a92e0ba6c',
'80cebf1f2d9e4690f05e9df646802d54299a009ed13e083d7300e26f83f05192',
'28e819dc3b81c5df6b4feb76f463c874b9243104cbd7d95a23c858ad6d16298b',
'40a945677d03fb0cf40f2e56cd88195f51732c71d10e55be6bc211f265f80eb6']
parts=[]
for i in range(14):
    if i==8:
        s=''.join((fix/f'part08{x}.txt').read_text().strip() for x in 'abc')
    elif i==9:
        s=''.join((fix/f'part09{x}.txt').read_text().strip() for x in 'abc')
    else:
        s=(base/f'part{i:02d}.b64').read_text().replace('\n','').replace('\r','').strip()
    h=hashlib.sha256(s.encode()).hexdigest()
    assert h==expected[i],(i,len(s),h,expected[i])
    parts.append(s)
    print(f'OVERLAY PART {i:02d} PASS')
text=''.join(parts)
assert len(text)==202236,len(text)
text += '='*((4-len(text)%4)%4)
raw=base64.b64decode(text,validate=True)
want='8244cf194a7738527613c0a844149065db53b5c67953e702c227ede93fa96ecc'
got=hashlib.sha256(raw).hexdigest()
assert got==want,(got,want)
xz=pathlib.Path(os.environ['RUNNER_TEMP'])/'010h-r5-overlay.tar.xz'
xz.write_bytes(raw)
with lzma.open(xz,'rb') as xf:
    with tarfile.open(fileobj=xf,mode='r:') as tf:
        tf.extractall(root)
assert (root/'content/app_info.json').exists()
print('0.1.0h OVERLAY SHA PASS',got)

subprocess.check_call([sys.executable, str(repo/'merzostream/ci/restore_wrappers.py')])
print('PURE DOTNET WRAPPERS RESTORED')
