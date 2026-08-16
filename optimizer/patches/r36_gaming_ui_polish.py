from pathlib import Path
import json, os, re

root = Path(os.environ['SOURCE_ROOT'])

def read(path):
    return path.read_text(encoding='utf-8-sig')

def write(path, text):
    path.write_text(text, encoding='utf-8')

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'R36 anchor missing: {label}')
    return text.replace(old, new, 1)

# -----------------------------------------------------------------------------
# R36 GAMING/DEVELOPER FLOW + CALM UI PALETTE
# User acceptance from R35 showed two concrete issues:
# 1) Gaming/Developer did select categories, but only navigated to Optimization,
#    leaving the Profiles sub-tab visible so the result looked like "nothing".
# 2) Full-fill primary buttons were still too bright on a dark 2K desktop.
# -----------------------------------------------------------------------------

vm_path = root / 'src' / 'MerzoOptimizer.App' / 'ViewModels' / 'MainWindowViewModel.cs'
vm = read(vm_path)

vm = replace_once(
    vm,
    '        SelectGamingProfileCommand = new AsyncRelayCommand(() => SelectCategoryProfileAsync(new[] { "Gaming" }, safeOnly: false), () => !IsStage2Busy);\n        SelectDeveloperProfileCommand = new AsyncRelayCommand(() => SelectCategoryProfileAsync(new[] { "Developer", "Explorer", "Edge" }, safeOnly: false), () => !IsStage2Busy);',
    '        SelectGamingProfileCommand = new AsyncRelayCommand(() => SelectNamedCategoryPresetAsync("GAMING", new[] { "Gaming" }, safeOnly: false), () => !IsStage2Busy);\n        SelectDeveloperProfileCommand = new AsyncRelayCommand(() => SelectNamedCategoryPresetAsync("DEVELOPER", new[] { "Developer", "Explorer", "Edge" }, safeOnly: false), () => !IsStage2Busy);',
    'gaming/developer command flow')

old_category = '''    private Task SelectCategoryProfileAsync(IReadOnlyCollection<string> categories, bool safeOnly)
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
new_category = '''    private async Task SelectNamedCategoryPresetAsync(string title, IReadOnlyCollection<string> categories, bool safeOnly)
    {
        await SelectCategoryProfileAsync(categories, safeOnly);
        var selected = SafeTweaks.Count(static x => x.IsSelected);
        var safe = SafeTweaks.Count(static x => x.IsSelected && x.Definition.Risk == TweakRisk.Safe);
        var balanced = SafeTweaks.Count(static x => x.IsSelected && x.Definition.Risk == TweakRisk.Balanced);
        SelectedOptimizationTabIndex = 2;
        SelectedTweaksText = selected == 0
            ? $"{title}: новых неприменённых настроек нет"
            : $"{title} · Выбрано: {selected} · SAFE: {safe} · BALANCED: {balanced}";
        Stage2StatusText = selected == 0
            ? $"{title}: подходящие настройки уже применены или не поддерживаются на этом ПК."
            : $"{title} загружен: {selected} настроек. Проверьте вкладку «Выбранное» и применяйте только после просмотра списка.";
    }

    private Task SelectCategoryProfileAsync(IReadOnlyCollection<string> categories, bool safeOnly)
    {
        // Category/manual presets must never inherit STANDARD/MAXIMUM telemetry
        // side-effects from a profile that was selected earlier.
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
vm = replace_once(vm, old_category, new_category, 'category preset implementation')

# Keep CanExecute refresh coherent for both special presets. Insert only if the
# commands are already refreshed in the busy setter but Developer was omitted.
if 'SelectGamingProfileCommand.RaiseCanExecuteChanged();' in vm and 'SelectDeveloperProfileCommand.RaiseCanExecuteChanged();' not in vm:
    vm = vm.replace('SelectGamingProfileCommand.RaiseCanExecuteChanged();',
                    'SelectGamingProfileCommand.RaiseCanExecuteChanged();\n            SelectDeveloperProfileCommand.RaiseCanExecuteChanged();', 1)

# R34 feedback text survived through R35 in one code path; make diagnostics and
# GitHub prefilled reports identify the actual production build.
vm = vm.replace('[Merzo R34][{kind}]', '[Merzo R36][{kind}]')
vm = vm.replace('Версия Merzo: 0.1.34 / Production R34', 'Версия Merzo: 0.1.36 / Production R36')
vm = vm.replace('MerzoDiagnostics-R35-', 'MerzoDiagnostics-R36-')
vm = vm.replace('Version: 0.1.35 / Production R35', 'Version: 0.1.36 / Production R36')
write(vm_path, vm)

# -----------------------------------------------------------------------------
# Button palette: the accent can stay as identity for small indicators, but a
# primary action should be a dark teal surface, not a luminous full-fill mint.
# -----------------------------------------------------------------------------
app_path = root / 'src' / 'MerzoOptimizer.App' / 'App.xaml'
app = read(app_path)
app = app.replace('#46B5A5', '#3E9B91').replace('#56C1B0', '#4AA99E')
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
app = replace_once(app, old_primary, new_primary, 'primary button palette')
write(app_path, app)

# -----------------------------------------------------------------------------
# Main window text/version and Gaming page wording.
# -----------------------------------------------------------------------------
xaml_path = root / 'src' / 'MerzoOptimizer.App' / 'MainWindow.xaml'
x = read(xaml_path)
x = x.replace('Production R35', 'Production R36').replace('v0.1.35', 'v0.1.36')
x = x.replace('Foreground="#08110F"', 'Foreground="#EEF6F4"')
x = x.replace('Что добавлено в R32', 'Gaming / Developer — готовые наборы')
x = x.replace('Выбор переносится на страницу «Оптимизация», где перед применением будет показан полный список изменений.',
              'После выбора Merzo сразу откроет «Оптимизация → Выбранное», покажет точный набор и ничего не применит без вашего подтверждения.')
write(xaml_path, x)

# Splash/crash labels.
appcs_path = root / 'src' / 'MerzoOptimizer.App' / 'App.xaml.cs'
appcs = read(appcs_path)
appcs = appcs.replace('"0.1.35" : pendingVersion', '"0.1.36" : pendingVersion', 1)
appcs = appcs.replace('[Crash][R35]', '[Crash][R36]')
appcs = appcs.replace('Версия: 0.1.35 / Production R35', 'Версия: 0.1.36 / Production R36')
write(appcs_path, appcs)

# All production assemblies must agree on the release version.
for csproj in (root / 'src').glob('*/**/*.csproj'):
    s = read(csproj)
    s = re.sub(r'<Version>[^<]+</Version>', '<Version>0.1.36</Version>', s)
    s = re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>', '<AssemblyVersion>0.1.36.0</AssemblyVersion>', s)
    s = re.sub(r'<FileVersion>[^<]+</FileVersion>', '<FileVersion>0.1.36.0</FileVersion>', s)
    s = re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>', '<InformationalVersion>0.1.36</InformationalVersion>', s)
    write(csproj, s)

notes = {
    'version': '0.1.36',
    'title': 'R36 GAMING FLOW & CALM UI',
    'summary': 'Gaming/Developer теперь открывают реально выбранный набор, а основные кнопки получили тёмную спокойную teal-палитру без яркой заливки.',
    'added': [
        'Gaming preset: после нажатия автоматически выбираются доступные Gaming-твики и открывается «Оптимизация → Выбранное».',
        'Developer preset работает аналогично для Developer/Explorer/Edge и показывает точное число выбранных SAFE/BALANCED изменений.',
        'Явный статус GAMING/DEVELOPER в строке выбранного набора — пользователь сразу видит, что именно было подготовлено.'
    ],
    'changed': [
        'Primary/Compact/Table action-кнопки больше не используют яркий Accent как полную заливку: основной фон теперь тёмный teal с мягким hover/pressed.',
        'Фирменный Accent дополнительно приглушён; маленькие индикаторы и выделения сохраняют узнаваемый цвет.',
        'Страница Gaming / Developer больше не обещает просто переход — она объясняет, что откроется уже подготовленный список.'
    ],
    'fixed': [
        'Исправлен R35 UX-баг: Gaming/Developer действительно выбирали твики, но оставляли пользователя на вкладке «Профили», из-за чего казалось, что кнопка ничего не сделала.',
        'Category-наборы больше не наследуют скрытый STANDARD/MAXIMUM profile tag от предыдущего выбора, поэтому случайные telemetry services/tasks не попадут в применение.',
        'Feedback/Diagnostics/Crash labels обновлены до R36; R34/R35 функциональность, Snapshot/Undo и R33 runtime stability gates сохранены.'
    ]
}
write(root / 'data' / 'release_notes.json', json.dumps(notes, ensure_ascii=False, indent=2) + '\n')
(root / 'R36_GAMING_UI_POLISH.marker').write_text('R36 GAMING FLOW & CALM UI\n', encoding='utf-8')

print('R36 gaming/ui polish patch: OK')
