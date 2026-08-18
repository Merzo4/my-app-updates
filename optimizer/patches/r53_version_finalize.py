from pathlib import Path
import os

root = Path(os.environ['SOURCE_ROOT'])
projects = [
    root/'src'/'MerzoOptimizer.App'/'MerzoOptimizer.App.csproj',
    root/'src'/'MerzoOptimizer.Core'/'MerzoOptimizer.Core.csproj',
    root/'src'/'MerzoOptimizer.Windows'/'MerzoOptimizer.Windows.csproj',
    root/'src'/'MerzoOptimizer.ElevatedHelper'/'MerzoOptimizer.ElevatedHelper.csproj',
]
old = '<AssemblyVersion>0.1.52.0</AssemblyVersion><FileVersion>0.1.52.0</FileVersion><InformationalVersion>0.1.52</InformationalVersion>'
new = '<AssemblyVersion>0.1.53.0</AssemblyVersion><FileVersion>0.1.53.0</FileVersion><InformationalVersion>0.1.53</InformationalVersion>'
for p in projects:
    text = p.read_text(encoding='utf-8-sig')
    if text.count(old) != 1:
        raise SystemExit(f'R53 version finalize anchor mismatch: {p.name}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
(root/'R53_VERSION_FINALIZE.marker').write_text('0.1.53\n', encoding='utf-8')
print('R53 exact project version finalize: OK')
