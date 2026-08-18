from pathlib import Path
import os, re

root = Path(os.environ['SOURCE_ROOT'])
projects = [
    root/'src'/'MerzoOptimizer.App'/'MerzoOptimizer.App.csproj',
    root/'src'/'MerzoOptimizer.Core'/'MerzoOptimizer.Core.csproj',
    root/'src'/'MerzoOptimizer.Windows'/'MerzoOptimizer.Windows.csproj',
    root/'src'/'MerzoOptimizer.ElevatedHelper'/'MerzoOptimizer.ElevatedHelper.csproj',
]
patterns = [
    (r'(<AssemblyVersion>\s*)(0\.1\.(?:51|52)\.0)(\s*</AssemblyVersion>)', '0.1.53.0', 'AssemblyVersion'),
    (r'(<FileVersion>\s*)(0\.1\.(?:51|52)\.0)(\s*</FileVersion>)', '0.1.53.0', 'FileVersion'),
    (r'(<InformationalVersion>\s*)(0\.1\.(?:51|52))(\s*</InformationalVersion>)', '0.1.53', 'InformationalVersion'),
]
for p in projects:
    text = p.read_text(encoding='utf-8-sig')
    for pattern, target, label in patterns:
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1:
            found = re.findall(rf'<{label}>\s*([^<]+)\s*</{label}>', text)
            raise SystemExit(f'R53 version finalize {label} mismatch: {p.name}: found={found}')
        text = re.sub(pattern, lambda m: m.group(1)+target+m.group(3), text, count=1)
    p.write_text(text, encoding='utf-8')
(root/'R53_VERSION_FINALIZE.marker').write_text('0.1.53\n', encoding='utf-8')
print('R53 exact project version finalize: OK')
