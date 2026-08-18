from pathlib import Path
import os

root = Path(os.environ['SOURCE_ROOT'])
projects = [
    root/'src'/'MerzoOptimizer.App'/'MerzoOptimizer.App.csproj',
    root/'src'/'MerzoOptimizer.Core'/'MerzoOptimizer.Core.csproj',
    root/'src'/'MerzoOptimizer.Windows'/'MerzoOptimizer.Windows.csproj',
    root/'src'/'MerzoOptimizer.ElevatedHelper'/'MerzoOptimizer.ElevatedHelper.csproj',
]
replacements = [
    ('<AssemblyVersion>0.1.52.0</AssemblyVersion>', '<AssemblyVersion>0.1.53.0</AssemblyVersion>'),
    ('<FileVersion>0.1.52.0</FileVersion>', '<FileVersion>0.1.53.0</FileVersion>'),
    ('<InformationalVersion>0.1.52</InformationalVersion>', '<InformationalVersion>0.1.53</InformationalVersion>'),
]
for p in projects:
    text = p.read_text(encoding='utf-8-sig')
    for old, new in replacements:
        if text.count(old) != 1:
            raise SystemExit(f'R53 version finalize anchor mismatch: {p.name}: {old}')
        text = text.replace(old, new, 1)
    p.write_text(text, encoding='utf-8')
(root/'R53_VERSION_FINALIZE.marker').write_text('0.1.53\n', encoding='utf-8')
print('R53 exact project version finalize: OK')
