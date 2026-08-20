from pathlib import Path
import json,re,os
root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')
def replace_once(s,old,new,label):
    c=s.count(old)
    if c!=1: raise SystemExit(f'R47 anchor {label}: count={c}')
    return s.replace(old,new,1)

# ---- Catalog: 3 cumulative builds + shell UX tweaks ----
tp=root/'data'/'tweaks.json'
tweaks=json.loads(read(tp))
byid={t['id']:t for t in tweaks}
ctx_id='explorer.classic_context_menu'
if ctx_id not in byid:
    ctx={
      'id':ctx_id,
      'name':'Классическое контекстное меню Windows 11',
      'category':'Explorer',
      'risk':'Balanced',
      'requires_admin':False,
      'requires_restart':True,
      'description':'Показывает полное классическое контекстное меню сразу по правой кнопке без дополнительного «Показать дополнительные параметры».',
      'expected_effect':'Быстрый доступ к полному меню Проводника. Требуется перезапуск Explorer или Windows.',
      'source_note':'Windows 11 per-user shell compatibility CLSID; reversible by removing the created default value/key through Snapshot/Undo.',
      'profile_tags':[],
      'registry_actions':[{
        'hive':'CurrentUser',
        'key_path':'SOFTWARE\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\\InprocServer32',
        'value_name':'',
        'value_type':'String',
        'string_value':''
      }],
      'min_windows_build':22000
    }
    tweaks.append(ctx);byid[ctx_id]=ctx

light_sources={'light','privacy_maximum','process_safe','background_light'}
game_sources={'performance','gaming_build_performance'}
extreme_sources={'process_lite','gaming_build_extreme'}
for t in tweaks:
    if t.get('scan_only'): continue
    tags=t.setdefault('profile_tags',[])
    tagset=set(tags)
    is_light=bool(tagset & light_sources) or t['id'] in {ctx_id,'explorer.launch_this_pc'}
    is_game=is_light or bool(tagset & game_sources)
    is_extreme=is_game or bool(tagset & extreme_sources)
    for ok,tag in [(is_light,'merzo_light'),(is_game,'merzo_game'),(is_extreme,'merzo_extreme')]:
        if ok and tag not in tags: tags.append(tag)
write(tp,json.dumps(tweaks,ensure_ascii=False,indent=2)+'\n')

# ---- VM: map legacy 3 commands to new builds and teach Apply engine semantics ----
vp=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s=read(vp)
s=replace_once(s,
'        SelectLightProfileCommand = new AsyncRelayCommand(() => SelectProfileAsync("light"), () => !IsStage2Busy && !IsDeepScanning);\n        SelectStandardProfileCommand = new AsyncRelayCommand(() => SelectProfileAsync("standard"), () => !IsStage2Busy && !IsDeepScanning);\n        SelectMaximumProfileCommand = new AsyncRelayCommand(() => SelectProfileAsync("maximum"), () => !IsStage2Busy && !IsDeepScanning);',
'        SelectLightProfileCommand = new AsyncRelayCommand(() => SelectProfileAsync("merzo_light"), () => !IsStage2Busy && !IsDeepScanning);\n        SelectStandardProfileCommand = new AsyncRelayCommand(() => SelectGamingTaggedPresetAsync("merzo_game", "ИГРОВАЯ СБОРКА"), () => !IsStage2Busy && !IsDeepScanning);\n        SelectMaximumProfileCommand = new AsyncRelayCommand(() => SelectGamingTaggedPresetAsync("merzo_extreme", "EXTREME СБОРКА"), () => !IsStage2Busy && !IsDeepScanning);',
'3 build commands')

s=replace_once(s,
'        var gamingSafe = profileTag == "gaming_build_safe";\n        var gamingPerformance = profileTag == "gaming_build_performance";\n        var gamingExtreme = profileTag == "gaming_build_extreme";\n        var gamingLab = profileTag == "gaming_build_lab";\n        var gamingBuild = gamingSafe || gamingPerformance || gamingExtreme || gamingLab;\n        var gamingNetworkMode = gamingExtreme || gamingLab ? "EXTREME" : gamingBuild ? "SAFE" : null;\n        var profileIncludesTelemetry = profileTag is "standard" or "maximum" or "lite_build" || gamingPerformance || gamingExtreme || gamingLab;\n        var profileIncludesWer = profileTag is "maximum" or "lite_build" || gamingExtreme || gamingLab;',
'        var merzoLight = profileTag == "merzo_light";\n        var merzoGame = profileTag == "merzo_game";\n        var merzoExtreme = profileTag == "merzo_extreme";\n        var gamingSafe = profileTag == "gaming_build_safe";\n        var gamingPerformance = profileTag == "gaming_build_performance" || merzoGame;\n        var gamingExtreme = profileTag == "gaming_build_extreme" || merzoExtreme;\n        var gamingLab = profileTag == "gaming_build_lab";\n        var gamingBuild = gamingSafe || gamingPerformance || gamingExtreme || gamingLab;\n        var gamingNetworkMode = gamingExtreme || gamingLab ? "EXTREME" : gamingBuild ? "SAFE" : null;\n        var profileIncludesTelemetry = merzoLight || merzoGame || merzoExtreme || profileTag is "standard" or "maximum" or "lite_build" || gamingPerformance || gamingExtreme || gamingLab;\n        var profileIncludesWer = merzoLight || merzoGame || merzoExtreme || profileTag is "maximum" or "lite_build" || gamingExtreme || gamingLab;',
'apply build flags')

s=replace_once(s,
'        var profileText = profileTag switch\n        {\n            "light" => "Privacy SAFE: безопасные privacy-политики без отключения telemetry-служб.",',
'        var profileText = profileTag switch\n        {\n            "merzo_light" => $"ЛАЙТ — Чистая Windows: максимальная privacy/telemetry-разгрузка, меньше рекламы/фона, Explorer UX и безопасное сокращение процессов. Services {services.Count}, tasks {tasks.Count}.",\n            "merzo_game" => $"GAME — всё из ЛАЙТ + performance/game tweaks, снижение фоновой нагрузки и Gaming Network SAFE. Services {services.Count}, tasks {tasks.Count}.",\n            "merzo_extreme" => $"EXTREME — всё из GAME + агрессивная разгрузка Windows, дополнительные условные службы/задачи и Gaming Network EXTREME. Services {services.Count}, tasks {tasks.Count}.",\n            "light" => "Privacy SAFE: безопасные privacy-политики без отключения telemetry-служб.",',
'profile text')

s=s.replace('        var gamingWarning = gamingExtreme || gamingLab\n            ? "\\n\\nВНИМАНИЕ: EXTREME/LAB может отключить функции Hotspot/Smart Card/Sensors и изменить параметры сетевого адаптера. Defender, Windows Update, Store, IPv6 и pagefile не отключаются."',
'''        var gamingWarning = gamingExtreme || gamingLab\n            ? "\\n\\nВНИМАНИЕ: EXTREME может отключить условные фоновые функции Hotspot/Smart Card/Sensors и изменить параметры сетевого адаптера. Defender, Windows Update, Store, IPv6 и pagefile не отключаются. Все поддерживаемые изменения остаются под Snapshot/Undo."''')

s=replace_once(s,
'        Stage2StatusText = profileTag switch\n        {\n            "light" => "LIGHT выбран: базовая оптимизация + безопасная приватность.",',
'        Stage2StatusText = profileTag switch\n        {\n            "merzo_light" => "ЛАЙТ выбран: чистая Windows, максимальная privacy/telemetry-разгрузка, реклама/предложения, фон и безопасные процессы. Проводник → Этот компьютер; классическое контекстное меню — на Windows 11.",\n            "merzo_game" => "GAME выбран: всё из ЛАЙТ + игровые/performance-твики и Gaming Network SAFE.",\n            "merzo_extreme" => "EXTREME выбран: всё из GAME + максимально агрессивная обратимая разгрузка и Gaming Network EXTREME.",\n            "light" => "LIGHT выбран: базовая оптимизация + безопасная приватность.",',
'select messages')

s=s.replace('        var light = CountProfileAvailable("light");\n        var standard = CountProfileAvailable("standard");\n        var maximum = CountProfileAvailable("maximum");\n        var liteBuild = CountProfileAvailable("lite_build");',
'''        var light = CountProfileAvailable("merzo_light");\n        var standard = CountProfileAvailable("merzo_game");\n        var maximum = CountProfileAvailable("merzo_extreme");\n        var liteBuild = CountProfileAvailable("lite_build");''')
s=s.replace('        LightProfileAvailableText = light == 0 ? "Уже настроено · Privacy SAFE" : $"Ещё {light} изменений · Privacy SAFE";\n        StandardProfileAvailableText = standard == 0 ? "Уже настроено · Telemetry STRICT" : $"Ещё {standard} изменений · Telemetry STRICT";\n        MaximumProfileAvailableText = maximum == 0 ? "Уже настроено · Privacy MAX" : $"Ещё {maximum} изменений · Privacy MAX";',
'''        LightProfileAvailableText = light == 0 ? "ЛАЙТ уже настроен" : $"ЛАЙТ · ещё {light} изменений";\n        StandardProfileAvailableText = standard == 0 ? "GAME уже настроен" : $"GAME · ещё {standard} изменений";\n        MaximumProfileAvailableText = maximum == 0 ? "EXTREME уже настроен" : $"EXTREME · ещё {maximum} изменений";''')
s=s.replace('            recommendedId = "light";\n            RecommendedProfileReason = $"Система уже сильно настроена: применено {already} из {applicable.Length} обратимых правил. LIGHT добавит только недостающие безопасные изменения.";',
'''            recommendedId = "light";\n            RecommendedProfileReason = $"Система уже сильно настроена: применено {already} из {applicable.Length} обратимых правил. ЛАЙТ добавит только недостающие изменения и полностью проверит privacy/telemetry.";''')
s=s.replace('            recommendedId = "standard";\n            RecommendedProfileReason = knownBuildDetected > 0\n                ? $"Найдено {knownBuildDetected} известных сборочных твиков. STANDARD дополнит их только отсутствующими обратимыми настройками и не будет повторно менять уже настроенное."\n                : $"Доступно ещё {available} обратимых настроек. STANDARD даёт лучший баланс между облегчением Windows, фоном и сохранением привычных функций.";',
'''            recommendedId = "standard";\n            RecommendedProfileReason = knownBuildDetected > 0\n                ? $"Найдено {knownBuildDetected} известных сборочных твиков. GAME дополнит их только отсутствующими обратимыми настройками."\n                : $"Доступно ещё {available} обратимых настроек. Для игрового ПК GAME даёт ЛАЙТ-базу плюс производительность и сетевой игровой профиль.";''')
s=s.replace('        RecommendedProfileTitle = recommendedId.ToUpperInvariant();',
'''        RecommendedProfileTitle = recommendedId == "light" ? "ЛАЙТ" : recommendedId == "standard" ? "GAME" : "EXTREME";''')
s=s.replace('        ProfileRecommendationText =\n            $"Рекомендуется {RecommendedProfileTitle}. LIGHT: {light} · STANDARD: {standard} · MAXIMUM: {maximum} · LITE BUILD: {liteBuild}. " +',
'''        ProfileRecommendationText =\n            $"Рекомендуется {RecommendedProfileTitle}. ЛАЙТ: {light} · GAME: {standard} · EXTREME: {maximum}. " +''')
s=s.replace('            ? "Выберите профиль: Merzo покажет план до любых изменений."', '            ? "Выберите сборку: Merzo покажет план до любых изменений."')
write(vp,s)

# ---- XAML: simplified primary nav + 3-build page, keep expert details collapsed ----
xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xp)
x=x.replace('Production 0.1.46 · R46 SECURITY HARDENING','Production 0.1.47 · R47 SIMPLE BUILDS')
x=x.replace('Production R46 · 0.1.46','Production R47 · 0.1.47')
x=x.replace('Text="R46" Foreground="{StaticResource Accent}"','Text="R47" Foreground="{StaticResource Accent}"',1)
x=x.replace('Content="Открыть оптимизацию"','Content="Выбрать сборку"')

nav_start=x.index('                    <RadioButton x:Name="DashboardNav"')
nav_end=x.index('                </StackPanel>\n                </ScrollViewer>',nav_start)
new_nav='''                    <RadioButton x:Name="DashboardNav" GroupName="MainNav" IsChecked="True" Style="{StaticResource NavRadioButton}" Click="Dashboard_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE80F;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Главная" FontWeight="SemiBold"/></StackPanel></RadioButton>\n                    <RadioButton x:Name="TweaksNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Tweaks_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE72E;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Сборки" FontWeight="SemiBold"/></StackPanel></RadioButton>\n                    <RadioButton x:Name="CleanupNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Cleanup_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE74D;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Очистка" FontWeight="SemiBold"/></StackPanel></RadioButton>\n                    <RadioButton x:Name="RestoreNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Restore_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE7A7;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Восстановление" FontWeight="SemiBold"/></StackPanel></RadioButton>\n                    <RadioButton x:Name="UpdatesNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Updates_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE895;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Обновления" FontWeight="SemiBold"/></StackPanel></RadioButton>\n                    <Expander Header="Экспертные инструменты" Foreground="{StaticResource TextSecondary}" FontSize="10.5" Margin="2,8,2,0" IsExpanded="False">\n                        <StackPanel Margin="0,4,0,0">\n                            <RadioButton x:Name="AuditNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Audit_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE721;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Аудит системы" FontWeight="SemiBold"/></StackPanel></RadioButton>\n                            <RadioButton x:Name="StartupNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Startup_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE7B8;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Автозагрузка" FontWeight="SemiBold"/></StackPanel></RadioButton>\n                            <RadioButton x:Name="ServicesTasksNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="ServicesTasks_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE90F;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Службы / задачи" FontWeight="SemiBold"/></StackPanel></RadioButton>\n                            <RadioButton x:Name="PowerNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Power_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE945;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Питание" FontWeight="SemiBold"/></StackPanel></RadioButton>\n                            <RadioButton x:Name="LogsNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Logs_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE81C;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Журнал" FontWeight="SemiBold"/></StackPanel></RadioButton>\n                            <RadioButton x:Name="GamingDevNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="GamingDev_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE7FC;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Gaming / Developer" FontWeight="SemiBold"/></StackPanel></RadioButton>\n                            <RadioButton x:Name="NetworkNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="Network_Click"><StackPanel Orientation="Horizontal"><TextBlock Text="&#xE968;" FontFamily="Segoe MDL2 Assets" FontSize="14" Width="24"/><TextBlock Text="Repair / Network" FontWeight="SemiBold"/></StackPanel></RadioButton>\n                        </StackPanel>\n                    </Expander>\n'''
x=x[:nav_start]+new_nav+x[nav_end:]

sec_start=x.index('            <!-- Optimization profiles -->')
sec_end=x.index('            <!-- Stage 3: Startup Optimizer -->',sec_start)
old_sec=x[sec_start:sec_end]
tab_start=old_sec.index('        <TabControl Grid.Row="2"')
tab_end=old_sec.index('        <Border x:Name="OptimizationApplyBar"',tab_start)
old_tabs=old_sec[tab_start:tab_end].rstrip()
old_tabs=old_tabs.replace('Grid.Row="2"','',1)
new_sec='''            <!-- R47 SIMPLE BUILDS -->\n            <TabItem>\n    <Grid x:Name="PageRoot2" Margin="14,10,14,14" ClipToBounds="True">\n        <Grid.RowDefinitions><RowDefinition Height="44"/><RowDefinition Height="58"/><RowDefinition Height="222"/><RowDefinition Height="92"/><RowDefinition Height="*"/></Grid.RowDefinitions>\n        <Grid Grid.Row="0"><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><StackPanel><TextBlock Style="{StaticResource PageTitle}" Text="Сборки Windows"/><TextBlock Text="Три понятных уровня. Каждая следующая сборка включает предыдущую." Foreground="{StaticResource TextMuted}" FontSize="10.8"/></StackPanel><Button Grid.Column="1" Style="{StaticResource CompactSecondaryButton}" Command="{Binding RunDeepOptimizationScanCommand}" Content="Проверить систему" Margin="0,0,6,0" VerticalAlignment="Center"/><Button Grid.Column="2" Style="{StaticResource CompactSecondaryButton}" Command="{Binding RunRecoveryTestCommand}" Content="Проверить Undo" VerticalAlignment="Center"/></Grid>\n        <Border Grid.Row="1" Style="{StaticResource R43HeroCard}" Padding="11,7" Margin="0,1,0,7"><Grid><Grid.ColumnDefinitions><ColumnDefinition Width="Auto"/><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><Border Width="34" Height="34" CornerRadius="17" Background="#173B38" Margin="0,0,10,0"><TextBlock Text="&#xE73E;" FontFamily="Segoe MDL2 Assets" Foreground="{StaticResource Accent}" FontSize="15" HorizontalAlignment="Center" VerticalAlignment="Center"/></Border><StackPanel Grid.Column="1" VerticalAlignment="Center"><TextBlock Text="Просто выбери уровень — Merzo сам соберёт только недостающие изменения" FontSize="11.4" FontWeight="SemiBold"/><TextBlock Text="Телеметрия отключается уже в ЛАЙТ. Defender / Windows Update / Store / IPv6 / pagefile сборки не отключают." Foreground="{StaticResource TextMuted}" FontSize="9.5"/></StackPanel><Border Grid.Column="2" Style="{StaticResource R43Pill}" VerticalAlignment="Center"><TextBlock Text="SNAPSHOT + UNDO" Foreground="{StaticResource Accent}" FontSize="9.4" FontWeight="Bold"/></Border></Grid></Border>\n        <UniformGrid Grid.Row="2" Columns="3" Margin="0,0,0,7">\n            <Border Style="{StaticResource R43PageCard}" Margin="0,0,7,0" Padding="12,10"><Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions><StackPanel><StackPanel Orientation="Horizontal"><TextBlock Text="ЛАЙТ" FontSize="17" FontWeight="SemiBold"/><Border Style="{StaticResource R43Pill}" Margin="7,0,0,0"><TextBlock Text="ЧИСТАЯ WINDOWS" Foreground="{StaticResource Accent}" FontSize="8.7" FontWeight="Bold"/></Border></StackPanel><TextBlock Text="Лёгкая, чистая и спокойная система" Foreground="{StaticResource Accent}" FontSize="10.2" Margin="0,4,0,6"/></StackPanel><StackPanel Grid.Row="1"><TextBlock Text="✓ Телеметрия / WER / privacy — максимум" FontSize="9.5" Margin="0,2"/><TextBlock Text="✓ Реклама, советы и consumer-предложения" FontSize="9.5" Margin="0,2"/><TextBlock Text="✓ Безопасное снижение фоновых процессов" FontSize="9.5" Margin="0,2"/><TextBlock Text="✓ Проводник сразу «Этот компьютер»" FontSize="9.5" Margin="0,2"/><TextBlock Text="✓ Классическое меню правой кнопки" FontSize="9.5" Margin="0,2"/><TextBlock Text="{Binding LightProfileAvailableText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.2" Margin="0,6,0,0"/></StackPanel><Button Grid.Row="2" Style="{StaticResource CompactSecondaryButton}" Command="{Binding SelectLightProfileCommand}" Content="Выбрать ЛАЙТ" Margin="0,8,0,0"/></Grid></Border>\n            <Border Style="{StaticResource R43HeroCard}" Margin="0,0,7,0" Padding="12,10"><Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions><StackPanel><StackPanel Orientation="Horizontal"><TextBlock Text="GAME" FontSize="17" FontWeight="SemiBold"/><Border Style="{StaticResource R43Pill}" Margin="7,0,0,0"><TextBlock Text="ДЛЯ ИГР" Foreground="{StaticResource Accent}" FontSize="8.7" FontWeight="Bold"/></Border></StackPanel><TextBlock Text="Всё из ЛАЙТ + игровая производительность" Foreground="{StaticResource Accent}" FontSize="10.2" Margin="0,4,0,6"/></StackPanel><StackPanel Grid.Row="1"><TextBlock Text="✓ Полностью включает ЛАЙТ" FontSize="9.5" Margin="0,2"/><TextBlock Text="✓ Game Mode / GPU / MMCSS где поддерживается" FontSize="9.5" Margin="0,2"/><TextBlock Text="✓ Performance и отзывчивость Windows" FontSize="9.5" Margin="0,2"/><TextBlock Text="✓ Меньше фоновых служб и задач" FontSize="9.5" Margin="0,2"/><TextBlock Text="✓ Gaming Network SAFE" FontSize="9.5" Margin="0,2"/><TextBlock Text="{Binding StandardProfileAvailableText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.2" Margin="0,6,0,0"/></StackPanel><Button Grid.Row="2" Style="{StaticResource CompactPrimaryButton}" Command="{Binding SelectStandardProfileCommand}" Content="Выбрать GAME" Margin="0,8,0,0"/></Grid></Border>\n            <Border Style="{StaticResource R43PageCard}" BorderBrush="#745A3A" Margin="0" Padding="12,10"><Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions><StackPanel><StackPanel Orientation="Horizontal"><TextBlock Text="EXTREME" FontSize="17" FontWeight="SemiBold"/><Border Background="#2D2117" BorderBrush="#745A3A" BorderThickness="1" CornerRadius="9" Padding="6,2" Margin="7,0,0,0"><TextBlock Text="ЖЁСТКО" Foreground="{StaticResource Warning}" FontSize="8.7" FontWeight="Bold"/></Border></StackPanel><TextBlock Text="Максимальная обратимая разгрузка" Foreground="{StaticResource Warning}" FontSize="10.2" Margin="0,4,0,6"/></StackPanel><StackPanel Grid.Row="1"><TextBlock Text="✓ Полностью включает GAME" FontSize="9.5" Margin="0,2"/><TextBlock Text="✓ Более агрессивные performance-твики" FontSize="9.5" Margin="0,2"/><TextBlock Text="✓ Дополнительные условные службы / задачи" FontSize="9.5" Margin="0,2"/><TextBlock Text="✓ Gaming Network EXTREME" FontSize="9.5" Margin="0,2"/><TextBlock Text="✓ Максимум фона убирается без критических служб" FontSize="9.5" Margin="0,2"/><TextBlock Text="{Binding MaximumProfileAvailableText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.2" Margin="0,6,0,0"/></StackPanel><Button Grid.Row="2" Style="{StaticResource CompactSecondaryButton}" Command="{Binding SelectMaximumProfileCommand}" Content="Выбрать EXTREME" Margin="0,8,0,0"/></Grid></Border>\n        </UniformGrid>\n        <Border x:Name="OptimizationApplyBar" Grid.Row="3" Style="{StaticResource R43HeroCard}" Padding="10,7" Margin="0,0,0,7" MinHeight="84"><Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions><StackPanel VerticalAlignment="Center"><TextBlock Text="ГОТОВО К УСТАНОВКЕ" Style="{StaticResource R43SectionLabel}"/><TextBlock Text="{Binding SelectedTweaksText, Mode=OneWay}" FontSize="11.5" FontWeight="SemiBold" Margin="0,2,0,0"/><TextBlock Text="{Binding Stage2StatusText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.1" TextTrimming="CharacterEllipsis"/><ProgressBar Value="{Binding DeepScanProgress, Mode=OneWay}" Maximum="100" Height="5" Margin="0,5,14,0"/><TextBlock Text="{Binding DeepScanStatusText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="8.8" Margin="0,2,14,0"/></StackPanel><Button Grid.Column="1" Style="{StaticResource CompactSecondaryButton}" Command="{Binding ClearTweakSelectionCommand}" Content="Снять выбор" Margin="0,0,6,0" VerticalAlignment="Center"/><Button Grid.Column="2" Style="{StaticResource CompactPrimaryButton}" Command="{Binding ApplySelectedTweaksCommand}" Content="Установить сборку" MinWidth="150" VerticalAlignment="Center"/></Grid></Border>\n        <Expander Grid.Row="4" Header="Дополнительно — ручная настройка, Privacy и подробный ход работы" IsExpanded="False" Foreground="{StaticResource TextSecondary}" FontSize="10.2" Margin="2,0,2,0">\n            <Border Style="{StaticResource R43PageCard}" Padding="7" Margin="0,5,0,0">\n''' + old_tabs + '''\n            </Border>\n        </Expander>\n    </Grid>\n</TabItem>\n\n'''
x=x[:sec_start]+new_sec+x[sec_end:]
write(xp,x)

# ---- SelfTest: keep old internal cascade, but UI contract now validates simple builds ----
sp=root/'src'/'MerzoOptimizer.SelfTest'/'Program.cs'
ss=read(sp)
ss=ss.replace('foreach (var token in new[] { "HasOptimizationScanResults", "RecommendedProfileTitle", "RecommendedProfileReason", "IsLightRecommended", "IsStandardRecommended", "RunDeepOptimizationScanCommand" })\n        if (!xaml.Contains(token, StringComparison.Ordinal)) failures.Add($"R20 scan-first/recommendation UI missing: {token}");\n    foreach (var token in new[] { "LIGHT", "STANDARD", "MAXIMUM", "LITE BUILD", "SelectLiteBuildProfileCommand", "Ход работы" })\n        if (!xaml.Contains(token, StringComparison.Ordinal)) failures.Add($"R20 profile UI missing: {token}");',
'''foreach (var token in new[] { "RunDeepOptimizationScanCommand", "OptimizationApplyBar", "Экспертные инструменты", "Дополнительно — ручная настройка" })\n        if (!xaml.Contains(token, StringComparison.Ordinal)) failures.Add($"R47 simplified UX missing: {token}");\n    foreach (var token in new[] { "ЛАЙТ", "GAME", "EXTREME", "Установить сборку", "Выбрать ЛАЙТ", "Выбрать GAME", "Выбрать EXTREME" })\n        if (!xaml.Contains(token, StringComparison.Ordinal)) failures.Add($"R47 build UI missing: {token}");''')
anchor='''    foreach (var tag in new[] { "privacy_safe", "privacy_strict", "privacy_maximum" })\n        if (!tweaks.Any(x => !x.ScanOnly && x.ProfileTags.Contains(tag, StringComparer.OrdinalIgnoreCase))) failures.Add($"R27 privacy profile tag missing: {tag}");\n'''
add=anchor+'''    var r47Light = tweaks.Where(x => !x.ScanOnly && x.ProfileTags.Contains("merzo_light", StringComparer.OrdinalIgnoreCase)).Select(x => x.Id).ToHashSet(StringComparer.OrdinalIgnoreCase);\n    var r47Game = tweaks.Where(x => !x.ScanOnly && x.ProfileTags.Contains("merzo_game", StringComparer.OrdinalIgnoreCase)).Select(x => x.Id).ToHashSet(StringComparer.OrdinalIgnoreCase);\n    var r47Extreme = tweaks.Where(x => !x.ScanOnly && x.ProfileTags.Contains("merzo_extreme", StringComparer.OrdinalIgnoreCase)).Select(x => x.Id).ToHashSet(StringComparer.OrdinalIgnoreCase);\n    if (r47Light.Count < 80 || r47Game.Count <= r47Light.Count || r47Extreme.Count <= r47Game.Count) failures.Add($"R47 cumulative build sizes invalid: LIGHT={r47Light.Count}, GAME={r47Game.Count}, EXTREME={r47Extreme.Count}");\n    if (!r47Light.IsSubsetOf(r47Game) || !r47Game.IsSubsetOf(r47Extreme)) failures.Add("R47 builds must be cumulative: LIGHT ⊂ GAME ⊂ EXTREME.");\n    foreach (var id in new[] { "explorer.launch_this_pc", "explorer.classic_context_menu" }) if (!r47Light.Contains(id)) failures.Add($"R47 LIGHT shell UX missing: {id}");\n'''
ss=replace_once(ss,anchor,add,'selftest R47 catalog')
write(sp,ss)

for csproj in (root/'src').glob('*/**/*.csproj'):
    c=read(csproj)
    c=re.sub(r'<Version>[^<]+</Version>','<Version>0.1.47</Version>',c)
    c=re.sub(r'<VersionPrefix>[^<]+</VersionPrefix>','<VersionPrefix>0.1.47</VersionPrefix>',c)
    c=re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>','<AssemblyVersion>0.1.47.0</AssemblyVersion>',c)
    c=re.sub(r'<FileVersion>[^<]+</FileVersion>','<FileVersion>0.1.47.0</FileVersion>',c)
    c=re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>','<InformationalVersion>0.1.47</InformationalVersion>',c)
    write(csproj,c)

rp=root/'data'/'release_notes.json'
notes=json.loads(read(rp)) if rp.exists() else {}
notes.update({
 'version':'0.1.47','title':'R47 SIMPLE BUILDS','summary':'Интерфейс упрощён до трёх накопительных сборок: ЛАЙТ, GAME и EXTREME; старые подробные инструменты сохранены в экспертном режиме.',
 'changes':[
  'Основная навигация сокращена до Главная / Сборки / Очистка / Восстановление / Обновления; остальные разделы спрятаны в «Экспертные инструменты».',
  'ЛАЙТ: максимальная privacy/telemetry-разгрузка, реклама/предложения, безопасное снижение фона, Проводник → Этот компьютер и классическое контекстное меню Windows 11.',
  'GAME полностью включает ЛАЙТ и добавляет performance/game tweaks, уменьшение фоновой нагрузки и Gaming Network SAFE.',
  'EXTREME полностью включает GAME и добавляет агрессивные обратимые настройки, дополнительные условные службы/задачи и Gaming Network EXTREME.',
  'Все три сборки сохраняют Snapshot → Apply → Verify → Log → Undo/Restore и не отключают Defender, Windows Update, Store, IPv6 или pagefile.',
  'Ручная настройка, Privacy и подробный ход работы доступны в сворачиваемом «Дополнительно».'
 ]})
write(rp,json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
(root/'R47_SIMPLE_BUILDS.marker').write_text('R47 SIMPLE BUILDS\n3 cumulative builds + simplified navigation + shell UX\n',encoding='utf-8')
print('R47 simple builds patch OK')