from pathlib import Path
import os, re

root = Path(os.environ['SOURCE_ROOT'])
projects = [
    root/'src'/'MerzoOptimizer.App'/'MerzoOptimizer.App.csproj',
    root/'src'/'MerzoOptimizer.Core'/'MerzoOptimizer.Core.csproj',
    root/'src'/'MerzoOptimizer.Windows'/'MerzoOptimizer.Windows.csproj',
    root/'src'/'MerzoOptimizer.ElevatedHelper'/'MerzoOptimizer.ElevatedHelper.csproj',
]
fields = [
    ('AssemblyVersion', {'0.1.51.0','0.1.52.0'}, '0.1.53.0'),
    ('FileVersion', {'0.1.51.0','0.1.52.0'}, '0.1.53.0'),
    ('InformationalVersion', {'0.1.51','0.1.52'}, '0.1.53'),
]
for p in projects:
    text = p.read_text(encoding='utf-8-sig')
    for label, allowed, target in fields:
        pattern = rf'(<{label}>\s*)([^<]+?)(\s*</{label}>)'
        matches = list(re.finditer(pattern, text))
        if not matches:
            raise SystemExit(f'R53 version finalize missing {label}: {p.name}')
        values = {m.group(2).strip() for m in matches}
        if not values <= allowed:
            raise SystemExit(f'R53 version finalize unknown {label}: {p.name}: found={sorted(values)}')
        text = re.sub(pattern, lambda m: m.group(1)+target+m.group(3), text)
    p.write_text(text, encoding='utf-8')
(root/'R53_VERSION_FINALIZE.marker').write_text('0.1.53\n', encoding='utf-8')
print('R53 exact project version finalize: OK')
