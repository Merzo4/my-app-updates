from pathlib import Path
import os

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# Production scripts pass through PowerShell generated-script layers. Keep the
# public process targets ASCII so the UI and hard gates cannot be corrupted by
# a runner/code-page conversion of the en dash.
files=[
    root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml',
    root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs',
]
changed=0
for p in files:
    s=read(p)
    n=s.replace('80–100','80-100').replace('60–80','60-80')
    if n!=s:
        changed+=1
        write(p,n)

if changed<2:
    raise SystemExit(f'R53 ASCII target normalization expected 2 generated files, changed={changed}')

x=read(files[0]);v=read(files[1])
for token in ('80-100','60-80'):
    if token not in x or token not in v:
        raise SystemExit(f'R53 ASCII target missing after normalization: {token}')
for bad in ('80–100','60–80'):
    if bad in x or bad in v:
        raise SystemExit(f'R53 Unicode target remained after normalization: {bad}')

(root/'R53_ASCII_TARGETS.marker').write_text('80-100 / 60-80 encoding-safe UI\n',encoding='utf-8')
print('R53 ASCII process targets: OK')
