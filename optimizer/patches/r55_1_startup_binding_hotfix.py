from pathlib import Path
import os,re

root=Path(os.environ['SOURCE_ROOT'])
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8')
def once(text,old,new,label):
    c=text.count(old)
    if c!=1: raise SystemExit(f'R55.1 anchor {label} count={c}')
    return text.replace(old,new,1)

# Field regression: WPF ProgressBar.Value defaults to TwoWay. The VM property
# has a private setter, so R55 crashed while constructing the main window.
xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xp)
x=once(x,'Value="{Binding ProcessStabilityProgress}"','Value="{Binding ProcessStabilityProgress, Mode=OneWay}"','progress-oneway')
if 'Value="{Binding ProcessStabilityProgress}"' in x:
    raise SystemExit('R55.1 unqualified ProcessStabilityProgress binding remains')

# Hotfix identity is explicit so a broken 0.1.55 can never be confused with it.
x=once(x,'Production R55 · 0.1.55','Production R55.1 · 0.1.55.1','visible-version')
x=once(x,'Text="R55"','Text="R55.1"','sidebar-version')
x=once(x,'Production 0.1.55 · R55 PROCESS STABILITY','Production 0.1.55.1 · R55.1 STARTUP BINDING HOTFIX','window-title')
write(xp,x)

# Version every production project as a real four-component hotfix.
projects=sorted((root/'src').glob('MerzoOptimizer.*/*.csproj'))
if len(projects)<5: raise SystemExit('R55.1 project set missing')
for cp in projects:
    t=read(cp)
    expected={'Version':'0.1.55.1','VersionPrefix':'0.1.55.1','AssemblyVersion':'0.1.55.1','FileVersion':'0.1.55.1','InformationalVersion':'0.1.55.1'}
    for label,value in expected.items():
        pat=rf'(<{label}>\s*)([^<]+?)(\s*</{label}>)'
        if re.search(pat,t):
            t=re.sub(pat,lambda m:m.group(1)+value+m.group(3),t)
    for required in ('AssemblyVersion','FileVersion','InformationalVersion'):
        if f'<{required}>' not in t: raise SystemExit(f'R55.1 missing {required}: {cp.name}')
    write(cp,t)

iss=root/'installer'/'MerzoWindowsOptimizer.iss'
i=read(iss)
# r55_version_finalize has already normalized the installer to 0.1.55.
if '0.1.55' not in i: raise SystemExit('R55.1 installer 0.1.55 anchor missing')
i=i.replace('0.1.55','0.1.55.1')
write(iss,i)

notes=root/'dist'/'R53_RELEASE_NOTES.md'
if notes.exists():
    n=read(notes)
    add='''\n\n## 0.1.55.1 — Startup Binding Hotfix\n- Исправлен критический сбой запуска R55: ProgressBar больше не пытается писать обратно в read-only ProcessStabilityProgress.\n- Для ProcessStabilityProgress принудительно используется OneWay binding.\n- Усилен release gate: проверяется реальное главное окно приложения и отсутствие нового startup-crash лога.\n- GAME, OneDrive и правила оптимизации не менялись.\n'''
    if '## 0.1.55.1 — Startup Binding Hotfix' not in n: n+=add
    write(notes,n)

(root/'R55_1_STARTUP_BINDING_HOTFIX.marker').write_text('0.1.55.1 / OneWay ProcessStabilityProgress / strong startup gate\n',encoding='utf-8')
print('R55_1_STARTUP_BINDING_HOTFIX_PASS')
