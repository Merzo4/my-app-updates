from pathlib import Path
import os,re,json

root=Path(os.environ.get('SOURCE_ROOT','/mnt/data/r28_work'))
VERSION='0.1.28'
RUNTIME='0.1.28.0'

# ---------------------------------------------------------------------------
# Version / visible identity
# ---------------------------------------------------------------------------
proj=root/'src'/'MerzoOptimizer.App'/'MerzoOptimizer.App.csproj'
p=proj.read_text(encoding='utf-8-sig')
p=re.sub(r'\s*<!-- MERZO_R2[6-8]_VERSION_BEGIN -->.*?<!-- MERZO_R2[6-8]_VERSION_END -->\s*','\n',p,flags=re.S)
stamp=f'''\n  <!-- MERZO_R28_VERSION_BEGIN -->
  <PropertyGroup>
    <Version>{VERSION}</Version>
    <VersionPrefix>{VERSION}</VersionPrefix>
    <AssemblyVersion>{RUNTIME}</AssemblyVersion>
    <FileVersion>{RUNTIME}</FileVersion>
    <InformationalVersion>{VERSION}</InformationalVersion>
  </PropertyGroup>
  <!-- MERZO_R28_VERSION_END -->\n'''
if '</Project>' not in p: raise SystemExit('Project end tag missing')
p=p.replace('</Project>',stamp+'</Project>',1)
proj.write_text(p,encoding='utf-8')

xaml=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=xaml.read_text(encoding='utf-8-sig')
x=re.sub(r'(<Window\b[^>]*\bTitle=")[^"]*(")',rf'\1Merzo Windows Optimizer — Production {VERSION} · R28 UX\2',x,count=1,flags=re.S)
x=re.sub(r'Production\s+R\d+(?:\s*·\s*[A-Z ]+)?','Production R28',x)
x=re.sub(r'Production\s+0\.1\.\d+(?:\s*·\s*[A-Z ]+)?',f'Production {VERSION}',x)
x=re.sub(r'v0\.1\.\d+',f'v{VERSION}',x)
x=x.replace('PRIVACY ENGINE ✓','PROFILE PRIVACY ✓').replace('PRIVACY ENGINE','PROFILE PRIVACY')

# ---------------------------------------------------------------------------
# Privacy is now part of the existing profiles, not a separate user-facing tab.
# LIGHT -> privacy-safe registry/policy
# STANDARD -> privacy-strict registry/policy + telemetry services/tasks
# MAXIMUM/LITE BUILD -> maximum privacy + WER service/tasks
# ---------------------------------------------------------------------------
tweaks_path=root/'data'/'tweaks.json'
tweaks=json.loads(tweaks_path.read_text(encoding='utf-8-sig'))
for t in tweaks:
    tags=t.setdefault('profile_tags',[])
    if 'privacy_safe' in tags:
        for tag in ('light','standard','maximum','lite_build'):
            if tag not in tags: tags.append(tag)
    if 'privacy_strict' in tags:
        for tag in ('standard','maximum','lite_build'):
            if tag not in tags: tags.append(tag)
    if 'privacy_maximum' in tags:
        for tag in ('maximum','lite_build'):
            if tag not in tags: tags.append(tag)
tweaks_path.write_text(json.dumps(tweaks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Remove the dedicated Telemetry tab inserted by R27.
x=re.sub(r'\n\s*<TabItem Header="Телеметрия" Style="\{StaticResource SubTabItem\}">.*?</TabItem>\n', '\n', x, count=1, flags=re.S)

# Make the profile cards explicitly explain the built-in privacy level.
x=x.replace('Реклама, рекомендации, лишний consumer-контент и самые безопасные фоновые настройки.',
            'Безопасная оптимизация + Privacy SAFE: реклама, Activity History, Spotlight, tailored experiences и лишний consumer-контент.')
x=x.replace('Всё из LIGHT плюс фоновые приложения, Game DVR, Delivery Optimization и более глубокая privacy/performance-настройка.',
            'Всё из LIGHT + Privacy STRICT: диагностические политики, DiagTrack/telemetry tasks, фоновые приложения, Game DVR и Delivery Optimization.')
x=x.replace('Всё из STANDARD плюс строгая конфиденциальность и тяжёлые обратимые настройки.',
            'Всё из STANDARD + Privacy MAX: максимальные обратимые privacy-настройки, WER service/tasks и более глубокая оптимизация.')
x=x.replace('Всё из STANDARD плюс строгая конфиденциальность и тяжёлые обратимые настройки для производительности.',
            'Всё из STANDARD + Privacy MAX: максимальные обратимые privacy-настройки, WER service/tasks и более глубокая оптимизация.')
x=x.replace('LITE BUILD: экспериментальный режим для уже облегчённых сборок.',
            'LITE BUILD: максимум профиля + Privacy MAX для уже облегчённых сборок.')

# Remove internal revision identifiers from user-facing text.
x=x.replace('R20 · ручное Disable/Restore с snapshot · KEEP правила заблокированы',
            'Ручное Disable/Restore с snapshot · критические KEEP-правила заблокированы')
x=x.replace('<!-- R20 Scan First + recommendation + profiles -->','<!-- Optimization profiles -->')
x=x.replace('<!-- R20: compact Cleanup Center + Debloat audit -->','<!-- Cleanup Center + Debloat audit -->')
x=x.replace('<!-- R20: Services + Scheduled Tasks reversible control -->','<!-- Services + Scheduled Tasks reversible control -->')
x=x.replace('<!-- R20: compact power center with explicit active plan -->','<!-- Compact power center with explicit active plan -->')

# ---------------------------------------------------------------------------
# Cleanup UI: third sub-tab dedicated to a persistent, visible operation flow.
# ---------------------------------------------------------------------------
cleanup_tab_anchor='<TabControl Grid.Row="1" Background="Transparent" BorderThickness="0" Margin="0,3,0,0">'
if cleanup_tab_anchor in x:
    x=x.replace(cleanup_tab_anchor,
                '<TabControl Grid.Row="1" Background="Transparent" BorderThickness="0" Margin="0,3,0,0" SelectedIndex="{Binding SelectedCleanupTabIndex, Mode=TwoWay}">',1)

progress_tab=r'''
                        <TabItem Header="Ход очистки" Style="{StaticResource SubTabItem}">
                            <Grid Margin="0,4,0,0">
                                <Grid.RowDefinitions><RowDefinition Height="118"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                                <Border Grid.Row="0" Background="#101B22" BorderBrush="#2A4B54" BorderThickness="1" CornerRadius="9" Padding="11,8" Margin="0,0,0,7">
                                    <Grid>
                                        <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                                        <Grid Grid.Row="0"><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                                            <StackPanel><TextBlock Text="{Binding CleanupOperationTitle, Mode=OneWay}" FontSize="12.5" FontWeight="SemiBold"/><TextBlock Text="{Binding CleanupOperationPhase, Mode=OneWay}" Foreground="{StaticResource Accent}" FontSize="9" FontWeight="SemiBold" Margin="0,2,0,0"/></StackPanel>
                                            <Border Grid.Column="1" Background="#173A35" BorderBrush="#2B655A" BorderThickness="1" CornerRadius="10" Padding="8,3" VerticalAlignment="Center"><TextBlock Text="{Binding CleanupProgressText, Mode=OneWay}" Foreground="{StaticResource Accent}" FontWeight="Bold" FontSize="9"/></Border>
                                        </Grid>
                                        <ProgressBar Grid.Row="1" Value="{Binding CleanupProgress, Mode=OneWay}" Maximum="100" Height="6" Margin="0,9,0,6"/>
                                        <Grid Grid.Row="2"><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
                                            <StackPanel Grid.Column="0"><TextBlock Text="Сейчас выполняется" Style="{StaticResource Eyebrow}"/><TextBlock Text="{Binding CleanupOperationDetail, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="8.5" TextWrapping="Wrap" Margin="0,2,12,0"/></StackPanel>
                                            <StackPanel Grid.Column="1"><TextBlock Text="Защита / результат" Style="{StaticResource Eyebrow}"/><TextBlock Text="{Binding CleanupOperationResult, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="8.5" TextWrapping="Wrap" Margin="0,2,0,0"/></StackPanel>
                                        </Grid>
                                    </Grid>
                                </Border>
                                <Border Grid.Row="1" Background="#0F151C" BorderBrush="{StaticResource BorderSoft}" BorderThickness="1" CornerRadius="9" Padding="8">
                                    <Grid><Grid.RowDefinitions><RowDefinition Height="26"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                                        <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><TextBlock Text="Этапы операции" FontSize="10.5" FontWeight="SemiBold"/><TextBlock Grid.Column="1" Text="Backup → Snapshot → Очистка → Проверка" Foreground="{StaticResource TextMuted}" FontSize="8"/></Grid>
                                        <ScrollViewer Grid.Row="1" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><ItemsControl ItemsSource="{Binding CleanupOperationSteps}"><ItemsControl.ItemTemplate><DataTemplate><Border Background="#121B24" BorderBrush="#202C39" BorderThickness="1" CornerRadius="7" Padding="8,5" Margin="0,0,0,4"><TextBlock Text="{Binding}" Foreground="{StaticResource TextSecondary}" FontSize="8.8" TextWrapping="Wrap"/></Border></DataTemplate></ItemsControl.ItemTemplate></ItemsControl></ScrollViewer>
                                    </Grid>
                                </Border>
                            </Grid>
                        </TabItem>
'''
if 'Header="Ход очистки"' not in x:
    close_anchor='''                        </TabItem>\n                    </TabControl>\n                </Grid>\n            </TabItem>\n\n            <!--'''
    cleanup_start=x.find('Text="Очистка / Debloat"')
    idx=x.find(close_anchor,cleanup_start)
    if idx < 0: raise SystemExit('Cleanup TabControl tail not found')
    insert_at=idx+len('                        </TabItem>')
    x=x[:insert_at]+progress_tab+x[insert_at:]

# Rich, non-empty tooltip for cleanup cards. Remove the two white/default tooltips.
x=x.replace(' ToolTip="{Binding RootPath}"','')
x=x.replace(' ToolTip="{Binding Description}"','')
card_open='<Border Width="392" Height="94" Style="{StaticResource CardBorder}" Margin="0,0,7,7" Padding="9,7">'
if card_open in x and 'Text="Что очищается"' not in x:
    rich_card='''<Border Width="392" Height="94" Style="{StaticResource CardBorder}" Margin="0,0,7,7" Padding="9,7">
                                                    <Border.ToolTip>
                                                        <ToolTip>
                                                            <StackPanel MaxWidth="430">
                                                                <TextBlock Text="{Binding Name, Mode=OneWay}" FontWeight="SemiBold" FontSize="11"/>
                                                                <TextBlock Text="Что очищается" Foreground="{StaticResource Accent}" FontSize="8" FontWeight="SemiBold" Margin="0,5,0,1"/>
                                                                <TextBlock Text="{Binding Description, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="8.5" TextWrapping="Wrap"/>
                                                                <TextBlock Text="Путь" Foreground="{StaticResource Accent}" FontSize="8" FontWeight="SemiBold" Margin="0,5,0,1"/>
                                                                <TextBlock Text="{Binding RootPath, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontFamily="Consolas" FontSize="8" TextWrapping="Wrap"/>
                                                                <TextBlock Text="Перед удалением создаются ZIP-backup и Snapshot; занятые/защищённые файлы пропускаются." Foreground="{StaticResource TextMuted}" FontSize="8" TextWrapping="Wrap" Margin="0,5,0,0"/>
                                                            </StackPanel>
                                                        </ToolTip>
                                                    </Border.ToolTip>'''
    x=x.replace(card_open,rich_card,1)

# ---------------------------------------------------------------------------
# Update Center: persistent changelog panel.
# ---------------------------------------------------------------------------
x=x.replace('GitHub Releases · обязательная SHA-256 проверка · установка только после подтверждения',
            'GitHub Releases · SHA-256 · уведомления об обновлении · полный список изменений')
x=x.replace('GitHub Updates · SHA-256 verification · автоматическая установка',
            'GitHub Updates · SHA-256 · уведомления · история изменений')

old_update_grid=re.compile(r'''                    <Grid Grid.Row="2">\s*<Grid.ColumnDefinitions><ColumnDefinition Width="1\*"/><ColumnDefinition Width="1\*"/></Grid.ColumnDefinitions>\s*<Border Grid.Column="0" Style="\{StaticResource PresetCardBorder\}".*?</Grid>\s*                </Grid>\s*            </TabItem>\s*\n\s*            <!-- Stage 2: Restore Center -->''',re.S)
new_update_grid=r'''                    <Grid Grid.Row="2">
                        <Grid.ColumnDefinitions><ColumnDefinition Width="1.65*"/><ColumnDefinition Width="1*"/></Grid.ColumnDefinitions>
                        <Border Grid.Column="0" Style="{StaticResource PresetCardBorder}" Margin="0,0,7,0" Padding="10,8">
                            <Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                                <StackPanel><TextBlock Text="Что нового" FontSize="13" FontWeight="SemiBold"/><TextBlock Text="{Binding UpdateReleaseTitleText, Mode=OneWay}" Foreground="{StaticResource Accent}" FontSize="9" FontWeight="SemiBold" Margin="0,3,0,5"/></StackPanel>
                                <ScrollViewer Grid.Row="1" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><TextBlock Text="{Binding UpdateReleaseNotesText, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="8.7" TextWrapping="Wrap" Padding="0,1,8,0"/></ScrollViewer>
                            </Grid>
                        </Border>
                        <Border Grid.Column="1" Style="{StaticResource PresetCardBorder}" Margin="0" Padding="10,8">
                            <StackPanel><TextBlock Text="Как проходит обновление" FontSize="12" FontWeight="SemiBold"/><TextBlock Text="1. При запуске Merzo проверяет свой канал релизов.&#x0a;2. Если версия новая — показывает уведомление и список изменений.&#x0a;3. Installer скачивается только после команды пользователя.&#x0a;4. SHA-256 проверяется до запуска.&#x0a;5. После первого запуска новой версии показывается окно «Что нового»." Foreground="{StaticResource TextSecondary}" FontSize="8.6" Margin="0,7,0,0" TextWrapping="Wrap"/><Border Background="#102D27" BorderBrush="#24554B" BorderThickness="1" CornerRadius="7" Padding="7,5" Margin="0,10,0,0"><TextBlock Text="Непроверенный installer не запускается. DEV/Portable не перезаписывается автоматически." Foreground="{StaticResource Accent}" FontSize="8.4" TextWrapping="Wrap"/></Border></StackPanel>
                        </Border>
                    </Grid>
                </Grid>
            </TabItem>

            <!-- Stage 2: Restore Center -->'''
x,count=old_update_grid.subn(new_update_grid,x,count=1)
if count==0: raise SystemExit('Update Center bottom grid replacement failed')
x=re.sub(r'Production R\d+: Check → Download → SHA-256 → Install\.',
         'Production R28: уведомление → changelog → SHA-256 → установка → «Что нового».',x)

xaml.write_text(x,encoding='utf-8')

# ---------------------------------------------------------------------------
# Dark tooltip style: fixes the white/blank tooltip appearance globally.
# ---------------------------------------------------------------------------
appx=root/'src'/'MerzoOptimizer.App'/'App.xaml'
a=appx.read_text(encoding='utf-8-sig')
if 'MERZO_R28_TOOLTIP_STYLE' not in a:
    anchor='''        <Style TargetType="TextBlock">\n            <Setter Property="Foreground" Value="{StaticResource TextPrimary}"/>\n        </Style>\n'''
    style=anchor+'''\n        <!-- MERZO_R28_TOOLTIP_STYLE -->
        <Style TargetType="ToolTip">
            <Setter Property="Background" Value="#111820"/>
            <Setter Property="Foreground" Value="{StaticResource TextPrimary}"/>
            <Setter Property="BorderBrush" Value="#33475A"/>
            <Setter Property="BorderThickness" Value="1"/>
            <Setter Property="Padding" Value="9,7"/>
            <Setter Property="HasDropShadow" Value="True"/>
            <Setter Property="Placement" Value="Mouse"/>
            <Setter Property="HorizontalOffset" Value="8"/>
            <Setter Property="VerticalOffset" Value="12"/>
        </Style>
'''
    if anchor not in a: raise SystemExit('App TextBlock style anchor missing')
    a=a.replace(anchor,style,1)
appx.write_text(a,encoding='utf-8')

# ---------------------------------------------------------------------------
# ViewModel: profile-integrated telemetry, cleanup visual flow, release notes.
# ---------------------------------------------------------------------------
vm=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s=vm.read_text(encoding='utf-8-sig')
field_anchor='    private string _cleanupStatusText = "Очистка: готова к сканированию";\n'
if '_cleanupOperationTitle' not in s:
    s=s.replace(field_anchor,field_anchor+'''    private string _cleanupOperationTitle = "Очистка ещё не запускалась";
    private string _cleanupOperationPhase = "Выберите категорию или пакет для очистки";
    private string _cleanupOperationDetail = "Здесь будет показано, что именно делает программа.";
    private string _cleanupOperationResult = "ZIP-backup + Snapshot + проверка результата";
    private double _cleanupProgress;
    private int _selectedCleanupTabIndex;
''',1)
if '_updateReleaseTitleText' not in s:
    s=s.replace('    private string _updateRepositoryText = "—";\n',
                '    private string _updateRepositoryText = "—";\n    private string _updateReleaseTitleText = "Что нового в текущей версии";\n    private string _updateReleaseNotesText = "Список изменений появится после проверки обновлений.";\n',1)
if '_selectedProfileTag' not in s:
    s=s.replace('    private int _selectedOptimizationTabIndex;\n',
                '    private int _selectedOptimizationTabIndex;\n    private string? _selectedProfileTag;\n    private string? _lastNotifiedUpdateVersion;\n',1)
collection_anchor='    public ObservableCollection<CleanupCategoryViewModel> CleanupCategories { get; } = [];\n'
if 'CleanupOperationSteps' not in s:
    s=s.replace(collection_anchor,collection_anchor+'    public ObservableCollection<string> CleanupOperationSteps { get; } = [];\n',1)
prop_anchor='    public string CleanupStatusText { get => _cleanupStatusText; private set => SetProperty(ref _cleanupStatusText, value); }\n'
if 'public string CleanupOperationTitle' not in s:
    s=s.replace(prop_anchor,prop_anchor+'''    public string CleanupOperationTitle { get => _cleanupOperationTitle; private set => SetProperty(ref _cleanupOperationTitle, value); }
    public string CleanupOperationPhase { get => _cleanupOperationPhase; private set => SetProperty(ref _cleanupOperationPhase, value); }
    public string CleanupOperationDetail { get => _cleanupOperationDetail; private set => SetProperty(ref _cleanupOperationDetail, value); }
    public string CleanupOperationResult { get => _cleanupOperationResult; private set => SetProperty(ref _cleanupOperationResult, value); }
    public double CleanupProgress { get => _cleanupProgress; private set { if (SetProperty(ref _cleanupProgress, Math.Clamp(value, 0, 100))) OnPropertyChanged(nameof(CleanupProgressText)); } }
    public string CleanupProgressText => $"{CleanupProgress:0}%";
    public int SelectedCleanupTabIndex { get => _selectedCleanupTabIndex; set => SetProperty(ref _selectedCleanupTabIndex, value); }
''',1)
update_prop='    public string UpdateRepositoryText { get => _updateRepositoryText; private set => SetProperty(ref _updateRepositoryText, value); }\n'
if 'public string UpdateReleaseTitleText' not in s:
    s=s.replace(update_prop,update_prop+'    public string UpdateReleaseTitleText { get => _updateReleaseTitleText; private set => SetProperty(ref _updateReleaseTitleText, value); }\n    public string UpdateReleaseNotesText { get => _updateReleaseNotesText; private set => SetProperty(ref _updateReleaseNotesText, value); }\n',1)
init_anchor='        UpdateOptimizationScanSummary(autoScan: true);\n'
if 'LoadLocalReleaseNotes();' not in s:
    s=s.replace(init_anchor,init_anchor+'        LoadLocalReleaseNotes();\n',1)

old_select='''    private Task SelectProfileAsync(string profileTag)
    {
        foreach (var card in SafeTweaks)
            card.IsSelected = !card.Definition.ScanOnly && card.ProfileTags.Contains(profileTag, StringComparer.OrdinalIgnoreCase) && card.IsSupported && !card.IsApplied;
        RefreshSelectedTweaks();
        UpdateSelectedTweaksText();
        SelectedOptimizationTabIndex = 2;
        return Task.CompletedTask;
    }
'''
new_select='''    private Task SelectProfileAsync(string profileTag)
    {
        _selectedProfileTag = profileTag;
        foreach (var card in SafeTweaks)
            card.IsSelected = !card.Definition.ScanOnly && card.ProfileTags.Contains(profileTag, StringComparer.OrdinalIgnoreCase) && card.IsSupported && !card.IsApplied;
        RefreshSelectedTweaks();
        UpdateSelectedTweaksText();
        SelectedOptimizationTabIndex = 2;
        Stage2StatusText = profileTag switch
        {
            "light" => "LIGHT выбран: базовая оптимизация + безопасная приватность.",
            "standard" => "STANDARD выбран: оптимизация + строгая privacy/telemetry-настройка.",
            "maximum" => "MAXIMUM выбран: глубокая оптимизация + максимальная обратимая приватность.",
            "lite_build" => "LITE BUILD выбран: расширенный профиль + максимальная privacy/telemetry-настройка.",
            _ => "Профиль выбран."
        };
        return Task.CompletedTask;
    }
'''
if old_select in s:
    s=s.replace(old_select,new_select,1)
else:
    s=s.replace('    private Task SelectProfileAsync(string profileTag)\n    {\n', '    private Task SelectProfileAsync(string profileTag)\n    {\n        _selectedProfileTag = profileTag;\n',1)
s=s.replace('''    private Task ClearTweakSelectionAsync()
    {
        foreach (var card in SafeTweaks)
''','''    private Task ClearTweakSelectionAsync()
    {
        _selectedProfileTag = null;
        foreach (var card in SafeTweaks)
''',1)
s=s.replace('LightProfileAvailableText = light == 0 ? "Уже настроено" : $"Ещё {light} изменений";',
            'LightProfileAvailableText = light == 0 ? "Уже настроено · Privacy SAFE" : $"Ещё {light} изменений · Privacy SAFE";')
s=s.replace('StandardProfileAvailableText = standard == 0 ? "Уже настроено" : $"Ещё {standard} изменений";',
            'StandardProfileAvailableText = standard == 0 ? "Уже настроено · Telemetry STRICT" : $"Ещё {standard} изменений · Telemetry STRICT";')
s=s.replace('MaximumProfileAvailableText = maximum == 0 ? "Уже настроено" : $"Ещё {maximum} изменений";',
            'MaximumProfileAvailableText = maximum == 0 ? "Уже настроено · Privacy MAX" : $"Ещё {maximum} изменений · Privacy MAX";')
s=s.replace('LiteBuildProfileAvailableText = liteBuild == 0 ? "Registry-часть уже настроена" : $"Ещё {liteBuild} обратимых изменений";',
            'LiteBuildProfileAvailableText = liteBuild == 0 ? "Уже настроено · Privacy MAX" : $"Ещё {liteBuild} изменений · Privacy MAX";')

apply_start=s.find('    private async Task ApplySelectedTweaksAsync()')
apply_end=s.find('    private void CleanupCategoryOnPropertyChanged',apply_start)
if apply_start<0 or apply_end<0: raise SystemExit('ApplySelectedTweaksAsync block not found')
apply_method=r'''    private async Task ApplySelectedTweaksAsync()
    {
        var selected = SafeTweaks.Where(static c => c.IsSelected && !c.Definition.ScanOnly && c.IsSupported && !c.IsApplied).ToArray();
        var profileTag = _selectedProfileTag;
        var profileIncludesTelemetry = profileTag is "standard" or "maximum" or "lite_build";
        var profileIncludesWer = profileTag is "maximum" or "lite_build";

        IReadOnlyList<ServiceAuditItem> services = Array.Empty<ServiceAuditItem>();
        IReadOnlyList<ScheduledTaskAuditItem> tasks = Array.Empty<ScheduledTaskAuditItem>();
        if (profileIncludesTelemetry)
        {
            var serviceSnapshot = await _serviceAudit.ScanAsync(_lifetimeCts.Token);
            var serviceNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "DiagTrack", "dmwappushservice" };
            if (profileIncludesWer) serviceNames.Add("WerSvc");
            services = serviceSnapshot.Where(x => serviceNames.Contains(x.ServiceName) && x.CanManage && !x.IsDisabled).ToArray();

            var taskSnapshot = await _taskAudit.ScanAsync(_lifetimeCts.Token);
            tasks = taskSnapshot.Where(x => x.CanManage && x.Enabled && IsPrivacyTelemetryTask(x) &&
                (profileIncludesWer || !x.FullPath.Contains(@"\Microsoft\Windows\Windows Error Reporting\", StringComparison.OrdinalIgnoreCase))).ToArray();
        }

        if (selected.Length == 0 && services.Count == 0 && tasks.Count == 0)
        {
            Stage2StatusText = "В выбранном профиле нет неприменённых изменений.";
            return;
        }

        var balancedCount = selected.Count(static c => c.Definition.Risk == TweakRisk.Balanced);
        var registryActions = selected.Sum(static c => c.Definition.RegistryActions.Count);
        var total = selected.Length + services.Count + tasks.Count;
        var privacyText = profileTag switch
        {
            "light" => "Privacy SAFE: безопасные privacy-политики без отключения telemetry-служб.",
            "standard" => $"Privacy STRICT: telemetry services {services.Count}, telemetry tasks {tasks.Count}.",
            "maximum" => $"Privacy MAX: telemetry/WER services {services.Count}, telemetry/WER tasks {tasks.Count}.",
            "lite_build" => $"Privacy MAX для LITE BUILD: services {services.Count}, tasks {tasks.Count}.",
            _ => "Ручной набор: дополнительные telemetry-службы автоматически не изменяются."
        };
        var warning = balancedCount > 0 ? $"\nBALANCED-изменений: {balancedCount}." : string.Empty;
        var confirmation = MessageBox.Show(
            $"Применить выбранный пакет?\n\nИзменений Registry/Policy: {selected.Length}\nRegistry-операций: {registryActions}\nСлужб телеметрии: {services.Count}\nЗадач телеметрии: {tasks.Count}{warning}\n\n{privacyText}\n\nПеред каждым изменением создаётся Snapshot. Если любой шаг завершится ошибкой, уже выполненные изменения этого запуска будут автоматически восстановлены.",
            "Merzo Windows Optimizer — применение профиля",
            MessageBoxButton.YesNo,
            (balancedCount > 0 || profileIncludesTelemetry) ? MessageBoxImage.Warning : MessageBoxImage.Question);
        if (confirmation != MessageBoxResult.Yes) return;

        SelectedOptimizationTabIndex = 3;
        DeepScanSteps.Clear();
        DeepScanProgress = 0;
        DeepScanStatusText = $"Применение профиля: 0/{total}";
        DeepScanSteps.Add($"План запущен · всего шагов {total} · Registry/Policy {selected.Length} · services {services.Count} · tasks {tasks.Count}");
        IsStage2Busy = true;
        var appliedSnapshotIds = new List<Guid>();
        var done = 0;
        try
        {
            foreach (var card in selected)
            {
                Stage2StatusText = $"Шаг {done + 1}/{total}: {card.Name}…";
                DeepScanStatusText = $"Registry/Policy {done + 1}/{total}: {card.Name}";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
                DeepScanSteps.Add($"→ {done + 1}/{total} · {card.Name}");
                var result = await _dispatcher.RunAsync($"Cumulative tweak {card.Id}", token => _tweakService.ApplyAsync(card.Definition, token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException($"{card.Name}: {result.Message}");
                if (result.Changed && result.SnapshotId is Guid id) appliedSnapshotIds.Add(id);
                done++;
                var snapshotLabel = result.SnapshotId is Guid snapshotGuid ? $" · snapshot {snapshotGuid.ToString("N")[..8]}" : string.Empty;
                DeepScanSteps[DeepScanSteps.Count - 1] = result.Changed ? $"✓ {done}/{total} · {card.Name}{snapshotLabel}" : $"✓ {done}/{total} · {card.Name} · уже настроено";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
            }

            foreach (var item in services)
            {
                Stage2StatusText = $"Шаг {done + 1}/{total}: отключение telemetry-службы {item.DisplayName}…";
                DeepScanStatusText = $"Telemetry service {done + 1}/{total}: {item.DisplayName}";
                DeepScanSteps.Add($"→ {done + 1}/{total} · служба {item.DisplayName}");
                var result = await _dispatcher.RunAsync($"Profile telemetry service {item.ServiceName}", token => _serviceAudit.DisableAsync(item.ServiceName, token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException($"{item.DisplayName}: {result.Message}");
                if (result.Changed && result.SnapshotId is Guid id) appliedSnapshotIds.Add(id);
                done++;
                DeepScanSteps[DeepScanSteps.Count - 1] = result.Changed ? $"✓ {done}/{total} · служба {item.DisplayName} отключена" : $"✓ {done}/{total} · служба {item.DisplayName} уже настроена";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
            }

            foreach (var item in tasks)
            {
                Stage2StatusText = $"Шаг {done + 1}/{total}: отключение telemetry-задачи {item.Name}…";
                DeepScanStatusText = $"Telemetry task {done + 1}/{total}: {item.Name}";
                DeepScanSteps.Add($"→ {done + 1}/{total} · задача {item.FullPath}");
                var result = await _dispatcher.RunAsync($"Profile telemetry task {item.FullPath}", token => _taskAudit.DisableAsync(item.Path, item.Name, token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException($"{item.FullPath}: {result.Message}");
                if (result.Changed && result.SnapshotId is Guid id) appliedSnapshotIds.Add(id);
                done++;
                DeepScanSteps[DeepScanSteps.Count - 1] = result.Changed ? $"✓ {done}/{total} · задача {item.Name} отключена" : $"✓ {done}/{total} · задача {item.Name} уже настроена";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
            }

            Stage2StatusText = $"Профиль применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count}.";
            DeepScanStatusText = $"План завершён: {done}/{total} · Snapshot {appliedSnapshotIds.Count}";
            DeepScanProgress = 100;
            DeepScanSteps.Add($"✓ Профиль завершён · Registry/Policy {selected.Length} · services {services.Count} · tasks {tasks.Count} · Snapshot {appliedSnapshotIds.Count}");
            foreach (var card in selected) card.IsSelected = false;
            _selectedProfileTag = null;
            RefreshSelectedTweaks();
            MessageBox.Show(Stage2StatusText + "\n\nПодробный ход операции сохранён на вкладке «Ход работы». Для отключённых служб рекомендуется перезагрузка Windows.", "Merzo Windows Optimizer — профиль применён", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested)
        {
            foreach (var snapshotId in appliedSnapshotIds.AsEnumerable().Reverse())
                await _dispatcher.RunAsync($"Rollback canceled snapshot {snapshotId:N}", token => _restoreService.RestoreAsync(snapshotId, token), CancellationToken.None);
            DeepScanStatusText = "Пакет остановлен · восстановление выполнено";
            Stage2StatusText = appliedSnapshotIds.Count > 0 ? "Пакет остановлен; изменения этого запуска восстановлены." : "Пакет остановлен.";
        }
        catch (Exception ex)
        {
            DeepScanStatusText = "Ошибка · выполняется восстановление…";
            foreach (var snapshotId in appliedSnapshotIds.AsEnumerable().Reverse())
                await _dispatcher.RunAsync($"Rollback snapshot {snapshotId:N}", token => _restoreService.RestoreAsync(snapshotId, token), CancellationToken.None);
            DeepScanStatusText = "Аварийное восстановление завершено";
            Stage2StatusText = $"Пакет отменён и восстановлен: {ex.Message}";
            MessageBox.Show(Stage2StatusText, "Merzo Windows Optimizer — восстановление", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            IsStage2Busy = false;
            if (!_lifetimeCts.IsCancellationRequested)
            {
                await RefreshStage2StateAsync();
                await RefreshServicesTasksAsync();
            }
        }
    }

'''
s=s[:apply_start]+apply_method+s[apply_end:]

clean_anchor='    private async Task CleanCategoryAsync(CleanupCategoryViewModel card)\n'
if 'private void BeginCleanupVisual' not in s:
    helpers=r'''    private void BeginCleanupVisual(string title, int categories, int files, long bytes)
    {
        SelectedCleanupTabIndex = 2;
        CleanupOperationSteps.Clear();
        CleanupProgress = 0;
        CleanupOperationTitle = title;
        CleanupOperationPhase = "Подготовка";
        CleanupOperationDetail = $"Категорий: {categories} · файлов: {files} · исходный объём: {FormatBytes(bytes)}";
        CleanupOperationResult = "Сначала создаётся ZIP-backup и Snapshot. Удаление начинается только после успешного резервирования.";
        CleanupOperationSteps.Add($"● Подготовка · категорий {categories} · файлов {files} · {FormatBytes(bytes)}");
    }

    private void SetCleanupVisual(double progress, string phase, string detail, string? result = null)
    {
        CleanupProgress = progress;
        CleanupOperationPhase = phase;
        CleanupOperationDetail = detail;
        if (!string.IsNullOrWhiteSpace(result)) CleanupOperationResult = result;
    }

'''
    if clean_anchor not in s: raise SystemExit('CleanCategoryAsync anchor missing')
    s=s.replace(clean_anchor,helpers+clean_anchor,1)

clean_start=s.find('    private async Task CleanCategoryAsync(CleanupCategoryViewModel card)')
clean_end=s.find('    private async Task RefreshDebloatAsync()',clean_start)
if clean_start<0 or clean_end<0: raise SystemExit('CleanCategoryAsync block not found')
clean_method=r'''    private async Task CleanCategoryAsync(CleanupCategoryViewModel card)
    {
        var confirmation = MessageBox.Show(
            $"Безопасно очистить категорию?\n\n{card.Name}\n{card.FileCountText} · {card.SizeText}\n{card.RootPath}\n\n" +
            "Перед очисткой программа создаст сжатую ZIP-копию и Snapshot восстановления. Только успешно сохранённые временные файлы будут удалены. Если резервная копия не даст экономии места или файл окажется занят, опасное удаление не выполняется.",
            "Merzo Windows Optimizer — безопасная очистка",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question);
        if (confirmation != MessageBoxResult.Yes) return;

        BeginCleanupVisual($"Очистка: {card.Name}", 1, card.Snapshot.EligibleFileCount, card.EligibleBytes);
        CleanupOperationSteps.Add($"→ Категория · {card.Name} · {card.FileCountText} · {card.SizeText}");
        CleanupOperationSteps.Add($"→ Путь · {card.RootPath}");
        SetCleanupVisual(18, "Проверка категории", $"Проверяю доступность и возраст файлов: {card.RootPath}");

        card.SetBusy(true);
        IsStage2Busy = true;
        CleanupStatusText = $"Создаю резервную копию и очищаю: {card.Name}…";
        try
        {
            SetCleanupVisual(32, "Backup → Snapshot → Очистка", $"Сохраняю подходящие файлы категории «{card.Name}» в ZIP, создаю Snapshot и только затем удаляю исходники.");
            CleanupOperationSteps.Add("→ Создание ZIP-backup и Snapshot восстановления");
            var result = await _dispatcher.RunAsync($"Cleanup {card.Id}", token => _cleanupService.CleanAsync(card.Id, token), _lifetimeCts.Token);
            SetCleanupVisual(88, "Проверка результата", "Проверяю результат очистки и состояние Snapshot…");

            CleanupStatusText = result.Changed ? $"{result.Message} Чистое освобождение: {FormatBytes(result.NetFreedBytes)}." : result.Message;
            if (result.Changed)
            {
                CleanupOperationSteps.Add($"✓ Удалено файлов: {result.ArchivedFileCount} · исходный объём {FormatBytes(result.OriginalBytes)} · ZIP {FormatBytes(result.BackupBytes)}");
                CleanupOperationSteps.Add($"✓ Чисто освобождено: {FormatBytes(result.NetFreedBytes)} · Snapshot {result.SnapshotId?.ToString("N")[..8]}");
                SetCleanupVisual(100, "Готово", $"Категория «{card.Name}» очищена.", $"Удалено: {result.ArchivedFileCount} файлов · освобождено: {FormatBytes(result.NetFreedBytes)} · восстановление доступно в разделе «Восстановление».");
            }
            else
            {
                CleanupOperationSteps.Add($"✓ Изменения не потребовались · {result.Message}");
                SetCleanupVisual(100, "Готово без изменений", result.Message, "Ничего опасного не удалено. Система осталась без изменений.");
            }
            MessageBox.Show(CleanupStatusText + "\n\nПодробности остаются на вкладке «Ход очистки».", "Merzo Windows Optimizer — очистка завершена", MessageBoxButton.OK, result.Success ? MessageBoxImage.Information : MessageBoxImage.Warning);
            await RefreshSnapshotsAsync();
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            CleanupStatusText = $"Ошибка очистки: {ex.Message}";
            CleanupOperationSteps.Add($"✕ Ошибка · {ex.Message}");
            SetCleanupVisual(100, "Ошибка", "Операция остановлена.", "Если были созданы изменения, механизм безопасности восстанавливает их через Snapshot/backup.");
            MessageBox.Show(CleanupStatusText, "Merzo Windows Optimizer — ошибка очистки", MessageBoxButton.OK, MessageBoxImage.Error);
        }
        finally
        {
            card.SetBusy(false);
            IsStage2Busy = false;
        }

        await RefreshCleanupAsync();
    }

'''
s=s[:clean_start]+clean_method+s[clean_end:]

pack_start=s.find('    private async Task CleanCategoryPackAsync(IReadOnlyList<CleanupCategoryViewModel> categories, string title)')
pack_end=s.find('    private async Task CleanAllSafeAsync()',pack_start)
if pack_start<0 or pack_end<0: raise SystemExit('CleanCategoryPackAsync block not found')
pack_method=r'''    private async Task CleanCategoryPackAsync(IReadOnlyList<CleanupCategoryViewModel> categories, string title)
    {
        if (categories.Count == 0) return;
        var bytes = categories.Sum(static c => c.EligibleBytes);
        var files = categories.Sum(static c => c.Snapshot.EligibleFileCount);
        var confirmation = MessageBox.Show(
            $"{title}\n\nКатегорий: {categories.Count}\nФайлов: {files}\nИсходный объём: {FormatBytes(bytes)}\n\n" +
            "Для каждой категории программа сначала создаёт ZIP-backup и Snapshot, затем очищает только успешно сохранённые файлы. Если любой шаг завершится ошибкой, уже выполненные изменения этого запуска будут автоматически восстановлены.",
            "Merzo Windows Optimizer — пакетная очистка",
            MessageBoxButton.YesNo,
            MessageBoxImage.Question);
        if (confirmation != MessageBoxResult.Yes) return;

        BeginCleanupVisual("Пакетная очистка", categories.Count, files, bytes);
        IsStage2Busy = true;
        var snapshots = new List<Guid>();
        long freed = 0;
        var cleanedFiles = 0;
        try
        {
            for (var i = 0; i < categories.Count; i++)
            {
                var category = categories[i];
                var baseProgress = i * 92.0 / categories.Count;
                CleanupStatusText = $"Очистка {i + 1}/{categories.Count}: {category.Name}…";
                SetCleanupVisual(baseProgress + 4, $"Категория {i + 1} из {categories.Count}", $"{category.Name} · {category.FileCountText} · {category.SizeText}\n{category.RootPath}", $"Snapshot создано: {snapshots.Count} · освобождено: {FormatBytes(freed)}");
                CleanupOperationSteps.Add($"→ {i + 1}/{categories.Count} · {category.Name} · {category.FileCountText} · {category.SizeText}");
                CleanupOperationSteps.Add($"   Backup → Snapshot → очистка · {category.RootPath}");

                var result = await _dispatcher.RunAsync($"Cleanup pack {category.Id}", token => _cleanupService.CleanAsync(category.Id, token), _lifetimeCts.Token);
                if (!result.Success)
                {
                    CleanupOperationSteps.Add($"✕ {i + 1}/{categories.Count} · {category.Name} · {result.Message}");
                    SetCleanupVisual(baseProgress + 6, "Ошибка · выполняется восстановление", result.Message, $"Восстанавливаю {snapshots.Count} уже созданных Snapshot…");
                    foreach (var snapshotId in snapshots.AsEnumerable().Reverse())
                        await _dispatcher.RunAsync($"Cleanup rollback {snapshotId:N}", token => _restoreService.RestoreAsync(snapshotId, token), CancellationToken.None);
                    CleanupStatusText = $"Очистка остановлена и восстановлена: {result.Message}";
                    CleanupOperationSteps.Add("↶ Все изменения этого запуска восстановлены.");
                    SetCleanupVisual(100, "Остановлено и восстановлено", "Пакет не оставил частично применённых изменений.", "Rollback завершён.");
                    MessageBox.Show(CleanupStatusText, "Merzo Windows Optimizer — восстановление", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }

                if (result.Changed && result.SnapshotId is Guid id)
                {
                    snapshots.Add(id);
                    freed += result.NetFreedBytes;
                    cleanedFiles += result.ArchivedFileCount;
                    CleanupOperationSteps.Add($"✓ {i + 1}/{categories.Count} · {category.Name} · удалено {result.ArchivedFileCount} · освобождено {FormatBytes(result.NetFreedBytes)} · Snapshot {id.ToString("N")[..8]}");
                }
                else
                {
                    CleanupOperationSteps.Add($"✓ {i + 1}/{categories.Count} · {category.Name} · без изменений · {result.Message}");
                }
                SetCleanupVisual((i + 1) * 92.0 / categories.Count, $"Завершено {i + 1} из {categories.Count}", $"Последняя категория: {category.Name}", $"Удалено файлов: {cleanedFiles} · Snapshot: {snapshots.Count} · освобождено: {FormatBytes(freed)}");
            }

            CleanupStatusText = $"Очистка завершена · Snapshot: {snapshots.Count} · чистое освобождение: {FormatBytes(freed)}.";
            CleanupOperationSteps.Add($"✓ Пакет завершён · категорий {categories.Count} · удалено файлов {cleanedFiles} · освобождено {FormatBytes(freed)} · Snapshot {snapshots.Count}");
            SetCleanupVisual(100, "Готово", $"Все {categories.Count} выбранных категорий обработаны.", $"Удалено: {cleanedFiles} файлов · освобождено: {FormatBytes(freed)} · Snapshot: {snapshots.Count}. Всё можно вернуть через «Восстановление».");
            MessageBox.Show(CleanupStatusText + "\n\nПодробности остаются на вкладке «Ход очистки».", "Merzo Windows Optimizer — очистка завершена", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested)
        {
            foreach (var snapshotId in snapshots.AsEnumerable().Reverse())
                await _dispatcher.RunAsync($"Cleanup canceled rollback {snapshotId:N}", token => _restoreService.RestoreAsync(snapshotId, token), CancellationToken.None);
            CleanupStatusText = snapshots.Count > 0 ? "Очистка остановлена; изменения этого запуска восстановлены." : "Очистка остановлена.";
            CleanupOperationSteps.Add("↶ Очистка остановлена при закрытии приложения; выполнено восстановление.");
            SetCleanupVisual(100, "Остановлено", CleanupStatusText, "Частично применённых изменений не оставлено.");
        }
        catch (Exception ex)
        {
            SetCleanupVisual(CleanupProgress, "Ошибка · выполняется восстановление", ex.Message, $"Snapshot для восстановления: {snapshots.Count}");
            foreach (var snapshotId in snapshots.AsEnumerable().Reverse())
                await _dispatcher.RunAsync($"Cleanup rollback {snapshotId:N}", token => _restoreService.RestoreAsync(snapshotId, token), CancellationToken.None);
            CleanupStatusText = $"Очистка аварийно остановлена и восстановлена: {ex.Message}";
            CleanupOperationSteps.Add($"✕ Ошибка · {ex.Message}");
            CleanupOperationSteps.Add("↶ Все изменения этого запуска восстановлены.");
            SetCleanupVisual(100, "Ошибка устранена восстановлением", ex.Message, "Rollback завершён.");
        }
        finally
        {
            IsStage2Busy = false;
            if (!_lifetimeCts.IsCancellationRequested)
            {
                await RefreshSnapshotsAsync();
                await RefreshCleanupAsync();
            }
        }
    }

'''
s=s[:pack_start]+pack_method+s[pack_end:]

s=s.replace('Удаление в R20 намеренно заблокировано до гарантированного Undo.', 'Удаление пока заблокировано до гарантированного Undo для Appx.')
s=s.replace('R20 автоматически откатит уже применённые шаги этого запуска.', 'программа автоматически восстановит уже применённые шаги этого запуска.')
s=s.replace('R20 сначала создаст сжатый ZIP-backup и snapshot, и только затем удалит успешно сохранённые временные файлы.', 'Сначала программа создаст сжатый ZIP-backup и Snapshot, и только затем удалит успешно сохранённые временные файлы.')

assign_anchor='''            UpdateStatusText = _lastUpdateCheck.Message;
            UpdateLatestText = _lastUpdateCheck.UpdateAvailable ? _lastUpdateCheck.LatestVersion : (_lastUpdateCheck.Configured ? "Актуально" : "Feed не настроен");
            DownloadUpdateCommand.RaiseCanExecuteChanged();
'''
if assign_anchor in s and 'UpdateReleaseTitleText = string.IsNullOrWhiteSpace' not in s:
    replacement=assign_anchor.replace('            DownloadUpdateCommand.RaiseCanExecuteChanged();\n','''            if (_lastUpdateCheck.Success)
            {
                UpdateReleaseTitleText = string.IsNullOrWhiteSpace(_lastUpdateCheck.ReleaseName) ? $"Версия {_lastUpdateCheck.LatestVersion}" : _lastUpdateCheck.ReleaseName;
                if (!string.IsNullOrWhiteSpace(_lastUpdateCheck.Notes)) UpdateReleaseNotesText = _lastUpdateCheck.Notes;
            }
            DownloadUpdateCommand.RaiseCanExecuteChanged();
''')
    s=s.replace(assign_anchor,replacement,1)
old_notice='''            if (!silent && _lastUpdateCheck is { Success: true, UpdateAvailable: true } available)
                MessageBox.Show($"Доступно обновление {available.LatestVersion}.\n\n{available.ReleaseName}\n\nНажмите «Скачать и установить». Merzo скачает installer, проверит SHA-256 и только потом предложит установку.", "Merzo Windows Optimizer — обновление найдено", MessageBoxButton.OK, MessageBoxImage.Information);
            else if (!silent && !_lastUpdateCheck.Success)
                MessageBox.Show(_lastUpdateCheck.Message, "Update Center", MessageBoxButton.OK, MessageBoxImage.Warning);
'''
new_notice='''            if (_lastUpdateCheck is { Success: true, UpdateAvailable: true } available)
            {
                if (!silent || !string.Equals(_lastNotifiedUpdateVersion, available.LatestVersion, StringComparison.OrdinalIgnoreCase))
                {
                    _lastNotifiedUpdateVersion = available.LatestVersion;
                    global::MerzoOptimizer.App.ReleaseNotesWindow.ShowUpdateAvailable(Application.Current?.MainWindow, available);
                }
            }
            else if (!silent && !_lastUpdateCheck.Success)
                MessageBox.Show(_lastUpdateCheck.Message, "Update Center", MessageBoxButton.OK, MessageBoxImage.Warning);
'''
if old_notice in s:
    s=s.replace(old_notice,new_notice,1)
update_method_anchor='    private Task CheckUpdatesAsync() => CheckUpdatesAsync(silent: false);\n'
if 'private void LoadLocalReleaseNotes()' not in s:
    loader=r'''    private void LoadLocalReleaseNotes()
    {
        try
        {
            var local = global::MerzoOptimizer.App.ReleaseNotesWindow.LoadCurrentRelease();
            UpdateReleaseTitleText = local.Title;
            UpdateReleaseNotesText = local.FormattedNotes;
        }
        catch
        {
            UpdateReleaseTitleText = "Что нового в текущей версии";
            UpdateReleaseNotesText = "Список изменений будет загружен при проверке обновлений.";
        }
    }

'''
    if update_method_anchor not in s: raise SystemExit('Update methods anchor missing')
    s=s.replace(update_method_anchor,loader+update_method_anchor,1)
vm.write_text(s,encoding='utf-8')

notes={
  'version':VERSION,
  'title':'Merzo Windows Optimizer 0.1.28 — Большое UX-обновление',
  'summary':'Профили приватности, прозрачные обновления и визуальный ход очистки.',
  'added':[
    'Телеметрия и privacy-настройки встроены прямо в LIGHT / STANDARD / MAXIMUM / LITE BUILD.',
    'STANDARD теперь включает строгую telemetry-настройку: DiagTrack/dmwappushservice и telemetry scheduled tasks с Snapshot/Undo.',
    'MAXIMUM и LITE BUILD включают максимальный обратимый privacy-набор, включая WER service/tasks.',
    'На странице «Обновления» появился полный список того, что добавлено, изменено и исправлено.',
    'При обнаружении следующей новой версии программа показывает уведомление с описанием обновления.',
    'После первого запуска новой версии показывается закрываемое окно «Что нового».',
    'В «Очистке» добавлена отдельная вкладка «Ход очистки» с прогрессом, текущей категорией, путём, Snapshot и результатом.'
  ],
  'changed':[
    'Убран отдельный пользовательский раздел «Телеметрия»: privacy теперь является частью основных профилей.',
    'Подтверждения очистки переписаны понятным языком без внутренних обозначений ревизий.',
    'Пакетная очистка показывает каждую категорию: backup → Snapshot → очистка → результат.',
    'Карточки очистки получили информативные подсказки: что очищается, путь и правила безопасности.'
  ],
  'fixed':[
    'Исправлены пустые/белые tooltip-подсказки: используется единый тёмный стиль с читаемым текстом.',
    'Убраны внутренние подписи вроде «R20» из пользовательских сообщений и экранов.',
    'Сохранено исправление совместимости со скриншотами активного окна.',
    'Сохранены SHA-256 проверка, UAC-установка, автоматический перезапуск после OTA и Snapshot/Undo.'
  ]
}
notes_path=root/'data'/'release_notes.json'
notes_path.write_text(json.dumps(notes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

notes_xaml=root/'src'/'MerzoOptimizer.App'/'ReleaseNotesWindow.xaml'
notes_xaml.write_text(r'''<Window x:Class="MerzoOptimizer.App.ReleaseNotesWindow"
        xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Merzo Windows Optimizer — Что нового"
        Width="660" Height="470" MinWidth="600" MinHeight="420"
        WindowStartupLocation="CenterOwner" ResizeMode="CanMinimize"
        Background="#0B0E13" Foreground="#F4F7FA" FontFamily="Segoe UI">
    <Grid Margin="14">
        <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
        <Border Grid.Row="0" Background="#102A26" BorderBrush="#2B655A" BorderThickness="1" CornerRadius="10" Padding="12,9">
            <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                <StackPanel><TextBlock Text="MERZO UPDATE" Foreground="#59D8C2" FontSize="9" FontWeight="Bold"/><TextBlock x:Name="HeadingText" FontSize="19" FontWeight="SemiBold" Margin="0,3,0,0" TextWrapping="Wrap"/><TextBlock x:Name="SubtitleText" Foreground="#A8B5C4" FontSize="9.5" Margin="0,4,0,0" TextWrapping="Wrap"/></StackPanel>
                <Border Grid.Column="1" Background="#173A35" BorderBrush="#2B655A" BorderThickness="1" CornerRadius="10" Padding="9,4" VerticalAlignment="Top"><TextBlock x:Name="VersionText" Foreground="#59D8C2" FontWeight="Bold" FontSize="9.5"/></Border>
            </Grid>
        </Border>
        <TextBlock Grid.Row="1" Text="Что изменилось" FontSize="12" FontWeight="SemiBold" Margin="2,11,0,6"/>
        <Border Grid.Row="2" Background="#111820" BorderBrush="#243040" BorderThickness="1" CornerRadius="9" Padding="10">
            <ScrollViewer VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"><TextBlock x:Name="NotesText" Foreground="#C4CDD8" FontSize="9.4" TextWrapping="Wrap" LineHeight="16"/></ScrollViewer>
        </Border>
        <Grid Grid.Row="3" Margin="0,10,0,0"><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
            <TextBlock x:Name="FooterText" Foreground="#8492A4" FontSize="8.5" VerticalAlignment="Center" TextWrapping="Wrap" Margin="2,0,14,0"/>
            <Button Grid.Column="1" Content="Понятно" Width="104" Height="30" Click="Close_Click" Background="#59D8C2" Foreground="#07110F" BorderBrush="#59D8C2" FontWeight="SemiBold" Cursor="Hand"/>
        </Grid>
    </Grid>
</Window>
''',encoding='utf-8')

notes_cs=root/'src'/'MerzoOptimizer.App'/'ReleaseNotesWindow.xaml.cs'
notes_cs.write_text(r'''using System.IO;
using System.Text;
using System.Text.Json;
using System.Windows;
using MerzoOptimizer.Core.Updates;

namespace MerzoOptimizer.App;

public partial class ReleaseNotesWindow : Window
{
    public sealed record LocalRelease(string Version, string Title, string Summary, string FormattedNotes);

    public ReleaseNotesWindow(string heading, string version, string subtitle, string notes, string footer)
    {
        InitializeComponent();
        HeadingText.Text = heading;
        VersionText.Text = string.IsNullOrWhiteSpace(version) ? "UPDATE" : $"v{version}";
        SubtitleText.Text = subtitle;
        NotesText.Text = notes;
        FooterText.Text = footer;
    }

    public static LocalRelease LoadCurrentRelease()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "data", "release_notes.json");
        if (!File.Exists(path)) return new LocalRelease("", "Что нового", "", "Список изменений отсутствует.");
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        var root = doc.RootElement;
        var version = root.TryGetProperty("version", out var v) ? v.GetString() ?? string.Empty : string.Empty;
        var title = root.TryGetProperty("title", out var t) ? t.GetString() ?? "Что нового" : "Что нового";
        var summary = root.TryGetProperty("summary", out var s) ? s.GetString() ?? string.Empty : string.Empty;
        var text = new StringBuilder();
        AppendSection(text, root, "added", "ДОБАВЛЕНО");
        AppendSection(text, root, "changed", "ИЗМЕНЕНО");
        AppendSection(text, root, "fixed", "ИСПРАВЛЕНО");
        return new LocalRelease(version, title, summary, text.ToString().Trim());
    }

    private static void AppendSection(StringBuilder text, JsonElement root, string property, string title)
    {
        if (!root.TryGetProperty(property, out var items) || items.ValueKind != JsonValueKind.Array) return;
        if (text.Length > 0) text.AppendLine().AppendLine();
        text.AppendLine(title);
        foreach (var item in items.EnumerateArray())
        {
            var value = item.GetString();
            if (!string.IsNullOrWhiteSpace(value)) text.Append("• ").AppendLine(value);
        }
    }

    public static void ShowCurrentReleaseIfNeeded(Window? owner)
    {
        try
        {
            var release = LoadCurrentRelease();
            if (string.IsNullOrWhiteSpace(release.Version)) return;
            var stateDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MerzoWindowsOptimizer", "ui");
            Directory.CreateDirectory(stateDir);
            var marker = Path.Combine(stateDir, "last-seen-release.txt");
            var seen = File.Exists(marker) ? File.ReadAllText(marker).Trim() : string.Empty;
            if (string.Equals(seen, release.Version, StringComparison.OrdinalIgnoreCase)) return;

            var dialog = new ReleaseNotesWindow("Что нового в Merzo Windows Optimizer", release.Version, release.Summary, release.FormattedNotes,
                "Это окно показывается один раз после установки новой версии. Полный список изменений также доступен на странице «Обновления».");
            if (owner is not null) dialog.Owner = owner;
            dialog.ShowDialog();
            File.WriteAllText(marker, release.Version);
        }
        catch
        {
        }
    }

    public static void ShowUpdateAvailable(Window? owner, UpdateCheckResult update)
    {
        var notes = string.IsNullOrWhiteSpace(update.Notes) ? "Для этой версии разработчик не добавил описание изменений." : update.Notes;
        var heading = $"Доступно обновление {update.LatestVersion}";
        var subtitle = string.IsNullOrWhiteSpace(update.ReleaseName) ? "Вышла новая версия Merzo Windows Optimizer." : update.ReleaseName;
        var dialog = new ReleaseNotesWindow(heading, update.LatestVersion, subtitle, notes,
            "Откройте страницу «Обновления» и нажмите «Скачать и установить». Перед запуском installer будет обязательно проверен по SHA-256.");
        if (owner is not null) dialog.Owner = owner;
        dialog.ShowDialog();
    }

    private void Close_Click(object sender, RoutedEventArgs e) => Close();
}
''',encoding='utf-8')

appcs=root/'src'/'MerzoOptimizer.App'/'App.xaml.cs'
c=appcs.read_text(encoding='utf-8-sig')
old_loaded='''            window.Loaded += async (_, _) =>
            {
                if (_viewModel is not null)
                    await _viewModel.InitializeAsync();
            };
'''
new_loaded='''            window.Loaded += async (_, _) =>
            {
                if (_viewModel is not null)
                    await _viewModel.InitializeAsync();
                ReleaseNotesWindow.ShowCurrentReleaseIfNeeded(window);
            };
'''
if old_loaded in c:
    c=c.replace(old_loaded,new_loaded,1)
elif 'ReleaseNotesWindow.ShowCurrentReleaseIfNeeded(window);' not in c:
    raise SystemExit('App Loaded anchor missing')
c=c.replace('WriteStartupDiagnostic("Main window shown successfully. R21 production shell + on-demand elevated helper initialized.");',
            'WriteStartupDiagnostic("Main window shown successfully. Production shell + on-demand elevated helper initialized.");')
appcs.write_text(c,encoding='utf-8')

up=root/'src'/'MerzoOptimizer.Windows'/'Updates'/'GitHubUpdateService.cs'
u=up.read_text(encoding='utf-8-sig')
u=u.replace('new ProductInfoHeaderValue("MerzoWindowsOptimizer", "0.1.21")','new ProductInfoHeaderValue("MerzoWindowsOptimizer", GetCurrentVersion())')
u=u.replace('?? "0.1.21"','?? "0.1.28"')
up.write_text(u,encoding='utf-8')

st=root/'src'/'MerzoOptimizer.SelfTest'/'Program.cs'
q=st.read_text(encoding='utf-8-sig')
q=re.sub(r'Merzo Windows Optimizer — .*?SelfTest(?: R\d+)?','Merzo Windows Optimizer — PRODUCTION R28 UX SelfTest',q,count=1)
q=re.sub(r'\s*foreach \(var token in new\[\] \{ "Header=\\"Телеметрия\\"", "ApplyPrivacySafeCommand", "ApplyPrivacyStrictCommand", "ApplyPrivacyMaximumCommand", "PrivacyStatusText" \}\) if \(!xaml.Contains\(token, StringComparison.Ordinal\)\) failures.Add\(\$"R27 privacy UI missing: \{token\}"\);\n?', '\n', q)
ui_anchor='''    if (xaml.Contains("Text=\"{Binding Id, Mode=OneWay}\"", StringComparison.Ordinal)) failures.Add("Technical tweak IDs must stay hidden from user cards.");\n'''
if 'R28 UX missing:' not in q:
    gate='''    foreach (var token in new[] { "Header=\\\"Ход очистки\\\"", "SelectedCleanupTabIndex", "CleanupOperationSteps", "UpdateReleaseNotesText", "Что нового" }) if (!xaml.Contains(token, StringComparison.Ordinal)) failures.Add($"R28 UX missing: {token}");\n    if (xaml.Contains("Header=\\\"Телеметрия\\\"", StringComparison.Ordinal)) failures.Add("Telemetry must be integrated into profiles, not shown as a separate R28 tab.");\n    if (!File.Exists(Path.Combine(AppContext.BaseDirectory, "data", "release_notes.json"))) failures.Add("R28 release_notes.json missing from payload.");\n'''
    if ui_anchor not in q: raise SystemExit('SelfTest UI anchor missing')
    q=q.replace(ui_anchor,ui_anchor+gate,1)
q=q.replace('R27 validation passed: scan-first UX, privacy/telemetry profiles, Snapshot+Undo, protected security components, Unicode power UI, OTA updater and on-demand UAC helper architecture.',
            'R28 validation passed: privacy integrated into core profiles, visual cleanup progress, readable tooltips, release changelog UX, Snapshot+Undo and verified OTA updater.')
st.write_text(q,encoding='utf-8')

fx=xaml.read_text(encoding='utf-8')
fv=vm.read_text(encoding='utf-8')
fa=appx.read_text(encoding='utf-8')
fr=notes_xaml.read_text(encoding='utf-8')
fc=appcs.read_text(encoding='utf-8')
ft=json.loads(tweaks_path.read_text(encoding='utf-8'))
for token in ['Production R28','Header="Ход очистки"','UpdateReleaseNotesText','CleanupOperationSteps']:
    if token not in fx and token not in fv: raise SystemExit(f'R28 token missing: {token}')
if 'Header="Телеметрия"' in fx: raise SystemExit('Dedicated Telemetry tab still present')
for tag in ['standard','maximum','lite_build']:
    if not any('privacy_strict' in t.get('profile_tags',[]) and tag in t.get('profile_tags',[]) for t in ft): raise SystemExit(f'Privacy STRICT not integrated into {tag}')
for tag in ['maximum','lite_build']:
    if not any('privacy_maximum' in t.get('profile_tags',[]) and tag in t.get('profile_tags',[]) for t in ft): raise SystemExit(f'Privacy MAX not integrated into {tag}')
for token in ['_selectedProfileTag','Profile telemetry service','Profile telemetry task','LoadLocalReleaseNotes','ShowUpdateAvailable']:
    if token not in fv: raise SystemExit(f'Profile/update engine missing: {token}')
if 'MERZO_R28_TOOLTIP_STYLE' not in fa: raise SystemExit('Tooltip style missing')
if 'ReleaseNotesWindow.ShowCurrentReleaseIfNeeded(window);' not in fc: raise SystemExit('First-launch release notes hook missing')
if not notes_path.exists() or 'Что нового' not in fr: raise SystemExit('Release notes UX missing')
if 'R20 сначала' in fv or 'R20 автоматически' in fv or 'Text="R20' in fx: raise SystemExit('Internal R20 user-facing wording remains')
print(f'R28 UX/profile integration patch: OK · tweaks={len(ft)}')
