from pathlib import Path
import os, re

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# Production scripts pass through generated PowerShell/script layers. Normalize
# every known dash variant and the inherited R52 GAME target to ASCII so public
# UI copy and hard gates cannot be broken by runner/code-page conversion.
files=[
    root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml',
    root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs',
]

def normalize(s):
    # Direct expected forms first.
    s=s.replace('80–100','80-100').replace('60–80','60-80')
    s=s.replace('90–120','80-100').replace('90-120','80-100')
    # Be defensive against dash substitutions produced by generated-script layers.
    s=re.sub(r'80\s*[‐‑‒–—−]\s*100','80-100',s)
    s=re.sub(r'60\s*[‐‑‒–—−]\s*80','60-80',s)
    s=re.sub(r'90\s*[‐‑‒–—−]\s*120','80-100',s)
    return s

for p in files:
    s=read(p)
    n=normalize(s)
    if n!=s:
        write(p,n)

x=read(files[0]);v=read(files[1])

# MainWindow must advertise both public targets. The ViewModel must at least
# contain the GAME target and EXTREME target used by processTargetText/reporting.
for token in ('80-100','60-80'):
    if token not in x:
        raise SystemExit(f'R53 ASCII target missing in UI after normalization: {token}')
    if token not in v:
        raise SystemExit(f'R53 ASCII target missing in ViewModel after normalization: {token}')

for bad in ('80–100','60–80','90–120'):
    if bad in x or bad in v:
        raise SystemExit(f'R53 Unicode/legacy target remained after normalization: {bad}')

(root/'R53_ASCII_TARGETS.marker').write_text('80-100 / 60-80 encoding-safe UI and ViewModel\n',encoding='utf-8')
print('R53 ASCII process targets: OK')
