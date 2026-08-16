from pathlib import Path
import json, os

root = Path(os.environ['SOURCE_ROOT'])
p = root / 'data' / 'tweaks.json'
tweaks = json.loads(p.read_text(encoding='utf-8-sig'))


def action_key(a):
    return (
        str(a.get('hive', '')).lower(),
        str(a.get('key_path', '')).lower(),
        str(a.get('value_name', '')).lower(),
    )


def add_tags(item, tags):
    arr = item.setdefault('profile_tags', [])
    for tag in tags:
        if tag not in arr:
            arr.append(tag)


def ensure_dword(tid, name, category, risk, admin, restart, description, effect, tags, hive, key, value_name, value):
    target = (hive.lower(), key.lower(), value_name.lower())
    for item in tweaks:
        for action in item.get('registry_actions') or []:
            if action_key(action) == target:
                # R34/R32 already knew several of these registry targets as
                # legacy/custom-build markers. R38 promotes those legacy cards
                # into real reversible settings instead of creating duplicate
                # actions. This also corrects the old SystemResponsiveness=0
                # marker to an effective experimental value of 10.
                action['value_type'] = 'DWord'
                action['integer_value'] = value
                if str(item.get('id', '')).startswith('legacy.'):
                    item['id'] = tid
                    item['name'] = name
                    item['category'] = category
                    item['risk'] = risk
                    item['requires_admin'] = admin
                    item['requires_restart'] = restart
                    item['scan_only'] = False
                    item['description'] = description
                    item['expected_effect'] = effect
                    item.pop('registry_states', None)
                add_tags(item, tags)
                return item.get('id', tid), False
    item = {
        'id': tid,
        'name': name,
        'category': category,
        'risk': risk,
        'requires_admin': admin,
        'requires_restart': restart,
        'scan_only': False,
        'description': description,
        'expected_effect': effect,
        'profile_tags': list(tags),
        'registry_actions': [{
            'hive': hive,
            'key_path': key,
            'value_name': value_name,
            'value_type': 'DWord',
            'integer_value': value,
        }],
    }
    tweaks.append(item)
    return tid, True

safe_tags = ['r38_new', 'gaming_safe', 'gaming_performance', 'gaming_extreme', 'gaming_lab']
perf_tags = ['r38_new', 'gaming_performance', 'gaming_extreme', 'gaming_lab']
extreme_tags = ['r38_new', 'gaming_extreme', 'gaming_lab']
lab_tags = ['r38_new', 'gaming_lab']

added = []
for spec in [
    ('r38.gaming.enable_game_mode', 'Включить Windows Game Mode', 'Gaming', 'Safe', False, False,
     'Включает штатный Game Mode Windows для текущего пользователя.',
     'Windows получает явный игровой сценарий и может уменьшать конкуренцию фоновой активности во время игры.',
     safe_tags, 'CurrentUser', r'SOFTWARE\Microsoft\GameBar', 'AutoGameModeEnabled', 1),
    ('r38.gaming.disable_user_presence_qos', 'Не снижать QoS foreground после бездействия', 'Gaming', 'Balanced', True, False,
     'Отключает переход foreground-задач в EcoQoS только из-за отсутствия пользовательского ввода. Это агрессивный gaming/performance режим.',
     'Может сохранить более высокий класс обслуживания активной игры/рендера при длительных игровых сессиях; увеличивает энергопотребление.',
     perf_tags, 'LocalMachine', r'SYSTEM\CurrentControlSet\Control\Power\PowerThrottling', 'DisableUserPresenceQos', 1),
    ('r38.gaming.mmcss_responsiveness_10', 'MMCSS: оставить системе 10% CPU', 'Gaming', 'Balanced', True, False,
     'Экспериментальная настройка Multimedia Class Scheduler. Уменьшает резерв CPU для низкоприоритетной системной активности до 10%.',
     'На CPU-нагруженных игровых системах может уменьшить конкуренцию с мультимедийными задачами. Эффект зависит от игры и драйверов.',
     extreme_tags, 'LocalMachine', r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile', 'SystemResponsiveness', 10),
    ('r38.gaming.foreground_scheduler_26', 'Foreground scheduler: приоритет отклика', 'Performance', 'Balanced', True, True,
     'Экспериментальный Win32 scheduler bias для более выраженного foreground-режима. Требует перезагрузку для чистого A/B сравнения.',
     'Может улучшить субъективный отклик foreground-нагрузки, но не гарантирует рост FPS на каждом ПК.',
     lab_tags, 'LocalMachine', r'SYSTEM\CurrentControlSet\Control\PriorityControl', 'Win32PrioritySeparation', 38),
    ('r38.graphics.hags_enable', 'Попробовать Hardware-accelerated GPU scheduling', 'Gaming', 'Balanced', True, True,
     'LAB-настройка HAGS. Имеет смысл только на поддерживаемом GPU/драйвере; после применения нужен перезапуск Windows.',
     'На части современных систем может уменьшить CPU-overhead планирования GPU, на других результат нейтрален или хуже — сравнивайте до/после.',
     lab_tags, 'LocalMachine', r'SYSTEM\CurrentControlSet\Control\GraphicsDrivers', 'HwSchMode', 2),
]:
    tid, was_added = ensure_dword(*spec)
    if was_added:
        added.append(tid)

# Build nested Gaming presets from the already reviewed catalog. SAFE only gets
# Safe Gaming cards. Balanced Gaming entries start at PERFORMANCE or higher.
for item in tweaks:
    if item.get('scan_only'):
        continue
    risk = str(item.get('risk', '')).lower()
    category = str(item.get('category', ''))
    tags = item.setdefault('profile_tags', [])
    if category == 'Gaming' and risk == 'safe':
        add_tags(item, ['gaming_safe', 'gaming_performance', 'gaming_extreme', 'gaming_lab'])
    elif category == 'Gaming' and risk == 'balanced' and 'gaming_lab' not in tags and 'gaming_extreme' not in tags:
        add_tags(item, ['gaming_performance', 'gaming_extreme', 'gaming_lab'])
    if 'performance' in tags and risk in {'safe', 'balanced'}:
        add_tags(item, ['gaming_performance', 'gaming_extreme', 'gaming_lab'])
    if 'process_safe' in tags:
        add_tags(item, ['gaming_performance', 'gaming_extreme', 'gaming_lab'])
    if 'background_light' in tags and risk == 'safe':
        add_tags(item, ['gaming_performance', 'gaming_extreme', 'gaming_lab'])
    if 'process_aggressive' in tags:
        add_tags(item, ['gaming_extreme', 'gaming_lab'])

# Remove accidental SAFE tag from non-Safe entries, then ensure strict nesting.
for item in tweaks:
    tags = item.setdefault('profile_tags', [])
    if str(item.get('risk', '')).lower() != 'safe' and 'gaming_safe' in tags:
        tags.remove('gaming_safe')
    if 'gaming_safe' in tags:
        add_tags(item, ['gaming_performance', 'gaming_extreme', 'gaming_lab'])
    if 'gaming_performance' in tags:
        add_tags(item, ['gaming_extreme', 'gaming_lab'])
    if 'gaming_extreme' in tags:
        add_tags(item, ['gaming_lab'])

p.write_text(json.dumps(tweaks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
counts = {tag: sum(1 for x in tweaks if not x.get('scan_only') and tag in (x.get('profile_tags') or [])) for tag in ['gaming_safe','gaming_performance','gaming_extreme','gaming_lab']}
ids = [x.get('id') for x in tweaks if str(x.get('id','')).startswith('r38.')]
print('R38 gaming catalog: OK', 'added=', len(added), 'total=', len(tweaks), counts, 'r38_ids=', ids)
