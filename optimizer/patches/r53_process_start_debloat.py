from pathlib import Path
import json, os, re

root=Path(os.environ['SOURCE_ROOT'])
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8')
def once(s,old,new,label):
    c=s.count(old)
    if c!=1: raise SystemExit(f'R53 {label} anchor count={c}')
    return s.replace(old,new,1)

# -----------------------------------------------------------------------------
# 1) Public build catalog: cleaner Start + measurable process-density control.
#    Process density reduces the visible svchost count by grouping services; it
#    is NOT presented as a magical FPS tweak and remains Snapshot/Undo-backed.
# -----------------------------------------------------------------------------
tp=root/'data'/'tweaks.json'
tweaks=json.loads(read(tp))
byid={x.get('id'):x for x in tweaks}

def action_key(a):
    return (str(a.get('hive','')).lower(),str(a.get('key_path','')).lower(),str(a.get('value_name','')).lower())
existing={action_key(a) for t in tweaks for a in (t.get('registry_actions') or [])}

def add(item):
    if item['id'] in byid: return
    acts=item.get('registry_actions') or []
    # Never duplicate an existing registry value with another public card.
    if acts and all(action_key(a) in existing for a in acts): return
    tweaks.append(item);byid[item['id']]=item
    for a in acts: existing.add(action_key(a))

PRIMARY=['merzo_light','merzo_game','merzo_extreme']
add({
 'id':'r53.start.hide_recent_documents','name':'Чистый Пуск: не показывать недавние документы','category':'Interface','risk':'Safe',
 'requires_admin':False,'requires_restart':True,'scan_only':False,
 'description':'Отключает отслеживание недавно открытых документов для рекомендаций Пуска текущего пользователя.',
 'expected_effect':'Меньше автоматически появляющегося содержимого в рекомендациях Пуска.',
 'source_note':'Explorer Advanced Start_TrackDocs; reversible by Snapshot/Undo. Пользовательские закрепления не удаляются.',
 'profile_tags':PRIMARY.copy(),
 'registry_actions':[{'hive':'CurrentUser','key_path':r'Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced','value_name':'Start_TrackDocs','value_type':'DWord','integer_value':0}]
})
add({
 'id':'r53.start.disable_web_search_suggestions','name':'Чистый Пуск/Поиск: убрать web-подсказки','category':'Interface','risk':'Safe',
 'requires_admin':False,'requires_restart':True,'scan_only':False,
 'description':'Отключает web suggestions в поиске Windows для текущего пользователя, сохраняя локальный поиск приложений и файлов.',
 'expected_effect':'Меньше web-рекомендаций и сетевого мусора при открытии поиска/Пуска.',
 'source_note':'Explorer policy DisableSearchBoxSuggestions; reversible by Snapshot/Undo.',
 'profile_tags':PRIMARY.copy(),
 'registry_actions':[{'hive':'CurrentUser','key_path':r'Software\Policies\Microsoft\Windows\Explorer','value_name':'DisableSearchBoxSuggestions','value_type':'DWord','integer_value':1}]
})
add({
 'id':'r53.process.service_host_density','name':'GAME: компактная группировка Service Host','category':'Performance','risk':'Advanced',
 'requires_admin':True,'requires_restart':True,'scan_only':False,
 'description':'Поднимает SvcHostSplitThresholdInKB выше типичного объёма RAM, чтобы Windows снова группировала часть служб в общие svchost. Это заметно уменьшает счётчик процессов, но снижает изоляцию служб.',
 'expected_effect':'Меньше отдельных svchost после перезагрузки. Само по себе не обещает FPS/latency прироста; польза — более компактный process footprint.',
 'source_note':'Windows service-host split threshold. R53 GAME/EXTREME only; Snapshot/Undo mandatory.',
 'profile_tags':['merzo_game','merzo_extreme'],
 'registry_actions':[{'hive':'LocalMachine','key_path':r'SYSTEM\CurrentControlSet\Control','value_name':'SvcHostSplitThresholdInKB','value_type':'DWord','integer_value':67108864}]
})

# Preserve public nesting.
for t in tweaks:
    tags=t.setdefault('profile_tags',[])
    if 'merzo_light' in tags:
        for z in ['merzo_game','merzo_extreme']:
            if z not in tags: tags.append(z)
    elif 'merzo_game' in tags and 'merzo_extreme' not in tags:
        tags.append('merzo_extreme')
write(tp,json.dumps(tweaks,ensure_ascii=False,indent=2)+'\n')

# -----------------------------------------------------------------------------
# 2) Conditional known service sources. GAME uses only low-risk home/gaming
#    sources; EXTREME adds indexing/prefetch/geolocation/media-sharing with
#    explicit compatibility warnings and normal Snapshot/Restore handling.
# -----------------------------------------------------------------------------
sp=root/'data'/'service_rules.json'
services=json.loads(read(sp));known={str(x.get('service_name','')).lower() for x in services}
extra=[
 ('WalletService','WalletService','BALANCED','Можно отключить на игровом ПК без Windows Wallet/NFC сценариев.','Не отключать, если используются Wallet/NFC/платёжные сценарии Windows.'),
 ('TrkWks','Distributed Link Tracking Client','BALANCED','На домашнем игровом ПК обычно не требуется отслеживание связей файлов между NTFS-томами/доменом.','В корпоративных и специфических файловых сценариях может использоваться.'),
 ('lfsvc','Geolocation Service','ADVANCED','EXTREME может отключить геолокацию Windows.','Погода, карты и приложения, которым нужна геопозиция, потеряют системную геолокацию.'),
 ('WMPNetworkSvc','Windows Media Player Network Sharing Service','ADVANCED','EXTREME может отключить сетевой шаринг медиатеки Windows Media Player.','Не отключать, если используется DLNA/Media Player network sharing.'),
 ('WSearch','Windows Search','ADVANCED','EXTREME отключает индексатор для уменьшения фоновой активности.','Поиск файлов/Пуск может стать медленнее и потерять индексированные результаты.'),
 ('SysMain','SysMain','ADVANCED','EXTREME отключает SysMain как агрессивный background-профиль.','На HDD и некоторых системах SysMain может улучшать запуск приложений; это не универсальный FPS-твик.')
]
for name,display,risk,rec,note in extra:
    if name.lower() not in known:
        services.append({'service_name':name,'display_name':display,'risk':risk,'recommendation':rec,'compatibility_note':note});known.add(name.lower())
write(sp,json.dumps(services,ensure_ascii=False,indent=2)+'\n')

# -----------------------------------------------------------------------------
# 3) Gaming Debloat: broaden only the fixed consumer allow-list. Xbox/Game Bar
#    pieces are removable only when Xbox app/Game Pass is NOT installed.
# -----------------------------------------------------------------------------
gp=root/'src'/'MerzoOptimizer.Windows'/'Gaming'/'WindowsGamingDebloatService.cs'
g=read(gp)
g=once(g,
'''    private static readonly string[] GameTargets =\n    [\n        ..LightTargets,\n        "Microsoft.OutlookForWindows",\n        "MSTeams",\n        "MicrosoftTeams",\n        "Microsoft.YourPhone",\n        "Microsoft.People",\n        "Microsoft.WindowsMaps",\n        "Microsoft.549981C3F5F10"\n    ];''',
'''    private static readonly string[] GameTargets =\n    [\n        ..LightTargets,\n        "Microsoft.OutlookForWindows",\n        "MSTeams",\n        "MicrosoftTeams",\n        "Microsoft.YourPhone",\n        "Microsoft.People",\n        "Microsoft.WindowsMaps",\n        "Microsoft.549981C3F5F10",\n        "Microsoft.Windows.DevHome",\n        "Microsoft.PowerAutomateDesktop",\n        "MicrosoftCorporationII.QuickAssist",\n        "Microsoft.XboxGamingOverlay",\n        "Microsoft.XboxGameOverlay",\n        "Microsoft.XboxSpeechToTextOverlay",\n        "Microsoft.XboxIdentityProvider"\n    ];''','game appx list')
g=once(g,
'''    private static readonly string[] ExtremeTargets =\n    [\n        ..GameTargets,\n        "Microsoft.ZuneMusic",\n        "Microsoft.ZuneVideo",\n        "MicrosoftCorporationII.MicrosoftFamily",\n        "Microsoft.Windows.DevHome"\n    ];''',
'''    private static readonly string[] ExtremeTargets =\n    [\n        ..GameTargets,\n        "Microsoft.ZuneMusic",\n        "Microsoft.ZuneVideo",\n        "MicrosoftCorporationII.MicrosoftFamily",\n        "Microsoft.WindowsAlarms",\n        "Microsoft.WindowsSoundRecorder",\n        "Microsoft.Todos"\n    ];''','extreme appx list')
g=once(g,
'''    private static readonly string[] XboxSignals =\n    [\n        "Microsoft.GamingApp",\n        "Microsoft.XboxApp",\n        "Microsoft.XboxGamingOverlay",\n        "Microsoft.XboxIdentityProvider",\n        "Microsoft.XboxGameOverlay",\n        "Microsoft.XboxSpeechToTextOverlay"\n    ];''',
'''    private static readonly string[] XboxSignals =\n    [\n        "Microsoft.GamingApp",\n        "Microsoft.XboxApp"\n    ];\n\n    private static readonly string[] XboxOptionalTargets =\n    [\n        "Microsoft.XboxGamingOverlay",\n        "Microsoft.XboxGameOverlay",\n        "Microsoft.XboxSpeechToTextOverlay",\n        "Microsoft.XboxIdentityProvider"\n    ];''','xbox signal semantics')
g=once(g,
'''        var target = Targets(mode);\n        var removable = installed.Where(x => target.Contains(x, StringComparer.OrdinalIgnoreCase)).Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(x => x).ToArray();\n        var xbox = installed.Any(x => XboxSignals.Contains(x, StringComparer.OrdinalIgnoreCase));''',
'''        var xbox = installed.Any(x => XboxSignals.Contains(x, StringComparer.OrdinalIgnoreCase));\n        var target = Targets(mode);\n        var removable = installed.Where(x => target.Contains(x, StringComparer.OrdinalIgnoreCase) && (!xbox || !XboxOptionalTargets.Contains(x, StringComparer.OrdinalIgnoreCase))).Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(x => x).ToArray();''','xbox conditional inspect')
write(gp,g)

# Helper has its own immutable allow-list; broaden and add the same Xbox guard.
hp=root/'src'/'MerzoOptimizer.ElevatedHelper'/'Program.cs'
h=read(hp)
h=once(h,
'''        string[] game = [..light,"Microsoft.OutlookForWindows","MSTeams","MicrosoftTeams","Microsoft.YourPhone","Microsoft.People","Microsoft.WindowsMaps","Microsoft.549981C3F5F10"];\n        string[] extreme = [..game,"Microsoft.ZuneMusic","Microsoft.ZuneVideo","MicrosoftCorporationII.MicrosoftFamily","Microsoft.Windows.DevHome"];''',
'''        string[] game = [..light,"Microsoft.OutlookForWindows","MSTeams","MicrosoftTeams","Microsoft.YourPhone","Microsoft.People","Microsoft.WindowsMaps","Microsoft.549981C3F5F10","Microsoft.Windows.DevHome","Microsoft.PowerAutomateDesktop","MicrosoftCorporationII.QuickAssist","Microsoft.XboxGamingOverlay","Microsoft.XboxGameOverlay","Microsoft.XboxSpeechToTextOverlay","Microsoft.XboxIdentityProvider"];\n        string[] extreme = [..game,"Microsoft.ZuneMusic","Microsoft.ZuneVideo","MicrosoftCorporationII.MicrosoftFamily","Microsoft.WindowsAlarms","Microsoft.WindowsSoundRecorder","Microsoft.Todos"];''','helper appx lists')
h=once(h,
'''            "$targets=@("+literal+")",\n            "$removed=New-Object System.Collections.Generic.List[string]",''',
'''            "$targets=@("+literal+")",\n            "$xboxOptional=@('Microsoft.XboxGamingOverlay','Microsoft.XboxGameOverlay','Microsoft.XboxSpeechToTextOverlay','Microsoft.XboxIdentityProvider')",\n            "$hasXbox=(@(Get-AppxPackage -Name Microsoft.GamingApp -ErrorAction SilentlyContinue).Count -gt 0) -or (@(Get-AppxPackage -Name Microsoft.XboxApp -ErrorAction SilentlyContinue).Count -gt 0)",\n            "$removed=New-Object System.Collections.Generic.List[string]",''','helper xbox state')
h=once(h,
'''            "foreach($name in $targets){",\n            "  $items=@(Get-AppxPackage -Name $name -ErrorAction SilentlyContinue)",''',
'''            "foreach($name in $targets){",\n            "  if($hasXbox -and $xboxOptional -contains $name){ continue }",\n            "  $items=@(Get-AppxPackage -Name $name -ErrorAction SilentlyContinue)",''','helper xbox guard')
write(hp,h)

# -----------------------------------------------------------------------------
# 4) Build engine: stronger but explicit source reduction + target reporting.
# -----------------------------------------------------------------------------
vp=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
v=read(vp)
v=once(v,
'''        var processCountBefore = processObjectsBefore.Length;\n        foreach (var p in processObjectsBefore) p.Dispose();''',
'''        var processCountBefore = processObjectsBefore.Length;\n        foreach (var p in processObjectsBefore) p.Dispose();\n        var processTargetText = merzoExtreme ? "60–80" : merzoGame ? "80–100" : "без жёсткой цели";''','process target variable')
v=once(v,
'''                foreach (var name in new[] { "MapsBroker", "Fax", "RemoteRegistry", "diagnosticshub.standardcollector.service", "RetailDemo" }) serviceNames.Add(name);''',
'''                foreach (var name in new[] { "MapsBroker", "Fax", "RemoteRegistry", "diagnosticshub.standardcollector.service", "RetailDemo", "WalletService", "TrkWks" }) serviceNames.Add(name);\n                if (merzoExtreme) foreach (var name in new[] { "lfsvc", "WMPNetworkSvc", "WSearch", "SysMain" }) serviceNames.Add(name);''','service target expansion')
v=v.replace('Цель на чистой Windows после reboot — примерно 90–120 процессов','Цель на чистой Windows после reboot — 80–100 процессов')
v=v.replace('EXTREME — GAME 2.0 + расширенный consumer debloat','EXTREME — GAME 2.0 + цель 60–80 процессов после reboot + расширенный consumer debloat')
v=v.replace('GAME-цель после reboot: ~90–120 (не гарантия)','цель после reboot: {processTargetText} (ориентир, не гарантия)')
v=v.replace('После перезагрузки выполните повторный аудит для финального результата.','После перезагрузки выполните повторный аудит: целевой диапазон этой сборки — {processTargetText}; драйверы и реально используемые функции могут оставить больше процессов.',1)
write(vp,v)

# UI copy. Keep exact targets visible before install.
xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xp)
x=x.replace('R52 GAME WOW + UI RELIABILITY','R53 PROCESS + CLEAN START')
x=x.replace('✓ Цель после reboot: ~90–120 процессов*','✓ Цель после reboot: 80–100 процессов*')
# Put the EXTREME target in its card without removing Recovery wording.
x=x.replace('✓ Перед запуском обязателен Recovery Package','✓ Цель после reboot: 60–80 процессов*\n                                    ✓ Перед запуском обязателен Recovery Package',1)
x=x.replace('*90–120 — ориентир для чистой Windows, не гарантия: драйверы и используемые функции влияют на итог. После reboot повторите аудит.',
'''*80–100 GAME / 60–80 EXTREME — ориентиры после reboot и 2–3 минут простоя. Process Density группирует часть svchost и уменьшает счётчик, но сама по себе не является FPS-твиком.''',1)
write(xp,x)

# Release notes data; the release script promotes visible build identity to 0.1.53.
rp=root/'data'/'release_notes.json'
data=json.loads(read(rp))
entry={'version':'0.1.53','title':'R53 PROCESS + CLEAN START','changes':[
 'GAME: целевой диапазон после reboot/простоя 80–100 процессов; EXTREME: 60–80. Это ориентир, а не фальшивая гарантия.',
 'Process Density группирует часть Service Host через обратимый SvcHostSplitThresholdInKB; это уменьшает число svchost, но не выдаётся за отдельный FPS-твик.',
 'Чистый Пуск усилен: недавние документы и web suggestions отключаются, старые consumer recommendations остаются выключенными; пользовательские закрепления не стираются.',
 'Gaming Debloat расширен: Outlook(new), consumer Teams, Phone Link, People/Maps/Cortana, Dev Home/Power Automate/Quick Assist; EXTREME дополнительно чистит media/Family/ToDo consumer Appx.',
 'Xbox/Game Bar компоненты удаляются только если Xbox app/Game Pass не обнаружены. Microsoft Store, Calculator, Notepad, Paint, Photos, Snipping Tool, Defender и Windows Update защищены.',
 'GAME дополнительно отключает только известные фоновые источники; EXTREME добавляет Search indexer/SysMain/geolocation/media sharing с явным риском и Recovery.',
 'Сохранены R52 исправления максимизации и прокрутки, R51 Widgets/readability, R49 Recovery/OneDrive и R48 OTA security.'
]}
if isinstance(data,list):
    data=[e for e in data if not(isinstance(e,dict) and e.get('version')=='0.1.53')];data.insert(0,entry)
elif isinstance(data,dict):
    data['version']='0.1.53';data['title']=entry['title'];data['changes']=entry['changes']
write(rp,json.dumps(data,ensure_ascii=False,indent=2)+'\n')

(root/'R53_PROCESS_CLEAN_START.marker').write_text('R53 PROCESS + CLEAN START\nGAME target 80-100; EXTREME target 60-80; clean Start; guarded Appx debloat\n',encoding='utf-8')
print('R53 process/clean-start/debloat patch: OK')
