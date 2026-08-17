from pathlib import Path
import os

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

print('R42 approved 1000x600 window contract: OK')
