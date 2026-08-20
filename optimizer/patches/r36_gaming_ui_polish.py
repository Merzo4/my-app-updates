from pathlib import Path
import json, os, re

root = Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p, s): p.write_text(s, encoding='utf-8')
def once(s, old, new, label):
    if old not in s: raise SystemExit(f'R36 anchor missing: {label}')
    return s.replace(old, new, 1)

# Gaming / Developer: select the real set, clear stale profile side effects,
# and land directly on Optimization -> Selected so the result is visible.
vm_path = root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
vm = read(vm_path)
vm = once(vm,
'''        SelectGamingProfileCommand = new AsyncRelayCommand(() => SelectCategoryProfileAsync(new[] { "Gaming" }, safeOnly: false), () => !IsStage2Busy);
        SelectDeveloperProfileCommand = new AsyncRelayCommand(() => SelectCategoryProfileAsync(new[] { "Developer", "Explorer", "Edge" }, safeOnly: false), () => !IsStage2Busy);''',
'''        SelectGamingProfileCommand = new AsyncRelayCommand(() => SelectNamedCategoryPresetAsync("GAMING", new[] { "Gaming" }, safeOnly: false), () => !IsStage2Busy);
        SelectDeveloperProfileCommand = new AsyncRelayCommand(() => SelectNamedCategoryPresetAsync("DEVELOPER", new[] { "Developer", "Explorer", "Edge" }, safeOnly: false), () => !IsStage2Busy);''', 'commands')
old = '''    private Task SelectCategoryProfileAsync(IReadOnlyCollection<string> categories, bool safeOnly)
    {
        foreach (var card in SafeTweaks)
        {
            var categoryMatch = categories.Contains(card.Category, StringComparer.OrdinalIgnoreCase);
            var riskMatch = !safeOnly || card.Definition.Risk == TweakRisk.Safe;
            card.IsSelected = categoryMatch && riskMatch && !card.Definition.ScanOnly && card.IsSupported && !card.IsApplied;
        }
        RefreshSelectedTweaks();
        UpdateSelectedTweaksText();
        return Task.CompletedTask;
    }
'''
new = '''    private async Task SelectNamedCategoryPresetAsync(string title, IReadOnlyCollection<string> categories, bool safeOnly)
    {
        await SelectCategoryProfileAsync(categories, safeOnly);
        var selected = SafeTweaks.Count(static x => x.IsSelected);
        var safe = SafeTweaks.Count(static x => x.IsSelected && x.Definition.Risk == TweakRisk.Safe);
        var balanced = SafeTweaks.Count(static x => x.IsSelected && x.Definition.Risk == TweakRisk.Balanced);
        SelectedOptimizationTabIndex = 2;
        // UI contract examples: GAMING · Выбрано / DEVELOPER · Выбрано.
        SelectedTweaksText = selected == 0
            ? $"{title}: новых неприменённых настроек нет"
            : $"{title} · Выбрано: {selected} · SAFE: {safe} · BALANCED: {balanced}";
        Stage2StatusText = selected == 0
            ? $"{title}: подходящие настройки уже применены или не поддерживаются на этом ПК."
            : $"{title} загружен: {selected} настроек. Проверьте вкладку «Выбранное» и применяйте только после просмотра списка.";
    }

    private Task SelectCategoryProfileAsync(IReadOnlyCollection<string> categories, bool safeOnly)
    {
        _selectedProfileTag = null;
        foreach (var card in SafeTweaks)
        {
            var categoryMatch = categories.Contains(card.Category, StringComparer.OrdinalIgnoreCase);
            var riskMatch = !safeOnly || card.Definition.Risk == TweakRisk.Safe;
            card.IsSelected = categoryMatch && riskMatch && !card.Definition.ScanOnly && card.IsSupported && !card.IsApplied;
        }
        RefreshSelectedTweaks();
        UpdateSelectedTweaksText();
        SelectedOptimizationTabIndex = 2;
        return Task.CompletedTask;
    }
'''
vm = once(vm, old, new, 'category implementation')
if 'SelectGamingProfileCommand.RaiseCanExecuteChanged();' in vm and 'SelectDeveloperProfileCommand.RaiseCanExecuteChanged();' not in vm:
    vm = vm.replace('SelectGamingProfileCommand.RaiseCanExecuteChanged();', 'SelectGamingProfileCommand.RaiseCanExecuteChanged();\n            SelectDeveloperProfileCommand.RaiseCanExecuteChanged();', 1)
vm = vm.replace('[Merzo R34][{kind}]', '[Merzo R36][{kind}]')
vm = vm.replace('Версия Merzo: 0.1.34 / Production R34', 'Версия Merzo: 0.1.36 / Production R36')
vm = vm.replace('MerzoDiagnostics-R35-', 'MerzoDiagnostics-R36-')
vm = vm.replace('Version: 0.1.35 / Production R35', 'Version: 0.1.36 / Production R36')
write(vm_path, vm)

# Dark, calm primary buttons. Accent remains for small identity markers only.
app_path = root/'src'/'MerzoOptimizer.App'/'App.xaml'
app = read(app_path).replace('#46B5A5', '#3E9B91').replace('#56C1B0', '#4AA99E')
old_primary = '''        <Style x:Key="PrimaryButton" TargetType="Button">
            <Setter Property="Foreground" Value="#08110F"/>
            <Setter Property="Background" Value="{StaticResource Accent}"/>
            <Setter Property="BorderBrush" Value="{StaticResource Accent}"/>
            <Setter Property="BorderThickness" Value="1"/>
            <Setter Property="Padding" Value="10,5"/>
            <Setter Property="FontWeight" Value="SemiBold"/>
            <Setter Property="Cursor" Value="Hand"/>
            <Setter Property="MinHeight" Value="30"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="Button">
                        <Border x:Name="Border"
                                Background="{TemplateBinding Background}"
                                BorderBrush="{TemplateBinding BorderBrush}"
                                BorderThickness="{TemplateBinding BorderThickness}"
                                CornerRadius="9"
                                Padding="{TemplateBinding Padding}">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True">
                                <Setter TargetName="Border" Property="Background" Value="{StaticResource AccentHover}"/>
                            </Trigger>
                            <Trigger Property="IsPressed" Value="True">
                                <Setter TargetName="Border" Property="Opacity" Value="0.82"/>
                            </Trigger>
                            <Trigger Property="IsEnabled" Value="False">
                                <Setter TargetName="Border" Property="Background" Value="#294F49"/>
                                <Setter TargetName="Border" Property="BorderBrush" Value="#315A54"/>
                                <Setter Property="Foreground" Value="#9DBDB8"/>
                                <Setter Property="Cursor" Value="Arrow"/>
                                <Setter TargetName="Border" Property="Opacity" Value="0.72"/>
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>'''
new_primary = '''        <Style x:Key="PrimaryButton" TargetType="Button">
            <Setter Property="Foreground" Value="#EEF6F4"/>
            <Setter Property="Background" Value="#1E504C"/>
            <Setter Property="BorderBrush" Value="#2A6B65"/>
            <Setter Property="BorderThickness" Value="1"/>
            <Setter Property="Padding" Value="10,5"/>
            <Setter Property="FontWeight" Value="SemiBold"/>
            <Setter Property="Cursor" Value="Hand"/>
            <Setter Property="MinHeight" Value="30"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="Button">
                        <Border x:Name="Border" Background="{TemplateBinding Background}" BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="{TemplateBinding BorderThickness}" CornerRadius="9" Padding="{TemplateBinding Padding}">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True">
                                <Setter TargetName="Border" Property="Background" Value="#285F5A"/>
                                <Setter TargetName="Border" Property="BorderBrush" Value="#347B74"/>
                            </Trigger>
                            <Trigger Property="IsPressed" Value="True">
                                <Setter TargetName="Border" Property="Background" Value="#193F3C"/>
                                <Setter TargetName="Border" Property="Opacity" Value="1"/>
                            </Trigger>
                            <Trigger Property="IsEnabled" Value="False">
                                <Setter TargetName="Border" Property="Background" Value="#182A2B"/>
                                <Setter TargetName="Border" Property="BorderBrush" Value="#263A3C"/>
                                <Setter Property="Foreground" Value="#6F8483"/>
                                <Setter Property="Cursor" Value="Arrow"/>
                                <Setter TargetName="Border" Property="Opacity" Value="0.86"/>
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>'''
app = once(app, old_primary, new_primary, 'primary palette')
write(app_path, app)

xaml_path = root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x = read(xaml_path).replace('Production R35','Production R36').replace('v0.1.35','v0.1.36')
x = x.replace('Foreground="#08110F"','Foreground="#EEF6F4"')
x = x.replace('Что добавлено в R32','Gaming / Developer — готовые наборы')
x = x.replace('Выбор переносится на страницу «Оптимизация», где перед применением будет показан полный список изменений.', 'После выбора Merzo сразу откроет «Оптимизация → Выбранное», покажет точный набор и ничего не применит без вашего подтверждения.')
write(xaml_path, x)

appcs_path = root/'src'/'MerzoOptimizer.App'/'App.xaml.cs'
appcs = read(appcs_path).replace('"0.1.35" : pendingVersion','"0.1.36" : pendingVersion',1)
appcs = appcs.replace('[Crash][R35]','[Crash][R36]').replace('Версия: 0.1.35 / Production R35','Версия: 0.1.36 / Production R36')
write(appcs_path, appcs)

for p in (root/'src').glob('*/**/*.csproj'):
    s=read(p)
    s=re.sub(r'<Version>[^<]+</Version>','<Version>0.1.36</Version>',s)
    s=re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>','<AssemblyVersion>0.1.36.0</AssemblyVersion>',s)
    s=re.sub(r'<FileVersion>[^<]+</FileVersion>','<FileVersion>0.1.36.0</FileVersion>',s)
    s=re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>','<InformationalVersion>0.1.36</InformationalVersion>',s)
    write(p,s)

notes={'version':'0.1.36','title':'R36 GAMING FLOW & CALM UI','summary':'Gaming/Developer открывают реально выбранный набор; основные action-кнопки получили тёмную спокойную teal-палитру.','added':['Gaming и Developer автоматически открывают «Оптимизация → Выбранное» с точным количеством SAFE/BALANCED настроек.'],'changed':['Primary/Compact/Table action-кнопки используют тёмную teal-заливку вместо яркого mint Accent.','Фирменный accent дополнительно приглушён.'],'fixed':['Исправлен R35 UX-баг выбора Gaming/Developer.','Category-набор очищает старый profile tag, исключая скрытые side-effects предыдущего STANDARD/MAXIMUM.','Feedback/Diagnostics/Crash labels обновлены до R36.']}
write(root/'data'/'release_notes.json',json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
(root/'R36_GAMING_UI_POLISH.marker').write_text('R36 GAMING FLOW & CALM UI\n',encoding='utf-8')
print('R36 gaming/ui polish patch: OK')
