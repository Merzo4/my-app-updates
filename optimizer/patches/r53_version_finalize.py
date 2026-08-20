from pathlib import Path
import os, re

root = Path(os.environ['SOURCE_ROOT'])
projects = sorted((root/'src').glob('MerzoOptimizer.*/*.csproj'))
if len(projects) < 5:
    raise SystemExit(f'R53 HF1 version finalize expected >=5 projects, found {len(projects)}')
fields = [
    ('AssemblyVersion', {'0.1.51.0','0.1.52.0','0.1.53.0'}, '0.1.53.1'),
    ('FileVersion', {'0.1.51.0','0.1.52.0','0.1.53.0'}, '0.1.53.1'),
    ('InformationalVersion', {'0.1.51','0.1.52','0.1.53'}, '0.1.53.1'),
]
for p in projects:
    text = p.read_text(encoding='utf-8-sig')
    for label, allowed, target in fields:
        pattern = rf'(<{label}>\s*)([^<]+?)(\s*</{label}>)'
        matches = list(re.finditer(pattern, text))
        if not matches:
            raise SystemExit(f'R53 HF1 version finalize missing {label}: {p.name}')
        values = {m.group(2).strip() for m in matches}
        if not values <= allowed:
            raise SystemExit(f'R53 HF1 version finalize unknown {label}: {p.name}: found={sorted(values)}')
        text = re.sub(pattern, lambda m: m.group(1)+target+m.group(3), text)
    p.write_text(text, encoding='utf-8')
(root/'R53_VERSION_FINALIZE.marker').write_text('0.1.53.1\n', encoding='utf-8')
print(f'R53 HF1 exact project version finalize: OK projects={len(projects)} version=0.1.53.1')
