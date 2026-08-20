from pathlib import Path
import os

root=Path(os.environ['SOURCE_ROOT'])
p=root/'src'/'MerzoOptimizer.Windows'/'Processes'/'WindowsProcessStabilityAnalyzer.cs'
s=p.read_text(encoding='utf-8-sig')
old='else if (doc.RootElement.ValueKind == JsonValueKind.Object && doc.RootElement.TryGetProperty("Execute", out var e)) AddExecutable(target, e.GetString());'
new='else if (doc.RootElement.ValueKind == JsonValueKind.Object && doc.RootElement.TryGetProperty("Execute", out var singleExecute)) AddExecutable(target, singleExecute.GetString());'
if s.count(old)!=1:
    raise SystemExit(f'R55 compile-fix anchor count={s.count(old)}')
p.write_text(s.replace(old,new,1),encoding='utf-8')
print('R55_COMPILE_FIX_PASS')
