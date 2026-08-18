from pathlib import Path
import json, os, re

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')
def replace_once(s,old,new,label):
    c=s.count(old)
    if c!=1: raise SystemExit(f'R49 {label} anchor count={c}')
    return s.replace(old,new,1)

# ---- App composition: inject Recovery Package and known OneDrive services. ----
app=root/'src'/'MerzoOptimizer.App'/'App.xaml.cs'
s=read(app)
s=replace_once(s,
'using MerzoOptimizer.Windows.Network;\n',
'using MerzoOptimizer.Windows.Network;\nusing MerzoOptimizer.Windows.Recovery;\nusing MerzoOptimizer.Windows.OneDrive;\n',
'app usings')
s=replace_once(s,
'''            var recoveryDiagnosticService = new SafeRecoveryDiagnosticService(logger);\n            var startupOptimizerService = new WindowsStartupOptimizerService(tweakService, snapshotService, restoreService);''',
'''            var recoveryDiagnosticService = new SafeRecoveryDiagnosticService(logger);\n            var recoveryPackageService = new WindowsRecoveryPackageService(_elevationBroker, Path.Combine(appDataRoot, "recovery-packages"), logger);\n            var oneDriveService = new WindowsOneDriveOptimizationService(_elevationBroker);\n            var startupOptimizerService = new WindowsStartupOptimizerService(tweakService, snapshotService, restoreService);''',
'app service creation')
s=replace_once(s,
'''                restoreService,\n                recoveryDiagnosticService,\n                startupOptimizerService,''',
'''                restoreService,\n                recoveryDiagnosticService,\n                recoveryPackageService,\n                oneDriveService,\n                startupOptimizerService,''',
'app vm args')
s=s.replace('string.IsNullOrWhiteSpace(pendingVersion) ? "0.1.46" : pendingVersion','string.IsNullOrWhiteSpace(pendingVersion) ? "0.1.49" : pendingVersion')
s=s.replace('[Crash][R46]','[Crash][R49]')
s=s.replace('Версия: 0.1.46 / Production R46','Версия: 0.1.49 / Production R49')
write(app,s)

# ---- ViewModel: guarded OneDrive decision + Recovery Package preflight for EXTREME/destructive step. ----
vm=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s=read(vm)
s=replace_once(s,
'using MerzoOptimizer.Core.Tweaks;\n',
'using MerzoOptimizer.Core.Tweaks;\nusing MerzoOptimizer.Windows.Recovery;\nusing MerzoOptimizer.Windows.OneDrive;\n',
'vm usings')
s=replace_once(s,
'''    private readonly IRecoveryDiagnosticService _recoveryDiagnosticService;\n    private readonly IStartupOptimizerService _startupOptimizer;''',
'''    private readonly IRecoveryDiagnosticService _recoveryDiagnosticService;\n    private readonly IRecoveryPackageService _recoveryPackageService;\n    private readonly IOneDriveOptimizationService _oneDriveService;\n    private readonly IStartupOptimizerService _startupOptimizer;''',
'vm fields')
s=replace_once(s,
'''        IRestoreService restoreService,\n        IRecoveryDiagnosticService recoveryDiagnosticService,\n        IStartupOptimizerService startupOptimizer,''',
'''        IRestoreService restoreService,\n        IRecoveryDiagnosticService recoveryDiagnosticService,\n        IRecoveryPackageService recoveryPackageService,\n        IOneDriveOptimizationService oneDriveService,\n        IStartupOptimizerService startupOptimizer,''',
'vm constructor args')
s=replace_once(s,
'''        _restoreService = restoreService;\n        _recoveryDiagnosticService = recoveryDiagnosticService;\n        _startupOptimizer = startupOptimizer;''',
'''        _restoreService = restoreService;\n        _recoveryDiagnosticService = recoveryDiagnosticService;\n        _recoveryPackageService = recoveryPackageService;\n        _oneDriveService = oneDriveService;\n        _startupOptimizer = startupOptimizer;''',
'vm constructor assignment')
s=s.replace('ApplySelectedTweaksCommand = new AsyncRelayCommand(ApplySelectedTweaksAsync, () => !IsStage2Busy && SafeTweaks.Any(x => x.IsSelected));',
'''ApplySelectedTweaksCommand = new AsyncRelayCommand(ApplySelectedTweaksAsync, () => !IsStage2Busy && (_selectedProfileTag is not null || SafeTweaks.Any(x => x.IsSelected)));''')

s=replace_once(s,
'''        var selected = SafeTweaks.Where(static c => c.IsSelected && !c.Definition.ScanOnly && c.IsSupported && !c.IsApplied).ToArray();''',
'''        var selected = SafeTweaks.Where(static c => c.IsSelected && !c.Definition.ScanOnly && c.IsSupported && !c.IsApplied).ToList();''',
'apply selected list')

onedrive_preflight=r'''        var oneDriveUninstallRequested = false;
        OneDriveStatus? oneDriveStatus = null;
        if (merzoLight || merzoGame || merzoExtreme)
        {
            try
            {
                oneDriveStatus = await _dispatcher.RunAsync("OneDrive preflight", token => _oneDriveService.InspectAsync(token), _lifetimeCts.Token);
                if (oneDriveStatus.Installed && oneDriveStatus.Configured)
                {
                    var optimizeOneDrive = global::MerzoOptimizer.App.MerzoDialog.Show(
                        "OneDrive установлен и настроен на этом ПК.\n\nДа — включить OneDrive в оптимизацию сборки.\nНет — оставить OneDrive полностью без изменений.\nОтмена — не запускать сборку.\n\nMerzo никогда не удаляет пользовательские папки и файлы OneDrive.",
                        "Merzo — OneDrive используется",
                        MessageBoxButton.YesNoCancel,
                        MessageBoxImage.Warning);
                    if (optimizeOneDrive == MessageBoxResult.Cancel) return;
                    if (optimizeOneDrive == MessageBoxResult.No)
                    {
                        selected.RemoveAll(static c => c.Id.Contains("onedrive", StringComparison.OrdinalIgnoreCase));
                    }
                    else
                    {
                        var removeOneDrive = global::MerzoOptimizer.App.MerzoDialog.Show(
                            "Полностью удалить приложение Microsoft OneDrive после применения сборки?\n\nДа — штатно удалить приложение OneDrive.\nНет — только отключить синхронизацию/автозапуск.\n\nОблачные и локальные пользовательские файлы Merzo не удаляет. Для полного удаления приложения сначала будет создан Recovery Package.",
                            "Merzo — OneDrive",
                            MessageBoxButton.YesNo,
                            MessageBoxImage.Warning);
                        oneDriveUninstallRequested = removeOneDrive == MessageBoxResult.Yes;
                    }
                }
                else if (oneDriveStatus.Installed && !oneDriveStatus.Configured)
                {
                    oneDriveUninstallRequested = true;
                }
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                Stage2StatusText = $"OneDrive preflight недоступен: {ex.Message}. Приложение OneDrive удаляться не будет.";
                oneDriveUninstallRequested = false;
            }
        }

'''
anchor='''        IReadOnlyList<ServiceAuditItem> services = Array.Empty<ServiceAuditItem>();\n'''
if s.count(anchor)!=1: raise SystemExit(f'R49 OneDrive insertion anchor count={s.count(anchor)}')
s=s.replace(anchor,onedrive_preflight+anchor,1)

s=replace_once(s,
'''        var networkSteps = gamingNetworkMode is null ? 0 : 1;\n        if (selected.Length == 0 && services.Count == 0 && tasks.Count == 0 && networkSteps == 0)''',
'''        var networkSteps = gamingNetworkMode is null ? 0 : 1;\n        var oneDriveSteps = oneDriveUninstallRequested ? 1 : 0;\n        if (selected.Count == 0 && services.Count == 0 && tasks.Count == 0 && networkSteps == 0 && oneDriveSteps == 0)''',
'apply step availability')
s=s.replace('var total = selected.Length + services.Count + tasks.Count + networkSteps;', 'var total = selected.Count + services.Count + tasks.Count + networkSteps + oneDriveSteps;')
s=s.replace('Registry/Policy: {selected.Length}', 'Registry/Policy: {selected.Count}')
s=s.replace('Registry/Policy {selected.Length}', 'Registry/Policy {selected.Count}')

s=s.replace('''"merzo_light" => $"ЛАЙТ — Чистая Windows: максимальная privacy/telemetry-разгрузка, меньше рекламы/фона, Explorer UX и безопасное сокращение процессов. Services {services.Count}, tasks {tasks.Count}.",''',
'''"merzo_light" => $"ЛАЙТ — Чистая Windows: максимально ограничивает доступную телеметрию, чистит Пуск/рекомендации, снижает фон, настраивает Explorer и OneDrive. Services {services.Count}, tasks {tasks.Count}.",''')
s=s.replace('''"merzo_game" => $"GAME — всё из ЛАЙТ + performance/game tweaks, снижение фоновой нагрузки и Gaming Network SAFE. Services {services.Count}, tasks {tasks.Count}.",''',
'''"merzo_game" => $"GAME — всё из ЛАЙТ + performance/game tweaks, Power Throttling off, снижение фоновой нагрузки и Gaming Network SAFE. Services {services.Count}, tasks {tasks.Count}.",''')
s=s.replace('''"merzo_extreme" => $"EXTREME — всё из GAME + агрессивная разгрузка Windows, дополнительные условные службы/задачи и Gaming Network EXTREME. Services {services.Count}, tasks {tasks.Count}.",''',
'''"merzo_extreme" => $"EXTREME — всё из GAME + агрессивная разгрузка, Game DVR off, дополнительные условные службы/задачи и Gaming Network EXTREME. Перед запуском обязателен Recovery Package. Services {services.Count}, tasks {tasks.Count}.",''')
s=s.replace('''? "\\n\\nВНИМАНИЕ: EXTREME может отключить условные фоновые функции Hotspot/Smart Card/Sensors и изменить параметры сетевого адаптера. Defender, Windows Update, Store, IPv6 и pagefile не отключаются. Все поддерживаемые изменения остаются под Snapshot/Undo."''',
'''? "\\n\\nВНИМАНИЕ: EXTREME может отключить условные фоновые функции Hotspot/Smart Card/Sensors, Game DVR и изменить параметры сетевого адаптера. Перед EXTREME Merzo обязан подготовить Recovery Package + System Restore. Defender, Windows Update, Store, IPv6 и pagefile не отключаются."''')

s=replace_once(s,
'''            $"Применить выбранный пакет?\\n\\nRegistry/Policy: {selected.Count}\\nRegistry-операций: {registryActions}\\nСлужб/фоновых источников: {services.Count}\\nScheduled Tasks: {tasks.Count}\\nGaming Network: {gamingNetworkMode ?? "нет"}{warning}\\n\\n{profileText}{gamingWarning}\\n\\nКаждая поддерживаемая системная операция идёт через Snapshot → Apply → Verify → Log → Undo. При ошибке уже выполненные Snapshot-изменения этого запуска восстанавливаются автоматически.",''',
'''            $"Применить выбранный пакет?\\n\\nRegistry/Policy: {selected.Count}\\nRegistry-операций: {registryActions}\\nСлужб/фоновых источников: {services.Count}\\nScheduled Tasks: {tasks.Count}\\nGaming Network: {gamingNetworkMode ?? "нет"}\\nOneDrive: {(oneDriveStatus?.Installed == true ? (oneDriveUninstallRequested ? "удаление приложения после Recovery Package" : "политики/автозапуск") : "не установлен")}\\nRecovery Package: {(merzoExtreme || oneDriveUninstallRequested ? "ОБЯЗАТЕЛЕН" : "обычный Snapshot/Undo")}{warning}\\n\\n{profileText}{gamingWarning}\\n\\nКаждая поддерживаемая системная операция идёт через Snapshot → Apply → Verify → Log → Undo. Необратимый шаг OneDrive выполняется только последним и только при готовом Recovery Package.",''',
'confirmation text')

recovery_preflight=r'''        RecoveryPackageResult? recoveryPackage = null;
        if (merzoExtreme || oneDriveUninstallRequested)
        {
            var recoveryPlan = new List<string>();
            recoveryPlan.AddRange(selected.Select(static c => "tweak:" + c.Id));
            recoveryPlan.AddRange(services.Select(static x => "service:" + x.ServiceName));
            recoveryPlan.AddRange(tasks.Select(static x => "task:" + x.FullPath));
            if (gamingNetworkMode is not null) recoveryPlan.Add("network:" + gamingNetworkMode);
            if (oneDriveUninstallRequested) recoveryPlan.Add("app:OneDrive/uninstall");
            Stage2StatusText = "Создаю Recovery Package и System Restore Point перед жёсткими изменениями…";
            recoveryPackage = await _dispatcher.RunAsync(
                "Recovery Package preflight",
                token => _recoveryPackageService.CreateAsync(merzoExtreme ? "EXTREME" : "ONEDRIVE", recoveryPlan, token),
                _lifetimeCts.Token);
            if (!recoveryPackage.Success)
            {
                if (merzoExtreme)
                {
                    Stage2StatusText = recoveryPackage.Message;
                    global::MerzoOptimizer.App.MerzoDialog.Show(
                        recoveryPackage.Message + "\n\nEXTREME отменён: без подтверждённой аварийной защиты жёсткая сборка не запускается.",
                        "Merzo — EXTREME заблокирован",
                        MessageBoxButton.OK,
                        MessageBoxImage.Error);
                    return;
                }

                oneDriveUninstallRequested = false;
                oneDriveSteps = 0;
                total = selected.Count + services.Count + tasks.Count + networkSteps;
                global::MerzoOptimizer.App.MerzoDialog.Show(
                    recoveryPackage.Message + "\n\nПолное удаление OneDrive отменено. Остальная ЛАЙТ/GAME оптимизация продолжится только с обратимыми OneDrive policy/startup изменениями.",
                    "Merzo — OneDrive оставлен",
                    MessageBoxButton.OK,
                    MessageBoxImage.Warning);
            }
        }

'''
anchor='''        SelectedOptimizationTabIndex = 4;\n'''
if s.count(anchor)<1: raise SystemExit('R49 selected tab anchor missing')
# There may be other assignments; target first occurrence after confirmation by replacing the exact nearby sequence.
seq='''        if (confirmation != MessageBoxResult.Yes) return;\n\n        SelectedOptimizationTabIndex = 4;\n'''
if s.count(seq)!=1: raise SystemExit(f'R49 recovery preflight sequence count={s.count(seq)}')
s=s.replace(seq,'        if (confirmation != MessageBoxResult.Yes) return;\n\n'+recovery_preflight+'        SelectedOptimizationTabIndex = 4;\n',1)

s=replace_once(s,
'''        DeepScanSteps.Add($"План запущен · всего шагов {total} · Registry/Policy {selected.Count} · services {services.Count} · tasks {tasks.Count} · network {gamingNetworkMode ?? "—"}");''',
'''        DeepScanSteps.Add($"План запущен · всего шагов {total} · Registry/Policy {selected.Count} · services {services.Count} · tasks {tasks.Count} · network {gamingNetworkMode ?? "—"} · OneDrive {(oneDriveUninstallRequested ? "remove" : "policy/keep")}");\n        if (recoveryPackage is { Success: true }) DeepScanSteps.Add($"✓ Recovery Package · {recoveryPackage.PackageId} · System Restore ready");''',
'operation start status')

onedrive_step=r'''            if (oneDriveUninstallRequested)
            {
                Stage2StatusText = $"Шаг {done + 1}/{total}: штатное удаление OneDrive…";
                DeepScanStatusText = $"OneDrive {done + 1}/{total}: штатное удаление приложения";
                DeepScanSteps.Add($"→ {done + 1}/{total} · OneDrive uninstall · пользовательские папки не трогаются");
                var result = await _dispatcher.RunAsync("OneDrive uninstall", token => _oneDriveService.UninstallAsync(token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException(result.Message);
                done++;
                DeepScanSteps[DeepScanSteps.Count - 1] = result.Changed
                    ? $"✓ {done}/{total} · OneDrive удалён штатным installer · файлы пользователя не удалялись"
                    : $"✓ {done}/{total} · OneDrive уже отсутствует / uninstall не потребовался";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
            }

'''
anchor='''            Stage2StatusText = gamingBuild\n'''
if s.count(anchor)!=1: raise SystemExit(f'R49 OneDrive execution anchor count={s.count(anchor)}')
s=s.replace(anchor,onedrive_step+anchor,1)

completion=r'''            if (recoveryPackage is { Success: true })
            {
                try
                {
                    await _recoveryPackageService.CompleteAsync(
                        recoveryPackage.PackageId,
                        appliedSnapshotIds,
                        gamingExtremeTouched,
                        oneDriveUninstallRequested ? "OneDrive uninstall was the final guarded step." : "EXTREME recovery package completed.",
                        _lifetimeCts.Token);
                }
                catch (Exception ex)
                {
                    DeepScanSteps.Add($"⚠ Recovery Package metadata: {ex.Message}");
                }
            }
'''
anchor='''            foreach (var card in selected) card.IsSelected = false;\n'''
if s.count(anchor)!=1: raise SystemExit(f'R49 recovery completion anchor count={s.count(anchor)}')
s=s.replace(anchor,completion+anchor,1)

# Better final wording: no fake performance claims, expose real recovery state.
s=s.replace('''Stage2StatusText = gamingBuild\n                ? $"Gaming Build применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count} · Network: {gamingNetworkMode}."\n                : $"Профиль применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count}.";''',
'''Stage2StatusText = gamingBuild\n                ? $"Gaming Build применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count} · Network: {gamingNetworkMode} · Recovery: {(recoveryPackage?.Success == true ? "готов" : "Snapshot/Undo")}."\n                : $"Профиль применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count} · Recovery: {(recoveryPackage?.Success == true ? "готов" : "Snapshot/Undo")}.";''')
write(vm,s)

# ---- XAML: explain the three builds honestly and compactly. ----
x=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
s=read(x)
s=s.replace('Production 0.1.48','Production 0.1.49')
s=s.replace('Production R48','Production R49')
s=s.replace('R48 OTA RELIABILITY','R49 PUBLIC READY')
s=s.replace('<!-- R47 SIMPLE BUILDS -->','<!-- R49 SIMPLE BUILDS FINAL -->')
s=s.replace('Телеметрия отключается уже в ЛАЙТ. Defender / Windows Update / Store / IPv6 / pagefile сборки не отключают.',
'''Доступная телеметрия максимально ограничивается уже в ЛАЙТ. OneDrive без настроенного аккаунта может быть удалён; пользовательские файлы Merzo не трогает.''')
s=s.replace('SNAPSHOT + UNDO','SNAPSHOT + UNDO + RECOVERY',1)
s=s.replace('✓ Телеметрия / WER / privacy — максимум','✓ Privacy / telemetry — максимально доступно')
s=s.replace('✓ Реклама, советы и consumer-предложения','✓ Чистый Пуск: рекомендации / реклама / recent')
s=s.replace('✓ Безопасное снижение фоновых процессов','✓ OneDrive: off; без аккаунта — guarded uninstall')
s=s.replace('✓ Game Mode / GPU / MMCSS где поддерживается','✓ Game Mode / GPU / MMCSS где поддерживается')
s=s.replace('✓ Performance и отзывчивость Windows','✓ Performance + Power Throttling off')
s=s.replace('✓ Меньше фоновых служб и задач','✓ Жёстче фоновые службы и задачи')
s=s.replace('Максимальная обратимая разгрузка','Максимальная жёсткая разгрузка + Recovery',1)
s=s.replace('✓ Более агрессивные performance-твики','✓ Агрессивные performance-твики + Game DVR off')
s=s.replace('✓ Максимум фона убирается без критических служб','✓ Перед запуском обязателен Recovery Package')
s=s.replace('Дополнительно — ручная настройка, Privacy и подробный ход работы','Дополнительно — ручная настройка, Privacy, LAB / скрытые исправления и ход работы')
write(x,s)

# ---- Stamp 0.1.49 everywhere and refresh release notes without losing unknown fields. ----
for csproj in (root/'src').rglob('*.csproj'):
    t=read(csproj)
    t=re.sub(r'<Version>[^<]+</Version>','<Version>0.1.49</Version>',t)
    t=re.sub(r'<VersionPrefix>[^<]+</VersionPrefix>','<VersionPrefix>0.1.49</VersionPrefix>',t)
    t=re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>','<AssemblyVersion>0.1.49.0</AssemblyVersion>',t)
    t=re.sub(r'<FileVersion>[^<]+</FileVersion>','<FileVersion>0.1.49.0</FileVersion>',t)
    t=re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>','<InformationalVersion>0.1.49</InformationalVersion>',t)
    write(csproj,t)

notes=root/'data'/'release_notes.json'
if notes.exists():
    data=json.loads(read(notes))
    data['version']='0.1.49'
    if 'title' in data: data['title']='R49 PUBLIC READY — CLEAN / GAME / EXTREME'
    changes=[
      'ЛАЙТ: чистый Пуск, privacy/tailored experience, Delivery Optimization без P2P, OneDrive preflight.',
      'OneDrive: если аккаунт не настроен — guarded uninstall только после Recovery Package; пользовательские файлы Merzo не удаляет.',
      'GAME: всё из ЛАЙТ + Power Throttling off и существующий gaming/performance stack.',
      'EXTREME: Recovery Package + System Restore обязателен до жёстких изменений; Game DVR off + Gaming Network EXTREME.',
      'LAB: отдельные экспериментальные/symptom-specific исправления не попадают в публичные сборки автоматически.',
      'R48 resilient updater и R46 security model сохранены.'
    ]
    for key in ('items','changes','notes'):
        if key in data and isinstance(data[key],list): data[key]=changes
    write(notes,json.dumps(data,ensure_ascii=False,indent=2)+'\n')

(root/'R49_BUILD_INTEGRATION.marker').write_text('R49 build integration\nRecovery Package + guarded OneDrive + SIMPLE BUILDS final\n',encoding='utf-8')
print('R49 build integration OK')
