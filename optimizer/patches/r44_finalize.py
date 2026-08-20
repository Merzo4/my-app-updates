from pathlib import Path
import json, os, re

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# Stamp the actual assemblies/projects. R43 intentionally pinned its own
# production identity, so Build-Production -Version alone cannot supersede it.
for csproj in (root/'src').rglob('*.csproj'):
    s=read(csproj)
    s=re.sub(r'<Version>[^<]+</Version>','<Version>0.1.44</Version>',s)
    s=re.sub(r'<VersionPrefix>[^<]+</VersionPrefix>','<VersionPrefix>0.1.44</VersionPrefix>',s)
    s=re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>','<AssemblyVersion>0.1.44.0</AssemblyVersion>',s)
    s=re.sub(r'<FileVersion>[^<]+</FileVersion>','<FileVersion>0.1.44.0</FileVersion>',s)
    s=re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>','<InformationalVersion>0.1.44</InformationalVersion>',s)
    write(csproj,s)

# Visible/versioned diagnostics must agree with the assembly identity.
for p in [
    root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml',
    root/'src'/'MerzoOptimizer.App'/'App.xaml.cs',
    root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
]:
    if not p.exists():
        continue
    s=read(p)
    s=s.replace('0.1.43','0.1.44')
    s=s.replace('Production R43','Production R44')
    s=s.replace('PRODUCTION R43 TRUE FULL UI','PRODUCTION R44 FUNCTION EXPANSION')
    s=s.replace('MerzoDiagnostics-R43-','MerzoDiagnostics-R44-')
    s=s.replace('[Bug][R43]','[Bug][R44]').replace('[Feature][R43]','[Feature][R44]').replace('[Crash][R43]','[Crash][R44]')
    write(p,s)

# Preserve the R44 release notes produced by the functional patch, while
# enforcing release identity even if an older cumulative patch wrote its own.
notes_path=root/'data'/'release_notes.json'
if notes_path.exists():
    notes=json.loads(read(notes_path))
else:
    notes={}
notes['version']='0.1.44'
notes['title']='R44 FUNCTION EXPANSION'
notes.setdefault('summary','Smart Audit 2.0, Profiles 2.0, Privacy / Telemetry Center, Startup Manager 2.0 и Debloat 2.0 поверх сохранённой R43 UI baseline.')
write(notes_path,json.dumps(notes,ensure_ascii=False,indent=2)+'\n')

# Sanity gates inside the patch itself.
for csproj in (root/'src').rglob('*.csproj'):
    s=read(csproj)
    for old in ('<AssemblyVersion>0.1.43.0</AssemblyVersion>','<FileVersion>0.1.43.0</FileVersion>','<Version>0.1.43</Version>'):
        if old in s:
            raise SystemExit(f'R44 stale project version survived in {csproj}: {old}')

(root/'R44_FINALIZE.marker').write_text('R44 FINALIZE 0.1.44\n',encoding='utf-8')
print('R44 finalize/version stamp: OK')
