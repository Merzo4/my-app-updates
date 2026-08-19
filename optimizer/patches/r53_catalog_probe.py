from pathlib import Path
import json, os

root = Path(os.environ['SOURCE_ROOT'])
tp = root / 'data' / 'tweaks.json'
items = json.loads(tp.read_text(encoding='utf-8-sig'))
byid = {str(x.get('id')): x for x in items}

EXPECTED = {
    'r53.start.hide_recent_documents': ('currentuser', r'software\microsoft\windows\currentversion\explorer\advanced', 'start_trackdocs'),
    'r53.start.disable_web_search_suggestions': ('currentuser', r'software\policies\microsoft\windows\explorer', 'disablesearchboxsuggestions'),
    'r53.process.service_host_density': ('localmachine', r'system\currentcontrolset\control', 'svchostsplitthresholdinkb'),
}

def action_key(a):
    return (
        str(a.get('hive', '')).lower(),
        str(a.get('key_path', '')).replace('/', '\\').lower(),
        str(a.get('value_name', '')).lower(),
    )

present = [tid for tid in EXPECTED if tid in byid]
print(f'R53 CATALOG PROBE total={len(items)} present={present}')
for tid, key in EXPECTED.items():
    if tid in byid:
        continue
    owners = []
    for item in items:
        for action in item.get('registry_actions') or []:
            if action_key(action) == key:
                owners.append({
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'profile_tags': item.get('profile_tags') or [],
                    'scan_only': bool(item.get('scan_only')),
                    'action': action,
                })
    print('R53 CATALOG COLLISION ' + tid + ' => ' + json.dumps(owners, ensure_ascii=False, sort_keys=True))

(root / 'R53_CATALOG_PROBE.marker').write_text('R53 exact tweak ownership probe completed\n', encoding='utf-8')
print('R53 catalog ownership probe: OK')
