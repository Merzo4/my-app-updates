from pathlib import Path
import json, os, re

root = Path(os.environ['SOURCE_ROOT'])

def read(p):
    return p.read_text(encoding='utf-8-sig')

def write(p, text):
    p.write_text(text, encoding='utf-8')

# -----------------------------------------------------------------------------
# DELIVERY BRIDGE
# Public 0.1.53 can parse four-part tags into System.Version, but serializes the
# selected version back with ToString(3). A tag mwo-v0.1.53.1 therefore becomes
# LatestVersion=0.1.53 and later fails the official-asset URL check. Ship this
# repair as three-part 0.1.54, which the old R53 updater can represent exactly.
# Once installed, preserve four-part versions end-to-end for future hotfixes.
# -----------------------------------------------------------------------------
updater = root/'src'/'MerzoOptimizer.Windows'/'Updates'/'GitHubUpdateService.cs'
u = read(updater)

required_old = [
    'LatestVersion = bestVersion.ToString(3),',
    'Message = updateAvailable ? $"Доступна версия {bestVersion.ToString(3)}." : "Установлена актуальная версия."',
    'LatestVersion = latest.ToString(3),',
    'private static string GetCurrentVersion() => Assembly.GetEntryAssembly()?.GetName().Version?.ToString(3) ?? "0.1.48";',
]
for token in required_old:
    if token not in u:
        raise SystemExit('R54 updater bridge anchor missing: ' + token)

u = u.replace('LatestVersion = bestVersion.ToString(3),', 'LatestVersion = FormatVersion(bestVersion),', 1)
u = u.replace('Message = updateAvailable ? $"Доступна версия {bestVersion.ToString(3)}." : "Установлена актуальная версия."',
              'Message = updateAvailable ? $"Доступна версия {FormatVersion(bestVersion)}." : "Установлена актуальная версия."', 1)
u = u.replace('LatestVersion = latest.ToString(3),', 'LatestVersion = FormatVersion(latest),', 1)
u = u.replace('private static string GetCurrentVersion() => Assembly.GetEntryAssembly()?.GetName().Version?.ToString(3) ?? "0.1.48";',
              'private static string GetCurrentVersion() => FormatVersion(typeof(GitHubUpdateService).Assembly.GetName().Version ?? new Version(0, 1, 54, 0));', 1)

anchor = '''    private static Version ParseVersion(string value)\n    {'''
helper = '''    private static string FormatVersion(Version version)\n    {\n        if (version.Revision >= 0)\n            return version.ToString(4);\n        if (version.Build >= 0)\n            return version.ToString(3);\n        return version.ToString(2);\n    }\n\n    private static Version ParseVersion(string value)\n    {'''
if anchor not in u:
    raise SystemExit('R54 FormatVersion insertion anchor missing')
u = u.replace(anchor, helper, 1)
write(updater, u)

# Bridge the visible identity from the already-applied R53.1 hotfix to a version
# the public R53 updater can actually download. Keep wording explicit that this
# is the delivery bridge for the R53 GAME fix, not a new optimization concept.
xaml = root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x = read(xaml)
repls = [
    ('Production 0.1.53.1 · R53 HOTFIX 1', 'Production 0.1.54 · R53 GAME HOTFIX BRIDGE'),
    ('Production R53.1 · 0.1.53.1', 'Production R54 · 0.1.54'),
    ('Text="R53.1"', 'Text="R54"'),
]
for old, new in repls:
    if old not in x:
        raise SystemExit('R54 UI bridge anchor missing: ' + old)
    x = x.replace(old, new, 1)
write(xaml, x)

# Inno must use the exact three-part version/tag visible to old R53.
iss = root/'installer'/'MerzoWindowsOptimizer.iss'
i = read(iss)
if '#define MyAppVersion "0.1.53.1"' in i:
    i = i.replace('#define MyAppVersion "0.1.53.1"', '#define MyAppVersion "0.1.54"', 1)
elif 'AppVersion=0.1.53.1' in i:
    i = i.replace('AppVersion=0.1.53.1', 'AppVersion=0.1.54', 1)
else:
    raise SystemExit('R54 installer bridge anchor missing')
i = i.replace('0.1.53.1', '0.1.54')
write(iss, i)

# Project/file version becomes conventional four-part 0.1.54.0. Informational
# version stays the public three-part release version.
projects = sorted((root/'src').glob('MerzoOptimizer.*/*.csproj'))
if len(projects) < 5:
    raise SystemExit(f'R54 bridge expected >=5 projects, found {len(projects)}')
for p in projects:
    text = read(p)
    for label, target in [('AssemblyVersion','0.1.54.0'),('FileVersion','0.1.54.0'),('InformationalVersion','0.1.54')]:
        pattern = rf'(<{label}>\s*)([^<]+?)(\s*</{label}>)'
        matches = list(re.finditer(pattern, text))
        if not matches:
            raise SystemExit(f'R54 bridge missing {label}: {p.name}')
        values = {m.group(2).strip() for m in matches}
        allowed = {'0.1.53.0','0.1.53.1','0.1.53'}
        if not values <= allowed:
            raise SystemExit(f'R54 bridge unknown {label}: {p.name}: {sorted(values)}')
        text = re.sub(pattern, lambda m: m.group(1)+target+m.group(3), text)
    write(p, text)

# Changelog metadata when present.
notes_json = root/'data'/'release_notes.json'
if notes_json.exists():
    try:
        data = json.loads(read(notes_json))
        note = ('0.1.54 — технический bridge для R53: исправлен откат GAME на Service Host Density и '
                'исправлен updater, который обрезал четырёхчастные hotfix-версии при проверке официального URL.')
        for key in ('items','changes','notes'):
            if isinstance(data.get(key), list) and note not in data[key]:
                data[key].append(note)
        write(notes_json, json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    except Exception:
        pass

# Fail closed on the exact updater regression.
u = read(updater)
for bad in [
    'LatestVersion = bestVersion.ToString(3),',
    'LatestVersion = latest.ToString(3),',
    'GetEntryAssembly()?.GetName().Version?.ToString(3)',
]:
    if bad in u:
        raise SystemExit('R54 updater truncation remains: ' + bad)
for good in [
    'LatestVersion = FormatVersion(bestVersion),',
    'LatestVersion = FormatVersion(latest),',
    'typeof(GitHubUpdateService).Assembly.GetName().Version',
    'return version.ToString(4);',
    'private static Version? ParseTaggedVersion',
]:
    if good not in u:
        raise SystemExit('R54 updater bridge contract missing: ' + good)

if 'Production R54 · 0.1.54' not in read(xaml) or 'Text="R54"' not in read(xaml):
    raise SystemExit('R54 visible identity gate failed')
installer_final = read(iss)
if '#define MyAppVersion "0.1.54"' not in installer_final and 'AppVersion=0.1.54' not in installer_final:
    raise SystemExit('R54 installer three-part bridge version missing')

(root/'R54_R53_HOTFIX_BRIDGE.marker').write_text(
    '0.1.54: R53 GAME rollback fix + old-R53-downloadable updater bridge + four-part future version support\n',
    encoding='utf-8')
print('R54 R53-hotfix updater bridge: OK')
