from pathlib import Path
import os

root = Path(os.environ['SOURCE_ROOT'])
needles = (
    'ADVANCED/EXPERT',
    'SafetyCheckResult',
    'R20',
    'Advanced',
    'Expert',
)

print('R53_GAME_APPLY_DIAG_BEGIN')
for p in sorted((root / 'src').rglob('*.cs')):
    try:
        lines = p.read_text(encoding='utf-8-sig').splitlines()
    except Exception:
        continue
    hits = [i for i, line in enumerate(lines) if any(n in line for n in needles)]
    if not hits:
        continue
    print('FILE=' + p.relative_to(root).as_posix())
    emitted = set()
    for i in hits:
        for j in range(max(0, i - 5), min(len(lines), i + 7)):
            if j in emitted:
                continue
            emitted.add(j)
            safe = lines[j].encode('ascii', 'backslashreplace').decode('ascii')
            print(f'{j+1:04d}: {safe}')

xaml = root / 'src' / 'MerzoOptimizer.App' / 'MainWindow.xaml'
if xaml.exists():
    print('R53_STALE_BADGE_DIAG_BEGIN')
    for i, line in enumerate(xaml.read_text(encoding='utf-8-sig').splitlines(), 1):
        if 'R52' in line or 'R53' in line:
            safe = line.encode('ascii', 'backslashreplace').decode('ascii')
            print(f'XAML {i:04d}: {safe}')
    print('R53_STALE_BADGE_DIAG_END')
print('R53_GAME_APPLY_DIAG_END')
