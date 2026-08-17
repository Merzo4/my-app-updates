from pathlib import Path
import json, os, re

root = Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# Fix the startup DispatcherUnhandledException seen on real Windows:
# ProgressBar.Value defaults to a writable binding mode, while NetworkProgress
# has a private setter. Force OneWay explicitly.
xp = root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x = read(xp)
old = 'ProgressBar Value="{Binding NetworkProgress}" Maximum="100"'
new = 'ProgressBar Value="{Binding NetworkProgress, Mode=OneWay}" Maximum="100"'
if old not in x and new not in x:
    raise SystemExit('R40 NetworkProgress binding anchor missing')
x = x.replace(old, new)
x = x.replace('Production R39','Production R40').replace('v0.1.39','v0.1.40')
write(xp,x)

# Advance visible diagnostics / crash-report identity.
for p in [root/'src'/'MerzoOptimizer.App'/'App.xaml.cs', root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs']:
    s = read(p)
    s = s.replace('Version: 0.1.39 / Production R39','Version: 0.1.40 / Production R40')
    s = s.replace('Версия: 0.1.39 / Production R39','Версия: 0.1.40 / Production R40')
    s = s.replace('MerzoDiagnostics-R39-','MerzoDiagnostics-R40-')
    s = s.replace('[Bug][R39]','[Bug][R40]').replace('[Feature][R39]','[Feature][R40]').replace('[Crash][R39]','[Crash][R40]')
    s = s.replace('"0.1.39" : pendingVersion','"0.1.40" : pendingVersion')
    write(p,s)

for csproj in (root/'src').glob('*/**/*.csproj'):
    s = read(csproj)
    s = re.sub(r'<Version>[^<]+</Version>','<Version>0.1.40</Version>',s)
    s = re.sub(r'<VersionPrefix>[^<]+</VersionPrefix>','<VersionPrefix>0.1.40</VersionPrefix>',s)
    s = re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>','<AssemblyVersion>0.1.40.0</AssemblyVersion>',s)
    s = re.sub(r'<FileVersion>[^<]+</FileVersion>','<FileVersion>0.1.40.0</FileVersion>',s)
    s = re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>','<InformationalVersion>0.1.40</InformationalVersion>',s)
    write(csproj,s)

notes = {
  'version':'0.1.40',
  'title':'R40 NETWORK BINDING HOTFIX',
  'summary':'Исправлен реальный сбой после обновления: WPF пытался записать в read-only NetworkProgress при создании страницы Repair / Network.',
  'fixed':[
    'NetworkProgress в ProgressBar теперь привязан строго Mode=OneWay, поэтому окно больше не падает с InvalidOperationException при загрузке интерфейса.',
    'Crash Reporter и диагностический отчёт теперь показывают версию 0.1.40 / Production R40.'
  ],
  'retained':[
    'R39 GAME BUILD: GAME SAFE / PERFORMANCE / EXTREME / LAB.',
    'Gaming Network SAFE/EXTREME и восстановление baseline адаптера.',
    'Process Reduction, Snapshot/Undo, Audit Memory, Update Center, Feedback/Crash Reporter.'
  ]
}
write(root/'data'/'release_notes.json', json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
(root/'R40_NETWORK_BINDING_HOTFIX.marker').write_text('R40 NETWORK BINDING HOTFIX\n', encoding='utf-8')
print('R40 network binding hotfix: OK')
