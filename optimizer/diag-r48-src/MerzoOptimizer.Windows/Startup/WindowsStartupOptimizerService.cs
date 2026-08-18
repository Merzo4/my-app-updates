using System.Security.Cryptography;
using System.Text;
using Microsoft.Win32;
using MerzoOptimizer.Core.Snapshots;
using MerzoOptimizer.Core.Startup;
using MerzoOptimizer.Core.Tweaks;

namespace MerzoOptimizer.Windows.Startup;

public sealed class WindowsStartupOptimizerService : IStartupOptimizerService
{
    private const string RunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string IdPrefix = "startup.disable.";

    private readonly ITweakExecutionService _tweaks;
    private readonly ISnapshotService _snapshots;
    private readonly IRestoreService _restore;

    public WindowsStartupOptimizerService(
        ITweakExecutionService tweaks,
        ISnapshotService snapshots,
        IRestoreService restore)
    {
        _tweaks = tweaks;
        _snapshots = snapshots;
        _restore = restore;
    }

    public async Task<IReadOnlyList<StartupManagedItem>> ScanAsync(CancellationToken cancellationToken = default)
    {
        var activeSnapshots = (await _snapshots.ListAsync(cancellationToken).ConfigureAwait(false))
            .Where(static s => !s.IsRestored && s.TweakId is not null && s.TweakId.StartsWith(IdPrefix, StringComparison.OrdinalIgnoreCase))
            .GroupBy(static s => s.TweakId!, StringComparer.OrdinalIgnoreCase)
            .ToDictionary(static g => g.Key, static g => g.OrderByDescending(s => s.CreatedAt).First(), StringComparer.OrdinalIgnoreCase);

        var items = new List<StartupManagedItem>();
        ReadRunKey(items, RegistryHiveScope.CurrentUser, global::Microsoft.Win32.Registry.CurrentUser, "HKCU Run", "User", activeSnapshots);
        ReadRunKey(items, RegistryHiveScope.LocalMachine, global::Microsoft.Win32.Registry.LocalMachine, "HKLM Run", "Machine", activeSnapshots);

        var currentIds = items.Select(static i => i.Id).ToHashSet(StringComparer.OrdinalIgnoreCase);
        foreach (var snapshot in activeSnapshots.Values)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (snapshot.TweakId is null || currentIds.Contains(snapshot.TweakId))
                continue;

            var registry = snapshot.RegistryValues.FirstOrDefault();
            if (registry is null || !registry.Existed)
                continue;

            items.Add(new StartupManagedItem
            {
                Id = snapshot.TweakId,
                Name = registry.ValueName,
                Command = DescribeSnapshotCommand(registry),
                Source = registry.Hive == RegistryHiveScope.CurrentUser ? "HKCU Run" : "HKLM Run",
                Scope = registry.Hive == RegistryHiveScope.CurrentUser ? "User" : "Machine",
                IsEnabled = false,
                CanManage = true,
                HasRestorePoint = true,
                Recommendation = "Отключено Merzo · можно вернуть из snapshot",
                DisableDefinition = BuildDisableDefinition(
                    snapshot.TweakId,
                    registry.ValueName,
                    registry.Hive,
                    registry.KeyPath,
                    registry.ValueName)
            });
        }

        return items
            .OrderByDescending(static i => i.IsEnabled)
            .ThenBy(static i => i.Name, StringComparer.OrdinalIgnoreCase)
            .ToArray();
    }

    public Task<TweakApplyResult> DisableAsync(StartupManagedItem item, CancellationToken cancellationToken = default)
    {
        if (!item.CanManage || item.DisableDefinition is null)
        {
            return Task.FromResult(new TweakApplyResult
            {
                Success = false,
                Changed = false,
                Message = "Эта запись автозагрузки пока доступна только для чтения."
            });
        }

        if (!item.IsEnabled)
        {
            return Task.FromResult(new TweakApplyResult
            {
                Success = true,
                Changed = false,
                Message = "Автозагрузка уже отключена."
            });
        }

        return _tweaks.ApplyAsync(item.DisableDefinition, cancellationToken);
    }

    public Task<RestoreResult> RestoreAsync(StartupManagedItem item, CancellationToken cancellationToken = default) =>
        _restore.RestoreLatestForTweakAsync(item.Id, cancellationToken);

    private static void ReadRunKey(
        ICollection<StartupManagedItem> items,
        RegistryHiveScope hive,
        RegistryKey root,
        string source,
        string scope,
        IReadOnlyDictionary<string, ChangeSnapshot> activeSnapshots)
    {
        try
        {
            using var key = root.OpenSubKey(RunKey, writable: false);
            if (key is null)
                return;

            foreach (var valueName in key.GetValueNames())
            {
                if (string.IsNullOrWhiteSpace(valueName))
                    continue;

                var command = key.GetValue(valueName, null, RegistryValueOptions.DoNotExpandEnvironmentNames)?.ToString() ?? string.Empty;
                var id = BuildId(hive, valueName);
                var hasSnapshot = activeSnapshots.ContainsKey(id);

                items.Add(new StartupManagedItem
                {
                    Id = id,
                    Name = valueName,
                    Command = command,
                    Source = source,
                    Scope = scope,
                    IsEnabled = true,
                    CanManage = true,
                    HasRestorePoint = hasSnapshot,
                    Recommendation = IsWindowsSecurityEntry(valueName, command)
                        ? "Рекомендуется оставить"
                        : "Можно отключить, если приложение не нужно сразу после входа",
                    DisableDefinition = BuildDisableDefinition(id, valueName, hive, RunKey, valueName)
                });
            }
        }
        catch
        {
            // Best-effort: a denied registry hive must not break the whole page.
        }
    }

    private static TweakDefinition BuildDisableDefinition(
        string id,
        string name,
        RegistryHiveScope hive,
        string keyPath,
        string valueName) => new()
    {
        Id = id,
        Name = $"Отключить автозагрузку: {name}",
        Category = "Startup",
        Risk = TweakRisk.Safe,
        RequiresAdmin = hive == RegistryHiveScope.LocalMachine,
        RequiresRestart = false,
        Description = "Удаляет только конкретную запись Run. Исходное значение сохраняется в snapshot и может быть восстановлено.",
        ExpectedEffect = "Приложение перестанет запускаться автоматически при входе в Windows.",
        RegistryActions =
        [
            new RegistryTweakAction
            {
                Mode = RegistryTweakActionMode.DeleteValue,
                Hive = hive,
                KeyPath = keyPath,
                ValueName = valueName,
                ValueType = RegistryTweakValueType.String
            }
        ]
    };

    private static string BuildId(RegistryHiveScope hive, string valueName)
    {
        var raw = $"{hive}|{RunKey}|{valueName}";
        var hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(raw))).ToLowerInvariant()[..12];
        return $"{IdPrefix}{hash}";
    }

    private static bool IsWindowsSecurityEntry(string name, string command) =>
        name.Contains("SecurityHealth", StringComparison.OrdinalIgnoreCase) ||
        command.Contains("SecurityHealth", StringComparison.OrdinalIgnoreCase);

    private static string DescribeSnapshotCommand(RegistryValueSnapshot entry) => entry.ValueType switch
    {
        RegistryTweakValueType.String or RegistryTweakValueType.ExpandString => entry.StringValue ?? string.Empty,
        RegistryTweakValueType.DWord or RegistryTweakValueType.QWord => entry.IntegerValue?.ToString() ?? string.Empty,
        _ => "<сохранено в snapshot>"
    };
}
