using System.Text.Json;
using MerzoOptimizer.Core.Logging;
using MerzoOptimizer.Core.Services;
using MerzoOptimizer.Core.Snapshots;

namespace MerzoOptimizer.Windows.Services;

public sealed class WindowsServiceAuditService : IServiceOptimizationService
{
    private readonly string _rulesPath;
    private readonly ISnapshotService? _snapshots;
    private readonly IRestoreService? _restore;
    private readonly IAuditLogger? _logger;

    public WindowsServiceAuditService(
        ISnapshotService? snapshots = null,
        IRestoreService? restore = null,
        IAuditLogger? logger = null,
        string? rulesPath = null)
    {
        _snapshots = snapshots;
        _restore = restore;
        _logger = logger;
        _rulesPath = rulesPath ?? Path.Combine(AppContext.BaseDirectory, "data", "service_rules.json");
    }

    public Task<IReadOnlyList<ServiceAuditItem>> ScanAsync(CancellationToken cancellationToken = default) =>
        Task.Run<IReadOnlyList<ServiceAuditItem>>(() => Scan(cancellationToken), cancellationToken);

    public async Task<ServiceOperationResult> DisableAsync(string serviceName, CancellationToken cancellationToken = default)
    {
        if (_snapshots is null || _restore is null || _logger is null)
            return new ServiceOperationResult { Success = false, Changed = false, Message = "Service Optimizer не инициализирован для изменений." };

        var item = Scan(cancellationToken).FirstOrDefault(x => string.Equals(x.ServiceName, serviceName, StringComparison.OrdinalIgnoreCase));
        if (item is null)
            return new ServiceOperationResult { Success = false, Changed = false, Message = "Служба не найдена в безопасном каталоге Merzo." };
        if (!item.CanManage)
            return new ServiceOperationResult { Success = false, Changed = false, Message = "Эта служба помечена KEEP и не может быть отключена из Merzo." };
        if (item.IsDisabled)
            return new ServiceOperationResult { Success = true, Changed = false, Message = "Служба уже отключена; Merzo ничего не менял." };

        var snapshot = await _snapshots.CreateForServiceAsync(
            $"service.{item.ServiceName}",
            $"Служба: {item.DisplayName}",
            $"Перед отключением службы {item.ServiceName}",
            new ServiceStateSnapshot { ServiceName = item.ServiceName, StartValue = item.StartValue, WasRunning = item.IsRunning },
            cancellationToken).ConfigureAwait(false);

        try
        {
            using var key = global::Microsoft.Win32.Registry.LocalMachine.OpenSubKey($@"SYSTEM\CurrentControlSet\Services\{item.ServiceName}", writable: true)
                ?? throw new InvalidOperationException("Не удалось открыть ключ службы для записи.");
            key.SetValue("Start", 4, global::Microsoft.Win32.RegistryValueKind.DWord);

            await _logger.WriteAsync(new AuditLogEntry
            {
                Category = "Services",
                Action = $"Disable service {item.ServiceName}",
                Status = "Success",
                TweakId = $"service.{item.ServiceName}",
                OldValue = $"Start={item.StartValue}; running={item.IsRunning}",
                NewValue = "Start=4 (Disabled)",
                Details = $"Snapshot {snapshot.Id}. Текущий процесс службы не останавливается принудительно; новый тип запуска применяется безопасно."
            }, cancellationToken).ConfigureAwait(false);

            return new ServiceOperationResult
            {
                Success = true,
                Changed = true,
                SnapshotId = snapshot.Id,
                Message = $"{item.DisplayName}: тип запуска изменён на «Отключена». Snapshot {snapshot.Id.ToString("N")[..8]} создан."
            };
        }
        catch (Exception ex)
        {
            var rollback = await _restore.RestoreAsync(snapshot.Id, CancellationToken.None).ConfigureAwait(false);
            return new ServiceOperationResult
            {
                Success = false,
                Changed = false,
                SnapshotId = snapshot.Id,
                Message = $"Не удалось изменить службу: {ex.Message}. Rollback: {rollback.Message}"
            };
        }
    }

    public async Task<ServiceOperationResult> RestoreAsync(string serviceName, CancellationToken cancellationToken = default)
    {
        if (_restore is null)
            return new ServiceOperationResult { Success = false, Changed = false, Message = "Restore Service не инициализирован." };
        var result = await _restore.RestoreLatestForTweakAsync($"service.{serviceName}", cancellationToken).ConfigureAwait(false);
        return new ServiceOperationResult { Success = result.Success, Changed = result.Changed, SnapshotId = result.SnapshotId, Message = result.Message };
    }

    private IReadOnlyList<ServiceAuditItem> Scan(CancellationToken cancellationToken)
    {
        if (!File.Exists(_rulesPath))
            return [];

        var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true, PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
        var rules = JsonSerializer.Deserialize<List<ServiceRule>>(File.ReadAllText(_rulesPath), options) ?? [];
        var result = new List<ServiceAuditItem>();

        foreach (var rule in rules)
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var key = global::Microsoft.Win32.Registry.LocalMachine.OpenSubKey($@"SYSTEM\CurrentControlSet\Services\{rule.ServiceName}");
            if (key is null)
                continue;

            var start = key.GetValue("Start") is int value ? value : -1;
            var display = key.GetValue("DisplayName")?.ToString();
            var imagePath = key.GetValue("ImagePath")?.ToString();
            var status = TryGetServiceStatus(rule.ServiceName);
            result.Add(new ServiceAuditItem
            {
                ServiceName = rule.ServiceName,
                DisplayName = string.IsNullOrWhiteSpace(display) || display.StartsWith('@') ? rule.DisplayName : display,
                Status = status,
                StartType = start switch { 0 => "Boot", 1 => "System", 2 => "Авто", 3 => "Вручную", 4 => "Отключена", _ => "Неизвестно" },
                StartValue = start,
                Risk = rule.Risk.ToUpperInvariant(),
                Recommendation = rule.Recommendation,
                DependencyNote = rule.DependencyNote,
                ImagePath = imagePath
            });
        }

        return result.OrderBy(static x => x.Risk).ThenBy(static x => x.DisplayName, StringComparer.CurrentCultureIgnoreCase).ToArray();
    }

    private static string TryGetServiceStatus(string serviceName)
    {
        try
        {
            var psi = new System.Diagnostics.ProcessStartInfo
            {
                FileName = "sc.exe",
                Arguments = $"query \"{serviceName}\"",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };
            using var process = System.Diagnostics.Process.Start(psi);
            if (process is null) return "Неизвестно";
            var output = process.StandardOutput.ReadToEnd();
            process.WaitForExit(1500);
            if (output.Contains("RUNNING", StringComparison.OrdinalIgnoreCase)) return "Работает";
            if (output.Contains("STOPPED", StringComparison.OrdinalIgnoreCase)) return "Остановлена";
            return "Неизвестно";
        }
        catch { return "Неизвестно"; }
    }
}
