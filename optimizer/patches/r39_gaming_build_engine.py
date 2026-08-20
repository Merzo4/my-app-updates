from pathlib import Path
import os

root = Path(os.environ['SOURCE_ROOT'])
p = root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s = p.read_text(encoding='utf-8-sig')

# R38 Gaming buttons now select complete Gaming Build plans, not only Gaming-category tweaks.
s = s.replace('SelectGamingTaggedPresetAsync("gaming_safe", "GAMING SAFE")', 'SelectGamingTaggedPresetAsync("gaming_build_safe", "GAME BUILD SAFE")', 1)
s = s.replace('SelectGamingTaggedPresetAsync("gaming_performance", "GAMING PERFORMANCE")', 'SelectGamingTaggedPresetAsync("gaming_build_performance", "GAME BUILD PERFORMANCE")', 1)
s = s.replace('SelectGamingTaggedPresetAsync("gaming_extreme", "GAMING EXTREME")', 'SelectGamingTaggedPresetAsync("gaming_build_extreme", "GAME BUILD EXTREME")', 1)
s = s.replace('SelectGamingTaggedPresetAsync("gaming_lab", "GAMING LAB")', 'SelectGamingTaggedPresetAsync("gaming_build_lab", "GAME BUILD LAB")', 1)

start = s.find('    private async Task ApplySelectedTweaksAsync()')
end = s.find('    private void CleanupCategoryOnPropertyChanged', start)
if start < 0 or end < 0:
    raise SystemExit('R39 ApplySelectedTweaksAsync boundaries missing')

method = r'''    private async Task ApplySelectedTweaksAsync()
    {
        var selected = SafeTweaks.Where(static c => c.IsSelected && !c.Definition.ScanOnly && c.IsSupported && !c.IsApplied).ToArray();
        var profileTag = _selectedProfileTag;
        var gamingSafe = profileTag == "gaming_build_safe";
        var gamingPerformance = profileTag == "gaming_build_performance";
        var gamingExtreme = profileTag == "gaming_build_extreme";
        var gamingLab = profileTag == "gaming_build_lab";
        var gamingBuild = gamingSafe || gamingPerformance || gamingExtreme || gamingLab;
        var gamingNetworkMode = gamingExtreme || gamingLab ? "EXTREME" : gamingBuild ? "SAFE" : null;
        var profileIncludesTelemetry = profileTag is "standard" or "maximum" or "lite_build" || gamingPerformance || gamingExtreme || gamingLab;
        var profileIncludesWer = profileTag is "maximum" or "lite_build" || gamingExtreme || gamingLab;

        IReadOnlyList<ServiceAuditItem> services = Array.Empty<ServiceAuditItem>();
        IReadOnlyList<ScheduledTaskAuditItem> tasks = Array.Empty<ScheduledTaskAuditItem>();
        if (profileIncludesTelemetry)
        {
            var serviceSnapshot = await _serviceAudit.ScanAsync(_lifetimeCts.Token);
            var serviceNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "DiagTrack", "dmwappushservice" };
            if (profileIncludesWer) serviceNames.Add("WerSvc");
            if (gamingPerformance || gamingExtreme || gamingLab)
            {
                foreach (var name in new[] { "MapsBroker", "Fax", "RemoteRegistry", "diagnosticshub.standardcollector.service" }) serviceNames.Add(name);
            }
            if (gamingExtreme || gamingLab)
            {
                foreach (var name in new[] { "icssvc", "SCardSvr", "ScDeviceEnum", "SCPolicySvc", "SensorDataService", "SensorService", "SensrSvc", "SEMgrSvc" }) serviceNames.Add(name);
            }
            if (gamingLab)
            {
                serviceNames.Add("TabletInputService");
                serviceNames.Add("WbioSrvc");
            }
            services = serviceSnapshot.Where(x => serviceNames.Contains(x.ServiceName) && x.CanManage && !x.IsDisabled).ToArray();

            var taskSnapshot = await _taskAudit.ScanAsync(_lifetimeCts.Token);
            tasks = taskSnapshot.Where(x => x.CanManage && x.Enabled && IsPrivacyTelemetryTask(x) &&
                (profileIncludesWer || !x.FullPath.Contains(@"\Microsoft\Windows\Windows Error Reporting\", StringComparison.OrdinalIgnoreCase))).ToArray();
        }

        var networkSteps = gamingNetworkMode is null ? 0 : 1;
        if (selected.Length == 0 && services.Count == 0 && tasks.Count == 0 && networkSteps == 0)
        {
            Stage2StatusText = "В выбранном профиле нет неприменённых изменений.";
            return;
        }

        var balancedCount = selected.Count(static c => c.Definition.Risk == TweakRisk.Balanced);
        var registryActions = selected.Sum(static c => c.Definition.RegistryActions.Count);
        var total = selected.Length + services.Count + tasks.Count + networkSteps;
        var profileText = profileTag switch
        {
            "light" => "Privacy SAFE: безопасные privacy-политики без отключения telemetry-служб.",
            "standard" => $"Privacy STRICT: telemetry services {services.Count}, telemetry tasks {tasks.Count}.",
            "maximum" => $"Privacy MAX: telemetry/WER services {services.Count}, telemetry/WER tasks {tasks.Count}.",
            "lite_build" => $"Privacy MAX для LITE BUILD: services {services.Count}, tasks {tasks.Count}.",
            "gaming_build_safe" => "GAME BUILD SAFE: безопасные игровые/фоновые твики + Gaming Network SAFE. Системные службы автоматически не отключаются.",
            "gaming_build_performance" => $"GAME BUILD PERFORMANCE: игровые и performance-твики + снижение источников фоновых процессов + {services.Count} подходящих служб + {tasks.Count} telemetry tasks + Gaming Network SAFE.",
            "gaming_build_extreme" => $"GAME BUILD EXTREME: агрессивная разгрузка Windows + {services.Count} условных служб + {tasks.Count} задач + Gaming Network EXTREME с сохранением baseline адаптера.",
            "gaming_build_lab" => $"GAME BUILD LAB: EXTREME + экспериментальные scheduler/GPU/MMCSS-твики и дополнительные условные службы. Это режим для A/B тестов, а не универсальный пресет.",
            _ => "Ручной набор: дополнительные службы и сеть автоматически не изменяются."
        };
        var warning = balancedCount > 0 ? $"\nBALANCED/EXPERIMENTAL твиков: {balancedCount}." : string.Empty;
        var gamingWarning = gamingExtreme || gamingLab
            ? "\n\nВНИМАНИЕ: EXTREME/LAB может отключить функции Hotspot/Smart Card/Sensors и изменить параметры сетевого адаптера. Defender, Windows Update, Store, IPv6 и pagefile не отключаются."
            : string.Empty;
        var confirmation = global::MerzoOptimizer.App.MerzoDialog.Show(
            $"Применить выбранный пакет?\n\nRegistry/Policy: {selected.Length}\nRegistry-операций: {registryActions}\nСлужб/фоновых источников: {services.Count}\nScheduled Tasks: {tasks.Count}\nGaming Network: {gamingNetworkMode ?? "нет"}{warning}\n\n{profileText}{gamingWarning}\n\nКаждая поддерживаемая системная операция идёт через Snapshot → Apply → Verify → Log → Undo. При ошибке уже выполненные Snapshot-изменения этого запуска восстанавливаются автоматически.",
            gamingBuild ? "Merzo Windows Optimizer — Gaming Build" : "Merzo Windows Optimizer — применение профиля",
            MessageBoxButton.YesNo,
            (balancedCount > 0 || profileIncludesTelemetry || gamingExtreme || gamingLab) ? MessageBoxImage.Warning : MessageBoxImage.Question);
        if (confirmation != MessageBoxResult.Yes) return;

        SelectedOptimizationTabIndex = 3;
        DeepScanSteps.Clear();
        DeepScanProgress = 0;
        DeepScanStatusText = $"Применение профиля: 0/{total}";
        DeepScanSteps.Add($"План запущен · всего шагов {total} · Registry/Policy {selected.Length} · services {services.Count} · tasks {tasks.Count} · network {gamingNetworkMode ?? "—"}");
        IsStage2Busy = true;
        var appliedSnapshotIds = new List<Guid>();
        var done = 0;
        var gamingExtremeTouched = false;
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
                Stage2StatusText = $"Шаг {done + 1}/{total}: отключение службы {item.DisplayName}…";
                DeepScanStatusText = $"Background service {done + 1}/{total}: {item.DisplayName}";
                DeepScanSteps.Add($"→ {done + 1}/{total} · служба {item.DisplayName}");
                var result = await _dispatcher.RunAsync($"Profile service {item.ServiceName}", token => _serviceAudit.DisableAsync(item.ServiceName, token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException($"{item.DisplayName}: {result.Message}");
                if (result.Changed && result.SnapshotId is Guid id) appliedSnapshotIds.Add(id);
                done++;
                DeepScanSteps[DeepScanSteps.Count - 1] = result.Changed ? $"✓ {done}/{total} · служба {item.DisplayName} отключена" : $"✓ {done}/{total} · служба {item.DisplayName} уже настроена";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
            }

            foreach (var item in tasks)
            {
                Stage2StatusText = $"Шаг {done + 1}/{total}: отключение фоновой задачи {item.Name}…";
                DeepScanStatusText = $"Scheduled task {done + 1}/{total}: {item.Name}";
                DeepScanSteps.Add($"→ {done + 1}/{total} · задача {item.FullPath}");
                var result = await _dispatcher.RunAsync($"Profile task {item.FullPath}", token => _taskAudit.DisableAsync(item.Path, item.Name, token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException($"{item.FullPath}: {result.Message}");
                if (result.Changed && result.SnapshotId is Guid id) appliedSnapshotIds.Add(id);
                done++;
                DeepScanSteps[DeepScanSteps.Count - 1] = result.Changed ? $"✓ {done}/{total} · задача {item.Name} отключена" : $"✓ {done}/{total} · задача {item.Name} уже настроена";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
            }

            if (gamingNetworkMode is not null)
            {
                Stage2StatusText = $"Шаг {done + 1}/{total}: Gaming Network {gamingNetworkMode}…";
                DeepScanStatusText = $"Gaming Network {done + 1}/{total}: {gamingNetworkMode}";
                DeepScanSteps.Add($"→ {done + 1}/{total} · Gaming Network {gamingNetworkMode}");
                if (gamingNetworkMode == "EXTREME") gamingExtremeTouched = true;
                var result = gamingNetworkMode == "EXTREME"
                    ? await _dispatcher.RunAsync("Gaming Build Network EXTREME", token => _networkRepairService.ApplyGamingNetworkExtremeAsync(token), _lifetimeCts.Token)
                    : await _dispatcher.RunAsync("Gaming Build Network SAFE", token => _networkRepairService.ApplyGamingNetworkSafeAsync(token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException(result.Message);
                done++;
                DeepScanSteps[DeepScanSteps.Count - 1] = $"✓ {done}/{total} · Gaming Network {gamingNetworkMode}";
                DeepScanProgress = done * 100.0 / Math.Max(1,total);
            }

            Stage2StatusText = gamingBuild
                ? $"Gaming Build применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count} · Network: {gamingNetworkMode}."
                : $"Профиль применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count}.";
            DeepScanStatusText = $"План завершён: {done}/{total} · Snapshot {appliedSnapshotIds.Count}";
            DeepScanProgress = 100;
            DeepScanSteps.Add($"✓ Профиль завершён · Registry/Policy {selected.Length} · services {services.Count} · tasks {tasks.Count} · network {gamingNetworkMode ?? "—"} · Snapshot {appliedSnapshotIds.Count}");
            foreach (var card in selected) card.IsSelected = false;
            _selectedProfileTag = null;
            RefreshSelectedTweaks();
            global::MerzoOptimizer.App.MerzoDialog.Show(Stage2StatusText + "\n\nПодробный ход операции сохранён на вкладке «Ход работы». Для отключённых служб рекомендуется перезагрузка Windows.", "Merzo Windows Optimizer — профиль применён", MessageBoxButton.OK, MessageBoxImage.Information);
        }
        catch (OperationCanceledException) when (_lifetimeCts.IsCancellationRequested)
        {
            if (gamingExtremeTouched)
            {
                try { await _dispatcher.RunAsync("Rollback Gaming Network", token => _networkRepairService.RestoreGamingNetworkAsync(token), CancellationToken.None); } catch { }
            }
            foreach (var snapshotId in appliedSnapshotIds.AsEnumerable().Reverse())
                await _dispatcher.RunAsync($"Rollback canceled snapshot {snapshotId:N}", token => _restoreService.RestoreAsync(snapshotId, token), CancellationToken.None);
            DeepScanStatusText = "Пакет остановлен · восстановление выполнено";
            Stage2StatusText = appliedSnapshotIds.Count > 0 ? "Пакет остановлен; изменения этого запуска восстановлены." : "Пакет остановлен.";
        }
        catch (Exception ex)
        {
            DeepScanStatusText = "Ошибка · выполняется восстановление…";
            if (gamingExtremeTouched)
            {
                try { await _dispatcher.RunAsync("Rollback Gaming Network", token => _networkRepairService.RestoreGamingNetworkAsync(token), CancellationToken.None); } catch { }
            }
            foreach (var snapshotId in appliedSnapshotIds.AsEnumerable().Reverse())
                await _dispatcher.RunAsync($"Rollback snapshot {snapshotId:N}", token => _restoreService.RestoreAsync(snapshotId, token), CancellationToken.None);
            DeepScanStatusText = "Аварийное восстановление завершено";
            Stage2StatusText = $"Пакет отменён и восстановлен: {ex.Message}";
            global::MerzoOptimizer.App.MerzoDialog.Show(Stage2StatusText, "Merzo Windows Optimizer — восстановление", MessageBoxButton.OK, MessageBoxImage.Error);
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
s = s[:start] + method + s[end:]
p.write_text(s, encoding='utf-8')
print('R39 Gaming Build engine: OK')
