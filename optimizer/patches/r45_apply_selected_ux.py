from pathlib import Path
import json, os, re

root=Path(os.environ['SOURCE_ROOT'])
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')
def replace_once(s,old,new,label):
    if old not in s: raise SystemExit('R45 anchor missing: '+label)
    return s.replace(old,new,1)

# -----------------------------------------------------------------------------
# VM: R44 inserted Privacy / Telemetry before "По одной" but the old numeric
# sub-tab indices remained from R43. This routed profile selection to the wrong
# tab ("По одной") and Apply to "Выбранное" instead of "Ход работы".
# -----------------------------------------------------------------------------
vp=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s=read(vp)

def method_body(text, name):
    m=re.search(r'\n    private\s+(?:async\s+)?(?:Task|void|int|string|bool)\s+'+re.escape(name)+r'\s*\(',text)
    if not m: return None,None,None
    start=m.start()+1
    nxt=re.search(r'\n    private\s+',text[m.end():])
    end=(m.end()+nxt.start()) if nxt else len(text)
    return start,end,text[start:end]

def replace_in_method(text,name,old,new,required=True):
    start,end,body=method_body(text,name)
    if body is None:
        if required: raise SystemExit('R45 method missing: '+name)
        return text
    if old not in body:
        if required: raise SystemExit(f'R45 method anchor missing: {name} :: {old}')
        return text
    body=body.replace(old,new)
    return text[:start]+body+text[end:]

# Selection result tab is now index 3: Profiles=0, Privacy=1, По одной=2,
# Выбранное=3, Ход работы=4.
for name in ['SelectGamingTaggedPresetAsync','SelectNamedCategoryPresetAsync','SelectCategoryProfileAsync','SelectProfileAsync']:
    s=replace_in_method(s,name,'SelectedOptimizationTabIndex = 2;','SelectedOptimizationTabIndex = 3;')
# Process advisor presets may also route to Selected in some baselines.
s=replace_in_method(s,'SelectProcessReductionProfileAsync','SelectedOptimizationTabIndex = 2;','SelectedOptimizationTabIndex = 3;',required=False)
# Deep scan and actual Apply must open the work/progress tab (index 4).
s=replace_in_method(s,'RunDeepOptimizationScanAsync','SelectedOptimizationTabIndex=3;','SelectedOptimizationTabIndex=4;')
s=replace_in_method(s,'ApplySelectedTweaksAsync','SelectedOptimizationTabIndex = 3;','SelectedOptimizationTabIndex = 4;')

write(vp,s)

# -----------------------------------------------------------------------------
# XAML: permanent bottom action bar for the whole Optimization page.
# It remains visible on Profiles / Privacy / По одной / Выбранное / Ход работы,
# so manual checkboxes and package selections always have a clear Apply action.
# -----------------------------------------------------------------------------
xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xp)
x=x.replace('Production 0.1.44 · R44 FUNCTION EXPANSION','Production 0.1.45 · R45 APPLY CENTER')
x=x.replace('Production R44 · 0.1.44','Production R45 · 0.1.45')
x=x.replace('Text="R44" Foreground="{StaticResource Accent}"','Text="R45" Foreground="{StaticResource Accent}"',1)

start=x.find('            <!-- Optimization profiles -->')
end=x.find('            <!-- Stage 3: Startup Optimizer -->',start)
if start<0 or end<0: raise SystemExit('R45 Optimization section not found')
sec=x[start:end]
row_old='<Grid.RowDefinitions><RowDefinition Height="44"/><RowDefinition Height="68"/><RowDefinition Height="*"/></Grid.RowDefinitions>'
row_new='<Grid.RowDefinitions><RowDefinition Height="44"/><RowDefinition Height="68"/><RowDefinition Height="*"/><RowDefinition Height="58"/></Grid.RowDefinitions>'
sec=replace_once(sec,row_old,row_new,'Optimization outer rows')

# Existing local buttons are kept for compatibility, but wording now matches
# what they really do.
sec=sec.replace('Content="Перейти к применению"','Content="Применить выбранное"')
sec=sec.replace('Content="Применить набор"','Content="Применить выбранное"')
sec=sec.replace('Content="Выбрать Privacy SAFE"','Content="Применить Privacy SAFE"')
sec=sec.replace('Content="Выбрать Privacy STRICT"','Content="Применить Privacy STRICT"')
sec=sec.replace('Content="Выбрать Privacy MAX"','Content="Применить Privacy MAX"')

last=sec.rfind('\n    </Grid>\n</TabItem>')
if last<0: raise SystemExit('R45 Optimization closing anchor missing')
footer='''\n        <Border Grid.Row="3" Style="{StaticResource R43HeroCard}" Padding="10,7" Margin="0,7,0,0">\n            <Grid>\n                <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>\n                <StackPanel VerticalAlignment="Center">\n                    <TextBlock Text="ВЫБРАНО ДЛЯ ПРИМЕНЕНИЯ" Style="{StaticResource R43SectionLabel}"/>\n                    <TextBlock Text="{Binding SelectedTweaksText, Mode=OneWay}" FontSize="11.5" FontWeight="SemiBold" Margin="0,2,0,0"/>\n                    <TextBlock Text="{Binding ProfilePlanText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.1" TextTrimming="CharacterEllipsis"/>\n                </StackPanel>\n                <Button Grid.Column="1" Style="{StaticResource CompactSecondaryButton}" Command="{Binding ClearTweakSelectionCommand}" Content="Снять выбор" Margin="0,0,6,0" VerticalAlignment="Center"/>\n                <Button Grid.Column="2" Style="{StaticResource CompactPrimaryButton}" Command="{Binding ApplySelectedTweaksCommand}" Content="Применить выбранное" MinWidth="150" VerticalAlignment="Center"/>\n            </Grid>\n        </Border>'''
sec=sec[:last]+footer+sec[last:]
x=x[:start]+sec+x[end:]
write(xp,x)

# Version stamp all projects.
for csproj in (root/'src').glob('*/**/*.csproj'):
    c=read(csproj)
    c=re.sub(r'<Version>[^<]+</Version>','<Version>0.1.45</Version>',c)
    c=re.sub(r'<VersionPrefix>[^<]+</VersionPrefix>','<VersionPrefix>0.1.45</VersionPrefix>',c)
    c=re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>','<AssemblyVersion>0.1.45.0</AssemblyVersion>',c)
    c=re.sub(r'<FileVersion>[^<]+</FileVersion>','<FileVersion>0.1.45.0</FileVersion>',c)
    c=re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>','<InformationalVersion>0.1.45</InformationalVersion>',c)
    write(csproj,c)

# Release notes.
rp=root/'data'/'release_notes.json'
data=json.loads(read(rp)) if rp.exists() else {}
data['version']='0.1.45'
data['title']='R45 APPLY CENTER'
data['summary']='Исправлена маршрутизация вкладок после R44 и добавлена постоянная кнопка применения выбранных оптимизаций.'
data['changes']=[
    'После LIGHT / STANDARD / MAXIMUM / GAME / LITE BUILD открывается вкладка «Выбранное», а не «По одной».',
    'На всей странице Оптимизация закреплена нижняя панель с количеством выбранных пунктов и кнопкой «Применить выбранное».',
    'Ручной выбор «По одной» теперь всегда имеет доступную кнопку применения без перехода на другую вкладку.',
    'После запуска применения автоматически открывается «Ход работы».',
    'Privacy-кнопки переименованы в «Применить …», потому что эти команды действительно запускают пакет после подтверждения.',
    'R44 Smart Audit/Profiles/Privacy/Startup/Debloat, Snapshot/Undo, Gaming, Network и Update Center сохранены.'
]
write(rp,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(root/'R45_APPLY_CENTER.marker').write_text('R45 APPLY CENTER\nR44 optimization sub-tab routing fixed + global Apply Selected bar\n',encoding='utf-8')
print('R45 apply center patch: OK')
