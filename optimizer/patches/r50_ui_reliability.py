from pathlib import Path
import json, os, re

root = Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')
def once(s, old, new, label):
    c=s.count(old)
    if c!=1: raise SystemExit(f'R50 {label} anchor count={c}')
    return s.replace(old,new,1)

xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xp)

# Exact shipped identity. R49 had the correct assembly version but a stale 0.1.48 subtitle.
x=once(x,'Title="Merzo Windows Optimizer — Production 0.1.49 · R49 PUBLIC READY"','Title="Merzo Windows Optimizer — Production 0.1.50 · R50 UI RELIABILITY"','window title')
x=once(x,'Text="Production R49 · 0.1.48"','Text="Production R50 · 0.1.50"','top subtitle')
x=once(x,'<TextBlock Text="R49" Foreground="{StaticResource Accent}" FontSize="9.2" FontWeight="Bold"/>','<TextBlock Text="R50" Foreground="{StaticResource Accent}" FontSize="9.2" FontWeight="Bold"/>','sidebar badge')

# Use our own compact expander chrome. This removes the native white circular arrow
# that visually conflicts with the dark Merzo shell.
style='''\n    <Window.Resources>\n        <Style x:Key="MerzoExpanderStyle" TargetType="{x:Type Expander}">\n            <Setter Property="HorizontalContentAlignment" Value="Stretch"/>\n            <Setter Property="VerticalContentAlignment" Value="Stretch"/>\n            <Setter Property="Template">\n                <Setter.Value>\n                    <ControlTemplate TargetType="{x:Type Expander}">\n                        <Grid>\n                            <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/></Grid.RowDefinitions>\n                            <ToggleButton x:Name="HeaderButton" Grid.Row="0" IsChecked="{Binding IsExpanded, RelativeSource={RelativeSource TemplatedParent}, Mode=TwoWay}" Background="Transparent" BorderThickness="0" Padding="2,4" HorizontalContentAlignment="Stretch">\n                                <ToggleButton.Template>\n                                    <ControlTemplate TargetType="{x:Type ToggleButton}">\n                                        <Border x:Name="HeaderHover" Background="Transparent" CornerRadius="7" Padding="{TemplateBinding Padding}">\n                                            <ContentPresenter HorizontalAlignment="{TemplateBinding HorizontalContentAlignment}" VerticalAlignment="Center"/>\n                                        </Border>\n                                        <ControlTemplate.Triggers>\n                                            <Trigger Property="IsMouseOver" Value="True"><Setter TargetName="HeaderHover" Property="Background" Value="#10242B"/></Trigger>\n                                        </ControlTemplate.Triggers>\n                                    </ControlTemplate>\n                                </ToggleButton.Template>\n                                <Grid>\n                                    <Grid.ColumnDefinitions><ColumnDefinition Width="18"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>\n                                    <TextBlock x:Name="Chevron" Text="&#xE70D;" FontFamily="Segoe MDL2 Assets" Foreground="{StaticResource Accent}" FontSize="10" VerticalAlignment="Center"/>\n                                    <ContentPresenter Grid.Column="1" ContentSource="Header" VerticalAlignment="Center"/>\n                                </Grid>\n                            </ToggleButton>\n                            <ContentPresenter x:Name="ExpandSite" Grid.Row="1" Visibility="Collapsed" ContentSource="Content" HorizontalAlignment="{TemplateBinding HorizontalContentAlignment}" VerticalAlignment="{TemplateBinding VerticalContentAlignment}"/>\n                        </Grid>\n                        <ControlTemplate.Triggers>\n                            <Trigger Property="IsExpanded" Value="True">\n                                <Setter TargetName="ExpandSite" Property="Visibility" Value="Visible"/>\n                                <Setter TargetName="Chevron" Property="Text" Value="&#xE70E;"/>\n                            </Trigger>\n                        </ControlTemplate.Triggers>\n                    </ControlTemplate>\n                </Setter.Value>\n            </Setter>\n        </Style>\n    </Window.Resources>\n'''
anchor='    </shell:WindowChrome.WindowChrome>\n\n    <Grid Background="{StaticResource WindowBg}">'
if anchor not in x: raise SystemExit('R50 Window.Resources anchor missing')
x=x.replace(anchor,'    </shell:WindowChrome.WindowChrome>\n'+style+'\n    <Grid Background="{StaticResource WindowBg}">',1)

x=once(x,'<Expander Header="Экспертные инструменты" Foreground="{StaticResource TextSecondary}" FontSize="10.5" Margin="2,8,2,0" IsExpanded="False">','<Expander Header="Экспертные инструменты" Style="{StaticResource MerzoExpanderStyle}" Foreground="{StaticResource TextSecondary}" FontSize="10.5" Margin="2,8,2,0" IsExpanded="False">','sidebar expander style')
x=once(x,'<Expander Grid.Row="4" Header="Дополнительно — ручная настройка, Privacy, LAB / скрытые исправления и ход работы" IsExpanded="False" Foreground="{StaticResource TextSecondary}" FontSize="10.2" Margin="2,0,2,0">','<Expander x:Name="BuildAdvancedExpander" Grid.Row="4" Header="Дополнительно — ручная настройка, Privacy, LAB / скрытые исправления и ход работы" Style="{StaticResource MerzoExpanderStyle}" IsExpanded="False" Foreground="{StaticResource TextSecondary}" FontSize="10.2" Margin="2,0,2,0">','build expander style')

# The R49 bug: expanded expert content was taller than Grid.Row 4 and got clipped by PageRoot2.
# Wrap the whole advanced area in a constrained viewer so the header remains usable and
# all expert tabs can actually be reached at 1000x600 and the 920x560 minimum.
sec=x.index('x:Name="PageRoot2"')
exp=x.index('<Expander x:Name="BuildAdvancedExpander"',sec)
open_end=x.index('>',exp)+1
border=x.index('<Border Style="{StaticResource R43PageCard}"',open_end)
x=x[:border]+'<ScrollViewer x:Name="BuildAdvancedScroll" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled" CanContentScroll="False">\n            '+x[border:]
exp_end=x.index('</Expander>',border)
x=x[:exp_end]+'            </ScrollViewer>\n        '+x[exp_end:]

# Long hardware / power strings remain readable without making the compact dashboard wider.
x=once(x,'Text="{Binding CpuText, Mode=OneWay}" TextTrimming="CharacterEllipsis"','Text="{Binding CpuText, Mode=OneWay}" TextTrimming="CharacterEllipsis" ToolTip="{Binding CpuText, Mode=OneWay}"','cpu tooltip')
x=once(x,'Text="{Binding PowerPlanText, Mode=OneWay}" TextTrimming="CharacterEllipsis"','Text="{Binding PowerPlanText, Mode=OneWay}" TextTrimming="CharacterEllipsis" ToolTip="{Binding PowerPlanText, Mode=OneWay}"','power tooltip')
write(xp,x)

# Stamp all production assemblies as 0.1.50.
for p in (root/'src').rglob('*.csproj'):
    s=read(p)
    s=s.replace('0.1.49.0','0.1.50.0').replace('0.1.49','0.1.50')
    write(p,s)

app=root/'src'/'MerzoOptimizer.App'/'App.xaml.cs'
s=read(app).replace('0.1.49','0.1.50').replace('[Crash][R49]','[Crash][R50]').replace('Production R49','Production R50')
write(app,s)

sp=root/'src'/'MerzoOptimizer.SelfTest'/'Program.cs'
s=read(sp).replace('PRODUCTION R49 PUBLIC READY','PRODUCTION R50 UI RELIABILITY')
write(sp,s)

# Release Center entry if the data file uses the current JSON list contract.
rp=root/'data'/'release_notes.json'
try:
    data=json.loads(read(rp))
    entry={
      'version':'0.1.50',
      'title':'R50 UI RELIABILITY',
      'changes':[
        'Исправлено раскрытие блока Дополнительно на странице Сборки: экспертный контент теперь имеет собственную прокрутку и не обрезается низом окна.',
        'Исправлена отображаемая версия в шапке.',
        'Белые системные стрелки Expander заменены компактными Merzo-chevron.',
        'Полные CPU и Power Plan доступны по наведению без увеличения компактного окна.',
        'R49 Recovery/OneDrive/трёхсборочная логика и R48 OTA/security сохранены.'
      ]
    }
    if isinstance(data,list):
        data=[e for e in data if not (isinstance(e,dict) and e.get('version')=='0.1.50')]
        data.insert(0,entry)
        write(rp,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    elif isinstance(data,dict) and isinstance(data.get('releases'),list):
        data['releases']=[e for e in data['releases'] if not (isinstance(e,dict) and e.get('version')=='0.1.50')]
        data['releases'].insert(0,entry)
        write(rp,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
except Exception:
    pass

(root/'R50_UI_RELIABILITY.marker').write_text('R50 UI RELIABILITY\nBuilds advanced scroll + Merzo expanders + version identity\n',encoding='utf-8')
print('R50 UI reliability patch: OK')
