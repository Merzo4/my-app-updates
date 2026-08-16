from pathlib import Path
import base64,zlib
here=Path(__file__).resolve().parent
payload=''.join((here/f'r32_payload.part{i}').read_text(encoding='utf-8').strip() for i in range(1,3))
src=zlib.decompress(base64.b64decode(payload)).decode('utf-8')
old="x=replace_once(x,tail,notice,'main window tail')"
new="""if tail in x:\n    x=x.replace(tail,notice,1)\nelse:\n    # R31 final can append its audit-status overlay after MainTabs. Insert before the final root Grid close.\n    root_tail='''    </Grid>\\n</Window>'''\n    if root_tail not in x:\n        raise SystemExit('R32 anchor missing: main window root tail')\n    overlay=notice.replace('        </TabControl>\\n\\n','',1).replace(root_tail,'',1)\n    x=x.replace(root_tail,overlay+root_tail,1)"""
if old not in src:
    raise SystemExit('R32 compatibility rewrite anchor missing')
src=src.replace(old,new,1)
exec(compile(src,'r32_payload','exec'), {'__name__':'__main__'})
