from pathlib import Path
import os, struct

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

mp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(mp)
changes={
    'Width="1180" Height="680"':'Width="1000" Height="600"',
    'MinWidth="1000" MinHeight="600"':'MinWidth="880" MinHeight="520"',
    '<ColumnDefinition Width="210"/>':'<ColumnDefinition Width="196"/>',
    'Margin="18,14,18,16"':'Margin="14,10,14,12"',
    '<RowDefinition Height="50"/>\n                        <RowDefinition Height="46"/>\n                        <RowDefinition Height="220"/>':'<RowDefinition Height="44"/>\n                        <RowDefinition Height="40"/>\n                        <RowDefinition Height="190"/>',
    '<Grid.RowDefinitions><RowDefinition Height="50"/><RowDefinition Height="44"/><RowDefinition Height="*"/></Grid.RowDefinitions>':'<Grid.RowDefinitions><RowDefinition Height="44"/><RowDefinition Height="40"/><RowDefinition Height="*"/></Grid.RowDefinitions>',
    '<RowDefinition Height="58"/>\n                            <RowDefinition Height="*"/>\n                            <RowDefinition Height="104"/>':'<RowDefinition Height="50"/>\n                            <RowDefinition Height="*"/>\n                            <RowDefinition Height="94"/>',
    '<Grid.RowDefinitions><RowDefinition Height="58"/><RowDefinition Height="92"/><RowDefinition Height="*"/></Grid.RowDefinitions>':'<Grid.RowDefinitions><RowDefinition Height="50"/><RowDefinition Height="78"/><RowDefinition Height="*"/></Grid.RowDefinitions>',
    '<Grid.RowDefinitions><RowDefinition Height="54"/><RowDefinition Height="148"/><RowDefinition Height="*"/></Grid.RowDefinitions>':'<Grid.RowDefinitions><RowDefinition Height="48"/><RowDefinition Height="124"/><RowDefinition Height="*"/></Grid.RowDefinitions>',
    '<Grid.RowDefinitions><RowDefinition Height="54"/><RowDefinition Height="80"/><RowDefinition Height="*"/></Grid.RowDefinitions>':'<Grid.RowDefinitions><RowDefinition Height="48"/><RowDefinition Height="68"/><RowDefinition Height="*"/></Grid.RowDefinitions>',
    'DockPanel Margin="10,12,10,10"':'DockPanel Margin="8,8,8,8"',
    'CornerRadius="11" Padding="10,8" Margin="0,8,0,0"':'CornerRadius="11" Padding="8,6" Margin="0,5,0,0"',
    'StackPanel Margin="6,0,4,11"':'StackPanel Margin="5,0,4,6"',
    'Text="РАЗДЕЛЫ" Margin="7,0,0,4"':'Text="РАЗДЕЛЫ" Margin="7,0,0,2"'
}
for old,new in changes.items():
    if old not in x:
        raise SystemExit('R42 window contract anchor missing: '+old[:80])
    x=x.replace(old,new)
write(mp,x)

ap=root/'src'/'MerzoOptimizer.App'/'App.xaml'
a=read(ap)
old='<Setter Property="Padding" Value="10,7"/>\n            <Setter Property="Margin" Value="0,2"/>'
new='<Setter Property="Padding" Value="9,5"/>\n            <Setter Property="Margin" Value="0,1"/>'
if old not in a: raise SystemExit('R42 nav density anchor missing')
a=a.replace(old,new)
write(ap,a)

# Self-contained 32-bit ICO, generated with the Python standard library so
# production builds do not depend on Pillow or any external image package.
w=h=32
pixels=bytearray()
for y in range(h-1,-1,-1):
    for x0 in range(w):
        # rounded dark tile
        dx=max(0,4-x0,x0-27); dy=max(0,4-y,y-27)
        inside=(dx*dx+dy*dy<=16)
        if not inside:
            b,g,r,alpha=0,0,0,0
        else:
            b,g,r,alpha=23,16,9,255
            # teal border
            if x0 in (4,5,26,27) or y in (4,5,26,27): b,g,r=172,184,85
            # compact M mark
            if (8<=x0<=10 and 10<=y<=23) or (21<=x0<=23 and 10<=y<=23): b,g,r=248,247,242
            if 10<=x0<=16 and abs(y-(x0+1))<=1: b,g,r=248,247,242
            if 16<=x0<=21 and abs(y-(33-x0))<=1: b,g,r=248,247,242
            # teal lightning accent
            if 16<=x0<=20 and 6<=y<=16 and (x0+y)>=24 and (x0+y)<=31: b,g,r=172,184,85
        pixels += bytes((b,g,r,alpha))
mask=bytes((w//8)*h)
bi=struct.pack('<IIIHHIIIIII',40,w,h*2,1,32,0,len(pixels),0,0,0,0)
image=bi+pixels+mask
ico=struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',w,h,0,0,1,32,len(image),22)+image
icon=root/'assets'/'MerzoWindowsOptimizer.ico'
icon.parent.mkdir(parents=True,exist_ok=True)
icon.write_bytes(ico)
if not icon.exists() or icon.stat().st_size < 1000:
    raise SystemExit('R42 icon generation failed')

print('R42 approved 1000x600 window contract + icon: OK')
