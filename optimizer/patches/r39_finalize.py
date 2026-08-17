from pathlib import Path
import json, os, re

root = Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# Visible identity.
xp = root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x = read(xp)
x = x.replace('Production R38','Production R39').replace('v0.1.38','v0.1.39')
write(xp,x)

for p in [root/'src'/'MerzoOptimizer.App'/'App.xaml.cs', root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs']:
    s = read(p)
    s = s.replace('Version: 0.1.38 / Production R38','Version: 0.1.39 / Production R39')
    s = s.replace('Версия: 0.1.38 / Production R38','Версия: 0.1.39 / Production R39')
    s = s.replace('MerzoDiagnostics-R38-','MerzoDiagnostics-R39-')
    s = s.replace('[Bug][R38]','[Bug][R39]').replace('[Feature][R38]','[Feature][R39]').replace('[Crash][R38]','[Crash][R39]')
    s = s.replace('"0.1.38" : pendingVersion','"0.1.39" : pendingVersion')
    write(p,s)

for csproj in (root/'src').glob('*/**/*.csproj'):
    s = read(csproj)
    s = re.sub(r'<Version>[^<]+</Version>','<Version>0.1.39</Version>',s)
    s = re.sub(r'<VersionPrefix>[^<]+</VersionPrefix>','<VersionPrefix>0.1.39</VersionPrefix>',s)
    s = re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>','<AssemblyVersion>0.1.39.0</AssemblyVersion>',s)
    s = re.sub(r'<FileVersion>[^<]+</FileVersion>','<FileVersion>0.1.39.0</FileVersion>',s)
    s = re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>','<InformationalVersion>0.1.39</InformationalVersion>',s)
    write(csproj,s)

notes = {
  'version':'0.1.39',
  'title':'R39 GAMING BUILD',
  'summary':'Gaming Boost встроен в основную оптимизацию: твики, снижение фоновой нагрузки, условные службы/задачи и игровая сеть выполняются одним подтверждённым планом.',
  'added':[
    'GAME BUILD появился рядом с основными профилями оптимизации; быстрый вариант запускает PERFORMANCE.',
    'Четыре игровых уровня: GAME SAFE, GAME PERFORMANCE, GAME EXTREME и GAME LAB.',
    'Gaming Build объединяет Registry/Policy, источники фоновых процессов, проверяемые службы/задачи и Gaming Network.',
    'PERFORMANCE использует Gaming Network SAFE; EXTREME/LAB используют Gaming Network EXTREME с сохранением baseline адаптера.',
    'EXTREME/LAB получили отдельное предупреждение о функциях Hotspot/Smart Card/Sensors и экспериментальных scheduler/GPU/MMCSS параметрах.'
  ],
  'changed':[
    'R38 Gaming Boost теперь выбирает полный gaming_build профиль, а не только настройки категории Gaming.',
    'Process Reduction включён в игровые профили через отключение источников фоновой нагрузки вместо случайного убийства системных процессов.',
    'Профильный движок показывает единый этапный план Registry → Services → Tasks → Gaming Network и сохраняет Snapshot/Undo.',
    'При ошибке EXTREME-сети Merzo пытается вернуть сохранённый baseline, затем откатывает Snapshot-изменения.'
  ],
  'safety':[
    'Defender, Windows Update, Store, IPv6 и pagefile Gaming Build не отключает.',
    'SAFE не отключает системные службы автоматически; PERFORMANCE/EXTREME/LAB показывают подтверждение перед изменениями.',
    'LAB остаётся экспериментальным и предназначен для сравнения FPS/frametime/фоновой нагрузки до и после.'
  ]
}
write(root/'data'/'release_notes.json', json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
if not (root/'R39_GAMING_BUILD.marker').exists():
    raise SystemExit('R39 Gaming Build marker missing')
print('R39 finalize: OK')
