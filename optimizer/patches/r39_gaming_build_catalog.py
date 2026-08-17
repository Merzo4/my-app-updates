from pathlib import Path
import json, os

root = Path(os.environ['SOURCE_ROOT'])
p = root / 'data' / 'tweaks.json'
tweaks = json.loads(p.read_text(encoding='utf-8-sig'))
tiers = ('gaming_build_safe','gaming_build_performance','gaming_build_extreme','gaming_build_lab')
allowed = {'Gaming','Performance','Background','Network','Privacy','Debloat','Search','Edge','Explorer','Notifications','Interface','Power','Multimedia'}

for item in tweaks:
    tags = item.setdefault('profile_tags', [])
    tags[:] = [t for t in tags if t not in tiers]
    if item.get('scan_only') or str(item.get('category','')) not in allowed:
        continue
    risk = str(item.get('risk','')).lower()
    category = str(item.get('category',''))
    safe = ('gaming_safe' in tags or 'process_safe' in tags) and risk == 'safe'
    perf = safe or 'gaming_performance' in tags or 'process_safe' in tags or ('performance' in tags and risk in {'safe','balanced'}) or ('background_light' in tags and risk == 'safe')
    extreme = perf or 'gaming_extreme' in tags or 'process_aggressive' in tags or ('maximum' in tags and category in {'Gaming','Performance','Background','Network','Debloat','Search','Edge','Notifications'} and risk in {'safe','balanced'})
    lab = extreme or 'gaming_lab' in tags or 'process_lite' in tags or ('lite_build' in tags and category in allowed)
    if safe: tags.extend([t for t in tiers if t not in tags])
    elif perf: tags.extend([t for t in tiers[1:] if t not in tags])
    elif extreme: tags.extend([t for t in tiers[2:] if t not in tags])
    elif lab: tags.append(tiers[3])

p.write_text(json.dumps(tweaks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
counts = {tag: sum(1 for x in tweaks if not x.get('scan_only') and tag in (x.get('profile_tags') or [])) for tag in tiers}
if not (counts[tiers[0]] > 0 and counts[tiers[0]] <= counts[tiers[1]] <= counts[tiers[2]] <= counts[tiers[3]]):
    raise SystemExit(f'R39 profile nesting invalid: {counts}')
(root/'R39_GAMING_BUILD.marker').write_text('R39 GAMING BUILD\n', encoding='utf-8')
print('R39 Gaming Build catalog: OK', counts, 'total=', len(tweaks))
