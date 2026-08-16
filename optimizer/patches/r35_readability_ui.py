from pathlib import Path
import json, os, re

root = Path(os.environ['SOURCE_ROOT'])

def read(path):
    return path.read_text(encoding='utf-8-sig')

def write(path, text):
    path.write_text(text, encoding='utf-8')

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R35 anchor missing: {label}')
    return text.replace(old, new, 1)

# R35 READABILITY UI: compact shell stays compact, but dense 2K/DPI text and
# controls get more breathing room and the teal accent becomes less fluorescent.
app_path = root / 'src' / 'MerzoOptimizer.App' / 'App.xaml'
app = read(app_path)
for old, new in {
    '#59D8C2': '#46B5A5',
    '#173A37': '#16312F',
    '#6CE4CF': '#56C1B0',
    '#9AF0E1': '#6BCABE',
    '#2D625A': '#294F49',
    '#315F59': '#315A54',
}.items():
    app = app.replace(old, new)

app = replace_once(app,
    '            <Setter Property="FontSize" Value="12"/>\n            <Setter Property="TextOptions.TextFormattingMode" Value="Display"/>',
    '            <Setter Property="FontSize" Value="13"/>\n            <Setter Property="UseLayoutRounding" Value="True"/>\n            <Setter Property="SnapsToDevicePixels" Value="True"/>\n            <Setter Property="TextOptions.TextFormattingMode" Value="Display"/>',
    'global window readability')

replacements = [
    ('<Setter Property="FontSize" Value="9"/>\n            <Setter Property="FontWeight" Value="SemiBold"/>\n            <Setter Property="Foreground" Value="{StaticResource TextMuted}"/>',
     '<Setter Property="FontSize" Value="10.5"/>\n            <Setter Property="FontWeight" Value="SemiBold"/>\n            <Setter Property="Foreground" Value="{StaticResource TextMuted}"/>', 'eyebrow'),
    ('<Style x:Key="CompactPrimaryButton" TargetType="Button" BasedOn="{StaticResource PrimaryButton}">\n            <Setter Property="MinHeight" Value="28"/>\n            <Setter Property="Padding" Value="11,4"/>\n            <Setter Property="FontSize" Value="9.5"/>',
     '<Style x:Key="CompactPrimaryButton" TargetType="Button" BasedOn="{StaticResource PrimaryButton}">\n            <Setter Property="MinHeight" Value="32"/>\n            <Setter Property="Padding" Value="12,5"/>\n            <Setter Property="FontSize" Value="11"/>\n            <Setter Property="VerticalContentAlignment" Value="Center"/>\n            <Setter Property="HorizontalContentAlignment" Value="Center"/>', 'compact primary'),
    ('<Style x:Key="CompactSecondaryButton" TargetType="Button" BasedOn="{StaticResource SecondaryButton}">\n            <Setter Property="MinHeight" Value="28"/>\n            <Setter Property="Padding" Value="10,4"/>\n            <Setter Property="FontSize" Value="9.5"/>',
     '<Style x:Key="CompactSecondaryButton" TargetType="Button" BasedOn="{StaticResource SecondaryButton}">\n            <Setter Property="MinHeight" Value="32"/>\n            <Setter Property="Padding" Value="11,5"/>\n            <Setter Property="FontSize" Value="11"/>\n            <Setter Property="VerticalContentAlignment" Value="Center"/>\n            <Setter Property="HorizontalContentAlignment" Value="Center"/>', 'compact secondary'),
    ('<Style x:Key="TableActionButton" TargetType="Button" BasedOn="{StaticResource SecondaryButton}">\n            <Setter Property="MinHeight" Value="24"/>\n            <Setter Property="MinWidth" Value="66"/>\n            <Setter Property="Padding" Value="8,2"/>\n            <Setter Property="Margin" Value="3,2"/>\n            <Setter Property="FontSize" Value="8.5"/>',
     '<Style x:Key="TableActionButton" TargetType="Button" BasedOn="{StaticResource SecondaryButton}">\n            <Setter Property="MinHeight" Value="28"/>\n            <Setter Property="MinWidth" Value="68"/>\n            <Setter Property="Padding" Value="8,3"/>\n            <Setter Property="Margin" Value="2,1"/>\n            <Setter Property="FontSize" Value="10"/>\n            <Setter Property="VerticalContentAlignment" Value="Center"/>', 'table secondary'),
    ('<Style x:Key="TablePrimaryButton" TargetType="Button" BasedOn="{StaticResource PrimaryButton}">\n            <Setter Property="MinHeight" Value="24"/>\n            <Setter Property="MinWidth" Value="72"/>\n            <Setter Property="Padding" Value="7,2"/>\n            <Setter Property="FontSize" Value="8.5"/>',
     '<Style x:Key="TablePrimaryButton" TargetType="Button" BasedOn="{StaticResource PrimaryButton}">\n            <Setter Property="MinHeight" Value="28"/>\n            <Setter Property="MinWidth" Value="74"/>\n            <Setter Property="Padding" Value="8,3"/>\n            <Setter Property="FontSize" Value="10"/>\n            <Setter Property="VerticalContentAlignment" Value="Center"/>', 'table primary'),
    ('<Style x:Key="PresetActionButton" TargetType="Button" BasedOn="{StaticResource SecondaryButton}">\n            <Setter Property="MinHeight" Value="27"/>\n            <Setter Property="Padding" Value="8,3"/>\n            <Setter Property="FontSize" Value="9"/>',
     '<Style x:Key="PresetActionButton" TargetType="Button" BasedOn="{StaticResource SecondaryButton}">\n            <Setter Property="MinHeight" Value="30"/>\n            <Setter Property="Padding" Value="9,4"/>\n            <Setter Property="FontSize" Value="10.5"/>', 'preset action'),
    ('<Style x:Key="SelectedListItemBorder" TargetType="Border" BasedOn="{StaticResource CompactListItemBorder}">\n            <Setter Property="Background" Value="#121E1D"/>\n            <Setter Property="BorderBrush" Value="#24463F"/>\n            <Setter Property="MinHeight" Value="50"/>',
     '<Style x:Key="SelectedListItemBorder" TargetType="Border" BasedOn="{StaticResource CompactListItemBorder}">\n            <Setter Property="Background" Value="#121D1C"/>\n            <Setter Property="BorderBrush" Value="#285047"/>\n            <Setter Property="MinHeight" Value="58"/>', 'selected item height'),
    ('<Setter Property="FontSize" Value="9.5"/>\n            <Setter Property="Padding" Value="0"/>\n        </Style>\n\n        <Style x:Key="FilterComboBox"',
     '<Setter Property="FontSize" Value="10.8"/>\n            <Setter Property="Padding" Value="0"/>\n        </Style>\n\n        <Style x:Key="FilterComboBox"', 'search font'),
    ('<Setter Property="FontSize" Value="9.5"/>\n            <Setter Property="MinHeight" Value="26"/>\n        </Style>\n\n        <!-- R20 dark checkbox',
     '<Setter Property="FontSize" Value="10.8"/>\n            <Setter Property="MinHeight" Value="28"/>\n        </Style>\n\n        <!-- R20 dark checkbox', 'combo font'),
    ('<Grid.ColumnDefinitions><ColumnDefinition Width="18"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>\n                            <Border x:Name="Box" Width="14" Height="14"',
     '<Grid.ColumnDefinitions><ColumnDefinition Width="20"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>\n                            <Border x:Name="Box" Width="16" Height="16"', 'checkbox size'),
    ('Text="✓" Foreground="#07110F" FontSize="10"', 'Text="✓" Foreground="#07110F" FontSize="11"', 'checkbox tick'),
    ('<Setter Property="Padding" Value="7,5"/>\n            <Setter Property="Margin" Value="0,1"/>',
     '<Setter Property="Padding" Value="8,6"/>\n            <Setter Property="Margin" Value="0,1"/>', 'navigation padding'),
    ('<Setter Property="Padding" Value="9,5"/>\n            <Setter Property="Margin" Value="0,0,3,4"/>',
     '<Setter Property="Padding" Value="10,6"/>\n            <Setter Property="Margin" Value="0,0,3,4"/>', 'subtab padding'),
]
for old, new, label in replacements:
    app = replace_once(app, old, new, label)
write(app_path, app)

xaml_path = root / 'src' / 'MerzoOptimizer.App' / 'MainWindow.xaml'
x = read(xaml_path)
x = x.replace('Production R34', 'Production R35').replace('v0.1.34', 'v0.1.35')
x = replace_once(x, 'CaptionHeight="32"', 'CaptionHeight="36"', 'window chrome caption')
x = replace_once(x, '<RowDefinition Height="32"/>', '<RowDefinition Height="36"/>', 'title row')
x = replace_once(x, '<ColumnDefinition Width="164"/>', '<ColumnDefinition Width="176"/>', 'sidebar width')
x = x.replace('<Grid.RowDefinitions><RowDefinition Height="40"/><RowDefinition Height="*"/></Grid.RowDefinitions>', '<Grid.RowDefinitions><RowDefinition Height="46"/><RowDefinition Height="*"/></Grid.RowDefinitions>')
x = x.replace('<Border Style="{StaticResource CompactListItemBorder}" MinHeight="54">', '<Border Style="{StaticResource CompactListItemBorder}" MinHeight="62">')
x = x.replace('<Grid.RowDefinitions><RowDefinition Height="88"/><RowDefinition Height="*"/></Grid.RowDefinitions>', '<Grid.RowDefinitions><RowDefinition Height="96"/><RowDefinition Height="*"/></Grid.RowDefinitions>', 1)

def bump_font(match):
    v = float(match.group(1))
    if v <= 8.4: nv = v + 1.5
    elif v <= 9.4: nv = v + 1.4
    elif v <= 10.4: nv = v + 1.2
    elif v <= 12.0: nv = v + 0.8
    else: return match.group(0)
    nv = max(nv, 9.4)
    out = f'{nv:.1f}'.rstrip('0').rstrip('.')
    return f'FontSize="{out}"'

x = re.sub(r'FontSize="([0-9]+(?:\.[0-9]+)?)"', bump_font, x)
write(xaml_path, x)

appcs_path = root / 'src' / 'MerzoOptimizer.App' / 'App.xaml.cs'
appcs = read(appcs_path)
appcs = appcs.replace('"0.1.34" : pendingVersion', '"0.1.35" : pendingVersion', 1)
appcs = appcs.replace('[Crash][R34]', '[Crash][R35]').replace('Версия: 0.1.34 / Production R34', 'Версия: 0.1.35 / Production R35')
write(appcs_path, appcs)

vm_path = root / 'src' / 'MerzoOptimizer.App' / 'ViewModels' / 'MainWindowViewModel.cs'
vm = read(vm_path)
vm = vm.replace('Version: 0.1.34 / Production R34', 'Version: 0.1.35 / Production R35')
vm = vm.replace('MerzoDiagnostics-R34-', 'MerzoDiagnostics-R35-')
vm = vm.replace('[Bug][R34]', '[Bug][R35]').replace('[Feature][R34]', '[Feature][R35]')
vm = vm.replace('Версия: 0.1.34 / Production R34', 'Версия: 0.1.35 / Production R35')
write(vm_path, vm)

for csproj in (root / 'src').glob('*/**/*.csproj'):
    s = read(csproj)
    s = re.sub(r'<Version>[^<]+</Version>', '<Version>0.1.35</Version>', s)
    s = re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>', '<AssemblyVersion>0.1.35.0</AssemblyVersion>', s)
    s = re.sub(r'<FileVersion>[^<]+</FileVersion>', '<FileVersion>0.1.35.0</FileVersion>', s)
    s = re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>', '<InformationalVersion>0.1.35</InformationalVersion>', s)
    write(csproj, s)

notes = {
    'version':'0.1.35',
    'title':'R35 READABILITY & DPI UI',
    'summary':'Исправлена тесная геометрия кнопок, смягчён акцент и увеличена мелкая типографика для 2K/DPI без отказа от компактного интерфейса.',
    'added':['DPI-safe layout rounding и pixel snapping для более ровных границ при 125/150% масштабировании Windows.','Самый мелкий текст поднят минимум до 9.4 DIP; основная навигация наследует 13 DIP.'],
    'changed':['Яркий бирюзовый акцент заменён более спокойным фирменным teal; hover также стал мягче.','Compact/Table/Preset кнопки получили больше высоты и внутреннего воздуха.','Плотные строки Выбранное/Ход работы и карточки списка получили дополнительную высоту.','Левая панель расширена на 12 DIP, верхняя строка — на 4 DIP.'],
    'fixed':['Устранена основная причина визуального наложения/обрезки кнопок на 2K и масштабированном рабочем столе.','Сохранены Process Reduction R34, Feedback/Crash Reporter, Update Center, Snapshot/Undo и R33 runtime stability gates.']
}
write(root / 'data' / 'release_notes.json', json.dumps(notes, ensure_ascii=False, indent=2) + '\n')
(root / 'R35_READABILITY_UI.marker').write_text('R35 READABILITY & DPI UI\n', encoding='utf-8')
print('R35 readability UI patch: OK')
