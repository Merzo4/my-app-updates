from pathlib import Path
import json, os, re

root = Path(os.environ['SOURCE_ROOT'])
app = root/'src'/'MerzoOptimizer.App'

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s, encoding='utf-8')

def must_replace(s, old, new, label):
    if old not in s:
        raise SystemExit(f'R42 anchor missing: {label}')
    return s.replace(old, new)

# ---------------------------------------------------------------------------
# R42 shared design system. The whole application keeps one calm dark/teal
# language; the patch changes presentation only and intentionally leaves all
# commands, services, IDs, bindings and apply/undo logic in place.
# ---------------------------------------------------------------------------
ap = app/'App.xaml'
a = read(ap)
colors = {
    '#0B0E13':'#091017', '#10151D':'#0D151D', '#0E1218':'#0B1219',
    '#151B24':'#111C26', '#1A2230':'#172631', '#111720':'#0F1821',
    '#243040':'#263A48', '#1C2633':'#1C2D39', '#3E9B91':'#55B8AC',
    '#16312F':'#142F2D', '#4AA99E':'#69C8BC', '#F4F7FA':'#F2F7F8',
    '#C4CDD8':'#CBD6DB', '#8492A4':'#899AA6', '#F1C66D':'#EBC56D',
    '#FF7C87':'#F1848D', '#111820':'#0E1820', '#33475A':'#2B4554',
    '#1E504C':'#235D57', '#2A6B65':'#33756D', '#285F5A':'#2B6A63',
    '#347B74':'#3B857C', '#193F3C':'#1C4C48', '#182A2B':'#162B2B',
    '#263A3C':'#29413F', '#6F8483':'#78908E', '#17202B':'#14212B',
    '#202936':'#1D2B37', '#283545':'#243847', '#27534D':'#2C5F58',
    '#121923':'#0F1A23', '#20423D':'#1C443F', '#27313E':'#20313D',
    '#101B22':'#0E1A22', '#2A4B54':'#28505A', '#102A26':'#102D2A',
    '#2B655A':'#317168', '#173A35':'#173B37', '#2A5F56':'#2E6961',
    '#141B24':'#111C26', '#112923':'#102A27', '#101820':'#0E1921',
    '#21171A':'#20171B', '#633642':'#633B45', '#351D24':'#342027',
    '#6A3442':'#70404A', '#10201F':'#102321', '#3D716B':'#397A71',
    '#173733':'#173C38', '#2A5A56':'#2D655F', '#69A7EF':'#72AEEF',
    '#6FC1B7':'#6CC8BD', '#6BCABE':'#72D0C4'
}
for old,new in colors.items():
    a = a.replace(old,new)

a = a.replace('FontSize" Value="13"', 'FontSize" Value="14"')
a = a.replace('<Setter Property="FontSize" Value="20"/>', '<Setter Property="FontSize" Value="24"/>')
a = a.replace('<Setter Property="FontSize" Value="14"/>\n            <Setter Property="FontWeight" Value="SemiBold"/>\n            <Setter Property="Foreground" Value="{StaticResource TextPrimary}"/>\n        </Style>\n\n        <Style x:Key="Eyebrow"', '<Setter Property="FontSize" Value="16"/>\n            <Setter Property="FontWeight" Value="SemiBold"/>\n            <Setter Property="Foreground" Value="{StaticResource TextPrimary}"/>\n        </Style>\n\n        <Style x:Key="Eyebrow"')
a = a.replace('<Setter Property="FontSize" Value="10.5"/>', '<Setter Property="FontSize" Value="11"/>')
a = a.replace('<Setter Property="CornerRadius" Value="7"/>\n            <Setter Property="Padding" Value="8"/>\n            <Setter Property="Margin" Value="0,0,6,6"/>', '<Setter Property="CornerRadius" Value="12"/>\n            <Setter Property="Padding" Value="12"/>\n            <Setter Property="Margin" Value="0,0,9,9"/>')
a = a.replace('<Setter Property="Padding" Value="8"/>\n            <Setter Property="CornerRadius" Value="8"/>', '<Setter Property="Padding" Value="11"/>\n            <Setter Property="CornerRadius" Value="12"/>')
a = a.replace('<Setter Property="Padding" Value="10,5"/>', '<Setter Property="Padding" Value="13,7"/>')
a = a.replace('<Setter Property="MinHeight" Value="30"/>', '<Setter Property="MinHeight" Value="34"/>')
a = a.replace('CornerRadius="9" Padding="{TemplateBinding Padding}"', 'CornerRadius="10" Padding="{TemplateBinding Padding}"')
a = a.replace('<Setter Property="MinHeight" Value="32"/>', '<Setter Property="MinHeight" Value="34"/>')
a = a.replace('<Setter Property="Padding" Value="12,5"/>', '<Setter Property="Padding" Value="13,6"/>')
a = a.replace('<Setter Property="Padding" Value="11,5"/>', '<Setter Property="Padding" Value="12,6"/>')
a = a.replace('<Setter Property="Padding" Value="10"/>\n            <Setter Property="Margin" Value="0,0,7,7"/>\n            <Setter Property="CornerRadius" Value="10"/>', '<Setter Property="Padding" Value="13"/>\n            <Setter Property="Margin" Value="0,0,9,9"/>\n            <Setter Property="CornerRadius" Value="12"/>')
a = a.replace('<Setter Property="Padding" Value="8,6"/>\n            <Setter Property="Margin" Value="0,1"/>', '<Setter Property="Padding" Value="10,7"/>\n            <Setter Property="Margin" Value="0,2"/>')
a = a.replace('CornerRadius="9"\n                                Padding="{TemplateBinding Padding}"', 'CornerRadius="10"\n                                Padding="{TemplateBinding Padding}"')
a = a.replace('<Setter Property="RowHeight" Value="26"/>', '<Setter Property="RowHeight" Value="32"/>')
a = a.replace('<Setter Property="ColumnHeaderHeight" Value="28"/>', '<Setter Property="ColumnHeaderHeight" Value="34"/>')
a = a.replace('<Setter Property="Height" Value="3"/>', '<Setter Property="Height" Value="5"/>')
a = a.replace('<Setter Property="Width" Value="36"/>\n            <Setter Property="Height" Value="32"/>', '<Setter Property="Width" Value="44"/>\n            <Setter Property="Height" Value="42"/>')

# Keep plain controls dark as well. This eliminates white native islands in
# dialogs/feedback panes without changing their behavior.
implicit = '''
        <!-- R42 shared fallback controls: no white native islands -->
        <Style TargetType="TextBox">
            <Setter Property="Background" Value="{StaticResource CardAlt}"/>
            <Setter Property="Foreground" Value="{StaticResource TextPrimary}"/>
            <Setter Property="BorderBrush" Value="{StaticResource Border}"/>
            <Setter Property="BorderThickness" Value="1"/>
            <Setter Property="CaretBrush" Value="{StaticResource Accent}"/>
            <Setter Property="Padding" Value="9,6"/>
            <Setter Property="SelectionBrush" Value="{StaticResource AccentSoft}"/>
        </Style>
        <Style TargetType="ComboBox">
            <Setter Property="Background" Value="{StaticResource CardAlt}"/>
            <Setter Property="Foreground" Value="{StaticResource TextPrimary}"/>
            <Setter Property="BorderBrush" Value="{StaticResource Border}"/>
            <Setter Property="MinHeight" Value="32"/>
            <Setter Property="Padding" Value="8,4"/>
        </Style>
        <Style TargetType="ListBox">
            <Setter Property="Background" Value="Transparent"/>
            <Setter Property="Foreground" Value="{StaticResource TextPrimary}"/>
            <Setter Property="BorderThickness" Value="0"/>
        </Style>
        <Style TargetType="ListView">
            <Setter Property="Background" Value="Transparent"/>
            <Setter Property="Foreground" Value="{StaticResource TextPrimary}"/>
            <Setter Property="BorderThickness" Value="0"/>
        </Style>
'''
if 'R42 shared fallback controls' not in a:
    a = a.replace('    </Application.Resources>', implicit + '    </Application.Resources>')
write(ap,a)

# ---------------------------------------------------------------------------
# Main window shell: larger 2K-friendly geometry, 44px title bar, readable
# navigation, calmer grouping. The TabControl and every existing TabItem stay
# intact, so no page command/binding is lost.
# ---------------------------------------------------------------------------
mp = app/'MainWindow.xaml'
x = read(mp)
x = re.sub(r'Title="Merzo Windows Optimizer[^\"]*"', 'Title="Merzo Windows Optimizer — Production 0.1.42 · R42 FULL UI REWORK"', x, count=1)
x = x.replace('Width="1000" Height="600"', 'Width="1180" Height="680"')
x = x.replace('MinWidth="880" MinHeight="520"', 'MinWidth="1000" MinHeight="600"')
x = x.replace('CaptionHeight="36"', 'CaptionHeight="44"')
x = x.replace('<RowDefinition Height="36"/>', '<RowDefinition Height="44"/>', 1)
x = x.replace('<ColumnDefinition Width="176"/>', '<ColumnDefinition Width="210"/>', 1)

top_start = x.index('        <!-- Compact title bar -->')
side_start = x.index('        <!-- Dense navigation -->')
tabs_start = x.index('        <TabControl x:Name="MainTabs"', side_start)
new_top = '''        <!-- R42 unified title bar -->
        <Border Grid.Row="0" Grid.ColumnSpan="2" Background="{StaticResource TopBarBg}" BorderBrush="{StaticResource BorderSoft}" BorderThickness="0,0,0,1">
            <Grid>
                <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                <StackPanel Grid.Column="0" Orientation="Horizontal" VerticalAlignment="Center" Margin="14,0,0,0">
                    <Border Width="26" Height="26" Background="{StaticResource Accent}" CornerRadius="8" Margin="0,0,9,0">
                        <TextBlock Text="M" Foreground="#07110F" FontWeight="Bold" FontSize="13" HorizontalAlignment="Center" VerticalAlignment="Center"/>
                    </Border>
                    <StackPanel VerticalAlignment="Center">
                        <TextBlock Text="Merzo Windows Optimizer" FontWeight="SemiBold" FontSize="13.5"/>
                        <TextBlock Text="Production R42 · 0.1.42" Foreground="{StaticResource TextMuted}" FontSize="10.5" Margin="0,-1,0,0"/>
                    </StackPanel>
                </StackPanel>
                <StackPanel Grid.Column="1" Orientation="Horizontal" VerticalAlignment="Center" Margin="0,0,8,0">
                    <Border Background="{StaticResource AccentSoft}" BorderBrush="#2C5F58" BorderThickness="1" CornerRadius="12" Padding="9,3" Margin="0,0,8,0">
                        <StackPanel Orientation="Horizontal"><Ellipse Width="6" Height="6" Fill="{StaticResource Accent}" Margin="0,0,6,0" VerticalAlignment="Center"/><TextBlock Text="SNAPSHOT + UNDO" Foreground="{StaticResource Accent}" FontSize="10.5" FontWeight="SemiBold"/></StackPanel>
                    </Border>
                    <TextBlock Text="Режим: " Foreground="{StaticResource TextMuted}" FontSize="11.5" VerticalAlignment="Center"/>
                    <TextBlock Text="{Binding AdminText, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="11.5" FontWeight="SemiBold" VerticalAlignment="Center"/>
                </StackPanel>
                <StackPanel Grid.Column="2" Orientation="Horizontal" shell:WindowChrome.IsHitTestVisibleInChrome="True">
                    <Button Style="{StaticResource TitleBarButton}" Content="&#xE921;" Click="Minimize_Click"/>
                    <Button Style="{StaticResource TitleBarButton}" Content="&#xE922;" Click="MaximizeRestore_Click"/>
                    <Button Style="{StaticResource CloseTitleBarButton}" Content="&#xE8BB;" Click="Close_Click"/>
                </StackPanel>
            </Grid>
        </Border>

'''
new_side = '''        <!-- R42 unified navigation -->
        <Border Grid.Row="1" Grid.Column="0" Background="{StaticResource SidebarBg}" BorderBrush="{StaticResource BorderSoft}" BorderThickness="0,0,1,0">
            <DockPanel Margin="10,12,10,10">
                <Border DockPanel.Dock="Bottom" Background="#102622" BorderBrush="#26554E" BorderThickness="1" CornerRadius="11" Padding="10,8" Margin="0,8,0,0">
                    <StackPanel>
                        <StackPanel Orientation="Horizontal"><Ellipse Width="7" Height="7" Fill="{StaticResource Accent}" Margin="0,0,7,0" VerticalAlignment="Center"/><TextBlock Text="Защищённый режим" Foreground="{StaticResource Accent}" FontSize="11.5" FontWeight="SemiBold"/></StackPanel>
                        <TextBlock Text="Snapshot · Verify · Undo" Foreground="{StaticResource TextMuted}" FontSize="10.5" Margin="0,3,0,0"/>
                    </StackPanel>
                </Border>
                <StackPanel>
                    <StackPanel Margin="6,0,4,11">
                        <TextBlock Text="MERZO" Foreground="{StaticResource Accent}" FontSize="11" FontWeight="Bold"/>
                        <TextBlock Text="Windows Optimizer" FontSize="17" FontWeight="SemiBold" Margin="0,1,0,0"/>
                        <TextBlock Text="v0.1.42 · FULL UI REWORK" Foreground="{StaticResource TextMuted}" FontSize="10.5"/>
                    </StackPanel>
                    <TextBlock Style="{StaticResource Eyebrow}" Text="РАЗДЕЛЫ" Margin="7,0,0,4"/>
                    <RadioButton x:Name="DashboardNav" GroupName="MainNav" IsChecked="True" Style="{StaticResource NavRadioButton}" Click="Dashboard_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE80F;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Главная" FontWeight="SemiBold"/></StackPanel></RadioButton>
                    <RadioButton x:Name="AuditNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Audit_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE721;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Аудит системы" FontWeight="SemiBold"/></StackPanel></RadioButton>
                    <RadioButton x:Name="TweaksNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Tweaks_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE72E;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Оптимизация" FontWeight="SemiBold"/></StackPanel></RadioButton>
                    <RadioButton x:Name="StartupNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Startup_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE7B8;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Автозагрузка" FontWeight="SemiBold"/></StackPanel></RadioButton>
                    <RadioButton x:Name="CleanupNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Cleanup_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE74D;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Очистка / Debloat" FontWeight="SemiBold"/></StackPanel></RadioButton>
                    <RadioButton x:Name="ServicesTasksNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="ServicesTasks_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE90F;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Службы / задачи" FontWeight="SemiBold"/></StackPanel></RadioButton>
                    <RadioButton x:Name="PowerNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Power_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE945;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Питание" FontWeight="SemiBold"/></StackPanel></RadioButton>
                    <RadioButton x:Name="UpdatesNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Updates_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE895;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Обновления" FontWeight="SemiBold"/></StackPanel></RadioButton>
                    <RadioButton x:Name="RestoreNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Restore_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE7A7;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Восстановление" FontWeight="SemiBold"/></StackPanel></RadioButton>
                    <RadioButton x:Name="LogsNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Logs_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE81C;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Журнал" FontWeight="SemiBold"/></StackPanel></RadioButton>
                    <RadioButton x:Name="GamingDevNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="GamingDev_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE7FC;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Gaming / Developer" FontWeight="SemiBold"/></StackPanel></RadioButton>
                    <RadioButton x:Name="NetworkNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Network_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE968;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Repair / Network" FontWeight="SemiBold"/></StackPanel></RadioButton>
                </StackPanel>
            </DockPanel>
        </Border>

'''
x = x[:top_start] + new_top + new_side + x[tabs_start:]

# Consistent content inset on every main page.
x = x.replace('Margin="11,8,11,9"', 'Margin="18,14,18,16"')

# Key pages get more air without introducing page-level fixed clipping.
x = x.replace('<RowDefinition Height="38"/>\n                        <RowDefinition Height="34"/>\n                        <RowDefinition Height="180"/>', '<RowDefinition Height="50"/>\n                        <RowDefinition Height="46"/>\n                        <RowDefinition Height="220"/>', 1)
x = x.replace('<Grid.RowDefinitions><RowDefinition Height="38"/><RowDefinition Height="34"/><RowDefinition Height="*"/></Grid.RowDefinitions>', '<Grid.RowDefinitions><RowDefinition Height="50"/><RowDefinition Height="44"/><RowDefinition Height="*"/></Grid.RowDefinitions>', 1)
x = x.replace('<RowDefinition Height="48"/>\n                            <RowDefinition Height="*"/>\n                            <RowDefinition Height="92"/>', '<RowDefinition Height="58"/>\n                            <RowDefinition Height="*"/>\n                            <RowDefinition Height="104"/>', 1)
x = x.replace('<Grid.RowDefinitions><RowDefinition Height="48"/><RowDefinition Height="72"/><RowDefinition Height="*"/></Grid.RowDefinitions>', '<Grid.RowDefinitions><RowDefinition Height="58"/><RowDefinition Height="92"/><RowDefinition Height="*"/></Grid.RowDefinitions>', 1)
x = x.replace('<Grid.RowDefinitions><RowDefinition Height="42"/><RowDefinition Height="118"/><RowDefinition Height="*"/></Grid.RowDefinitions>', '<Grid.RowDefinitions><RowDefinition Height="54"/><RowDefinition Height="148"/><RowDefinition Height="*"/></Grid.RowDefinitions>', 1)
x = x.replace('<Grid.RowDefinitions><RowDefinition Height="43"/><RowDefinition Height="61"/><RowDefinition Height="*"/></Grid.RowDefinitions>', '<Grid.RowDefinitions><RowDefinition Height="54"/><RowDefinition Height="80"/><RowDefinition Height="*"/></Grid.RowDefinitions>', 1)

# R42 wording/identity and the cumulative R40 read-only binding safety gate.
x = x.replace('Production R40','Production R42').replace('v0.1.40','v0.1.42')
x = x.replace('ProgressBar Value="{Binding NetworkProgress}" Maximum="100"', 'ProgressBar Value="{Binding NetworkProgress, Mode=OneWay}" Maximum="100"')
if 'ProgressBar Value="{Binding NetworkProgress, Mode=OneWay}"' not in x:
    raise SystemExit('R42 NetworkProgress OneWay gate missing')
if 'СЛЕДУЮЩИЕ ЭТАПЫ' in x:
    raise SystemExit('R42 legacy navigation heading survived')
write(mp,x)

# ---------------------------------------------------------------------------
# Apply the same palette to every app-owned XAML surface (splash, release notes,
# recommendation/operation dialogs, etc.). No code-behind behavior is changed.
# ---------------------------------------------------------------------------
for p in app.rglob('*.xaml'):
    if p == ap or p == mp:
        continue
    s = read(p)
    for old,new in colors.items():
        s = s.replace(old,new)
    s = s.replace('Production R40','Production R42').replace('v0.1.40','v0.1.42')
    # Older explicit production labels left by cumulative patches are visual-only.
    s = re.sub(r'Production R(?:3[3-9]|40)', 'Production R42', s)
    write(p,s)

# Version identity in app diagnostics/splash/feedback. Keep the safety logic.
for p in [app/'App.xaml.cs', app/'ViewModels'/'MainWindowViewModel.cs']:
    s = read(p)
    s = s.replace('Version: 0.1.40 / Production R40','Version: 0.1.42 / Production R42')
    s = s.replace('Версия: 0.1.40 / Production R40','Версия: 0.1.42 / Production R42')
    s = s.replace('MerzoDiagnostics-R40-','MerzoDiagnostics-R42-')
    s = s.replace('[Bug][R40]','[Bug][R42]').replace('[Feature][R40]','[Feature][R42]').replace('[Crash][R40]','[Crash][R42]')
    s = s.replace('"0.1.40" : pendingVersion','"0.1.42" : pendingVersion')
    s = s.replace('"0.1.40"','"0.1.42"') if p.name == 'App.xaml.cs' else s
    # Correct stale crash body inherited from older releases.
    s = re.sub(r'Версия: 0\.1\.\d+ / Production R\d+', 'Версия: 0.1.42 / Production R42', s)
    write(p,s)

# Project version stamps: all output assemblies must agree.
for csproj in (root/'src').rglob('*.csproj'):
    s = read(csproj)
    s = re.sub(r'<Version>[^<]+</Version>','<Version>0.1.42</Version>',s)
    s = re.sub(r'<VersionPrefix>[^<]+</VersionPrefix>','<VersionPrefix>0.1.42</VersionPrefix>',s)
    s = re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>','<AssemblyVersion>0.1.42.0</AssemblyVersion>',s)
    s = re.sub(r'<FileVersion>[^<]+</FileVersion>','<FileVersion>0.1.42.0</FileVersion>',s)
    s = re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>','<InformationalVersion>0.1.42</InformationalVersion>',s)
    write(csproj,s)

notes = {
  'version':'0.1.42',
  'title':'R42 FULL UI REWORK',
  'summary':'Полный единый интерфейс Merzo Windows Optimizer: новый shell, увеличенная читаемость, одна дизайн-система для всех разделов и сохранённая рабочая логика R39/R40.',
  'new':[
    'Единый R42 shell: увеличенный 2K-friendly интерфейс, 44px top bar, читаемая навигация и спокойная тёмная teal-палитра.',
    'Все 12 разделов, splash и app-owned окна используют общий дизайн-системный слой без белых системных островов.',
    'Главная, Оптимизация, Обновления и Repair / Network получили увеличенные рабочие области и более ясную визуальную иерархию.'
  ],
  'fixed':[
    'Сохранён cumulative R40 fix: NetworkProgress ProgressBar использует только Mode=OneWay.',
    'Обновлена видимая и диагностическая версия до 0.1.42 / Production R42, включая splash и crash report.',
    'Убрана устаревшая группа навигации «СЛЕДУЮЩИЕ ЭТАПЫ» — Gaming / Developer и Repair / Network являются полноценными разделами.'
  ],
  'retained':[
    'Snapshot → Apply → Verify → Log → Undo/Restore.',
    'R39 GAME BUILD: SAFE / PERFORMANCE / EXTREME / LAB и Gaming Network.',
    'Update Center с SHA-256 и подтверждением установки, Audit Memory, Process Reduction, Recovery и Feedback/Crash Reporter.'
  ]
}
write(root/'data'/'release_notes.json', json.dumps(notes, ensure_ascii=False, indent=2)+'\n')
(root/'R42_FULL_UI_REWORK.marker').write_text('R42 FULL UI REWORK\n', encoding='utf-8')
print('R42 full UI rework patch: OK')
