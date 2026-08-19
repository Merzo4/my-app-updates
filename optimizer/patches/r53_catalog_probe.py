from pathlib import Path
import json, os

root = Path(os.environ['SOURCE_ROOT'])
tp = root / 'data' / 'tweaks.json'
items = json.loads(tp.read_text(encoding='utf-8-sig'))

LEGACY_ID = 'privacy.disable_recent_documents_tracking'
R53_ID = 'r53.start.hide_recent_documents'
EXPECTED_IDS = {
    R53_ID,
    'r53.start.disable_web_search_suggestions',
    'r53.process.service_host_density',
}
EXPECTED_ACTION = (
    'currentuser',
    r'software\microsoft\windows\currentversion\explorer\advanced',
    'start_trackdocs',
)


def action_key(a):
    return (
        str(a.get('hive', '')).lower(),
        str(a.get('key_path', '')).replace('/', '\\').lower(),
        str(a.get('value_name', '')).lower(),
    )


def by_id():
    return {str(x.get('id')): x for x in items}


catalog = by_id()
if R53_ID not in catalog:
    legacy = catalog.get(LEGACY_ID)
    if legacy is None:
        raise SystemExit('R53 catalog migration failed: legacy recent-documents tweak missing')

    actions = legacy.get('registry_actions') or []
    if len(actions) != 1:
        raise SystemExit('R53 catalog migration failed: legacy recent-documents action count changed')
    action = actions[0]
    if action_key(action) != EXPECTED_ACTION:
        raise SystemExit('R53 catalog migration failed: legacy recent-documents registry target changed')
    if str(action.get('value_type', '')).lower() != 'dword' or int(action.get('integer_value', -1)) != 0:
        raise SystemExit('R53 catalog migration failed: legacy recent-documents value is no longer DWORD 0')

    # Do not rename an ID that runtime source/data still addresses directly.
    # Profiles are tag-driven, but this gate makes that assumption explicit and fail-closed.
    direct_refs = []
    for base in (root / 'src', root / 'data'):
        if not base.exists():
            continue
        for p in base.rglob('*'):
            if not p.is_file() or p == tp or p.suffix.lower() not in {'.cs', '.xaml', '.json', '.xml', '.config'}:
                continue
            try:
                text = p.read_text(encoding='utf-8-sig')
            except (UnicodeError, OSError):
                continue
            if LEGACY_ID in text:
                direct_refs.append(str(p.relative_to(root)).replace('\\', '/'))
    if direct_refs:
        raise SystemExit('R53 catalog migration blocked by direct legacy ID refs: ' + ','.join(sorted(direct_refs)))

    # Same proven Registry mutation, same Snapshot/Undo path, one catalog owner.
    # Only promote the stable catalog identifier required by cumulative R53.
    legacy['id'] = R53_ID
    tags = list(dict.fromkeys((legacy.get('profile_tags') or []) + ['merzo_light', 'merzo_game', 'merzo_extreme']))
    legacy['profile_tags'] = tags

catalog = by_id()
missing = sorted(EXPECTED_IDS - set(catalog))
if missing:
    raise SystemExit('R53 exact catalog IDs missing after migration: ' + ','.join(missing))

owners = []
for item in items:
    for action in item.get('registry_actions') or []:
        if action_key(action) == EXPECTED_ACTION:
            owners.append(str(item.get('id')))
if owners != [R53_ID]:
    raise SystemExit('R53 recent-documents action ownership invalid: ' + ','.join(owners))

# Guard against duplicate catalog IDs after the promotion.
ids = [str(x.get('id')) for x in items]
if len(ids) != len(set(ids)):
    raise SystemExit('R53 catalog migration produced duplicate IDs')

tp.write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(root / 'R53_CATALOG_PROBE.marker').write_text(
    'R53 exact catalog migration complete\nrecent-documents legacy ID promoted without duplicate Registry mutation\n',
    encoding='utf-8',
)
print('R53 exact catalog IDs: OK total=' + str(len(items)))
