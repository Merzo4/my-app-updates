from pathlib import Path
import json, os, re

root=Path(os.environ['SOURCE_ROOT'])
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')
def req(s,old,new,label):
    if old not in s: raise SystemExit(f'R35 anchor missing: {label}')
    return s.replace(old,new,1)

def style_patch(text,key,changes):
    m=re.search(rf'(<Style x:Key="{re.escape(key)}"\b.*?</Style>)',text,re.S)
    if not m: raise SystemExit(f'R35 style missing: {key}')
    block=m.group(1)
    for prop,old,new in changes:
        a=f'<Setter Property="{prop}" Value="{old}"/>'
        b=f'<Setter Property="{prop}" Value="{new}"/>'
        if a not in block: raise SystemExit(f'R35 {key}.{prop}={old} missing')
        block=block.replace(a,b,1)
    return text[:m.start(1)]+block+text[m.end(1):]

# ---------- App resources: calmer teal + larger controls + DPI rounding ----------
ap=root/'src'/'MerzoOptimizer.App'/'App.xaml'
a=read(ap)
for old,new in {'#59D8C2':'#46B5A5','#173A37':'#16312F','#6CE4CF':'#56C1B0','#9AF0E1':'#6BCABE','#2D625A':'#294F49','#315F59':'#315A54'}.items():
    a=a.replace(old,new)
a=req(a,'<Setter Property="FontSize" Value="12"/>\n            <Setter Property="TextOptions.TextFormattingMode" Value="Display"/>','<Setter Property="FontSize" Value="13"/>\n            <Setter Property="UseLayoutRounding" Value="True"/>\n            <Setter Property="SnapsToDevicePixels" Value="True"/>\n            <Setter Property="TextOptions.TextFormattingMode" Value="Display"/>','window font/DPI')
a=style_patch(a,'Eyebrow',[('FontSize','9','10.5')])
a=style_patch(a,'CompactPrimaryButton',[('MinHeight','28','32'),('Padding','11,4','12,5'),('FontSize','9.5','11')])
a=style_patch(a,'CompactSecondaryButton',[('MinHeight','28','32'),('Padding','10,4','11,5'),('FontSize','9.5','11')])
a=style_patch(a,'TableActionButton',[('MinHeight','24','28'),('MinWidth','66','68'),('Padding','8,2','8,3'),('Margin','3,2','2,1'),('FontSize','8.5','10')])
a=style_patch(a,'TablePrimaryButton',[('MinHeight','24','28'),('MinWidth','72','74'),('Padding','7,2','8,3'),('FontSize','8.5','10')])
a=style_patch(a,'PresetActionButton',[('MinHeight','27','30'),('Padding','8,3','9,4'),('FontSize','9','10.5')])
a=style_patch(a,'SelectedListItemBorder',[('Background','#121E1D','#121D1C'),('BorderBrush','#24463F','#285047'),('MinHeight','50','58')])
a=style_patch(a,'SearchTextBox',[('FontSize','9.5','10.8')])
a=style_patch(a,'FilterComboBox',[('FontSize','9.5','10.8'),('MinHeight','26','28')])
a=style_patch(a,'NavRadioButton',[('Padding','7,5','8,6')])
a=style_patch(a,'SubTabItem',[('Padding','9,5','10,6')])
# Add alignment setters after font sizes for compact/table buttons.
for key in ('CompactPrimaryButton','CompactSecondaryButton','TableActionButton','TablePrimaryButton'):
    m=re.search(rf'(<Style x:Key="{key}"\b.*?</Style>)',a,re.S); block=m.group(1)
    if 'VerticalContentAlignment' not in block:
        block=block.replace('</Style>','    <Setter Property="VerticalContentAlignment" Value="Center"/>\n        </Style>')
    if key.startswith('Compact') and 'HorizontalContentAlignment' not in block:
        block=block.replace('</Style>','    <Setter Property="HorizontalContentAlignment" Value="Center"/>\n        </Style>')
    a=a[:m.start(1)]+block+a[m.end(1):]
a=req(a,'<Grid.ColumnDefinitions><ColumnDefinition Width="18"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>\n                            <Border x:Name="Box" Width="14" Height="14"','<Grid.ColumnDefinitions><ColumnDefinition Width="20"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>\n                            <Border x:Name="Box" Width="16" Height="16"','checkbox')
a=req(a,'Text="✓" Foreground="#07110F" FontSize="10"','Text="✓" Foreground="#07110F" FontSize="11"','checkbox tick')
write(ap,a)

# ---------- Main window: readable small type, no fixed-row squeeze ----------
xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml';x=read(xp)
x=x.replace('Production R34','Production R35').replace('v0.1.34','v0.1.35')
x=req(x,'CaptionHeight="32"','CaptionHeight="36"','caption')
x=req(x,'<RowDefinition Height="32"/>','<RowDefinition Height="36"/>','title row')
x=req(x,'<ColumnDefinition Width="164"/>','<ColumnDefinition Width="176"/>','sidebar')
x=x.replace('<Grid.RowDefinitions><RowDefinition Height="40"/><RowDefinition Height="*"/></Grid.RowDefinitions>','<Grid.RowDefinitions><RowDefinition Height="46"/><RowDefinition Height="*"/></Grid.RowDefinitions>')
x=x.replace('<Border Style="{StaticResource CompactListItemBorder}" MinHeight="54">','<Border Style="{StaticResource CompactListItemBorder}" MinHeight="62">')
x=x.replace('<Grid.RowDefinitions><RowDefinition Height="88"/><RowDefinition Height="*"/></Grid.RowDefinitions>','<Grid.RowDefinitions><RowDefinition Height="96"/><RowDefinition Height="*"/></Grid.RowDefinitions>',1)

def bump(m):
    v=float(m.group(1))
    if v>12: return m.group(0)
    if v<=8.4: nv=v+1.5
    elif v<=9.4: nv=v+1.4
    elif v<=10.4: nv=v+1.2
    else: nv=v+0.8
    nv=max(nv,9.4)  # no microscopic labels on 2K/125-150% DPI
    out=f'{nv:.1f}'.rstrip('0').rstrip('.')
    return f'FontSize="{out}"'
x=re.sub(r'FontSize="([0-9]+(?:\.[0-9]+)?)"',bump,x)
write(xp,x)

# ---------- Version labels in splash / crash / feedback ----------
acp=root/'src'/'MerzoOptimizer.App'/'App.xaml.cs';ac=read(acp)
ac=ac.replace('"0.1.34" : pendingVersion','"0.1.35" : pendingVersion',1).replace('[Crash][R34]','[Crash][R35]').replace('Версия: 0.1.34 / Production R34','Версия: 0.1.35 / Production R35')
write(acp,ac)
vp=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs';v=read(vp)
v=v.replace('Version: 0.1.34 / Production R34','Version: 0.1.35 / Production R35').replace('MerzoDiagnostics-R34-','MerzoDiagnostics-R35-').replace('[Bug][R34]','[Bug][R35]').replace('[Feature][R34]','[Feature][R35]').replace('Версия: 0.1.34 / Production R34','Версия: 0.1.35 / Production R35')
write(vp,v)

# ---------- Hard version consistency ----------
for p in (root/'src').glob('*/**/*.csproj'):
    s=read(p)
    s=re.sub(r'<Version>[^<]+</Version>','<Version>0.1.35</Version>',s)
    s=re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>','<AssemblyVersion>0.1.35.0</AssemblyVersion>',s)
    s=re.sub(r'<FileVersion>[^<]+</FileVersion>','<FileVersion>0.1.35.0</FileVersion>',s)
    s=re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>','<InformationalVersion>0.1.35</InformationalVersion>',s)
    write(p,s)

notes={'version':'0.1.35','title':'R35 READABILITY & DPI UI','summary':'Исправлена тесная геометрия кнопок, смягчён акцент и увеличена мелкая типографика для 2K/DPI без отказа от компактного интерфейса.','added':['DPI-safe layout rounding и pixel snapping для ровных границ при 125/150% масштабировании Windows.','Самый мелкий текст теперь не ниже 9.4 DIP; основная навигация наследует 13 DIP.'],'changed':['Яркий бирюзовый акцент заменён спокойным фирменным teal; hover также стал мягче.','Compact/Table/Preset кнопки получили больше высоты и внутреннего пространства.','Плотные строки Выбранное/Ход работы и карточки списка получили дополнительную высоту.','Левая панель расширена на 12 DIP, верхняя строка на 4 DIP.'],'fixed':['Устранена основная причина визуального наложения/обрезки кнопок на 2K и масштабированном рабочем столе.','Сохранены Process Reduction R34, Feedback/Crash Reporter, Update Center, Snapshot/Undo и R33 runtime stability gates.']}
write(root/'data'/'release_notes.json',json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
(root/'R35_READABILITY_UI.marker').write_text('R35 READABILITY & DPI UI\n',encoding='utf-8')
print('R35 readability UI patch: OK')
