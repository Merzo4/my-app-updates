from pathlib import Path
import base64, hashlib, io, json, lzma, os, tarfile
root=Path(os.environ["SOURCE_ROOT"]).resolve()
parts=sorted(Path(__file__).parent.glob("r46_payload.part*"))
if len(parts)!=7: raise SystemExit(f"R46 payload parts missing: {len(parts)}")
payload="".join(p.read_text(encoding="ascii").strip() for p in parts)
raw=lzma.decompress(base64.b64decode(payload,validate=True))
expected=json.loads('{"R46_SECURITY_LAYOUT_HARDENING.marker":"367e16843157b119c15217052b777ba4769e711033bf9dbad9bb3bbac2bd830c","data/release_notes.json":"3e78b0ec9919ee3bba0433188e93e0aaa6687744e7d5bd6520f26cda52ea4db5","src/MerzoOptimizer.App/App.xaml.cs":"2973916b7edb121459cb10bfc79302de0505a4d3d71d793f4a23823cc81b0dae","src/MerzoOptimizer.App/MainWindow.xaml":"9a0b02ff054d898ac36b3d99b79c9194ba866c89e81dc4a876e2a274c6736327","src/MerzoOptimizer.App/MerzoOptimizer.App.csproj":"d3b316b16b5c130aca8945e1a6b0fe54daeed42efe4863ee780e32d98a8caae0","src/MerzoOptimizer.App/ViewModels/MainWindowViewModel.cs":"08fa2aa4d544f5a044ed0a1af2a89d743a9d6d0133ac0876abc07e8aff1be422","src/MerzoOptimizer.Core/MerzoOptimizer.Core.csproj":"77ff71ea8c251f2072880d631a8adc685e867e36d7fb743f1b0be6e0b984a292","src/MerzoOptimizer.Core/Updates/UpdateModels.cs":"42dd66f3c7d0b57a1ffc22a512d9d68ae6003d08a0c0408a5f69a446a0206f43","src/MerzoOptimizer.ElevatedHelper/MerzoOptimizer.ElevatedHelper.csproj":"f06d677e33fbc611a0105d6fcb0c896efe6c6318752d2c38ee54d4f3d0476180","src/MerzoOptimizer.ElevatedHelper/Program.cs":"b66ba162a45578f0003c0daf5960e54f12182a74064584f8a2cc7a04b3172329","src/MerzoOptimizer.SelfTest/MerzoOptimizer.SelfTest.csproj":"172434968c4eb62bc7c46b20d75e7fbd68d7d9cb963c1370d9d907c31f9b9d86","src/MerzoOptimizer.Windows/Elevation/ElevatedOperationBroker.cs":"a6a2a1c2a716710d677947a3cf3d2d95e5872b4d3bf70a90334edbe56e46f79a","src/MerzoOptimizer.Windows/Elevation/ElevationAwareServices.cs":"42c2a5a8b3ae3c514aa3fdacf8459a8779189ce44fb45b8c09537c0d9bb21fd1","src/MerzoOptimizer.Windows/MerzoOptimizer.Windows.csproj":"c091be5842fe9047bc2697c8bffaeba2a818cff4986dd38e781105370a41617e","src/MerzoOptimizer.Windows/Updates/GitHubUpdateService.cs":"046f883dbbbcdac5a3ed1a674f7c2f87c36c07a0dfb2d9b6de73cd9fa566434a"}')
seen=set()
with tarfile.open(fileobj=io.BytesIO(raw),mode="r:") as t:
    for m in t.getmembers():
        if not m.isfile() or m.name not in expected: raise SystemExit(f"Unexpected R46 payload entry: {m.name}")
        target=(root/m.name).resolve()
        if root != target and root not in target.parents: raise SystemExit("Unsafe R46 payload path")
        data=t.extractfile(m).read()
        if hashlib.sha256(data).hexdigest()!=expected[m.name]: raise SystemExit(f"R46 payload hash mismatch: {m.name}")
        target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data); seen.add(m.name)
if seen!=set(expected): raise SystemExit("R46 payload is incomplete")
print(f"R46 security/layout hardening patch: OK ({len(seen)} files)")
