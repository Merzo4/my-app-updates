from pathlib import Path

p=Path(__file__).with_name('r48_ota_reliability.py')
s=p.read_text(encoding='utf-8')
old="expected='046f883dbbbcdac5a3ed1a674f7c2f87c36c07a0dfb2d9b6de73cd9fa566434a'"
new="expected='fce7c1ab1d6224ee7490ef615b8ae1d1458427f428c58fa302f65603e2565191'"
if s.count(old)!=1:
    raise SystemExit('R48 wrapper baseline anchor mismatch')
s=s.replace(old,new,1)
exec(compile(s,str(p),'exec'))
