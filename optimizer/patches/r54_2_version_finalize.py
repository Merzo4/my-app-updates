from pathlib import Path
import os,re

root=Path(os.environ['SOURCE_ROOT'])
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# R54.2 visible identity. The outer R54.2 controller can already promote the
# inherited R54.1 suffix so old source gates and shipped UI validate the same
# product identity. Keep this finalizer idempotent for that suffix.
xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xp)
for old,new in [
    ('Production R54.1 · 0.1.54.1','Production R54.2 · 0.1.54.2'),
    ('Text="R54.1"','Text="R54.2"'),
]:
    if old not in x: raise SystemExit('R54.2 UI version anchor missing: '+old)
    x=x.replace(old,new,1)
old_suffix='Production 0.1.54.1 · R54 SERVICE CONTROL HOTFIX'
new_suffix='Production 0.1.54.2 · R54.2 ONEDRIVE + GAME RELIABILITY'
already_suffix='Production 0.1.54.1 · R54.2 ONEDRIVE + GAME RELIABILITY'
if old_suffix in x:
    x=x.replace(old_suffix,new_suffix,1)
elif already_suffix in x:
    x=x.replace(already_suffix,new_suffix,1)
elif new_suffix not in x:
    raise SystemExit('R54.2 UI suffix anchor missing')
write(xp,x)

iss=root/'installer'/'MerzoWindowsOptimizer.iss'
i=read(iss)
if '#define MyAppVersion "0.1.54.1"' in i:
    i=i.replace('#define MyAppVersion "0.1.54.1"','#define MyAppVersion "0.1.54.2"',1)
elif 'AppVersion=0.1.54.1' in i:
    i=i.replace('AppVersion=0.1.54.1','AppVersion=0.1.54.2',1)
else:
    raise SystemExit('R54.2 installer version anchor missing')
i=i.replace('0.1.54.1','0.1.54.2').replace('0.1.54.2.2','0.1.54.2')
write(iss,i)

projects=sorted((root/'src').glob('MerzoOptimizer.*/*.csproj'))
if len(projects)<5: raise SystemExit('R54.2 project set missing')
for cp in projects:
    t=read(cp)
    for label in ('AssemblyVersion','FileVersion','InformationalVersion'):
        pat=rf'(<{label}>\s*)([^<]+?)(\s*</{label}>)'
        ms=list(re.finditer(pat,t))
        if not ms: raise SystemExit(f'R54.2 missing {label}: {cp.name}')
        vals={m.group(2).strip() for m in ms}
        if not vals <= {'0.1.54.1','0.1.54.1.0'}:
            raise SystemExit(f'R54.2 unexpected {label}: {cp.name}: {sorted(vals)}')
        t=re.sub(pat,lambda m:m.group(1)+'0.1.54.2'+m.group(3),t)
    write(cp,t)

notes=root/'dist'/'R53_RELEASE_NOTES.md'
if notes.exists():
    n=read(notes)
    add='''\n\n## 0.1.54.2 — OneDrive + GAME reliability\n- OneDriveSetup leftovers no longer count as an installed OneDrive client.\n- Unconfigured OneDrive removal requires explicit user choice.\n- Optional OneDrive uninstall failures no longer roll back the whole LIGHT/GAME package.\n- OneDrive uninstall verifies the real client state after setup execution and never removes user folders/files.\n- Release requires mutation/runtime acceptance before publication.\n'''
    if '## 0.1.54.2 — OneDrive + GAME reliability' not in n: n+=add
    write(notes,n)

(root/'R54_2_VERSION_FINAL.marker').write_text('0.1.54.2 / Production R54.2\n',encoding='utf-8')
print('R54.2 version finalize: OK')
