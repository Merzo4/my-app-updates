from pathlib import Path
import os,re

root=Path(os.environ['SOURCE_ROOT'])
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# Public feature release identity: 0.1.55 (assembly/file = 0.1.55.0).
xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xp)
replacements=[
    ('Production R54.2 · 0.1.54.2','Production R55 · 0.1.55'),
    ('Text="R54.2"','Text="R55"'),
    ('Production 0.1.54.2 · R54.2 ONEDRIVE + GAME RELIABILITY','Production 0.1.55 · R55 PROCESS STABILITY'),
]
for old,new in replacements:
    if old not in x: raise SystemExit('R55 UI version anchor missing: '+old)
    x=x.replace(old,new,1)
write(xp,x)

iss=root/'installer'/'MerzoWindowsOptimizer.iss'
i=read(iss)
if '#define MyAppVersion "0.1.54.2"' in i:
    i=i.replace('#define MyAppVersion "0.1.54.2"','#define MyAppVersion "0.1.55"',1)
elif 'AppVersion=0.1.54.2' in i:
    i=i.replace('AppVersion=0.1.54.2','AppVersion=0.1.55',1)
else:
    raise SystemExit('R55 installer version anchor missing')
i=i.replace('0.1.54.2','0.1.55')
write(iss,i)

projects=sorted((root/'src').glob('MerzoOptimizer.*/*.csproj'))
if len(projects)<5: raise SystemExit('R55 project set missing')
for cp in projects:
    t=read(cp)
    expected={'Version':'0.1.55','VersionPrefix':'0.1.55','AssemblyVersion':'0.1.55.0','FileVersion':'0.1.55.0','InformationalVersion':'0.1.55'}
    for label,value in expected.items():
        pat=rf'(<{label}>\s*)([^<]+?)(\s*</{label}>)'
        if re.search(pat,t):
            t=re.sub(pat,lambda m:m.group(1)+value+m.group(3),t)
    # Assembly/File/Informational exist in every production project in R54.2.
    for required in ('AssemblyVersion','FileVersion','InformationalVersion'):
        if f'<{required}>' not in t: raise SystemExit(f'R55 missing {required}: {cp.name}')
    write(cp,t)

notes=root/'dist'/'R53_RELEASE_NOTES.md'
if notes.exists():
    n=read(notes)
    add='''\n\n## 0.1.55 — Process Stability / Delayed Start\n- Новый read-only 15-минутный аудит процессов: старт, 1, 5, 10 и 15 минут.\n- Группировка поздно появившихся процессов по семействам вместо списка одинаковых PID.\n- Определение вероятного источника: автозагрузка, Scheduled Task, Win32 service, приложение, Windows или драйвер.\n- Консервативная классификация: «Не трогать», «Драйвер / оставить», «Проверить», «Необязательный».\n- Неизвестные службы/задачи/процессы автоматически не отключаются; GAME продолжает менять только проверенный allow-list через Snapshot/Undo.\n- Отчёт показывает стартовый, 15-минутный и пиковый счётчик, а также вклад необязательных и защищённых источников.\n'''
    if '## 0.1.55 — Process Stability / Delayed Start' not in n: n+=add
    write(notes,n)

(root/'R55_VERSION_FINAL.marker').write_text('0.1.55 / Production R55 PROCESS STABILITY\n',encoding='utf-8')
print('R55_VERSION_FINALIZE_PASS')
