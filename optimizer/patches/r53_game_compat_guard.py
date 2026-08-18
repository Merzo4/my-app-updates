from pathlib import Path
import os, re

root=Path(os.environ['SOURCE_ROOT'])
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

optional=[
    'Microsoft.XboxGamingOverlay',
    'Microsoft.XboxGameOverlay',
    'Microsoft.XboxSpeechToTextOverlay',
    'Microsoft.XboxIdentityProvider',
]

# GAME must prioritize compatibility: do not remove Xbox/Game Bar identity pieces
# solely because the Xbox front-end app is absent. EXTREME may offer removal,
# still guarded by the R53 Xbox/Game Pass detection added upstream.
gp=root/'src'/'MerzoOptimizer.Windows'/'Gaming'/'WindowsGamingDebloatService.cs'
g=read(gp)
mg=re.search(r'(private static readonly string\[\] GameTargets\s*=\s*\[)(.*?)(\n\s*\];)',g,re.S)
me=re.search(r'(private static readonly string\[\] ExtremeTargets\s*=\s*\[)(.*?)(\n\s*\];)',g,re.S)
if not mg or not me: raise SystemExit('R53 GAME compatibility target blocks missing')
game_body=mg.group(2)
extreme_body=me.group(2)
for name in optional:
    game_body=re.sub(rf'\n\s*"{re.escape(name)}"\s*,?', '', game_body)
    if f'"{name}"' not in extreme_body:
        extreme_body=extreme_body.rstrip()+f',\n        "{name}"'
g=g[:mg.start(2)]+game_body+g[mg.end(2):]
# Re-find EXTREME after changing earlier text positions.
me=re.search(r'(private static readonly string\[\] ExtremeTargets\s*=\s*\[)(.*?)(\n\s*\];)',g,re.S)
if not me: raise SystemExit('R53 EXTREME target block missing after GAME rewrite')
extreme_body=me.group(2)
for name in optional:
    if f'"{name}"' not in extreme_body:
        extreme_body=extreme_body.rstrip()+f',\n        "{name}"'
g=g[:me.start(2)]+extreme_body+g[me.end(2):]
write(gp,g)

# Mirror the exact policy in ElevatedHelper's immutable allow-list.
hp=root/'src'/'MerzoOptimizer.ElevatedHelper'/'Program.cs'
h=read(hp)
arr=re.search(r'string\[\]\s+game\s*=\s*\[(.*?)\];\s*\n\s*string\[\]\s+extreme\s*=\s*\[(.*?)\];',h,re.S)
if not arr: raise SystemExit('R53 helper GAME/EXTREME arrays missing')
game=arr.group(1)
extreme=arr.group(2)
for name in optional:
    game=re.sub(rf',?\s*"{re.escape(name)}"', '', game)
    if f'"{name}"' not in extreme:
        extreme=extreme.rstrip()+f',"{name}"'
replacement=f'string[] game = [{game}];\n        string[] extreme = [{extreme}];'
h=h[:arr.start()]+replacement+h[arr.end():]
write(hp,h)

# Hard gates: Xbox optional components may exist in EXTREME, never in GAME.
g=read(gp)
mg=re.search(r'private static readonly string\[\] GameTargets\s*=\s*\[(.*?)\n\s*\];',g,re.S)
me=re.search(r'private static readonly string\[\] ExtremeTargets\s*=\s*\[(.*?)\n\s*\];',g,re.S)
if not mg or not me: raise SystemExit('R53 GAME compatibility verification blocks missing')
for name in optional:
    if name in mg.group(1): raise SystemExit(f'R53 GAME must preserve {name}')
    if name not in me.group(1): raise SystemExit(f'R53 EXTREME optional target missing {name}')

(root/'R53_GAME_COMPAT_GUARD.marker').write_text(
    'GAME preserves Xbox/Game Bar optional components; EXTREME conditional only\n',encoding='utf-8')
print('R53 GAME compatibility guard: OK')
