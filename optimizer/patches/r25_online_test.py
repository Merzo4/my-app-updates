from pathlib import Path
import os
root=Path(os.environ['SOURCE_ROOT'])
xaml=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=xaml.read_text(encoding='utf-8-sig')
x=x.replace('Production 0.1.24','Production 0.1.25 · ONLINE UPDATE TEST')
x=x.replace('Production R24 · Online Update Ready','Production R25 · ONLINE UPDATE TEST ✓')
# Make successful online upgrade visually unmistakable even if one of the older title strings differs.
if 'ONLINE UPDATE TEST' not in x:
    x=x.replace('Merzo Windows Optimizer', 'Merzo Windows Optimizer · ONLINE UPDATE TEST R25', 1)
xaml.write_text(x,encoding='utf-8')
if 'ONLINE UPDATE TEST' not in xaml.read_text(encoding='utf-8'):
    raise SystemExit('R25 visual marker missing')
print('R25 ONLINE UPDATE TEST marker: OK')
