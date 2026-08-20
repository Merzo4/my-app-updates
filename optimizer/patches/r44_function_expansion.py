from pathlib import Path
import json, os

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')
def replace_once(s, old, new, label):
    if old not in s:
        raise SystemExit('R44 anchor missing: '+label)
    return s.replace(old,new,1)

# -----------------------------------------------------------------------------
# ViewModel: add derived Smart Audit / Profiles / Privacy / Startup / Debloat
# intelligence without changing the existing execution engines.
# -----------------------------------------------------------------------------
vm=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s=read(vm)

field_anchor='''    private string _privacyStatusText = "Телеметрия: готова к privacy-аудиту";\n    private string _privacySummaryText = "Документированные privacy-политики + telemetry services/tasks";'''
field_new=field_anchor+'''\n    private string _smartAuditOverallText = "Smart Audit 2.0 появится после проверки.";\n    private string _smartAuditRecommendationText = "Сначала выполните аудит — Merzo сформирует персональный план.";\n    private string _smartAuditPrivacyText = "Privacy: —";\n    private string _smartAuditPerformanceText = "Performance: —";\n    private string _smartAuditGamingText = "Gaming: —";\n    private string _smartAuditStartupText = "Startup: —";\n    private string _smartAuditServicesText = "Services / Tasks: —";\n    private string _smartAuditCleanupText = "Cleanup: —";\n    private string _profilePlanText = "План применения появится после выбора профиля.";\n    private string _privacyCoverageText = "SAFE / STRICT / MAXIMUM будут рассчитаны после аудита.";\n    private string _startupManagerSummaryText = "Startup Manager 2.0 ещё не сканировал систему.";\n    private string _debloatClassificationText = "Debloat 2.0: сначала выполните Appx-аудит.";'''
s=replace_once(s,field_anchor,field_new,'R44 VM fields')

prop_anchor='''    public string PrivacyStatusText { get => _privacyStatusText; private set => SetProperty(ref _privacyStatusText, value); }\n    public string PrivacySummaryText { get => _privacySummaryText; private set => SetProperty(ref _privacySummaryText, value); }'''
prop_new=prop_anchor+'''\n    public string SmartAuditOverallText { get => _smartAuditOverallText; private set => SetProperty(ref _smartAuditOverallText, value); }\n    public string SmartAuditRecommendationText { get => _smartAuditRecommendationText; private set => SetProperty(ref _smartAuditRecommendationText, value); }\n    public string SmartAuditPrivacyText { get => _smartAuditPrivacyText; private set => SetProperty(ref _smartAuditPrivacyText, value); }\n    public string SmartAuditPerformanceText { get => _smartAuditPerformanceText; private set => SetProperty(ref _smartAuditPerformanceText, value); }\n    public string SmartAuditGamingText { get => _smartAuditGamingText; private set => SetProperty(ref _smartAuditGamingText, value); }\n    public string SmartAuditStartupText { get => _smartAuditStartupText; private set => SetProperty(ref _smartAuditStartupText, value); }\n    public string SmartAuditServicesText { get => _smartAuditServicesText; private set => SetProperty(ref _smartAuditServicesText, value); }\n    public string SmartAuditCleanupText { get => _smartAuditCleanupText; private set => SetProperty(ref _smartAuditCleanupText, value); }\n    public string ProfilePlanText { get => _profilePlanText; private set => SetProperty(ref _profilePlanText, value); }\n    public string PrivacyCoverageText { get => _privacyCoverageText; private set => SetProperty(ref _privacyCoverageText, value); }\n    public string StartupManagerSummaryText { get => _startupManagerSummaryText; private set => SetProperty(ref _startupManagerSummaryText, value); }\n    public string DebloatClassificationText { get => _debloatClassificationText; private set => SetProperty(ref _debloatClassificationText, value); }'''
s=replace_once(s,prop_anchor,prop_new,'R44 VM properties')

# Keep profile plan live as the user selects/deselects tweaks.
sel_anchor='''        SelectedTweaksText = selected == 0 ? "Ничего не выбрано" : $"Выбрано: {selected} · SAFE: {safe} · BALANCED: {balanced}";\n    }'''
sel_new='''        SelectedTweaksText = selected == 0 ? "Ничего не выбрано" : $"Выбрано: {selected} · SAFE: {safe} · BALANCED: {balanced}";\n        UpdateR44IntelligenceSummary();\n    }'''
s=replace_once(s,sel_anchor,sel_new,'selected tweak summary')

# Refresh derived summaries after manually refreshing Startup / Cleanup / Debloat.
s=replace_once(s,
'''            StartupOptimizerStatusText = $"Найдено: {enabled} активных · отключено Merzo: {disabled}. Startup Folder пока только в общем Audit.";''',
'''            StartupOptimizerStatusText = $"Найдено: {enabled} активных · отключено Merzo: {disabled}. Startup Folder и другие источники учитываются в общем Audit.";\n            UpdateR44IntelligenceSummary();''','startup refresh summary')

s=replace_once(s,
'''            DebloatStatusText = $"Найдено необязательных Appx: {apps.Count(static a => a.Installed)}. Удаление пока заблокировано до гарантированного Undo для Appx.";''',
'''            DebloatStatusText = $"Найдено необязательных Appx: {apps.Count(static a => a.Installed)}. R44 оставляет удаление заблокированным до гарантированного Undo для Appx.";\n            UpdateR44IntelligenceSummary();''','debloat refresh summary')

cleanup_anchor='''                CleanupStatusText = $"Категорий: {categories.Count} · найдено: {FormatBytes(categories.Sum(static c => c.EligibleBytes))} · файлы младше 24 часов не трогаем.";\n                UpdateCleanupSelectionText(); CleanAllSafeCommand.RaiseCanExecuteChanged(); CleanSelectedCommand.RaiseCanExecuteChanged();'''
cleanup_new='''                CleanupStatusText = $"Категорий: {categories.Count} · найдено: {FormatBytes(categories.Sum(static c => c.EligibleBytes))} · файлы младше 24 часов не трогаем.";\n                UpdateCleanupSelectionText(); CleanAllSafeCommand.RaiseCanExecuteChanged(); CleanSelectedCommand.RaiseCanExecuteChanged();\n                UpdateR44IntelligenceSummary();'''
s=replace_once(s,cleanup_anchor,cleanup_new,'cleanup refresh summary')

method_anchor='''    private void UpdateOptimizationScanSummary(bool autoScan)\n    {'''
method='''    private void UpdateR44IntelligenceSummary()\n    {\n        var applicable = SafeTweaks.Where(static x => !x.Definition.ScanOnly && x.IsSupported).ToArray();\n        var applied = applicable.Count(static x => x.IsApplied);\n        var available = applicable.Count(static x => !x.IsApplied);\n        var unsupported = SafeTweaks.Count(static x => !x.IsSupported);\n\n        var privacy = SafeTweaks.Where(card =>\n            card.ProfileTags.Contains("privacy_safe", StringComparer.OrdinalIgnoreCase) ||\n            card.ProfileTags.Contains("privacy_strict", StringComparer.OrdinalIgnoreCase) ||\n            card.ProfileTags.Contains("privacy_maximum", StringComparer.OrdinalIgnoreCase)).ToArray();\n        var privacyApplicable = privacy.Where(static x => !x.Definition.ScanOnly && x.IsSupported).ToArray();\n        var privacyApplied = privacyApplicable.Count(static x => x.IsApplied);\n        var privacyAvailable = privacyApplicable.Count(static x => !x.IsApplied);\n\n        var performance = SafeTweaks.Where(card =>\n            card.ProfileTags.Contains("performance", StringComparer.OrdinalIgnoreCase) ||\n            card.ProfileTags.Contains("process_safe", StringComparer.OrdinalIgnoreCase) ||\n            card.ProfileTags.Contains("process_lite", StringComparer.OrdinalIgnoreCase)).ToArray();\n        var performanceApplicable = performance.Where(static x => !x.Definition.ScanOnly && x.IsSupported).ToArray();\n        var performanceApplied = performanceApplicable.Count(static x => x.IsApplied);\n        var performanceAvailable = performanceApplicable.Count(static x => !x.IsApplied);\n\n        var gaming = SafeTweaks.Where(card =>\n            card.ProfileTags.Contains("gaming_build_safe", StringComparer.OrdinalIgnoreCase) ||\n            card.ProfileTags.Contains("gaming_build_performance", StringComparer.OrdinalIgnoreCase) ||\n            card.ProfileTags.Contains("gaming_build_extreme", StringComparer.OrdinalIgnoreCase) ||\n            card.ProfileTags.Contains("gaming_build_lab", StringComparer.OrdinalIgnoreCase)).ToArray();\n        var gamingApplicable = gaming.Where(static x => !x.Definition.ScanOnly && x.IsSupported).ToArray();\n        var gamingApplied = gamingApplicable.Count(static x => x.IsApplied);\n        var gamingAvailable = gamingApplicable.Count(static x => !x.IsApplied);\n\n        var startupActiveManageable = StartupOptimizerItems.Count(static x => x.Item.IsEnabled && x.Item.CanManage);\n        var startupProtected = StartupOptimizerItems.Count(static x => x.Item.IsEnabled && !x.Item.CanManage);\n        var startupDisabledByMerzo = StartupOptimizerItems.Count(static x => !x.Item.IsEnabled && x.Item.HasRestorePoint);\n        var serviceCandidates = ServiceAuditItems.Count(static x => x.Snapshot.CanManage && !x.Snapshot.IsDisabled);\n        var taskCandidates = ScheduledTaskAuditItems.Count(static x => x.Snapshot.CanManage && x.Snapshot.Enabled);\n        var cleanupBytes = CleanupCategories.Where(static x => x.CanClean).Sum(static x => x.EligibleBytes);\n\n        SmartAuditOverallText = $"Твики: применено {applied} · доступно {available} · не применимо {unsupported}. Проверка остаётся read-only до явного Apply.";\n        SmartAuditPrivacyText = $"{privacyApplied}/{privacyApplicable.Length} настроено · ещё {privacyAvailable}";\n        SmartAuditPerformanceText = $"{performanceApplied}/{performanceApplicable.Length} настроено · ещё {performanceAvailable}";\n        SmartAuditGamingText = $"{gamingApplied}/{gamingApplicable.Length} настроено · ещё {gamingAvailable}";\n        SmartAuditStartupText = $"Run: {startupActiveManageable} управляемых · {startupProtected} защищённых · {startupDisabledByMerzo} отключено Merzo";\n        SmartAuditServicesText = $"Кандидаты: службы {serviceCandidates} · задачи {taskCandidates}";\n        SmartAuditCleanupText = $"Можно безопасно очистить: {FormatBytesCompact(cleanupBytes)}";\n        SmartAuditRecommendationText = $"Рекомендуется {RecommendedProfileTitle}. Merzo применит только отсутствующие поддерживаемые правила; уже настроенное повторно не меняется.";\n\n        var privacySafe = CountProfileAvailable("privacy_safe");\n        var privacyStrict = CountProfileAvailable("privacy_strict");\n        var privacyMaximum = CountProfileAvailable("privacy_maximum");\n        PrivacyCoverageText = $"SAFE: ещё {privacySafe} · STRICT: ещё {privacyStrict} · MAXIMUM: ещё {privacyMaximum}. Состояния берутся из фактического аудита, а не из предположений.";\n\n        var selected = SafeTweaks.Where(static x => x.IsSelected).ToArray();\n        var selectedSafe = selected.Count(static x => x.Definition.Risk == TweakRisk.Safe);\n        var selectedBalanced = selected.Count(static x => x.Definition.Risk == TweakRisk.Balanced);\n        ProfilePlanText = selected.Length == 0\n            ? "Выберите профиль: Merzo покажет план до любых изменений."\n            : $"План: {selected.Length} твиков · SAFE {selectedSafe} · BALANCED {selectedBalanced} · затем Snapshot → Apply → Verify → Undo/Restore.";\n\n        StartupManagerSummaryText = $"Run-управление: {startupActiveManageable} активных · защищено {startupProtected} · отключено Merzo {startupDisabledByMerzo}. Общий аудит источников: {StartupItems.Count}.";\n\n        var installed = DebloatApps.Where(static x => x.Installed).ToArray();\n        string[] consumerTokens = ["Clipchamp", "Solitaire", "GetHelp", "Getstarted", "BingNews", "BingWeather"];\n        string[] protectedTokens = ["WindowsStore", "SecHealthUI", "ShellExperienceHost", "StartMenuExperienceHost", "DesktopAppInstaller", "VCLibs", "UI.Xaml", "AAD.BrokerPlugin", "AccountsControl"];\n        var obviousConsumer = installed.Count(app => consumerTokens.Any(token => app.PackageName?.Contains(token, StringComparison.OrdinalIgnoreCase) == true));\n        var protectedSystem = installed.Count(app => protectedTokens.Any(token => app.PackageName?.Contains(token, StringComparison.OrdinalIgnoreCase) == true));\n        var optional = Math.Max(0, installed.Length - obviousConsumer - protectedSystem);\n        DebloatClassificationText = $"Consumer bloat: {obviousConsumer} · по желанию: {optional} · системные/защищённые: {protectedSystem}. Удаление в R44 остаётся audit-only до гарантированного Undo.";\n    }\n\n'''+method_anchor
s=replace_once(s,method_anchor,method,'R44 intelligence method')

summary_anchor='''        ProfileRecommendationText =\n            $"Рекомендуется {RecommendedProfileTitle}. LIGHT: {light} · STANDARD: {standard} · MAXIMUM: {maximum} · LITE BUILD: {liteBuild}. " +\n            (knownBuildDetected > 0\n                ? $"Эта Windows уже содержит {knownBuildDetected} известных сборочных настроек — Merzo не применит их повторно."\n                : "Опасные/устаревшие сборочные правила проверяются отдельно и автоматически не применяются.");\n\n        if (autoScan)'''
summary_new='''        ProfileRecommendationText =\n            $"Рекомендуется {RecommendedProfileTitle}. LIGHT: {light} · STANDARD: {standard} · MAXIMUM: {maximum} · LITE BUILD: {liteBuild}. " +\n            (knownBuildDetected > 0\n                ? $"Эта Windows уже содержит {knownBuildDetected} известных сборочных настроек — Merzo не применит их повторно."\n                : "Опасные/устаревшие сборочные правила проверяются отдельно и автоматически не применяются.");\n\n        UpdateR44IntelligenceSummary();\n\n        if (autoScan)'''
s=replace_once(s,summary_anchor,summary_new,'deep scan R44 summary')

write(vm,s)

# -----------------------------------------------------------------------------
# XAML: keep R43 shell but add functional R44 surfaces.
# -----------------------------------------------------------------------------
xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xp)
x=x.replace('Production 0.1.43 · R43 TRUE FULL UI','Production 0.1.44 · R44 FUNCTION EXPANSION')
x=x.replace('Production R43 · 0.1.43','Production R44 · 0.1.44')
x=x.replace('Text="R43" Foreground="{StaticResource Accent}"','Text="R44" Foreground="{StaticResource Accent}"',1)

# Audit header + Smart Audit 2.0 tab.
x=replace_once(x,
'Text="Read-only диагностика, процессы и накопители"',
'Text="Smart Audit 2.0: Privacy / Performance / Gaming / Startup / Services / Cleanup"','audit subtitle')

audit_tab_anchor='<TabItem Header="Автозагрузка" Style="{StaticResource SubTabItem}">'
smart_tab='''<TabItem Header="Smart Audit 2.0" Style="{StaticResource SubTabItem}"><Grid Margin="0,6,0,0"><Grid.RowDefinitions><RowDefinition Height="78"/><RowDefinition Height="*"/></Grid.RowDefinitions><Border Style="{StaticResource R43HeroCard}" Padding="11,8" Margin="0,0,0,7"><Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="220"/></Grid.ColumnDefinitions><StackPanel><TextBlock Text="Персональный аудит этого ПК" FontSize="12.8" FontWeight="SemiBold"/><TextBlock Text="{Binding SmartAuditOverallText, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="9.8" TextWrapping="Wrap" Margin="0,3,10,0"/></StackPanel><Border Grid.Column="1" Style="{StaticResource R43Pill}" VerticalAlignment="Center"><TextBlock Text="{Binding RecommendedProfileTitle, Mode=OneWay}" Foreground="{StaticResource Accent}" FontSize="11" FontWeight="Bold" TextAlignment="Center"/></Border></Grid></Border><UniformGrid Grid.Row="1" Columns="3"><Border Style="{StaticResource R43PageCard}" Margin="0,0,7,7"><StackPanel><TextBlock Text="PRIVACY / TELEMETRY" Style="{StaticResource R43SectionLabel}"/><TextBlock Text="{Binding SmartAuditPrivacyText, Mode=OneWay}" FontSize="12" FontWeight="SemiBold" Margin="0,5,0,0"/><TextBlock Text="SAFE / STRICT / MAXIMUM считаются по фактическому состоянию." Foreground="{StaticResource TextMuted}" FontSize="9.3" TextWrapping="Wrap" Margin="0,4,0,0"/></StackPanel></Border><Border Style="{StaticResource R43PageCard}" Margin="0,0,7,7"><StackPanel><TextBlock Text="PERFORMANCE" Style="{StaticResource R43SectionLabel}"/><TextBlock Text="{Binding SmartAuditPerformanceText, Mode=OneWay}" FontSize="12" FontWeight="SemiBold" Margin="0,5,0,0"/><TextBlock Text="Только поддерживаемые обратимые правила." Foreground="{StaticResource TextMuted}" FontSize="9.3" TextWrapping="Wrap" Margin="0,4,0,0"/></StackPanel></Border><Border Style="{StaticResource R43PageCard}" Margin="0,0,0,7"><StackPanel><TextBlock Text="GAMING" Style="{StaticResource R43SectionLabel}"/><TextBlock Text="{Binding SmartAuditGamingText, Mode=OneWay}" FontSize="12" FontWeight="SemiBold" Margin="0,5,0,0"/><TextBlock Text="GAME BUILD учитывает уже применённые настройки." Foreground="{StaticResource TextMuted}" FontSize="9.3" TextWrapping="Wrap" Margin="0,4,0,0"/></StackPanel></Border><Border Style="{StaticResource R43PageCard}" Margin="0,0,7,0"><StackPanel><TextBlock Text="STARTUP" Style="{StaticResource R43SectionLabel}"/><TextBlock Text="{Binding SmartAuditStartupText, Mode=OneWay}" FontSize="11.4" FontWeight="SemiBold" Margin="0,5,0,0" TextWrapping="Wrap"/></StackPanel></Border><Border Style="{StaticResource R43PageCard}" Margin="0,0,7,0"><StackPanel><TextBlock Text="SERVICES / TASKS" Style="{StaticResource R43SectionLabel}"/><TextBlock Text="{Binding SmartAuditServicesText, Mode=OneWay}" FontSize="11.4" FontWeight="SemiBold" Margin="0,5,0,0" TextWrapping="Wrap"/></StackPanel></Border><Border Style="{StaticResource R43PageCard}"><StackPanel><TextBlock Text="CLEANUP" Style="{StaticResource R43SectionLabel}"/><TextBlock Text="{Binding SmartAuditCleanupText, Mode=OneWay}" FontSize="11.4" FontWeight="SemiBold" Margin="0,5,0,0" TextWrapping="Wrap"/><TextBlock Text="{Binding SmartAuditRecommendationText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.1" TextWrapping="Wrap" Margin="0,4,0,0"/></StackPanel></Border></UniformGrid></Grid></TabItem>\n            '''
x=replace_once(x,audit_tab_anchor,smart_tab+audit_tab_anchor,'Smart Audit tab')

# Profiles 2.0 wording and plan summary.
x=replace_once(x,
'Text="Профиль → план применения → Snapshot → Apply → Verify → Undo"',
'Text="Profiles 2.0: рекомендация → предварительный план → Snapshot → Apply → Verify → Undo"','profiles subtitle')

plan_anchor='<TextBlock Text="{Binding SelectedTweaksText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.5"/>'
plan_new='<TextBlock Text="{Binding SelectedTweaksText, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="9.5"/><TextBlock Text="{Binding ProfilePlanText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.1" TextTrimming="CharacterEllipsis" Margin="0,2,8,0"/>'
x=replace_once(x,plan_anchor,plan_new,'Profiles 2 plan')

# Privacy / Telemetry Center as a new Optimization subtab, using the existing
# reversible privacy commands/engine rather than inventing a second executor.
privacy_anchor='<TabItem Header="По одной" Style="{StaticResource SubTabItem}">'
privacy_tab='''<TabItem Header="Privacy / Telemetry" Style="{StaticResource SubTabItem}"><Grid Margin="0,6,0,0"><Grid.RowDefinitions><RowDefinition Height="84"/><RowDefinition Height="*"/></Grid.RowDefinitions><Border Style="{StaticResource R43HeroCard}" Padding="11,8" Margin="0,0,0,7"><Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><StackPanel><TextBlock Text="Privacy / Telemetry Center 2.0" FontSize="12.8" FontWeight="SemiBold"/><TextBlock Text="{Binding PrivacyStatusText, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="9.7" Margin="0,2,0,0"/><TextBlock Text="{Binding PrivacyCoverageText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.2" TextWrapping="Wrap" Margin="0,2,10,0"/></StackPanel><Button Grid.Column="1" Style="{StaticResource CompactSecondaryButton}" Command="{Binding RefreshPrivacyCommand}" Content="Обновить аудит" VerticalAlignment="Center"/></Grid></Border><UniformGrid Grid.Row="1" Columns="3"><Border Style="{StaticResource R43PageCard}" Margin="0,0,7,0"><StackPanel><TextBlock Text="SAFE" FontSize="15" FontWeight="SemiBold"/><TextBlock Text="Реклама, Activity History, Advertising ID и безопасные privacy policy." Foreground="{StaticResource TextMuted}" FontSize="9.5" TextWrapping="Wrap" Margin="0,5,0,0"/><TextBlock Text="Не отключает критические службы Windows." Foreground="{StaticResource Accent}" FontSize="9.3" Margin="0,7,0,0"/><Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding ApplyPrivacySafeCommand}" Content="Выбрать Privacy SAFE" Margin="0,10,0,0"/></StackPanel></Border><Border Style="{StaticResource R43HeroCard}" Margin="0,0,7,0"><StackPanel><TextBlock Text="STRICT" FontSize="15" FontWeight="SemiBold"/><TextBlock Text="Более строгие документированные telemetry/privacy политики и обратимые правила." Foreground="{StaticResource TextMuted}" FontSize="9.5" TextWrapping="Wrap" Margin="0,5,0,0"/><TextBlock Text="Рекомендуется после Smart Audit." Foreground="{StaticResource Accent}" FontSize="9.3" Margin="0,7,0,0"/><Button Style="{StaticResource CompactPrimaryButton}" Command="{Binding ApplyPrivacyStrictCommand}" Content="Выбрать Privacy STRICT" Margin="0,10,0,0"/></StackPanel></Border><Border Style="{StaticResource R43PageCard}"><StackPanel><TextBlock Text="MAXIMUM" FontSize="15" FontWeight="SemiBold"/><TextBlock Text="Максимальный набор поддерживаемых privacy правил без scan-only и мифических твиков." Foreground="{StaticResource TextMuted}" FontSize="9.5" TextWrapping="Wrap" Margin="0,5,0,0"/><TextBlock Text="Требует внимательной проверки совместимости." Foreground="{StaticResource Warning}" FontSize="9.3" Margin="0,7,0,0"/><Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding ApplyPrivacyMaximumCommand}" Content="Выбрать Privacy MAX" Margin="0,10,0,0"/></StackPanel></Border></UniformGrid></Grid></TabItem>\n            '''
x=replace_once(x,privacy_anchor,privacy_tab+privacy_anchor,'Privacy Center tab')

# Startup Manager 2.0 summary, while remaining honest about managed Run entries.
x=replace_once(x,
'Text="Источник, влияние и обратимое отключение"',
'Text="Startup Manager 2.0: управляемые Run-записи + общий аудит других источников"','startup subtitle')
startup_hero='<TextBlock Text="{Binding StartupOptimizerStatusText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.7" Margin="0,2,0,0"/>'
startup_hero_new='<TextBlock Text="{Binding StartupOptimizerStatusText, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="9.5" Margin="0,2,0,0"/><TextBlock Text="{Binding StartupManagerSummaryText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.1" TextTrimming="CharacterEllipsis" Margin="0,2,10,0"/>'
x=replace_once(x,startup_hero,startup_hero_new,'Startup Manager summary')

# Debloat 2.0 classification; actions intentionally remain audit-only.
x=replace_once(x,
'Text="Очистка данных и отдельный Appx/Debloat — с понятной обратимостью"',
'Text="Cleanup + Debloat 2.0: объём до удаления, категории Appx и строгая защита Undo"','debloat subtitle')
debloat_tab_anchor='<TabItem Header="Debloat Appx" Style="{StaticResource SubTabItem}"><Grid Margin="0,6,0,0"><Grid.RowDefinitions><RowDefinition Height="48"/><RowDefinition Height="*"/></Grid.RowDefinitions>'
debloat_tab_new='<TabItem Header="Debloat Appx" Style="{StaticResource SubTabItem}"><Grid Margin="0,6,0,0"><Grid.RowDefinitions><RowDefinition Height="68"/><RowDefinition Height="*"/></Grid.RowDefinitions>'
x=replace_once(x,debloat_tab_anchor,debloat_tab_new,'Debloat row height')
debloat_status='<TextBlock Text="{Binding DebloatStatusText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.5"/>'
debloat_status_new='<TextBlock Text="{Binding DebloatStatusText, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="9.4"/><TextBlock Text="{Binding DebloatClassificationText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.0" TextTrimming="CharacterEllipsis" Margin="0,2,8,0"/>'
x=replace_once(x,debloat_status,debloat_status_new,'Debloat classification')

write(xp,x)

# Release notes metadata.
rp=root/'data'/'release_notes.json'
if rp.exists():
    data=json.loads(read(rp))
    data['version']='0.1.44'
    data['title']='R44 FUNCTION EXPANSION'
    changes=[
        'Smart Audit 2.0: персональные Privacy / Performance / Gaming / Startup / Services / Cleanup итоги.',
        'Profiles 2.0: предварительный план до применения и рекомендация по фактическому аудиту.',
        'Privacy / Telemetry Center 2.0: SAFE / STRICT / MAXIMUM поверх существующего обратимого privacy engine.',
        'Startup Manager 2.0: управляемые Run-записи плюс честный общий аудит остальных источников.',
        'Debloat 2.0: классификация Appx; удаление остаётся заблокировано до гарантированного Undo.',
        'R43 UI baseline, Snapshot/Undo, Gaming, Network и Update Center сохранены.'
    ]
    if 'changes' in data: data['changes']=changes
    elif 'items' in data: data['items']=changes
    else: data['changes']=changes
    rp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

(root/'R44_FUNCTION_EXPANSION.marker').write_text('R44 FUNCTION EXPANSION\nSmart Audit 2.0 + Profiles 2.0 + Privacy/Telemetry + Startup Manager 2.0 + Debloat 2.0\n',encoding='utf-8')
print('R44 function expansion patch: OK')
