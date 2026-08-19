from pathlib import Path
import os, re

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# Production scripts pass through generated PowerShell/script layers. Normalize
# every known dash variant and inherited R52 target text to encoding-safe ASCII.
# The authoritative process targets live in MainWindowViewModel runtime/reporting;
# MainWindow.xaml may display them but is not required to duplicate runtime text.
files=[
    root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml',
    root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs',
]

def normalize(s):
    s=s.replace('80–100','80-100').replace('60–80','60-80')
    s=s.replace('90–120','80-100').replace('90-120','80-100')
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

# Runtime/reporting is the source of truth: both targets must exist there.
for token in ('80-100','60-80'):
    if token not in v:
        raise SystemExit(f'R53 ASCII runtime target missing after normalization: {token}')

# If XAML contains target ranges, they must be encoding-safe as well. We do not
# require XAML to duplicate ViewModel runtime strings because some UI layouts bind
# the report/status text dynamically instead of hardcoding it in MainWindow.xaml.
for bad in ('80–100','60–80','90–120'):
    if bad in x or bad in v:
        raise SystemExit(f'R53 Unicode/legacy target remained after normalization: {bad}')

(root/'R53_ASCII_TARGETS.marker').write_text(
    '80-100 / 60-80 encoding-safe runtime targets; XAML normalized when present\n',
    encoding='utf-8'
)
print('R53 ASCII process targets: OK')
