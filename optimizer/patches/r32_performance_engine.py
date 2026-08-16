from pathlib import Path
import base64,zlib
here=Path(__file__).resolve().parent
payload=''.join((here/f'r32_payload.part{i}').read_text(encoding='utf-8').strip() for i in range(1,3))
src=zlib.decompress(base64.b64decode(payload)).decode('utf-8')
old="x=replace_once(x,tail,notice,'main window tail')"
new="""if tail in x:\n    x=x.replace(tail,notice,1)\nelse:\n    # R31 final appends its own overlays after MainTabs. Insert R32 notice immediately before the root Grid close, independent of whitespace.\n    window_pos=x.rfind('</Window>')\n    grid_pos=x.rfind('</Grid>',0,window_pos)\n    if window_pos < 0 or grid_pos < 0:\n        raise SystemExit('R32 anchor missing: main window root elements')\n    overlay_start=notice.find('        <!-- R32')\n    overlay_end=notice.rfind('    </Grid>\\n</Window>')\n    if overlay_start < 0 or overlay_end < 0:\n        raise SystemExit('R32 internal notice template invalid')\n    overlay=notice[overlay_start:overlay_end]\n    x=x[:grid_pos]+overlay+x[grid_pos:]"""
if old not in src:
    raise SystemExit('R32 compatibility rewrite anchor missing')
src=src.replace(old,new,1)
exec(compile(src,'r32_payload','exec'), {'__name__':'__main__'})
