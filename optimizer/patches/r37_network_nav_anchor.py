from pathlib import Path
import os,re
root=Path(os.environ['SOURCE_ROOT'])
p=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
s=p.read_text(encoding='utf-8-sig')
# R36 sidebar Gaming entry is a self-closing RadioButton but has no x:Name.
# Give that exact existing control a name so the following network patch can
# clone its already-approved style instead of guessing a new navigation style.
m=re.search(r'<RadioButton\b[^>]*Click="GamingDev_Click"[^>]*/>',s,re.S)
if not m:
    raise SystemExit('R37 nav-prep: GamingDev self-closing RadioButton not found')
tag=m.group(0)
if 'x:Name=' not in tag:
    tag=tag.replace('<RadioButton','<RadioButton x:Name="GamingDevNav"',1)
    s=s[:m.start()]+tag+s[m.end():]
elif 'x:Name="GamingDevNav"' not in tag:
    raise SystemExit('R37 nav-prep: Gaming entry already has unexpected x:Name')
p.write_text(s,encoding='utf-8')
print('R37 network nav anchor prep: OK')
