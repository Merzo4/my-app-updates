from pathlib import Path
import os,re

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# R49 first pass made the global top-bar security pill too wide at the 920px contract.
# Keep that global pill compact and show Recovery only on the Builds page where it matters.
xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xp)
if x.count('SNAPSHOT + UNDO + RECOVERY') != 1:
    raise SystemExit(f'R49 finalize topbar recovery badge count={x.count("SNAPSHOT + UNDO + RECOVERY")}')
x=x.replace('SNAPSHOT + UNDO + RECOVERY','SNAPSHOT + UNDO',1)
section=x.index('<!-- R49 SIMPLE BUILDS FINAL -->')
pos=x.find('SNAPSHOT + UNDO',section)
if pos < 0:
    raise SystemExit('R49 finalize builds recovery badge anchor missing')
x=x[:pos]+'UNDO + RECOVERY'+x[pos+len('SNAPSHOT + UNDO'):]
# Sidebar release badge must match the actual shipped version.
if 'Text="R48" Foreground="{StaticResource Accent}"' in x:
    x=x.replace('Text="R48" Foreground="{StaticResource Accent}"','Text="R49" Foreground="{StaticResource Accent}"',1)
write(xp,x)

# Fully qualify Management type used only by the fixed restore-point helper script.
hp=root/'src'/'MerzoOptimizer.ElevatedHelper'/'Program.cs'
h=read(hp)
h=h.replace('[Management.ManagementDateTimeConverter]::ToDateTime','[System.Management.ManagementDateTimeConverter]::ToDateTime')
write(hp,h)

# The SelfTest title is diagnostic output, but it must identify the actual release too.
sp=root/'src'/'MerzoOptimizer.SelfTest'/'Program.cs'
s=read(sp)
s=re.sub(r'Merzo Windows Optimizer — PRODUCTION R48 OTA RELIABILITY SelfTest','Merzo Windows Optimizer — PRODUCTION R49 PUBLIC READY SelfTest',s)
write(sp,s)

(root/'R49_FINALIZE.marker').write_text('R49 FINALIZE\ncompact topbar + Builds recovery badge + release identity\n',encoding='utf-8')
print('R49 finalize OK')
