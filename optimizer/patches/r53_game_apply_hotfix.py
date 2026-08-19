from pathlib import Path
import json, os, re

root = Path(os.environ['SOURCE_ROOT'])

def read(p):
    return p.read_text(encoding='utf-8-sig')

def write(p, text):
    p.write_text(text, encoding='utf-8')

# -----------------------------------------------------------------------------
# R53 HOTFIX 1
# The R53 GAME profile intentionally contains one Advanced tweak:
# r53.process.service_host_density. R20 SafetyEngine still denied every
# Advanced/Expert tweak unconditionally, so GAME aborted and the transaction
# rolled back. Keep the global guard. Allow ONLY the exact R53 managed action,
# with exact ID/tags/registry target/value. Any generic/tampered Advanced tweak
# remains blocked.
# -----------------------------------------------------------------------------
safety = root/'src'/'MerzoOptimizer.Core'/'Safety'/'SafetyEngine.cs'
s = read(safety)
old = '''        if (tweak.Risk is TweakRisk.Advanced or TweakRisk.Expert)\n        {\n            return new SafetyCheckResult\n            {\n                Allowed = false,\n                Message = "R20 не применяет ADVANCED/EXPERT автоматически. Эти уровни будут доступны только в отдельном ручном режиме."\n            };\n        }'''
new = '''        var isR53ManagedServiceHostDensity =\n            string.Equals(tweak.Id, "r53.process.service_host_density", StringComparison.OrdinalIgnoreCase) &&\n            tweak.Risk == TweakRisk.Advanced &&\n            tweak.ProfileTags.Contains("merzo_game", StringComparer.OrdinalIgnoreCase) &&\n            tweak.ProfileTags.Contains("merzo_extreme", StringComparer.OrdinalIgnoreCase) &&\n            tweak.RegistryActions.Count == 1 &&\n            tweak.RegistryActions[0].Hive == RegistryHiveScope.LocalMachine &&\n            string.Equals(tweak.RegistryActions[0].KeyPath, @"SYSTEM\\CurrentControlSet\\Control", StringComparison.OrdinalIgnoreCase) &&\n            string.Equals(tweak.RegistryActions[0].ValueName, "SvcHostSplitThresholdInKB", StringComparison.OrdinalIgnoreCase) &&\n            tweak.RegistryActions[0].IntegerValue == 67108864;\n\n        if (tweak.Risk is TweakRisk.Advanced or TweakRisk.Expert)\n        {\n            if (!isR53ManagedServiceHostDensity)\n            {\n                return new SafetyCheckResult\n                {\n                    Allowed = false,\n                    Message = "ADVANCED/EXPERT не применяются автоматически. Исключение — только встроенное R53 GAME/EXTREME действие Service Host Density с точной проверкой контракта и Snapshot/Undo."\n                };\n            }\n        }'''
if old not in s:
    raise SystemExit('R53 HF1 SafetyEngine guard anchor missing')
s = s.replace(old, new, 1)

old_msg = '''            Message = tweak.Risk == TweakRisk.Balanced\n                ? "BALANCED совместим: требуется явное подтверждение пользователя; перед изменением будет создан snapshot."\n                : "SAFE совместим: перед изменением будет создан snapshot."'''
new_msg = '''            Message = tweak.Risk switch\n            {\n                TweakRisk.Advanced when isR53ManagedServiceHostDensity => "ADVANCED R53 profile-managed: разрешено только точное GAME/EXTREME действие Service Host Density; перед изменением обязателен snapshot.",\n                TweakRisk.Balanced => "BALANCED совместим: требуется явное подтверждение пользователя; перед изменением будет создан snapshot.",\n                _ => "SAFE совместим: перед изменением будет создан snapshot."\n            }'''
if old_msg not in s:
    raise SystemExit('R53 HF1 SafetyEngine success-message anchor missing')
s = s.replace(old_msg, new_msg, 1)
write(safety, s)

# SelfTest must prove BOTH sides of the contract:
# 1) generic Advanced stays denied;
# 2) the exact shipped R53 managed tweak is allowed for an administrator.
selftest = root/'src'/'MerzoOptimizer.SelfTest'/'Program.cs'
t = read(selftest)
anchor = '''    if (safety.Evaluate(advancedProbe, true, Environment.OSVersion.Version.Build).Allowed) failures.Add("SafetyEngine must keep ADVANCED/EXPERT auto-apply blocked in R20.");'''
insert = anchor + '''\n\n    var r53ManagedAdvanced = tweaks.FirstOrDefault(x => string.Equals(x.Id, "r53.process.service_host_density", StringComparison.OrdinalIgnoreCase));\n    if (r53ManagedAdvanced is null)\n        failures.Add("R53 managed Service Host Density tweak is missing.");\n    else if (!safety.Evaluate(r53ManagedAdvanced, true, Environment.OSVersion.Version.Build).Allowed)\n        failures.Add("R53 GAME must be able to apply the exact managed Service Host Density tweak while generic ADVANCED/EXPERT remains blocked.");'''
if anchor not in t:
    raise SystemExit('R53 HF1 SelfTest Advanced guard anchor missing')
t = t.replace(anchor, insert, 1)
write(selftest, t)

# Fix the stale R52 labels visible in the shipped R53 UI.
xaml = root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x = read(xaml)
replacements = [
    ('Title="Merzo Windows Optimizer — Production 0.1.52 · R53 PROCESS + CLEAN START"',
     'Title="Merzo Windows Optimizer — Production 0.1.53.1 · R53 HOTFIX 1"'),
    ('<TextBlock Text="Production R53 · 0.1.53" Foreground="{StaticResource TextMuted}" FontSize="10.5" Margin="0,-1,0,0"/>',
     '<TextBlock Text="Production R53.1 · 0.1.53.1" Foreground="{StaticResource TextMuted}" FontSize="10.5" Margin="0,-1,0,0"/>'),
    ('<TextBlock Text="R52" Foreground="{StaticResource Accent}" FontSize="9.2" FontWeight="Bold"/>',
     '<TextBlock Text="R53.1" Foreground="{StaticResource Accent}" FontSize="9.2" FontWeight="Bold"/>'),
]
for old_x, new_x in replacements:
    if old_x not in x:
        raise SystemExit('R53 HF1 stale UI anchor missing: ' + old_x[:70])
    x = x.replace(old_x, new_x, 1)
write(xaml, x)

# Hotfix must be a newer OTA version so already-installed 0.1.53 clients can see it.
iss = root/'installer'/'MerzoWindowsOptimizer.iss'
i = read(iss)
if 'AppVersion=0.1.53' not in i:
    raise SystemExit('R53 HF1 installer AppVersion anchor missing')
i = i.replace('AppVersion=0.1.53', 'AppVersion=0.1.53.1', 1)
# Keep any explicit AppVerName in sync when present.
i = re.sub(r'(?mi)^(AppVerName=.*?)(?:0\.1\.53)(.*)$', lambda m: m.group(1)+'0.1.53.1'+m.group(2), i, count=1)
write(iss, i)

# Append a user-facing changelog entry without changing the risk classification.
notes_json = root/'data'/'release_notes.json'
if notes_json.exists():
    try:
        data = json.loads(read(notes_json))
        note = 'R53 Hotfix 1: исправлен откат GAME на Service Host Density; общий запрет ADVANCED/EXPERT сохранён, разрешено только точное встроенное GAME/EXTREME действие. Исправлены оставшиеся подписи R52 в интерфейсе.'
        for key in ('items','changes','notes'):
            if isinstance(data.get(key), list) and note not in data[key]:
                data[key].append(note)
        write(notes_json, json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    except Exception:
        pass

# Fail-closed source assertions for the exact hotfix contract.
s = read(safety)
for token in (
    'r53.process.service_host_density',
    'SvcHostSplitThresholdInKB',
    '67108864',
    'if (!isR53ManagedServiceHostDensity)',
):
    if token not in s:
        raise SystemExit('R53 HF1 SafetyEngine contract missing: ' + token)
if 'tweak.Risk is TweakRisk.Advanced or TweakRisk.Expert' not in s:
    raise SystemExit('R53 HF1 global ADVANCED/EXPERT guard was weakened/removed')
if 'r53ManagedAdvanced' not in read(selftest):
    raise SystemExit('R53 HF1 SelfTest managed-advanced proof missing')
if 'R52" Foreground="{StaticResource Accent}" FontSize="9.2"' in read(xaml):
    raise SystemExit('R53 HF1 stale R52 navigation badge remains')

(root/'R53_GAME_APPLY_HOTFIX.marker').write_text(
    '0.1.53.1: exact Service Host Density allow-list + generic Advanced/Expert deny + stale R52 UI fixed\n',
    encoding='utf-8')
print('R53 GAME apply hotfix: OK')
