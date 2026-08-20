from pathlib import Path
import json, os

root = Path(os.environ['SOURCE_ROOT'])
p = root / 'data' / 'tweaks.json'
tweaks = json.loads(p.read_text(encoding='utf-8-sig'))
byid = {x['id']: x for x in tweaks}

PRIMARY = ['merzo_light','merzo_game','merzo_extreme']

def ensure_tags(item, tags):
    current = item.setdefault('profile_tags', [])
    for tag in tags:
        if tag not in current:
            current.append(tag)

def add(item):
    if item['id'] in byid:
        raise SystemExit(f"R49 duplicate tweak id: {item['id']}")
    tweaks.append(item)
    byid[item['id']] = item

# OneDrive policy already existed but was EXTREME-only. In R49 all three main builds
# manage OneDrive, while actual app uninstall is a separate guarded operation.
if 'onedrive.disable_sync' not in byid:
    raise SystemExit('R49 requires existing onedrive.disable_sync baseline')
ensure_tags(byid['onedrive.disable_sync'], PRIMARY)

add({
  'id':'r49.start.hide_recently_added',
  'name':'Чистый Пуск: скрыть «Недавно добавленные»',
  'category':'Interface',
  'risk':'Safe',
  'requires_admin':False,
  'requires_restart':True,
  'description':'Убирает блок недавно добавленных приложений из меню Пуск через штатную policy Windows.',
  'expected_effect':'Более чистый Пуск без автоматически добавляемого списка новых программ.',
  'source_note':'Microsoft Start policy HideRecentlyAddedApps; reversible by Snapshot/Undo.',
  'profile_tags':PRIMARY.copy(),
  'registry_actions':[{
    'hive':'CurrentUser','key_path':r'Software\Policies\Microsoft\Windows\Explorer','value_name':'HideRecentlyAddedApps','value_type':'DWord','integer_value':1
  }]
})

add({
  'id':'r49.start.hide_personalized_sites',
  'name':'Чистый Пуск: скрыть персональные веб-рекомендации',
  'category':'Interface',
  'risk':'Safe',
  'requires_admin':False,
  'requires_restart':True,
  'min_windows_build':22621,
  'description':'Убирает персонализированные рекомендации сайтов из раздела рекомендаций Пуска на поддерживаемых Windows 11.',
  'expected_effect':'Меньше рекламно-рекомендательного содержимого в Пуске.',
  'source_note':'Microsoft Start policy HideRecommendedPersonalizedSites; unsupported builds are skipped.',
  'profile_tags':PRIMARY.copy(),
  'registry_actions':[{
    'hive':'CurrentUser','key_path':r'Software\Policies\Microsoft\Windows\Explorer','value_name':'HideRecommendedPersonalizedSites','value_type':'DWord','integer_value':1
  }]
})

add({
  'id':'r49.start.hide_frequent_apps',
  'name':'Чистый Пуск: скрыть часто используемые программы',
  'category':'Interface',
  'risk':'Safe',
  'requires_admin':False,
  'requires_restart':True,
  'description':'Убирает автоматически формируемый список часто используемых программ из Пуска.',
  'expected_effect':'Пуск остаётся компактнее и показывает меньше автоматически подобранного содержимого.',
  'source_note':'Windows Start/Menu policy; reversible by Snapshot/Undo.',
  'profile_tags':PRIMARY.copy(),
  'registry_actions':[{
    'hive':'CurrentUser','key_path':r'Software\Microsoft\Windows\CurrentVersion\Policies\Explorer','value_name':'NoStartMenuMFUprogramsList','value_type':'DWord','integer_value':1
  }]
})

add({
  'id':'r49.privacy.disable_tailored_experiences',
  'name':'Отключить персонализированный опыт на диагностических данных',
  'category':'Privacy',
  'risk':'Safe',
  'requires_admin':False,
  'requires_restart':False,
  'description':'Запрещает Windows использовать диагностические данные для персонализированных советов, рекомендаций и предложений.',
  'expected_effect':'Меньше персонализированных рекомендаций на основе диагностических данных.',
  'source_note':'Windows CloudContent policy DisableTailoredExperiencesWithDiagnosticData.',
  'profile_tags':PRIMARY + ['privacy_safe','privacy_strict','privacy_maximum'],
  'registry_actions':[{
    'hive':'CurrentUser','key_path':r'Software\Policies\Microsoft\Windows\CloudContent','value_name':'DisableTailoredExperiencesWithDiagnosticData','value_type':'DWord','integer_value':1
  }]
})

add({
  'id':'r49.delivery.disable_peer_downloads',
  'name':'Delivery Optimization: без P2P между компьютерами',
  'category':'Background',
  'risk':'Safe',
  'requires_admin':True,
  'requires_restart':False,
  'description':'Отключает peer-to-peer обмен обновлениями между компьютерами, сохраняя обычную загрузку обновлений через Microsoft.',
  'expected_effect':'Меньше фоновой P2P-сетевой активности без отключения Windows Update.',
  'source_note':'Delivery Optimization DownloadMode 0; Windows Update remains enabled.',
  'profile_tags':PRIMARY.copy(),
  'registry_actions':[{
    'hive':'LocalMachine','key_path':r'SOFTWARE\Policies\Microsoft\Windows\DeliveryOptimization','value_name':'DODownloadMode','value_type':'DWord','integer_value':0
  }]
})

add({
  'id':'r49.onedrive.disable_startup',
  'name':'OneDrive: убрать автоматический запуск',
  'category':'Background',
  'risk':'Safe',
  'requires_admin':False,
  'requires_restart':False,
  'description':'Убирает только стандартную Run-запись OneDrive. Исходное значение сохраняется в Snapshot.',
  'expected_effect':'OneDrive не стартует автоматически вместе с входом в Windows.',
  'source_note':'Known per-user OneDrive Run value; user files are never deleted.',
  'profile_tags':PRIMARY.copy(),
  'registry_actions':[{
    'mode':'DeleteValue','hive':'CurrentUser','key_path':r'Software\Microsoft\Windows\CurrentVersion\Run','value_name':'OneDrive','value_type':'String'
  }]
})

add({
  'id':'r49.power.disable_power_throttling',
  'name':'GAME: отключить Power Throttling',
  'category':'Power',
  'risk':'Balanced',
  'requires_admin':True,
  'requires_restart':False,
  'min_windows_build':22000,
  'description':'Отключает системный Power Throttling для большей предсказуемости производительности. На ноутбуке может увеличить энергопотребление.',
  'expected_effect':'Меньше фонового ограничения производительности ценой возможного роста энергопотребления.',
  'source_note':'Microsoft Power policy PowerThrottlingTurnOff / PowerThrottlingOff.',
  'profile_tags':['merzo_game','merzo_extreme','gaming_build_performance','gaming_build_extreme','gaming_build_lab'],
  'registry_actions':[{
    'hive':'LocalMachine','key_path':r'SYSTEM\CurrentControlSet\Control\Power\PowerThrottling','value_name':'PowerThrottlingOff','value_type':'DWord','integer_value':1
  }]
})

add({
  'id':'r49.gaming.disable_game_dvr',
  'name':'EXTREME: отключить Game DVR / фоновую запись',
  'category':'Gaming',
  'risk':'Advanced',
  'requires_admin':True,
  'requires_restart':True,
  'description':'Отключает Game DVR и фоновую игровую запись. Не применять, если нужна запись Xbox Game Bar.',
  'expected_effect':'Убирает ненужный capture-компонент в игровой системе, где запись Game Bar не используется.',
  'source_note':'Known Windows GameDVR policy + per-user GameDVR state; Snapshot/Undo enabled.',
  'profile_tags':['merzo_extreme','gaming_build_extreme','gaming_build_lab'],
  'registry_actions':[
    {'hive':'LocalMachine','key_path':r'SOFTWARE\Policies\Microsoft\Windows\GameDVR','value_name':'AllowGameDVR','value_type':'DWord','integer_value':0},
    {'hive':'CurrentUser','key_path':r'System\GameConfigStore','value_name':'GameDVR_Enabled','value_type':'DWord','integer_value':0}
  ]
})

# Hidden symptom-specific fix. It never enters LIGHT/GAME/EXTREME automatically.
add({
  'id':'r49.lab.mpo_stutter_workaround',
  'name':'LAB: DWM/MPO workaround для мерцаний и отдельных stutter-сценариев',
  'category':'Gaming',
  'risk':'Expert',
  'requires_admin':True,
  'requires_restart':True,
  'description':'Экспериментальный workaround DWM. Использовать только при реальных проблемах MPO/оверлеев; это не универсальный FPS-твик.',
  'expected_effect':'Может убрать мерцания/заикания на отдельных конфигурациях; на исправной системе преимуществ не обещается.',
  'source_note':'LAB-only symptom workaround. Never auto-selected by the three public builds.',
  'profile_tags':['gaming_build_lab'],
  'registry_actions':[{
    'hive':'LocalMachine','key_path':r'SOFTWARE\Microsoft\Windows\Dwm','value_name':'OverlayTestMode','value_type':'DWord','integer_value':5
  }]
})

# Verify strict nesting for public builds and keep known critical anti-patterns out.
for item in tweaks:
    tags=set(item.get('profile_tags') or [])
    if 'merzo_light' in tags:
        ensure_tags(item,['merzo_game','merzo_extreme'])
    elif 'merzo_game' in tags:
        ensure_tags(item,['merzo_extreme'])

for forbidden in ['performance.keep_defender_advisory','performance.keep_windows_update_advisory','performance.keep_ipv6_advisory','performance.keep_pagefile_advisory','performance.keep_timer_advisory','performance.keep_tcp_magic_advisory']:
    if forbidden in byid:
        tags=set(byid[forbidden].get('profile_tags') or [])
        if tags & set(PRIMARY):
            raise SystemExit(f'R49 forbidden advisory leaked into public build: {forbidden}')

p.write_text(json.dumps(tweaks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
counts={tag:sum(1 for x in tweaks if not x.get('scan_only') and tag in (x.get('profile_tags') or [])) for tag in PRIMARY}
if not (0 < counts['merzo_light'] <= counts['merzo_game'] <= counts['merzo_extreme']):
    raise SystemExit(f'R49 public build nesting invalid: {counts}')
(root/'R49_CATALOG.marker').write_text('R49 catalog\n'+json.dumps(counts,ensure_ascii=False)+'\n',encoding='utf-8')
print('R49 catalog OK', counts, 'total=', len(tweaks))
