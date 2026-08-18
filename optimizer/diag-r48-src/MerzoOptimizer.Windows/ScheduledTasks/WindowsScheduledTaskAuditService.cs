using System.Diagnostics;
using System.Text;
using System.Text.Json;
using MerzoOptimizer.Core.Logging;
using MerzoOptimizer.Core.ScheduledTasks;
using MerzoOptimizer.Core.Snapshots;

namespace MerzoOptimizer.Windows.ScheduledTasks;

public sealed class WindowsScheduledTaskAuditService : IScheduledTaskOptimizationService
{
    private readonly string _rulesPath;
    private readonly ISnapshotService? _snapshots;
    private readonly IRestoreService? _restore;
    private readonly IAuditLogger? _logger;

    public WindowsScheduledTaskAuditService(
        ISnapshotService? snapshots = null,
        IRestoreService? restore = null,
        IAuditLogger? logger = null,
        string? rulesPath = null)
    {
        _snapshots = snapshots;
        _restore = restore;
        _logger = logger;
        _rulesPath = rulesPath ?? Path.Combine(AppContext.BaseDirectory, "data", "task_rules.json");
    }

    public async Task<IReadOnlyList<ScheduledTaskAuditItem>> ScanAsync(CancellationToken cancellationToken = default)
    {
        if (!File.Exists(_rulesPath))
            return [];

        var jsonOptions = new JsonSerializerOptions { PropertyNameCaseInsensitive = true, PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };
        var rules = JsonSerializer.Deserialize<List<ScheduledTaskRule>>(await File.ReadAllTextAsync(_rulesPath, cancellationToken), jsonOptions) ?? [];
        if (rules.Count == 0) return [];

        var script = "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); Get-ScheduledTask | Select-Object TaskName,TaskPath,State,Author,@{N='Enabled';E={$_.Settings.Enabled}} | ConvertTo-Json -Compress -Depth 4";
        var output = await RunPowerShellAsync(script, cancellationToken).ConfigureAwait(false);
        if (string.IsNullOrWhiteSpace(output)) return [];

        using var doc = JsonDocument.Parse(output);
        var elements = doc.RootElement.ValueKind == JsonValueKind.Array
            ? doc.RootElement.EnumerateArray().ToArray()
            : new[] { doc.RootElement };
        var result = new List<ScheduledTaskAuditItem>();

        foreach (var element in elements)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var name = GetString(element, "TaskName");
            var path = GetString(element, "TaskPath");
            var full = path + name;
            var rule = rules.FirstOrDefault(r => full.Contains(r.Pattern, StringComparison.OrdinalIgnoreCase));
            if (rule is null) continue;

            result.Add(new ScheduledTaskAuditItem
            {
                Name = name,
                Path = path,
                State = GetString(element, "State"),
                Enabled = GetBool(element, "Enabled", fallback: !string.Equals(GetString(element, "State"), "Disabled", StringComparison.OrdinalIgnoreCase)),
                Author = GetString(element, "Author"),
                Risk = rule.Risk.ToUpperInvariant(),
                Recommendation = rule.Recommendation
            });
        }

        return result.OrderBy(static x => x.Risk).ThenBy(static x => x.Path).ThenBy(static x => x.Name).ToArray();
    }

    public async Task<ScheduledTaskOperationResult> DisableAsync(string taskPath, string taskName, CancellationToken cancellationToken = default)
    {
        if (_snapshots is null || _restore is null || _logger is null)
            return new ScheduledTaskOperationResult { Success = false, Changed = false, Message = "Task Optimizer не инициализирован для изменений." };

        var item = (await ScanAsync(cancellationToken).ConfigureAwait(false)).FirstOrDefault(x =>
            string.Equals(x.Path, taskPath, StringComparison.OrdinalIgnoreCase) && string.Equals(x.Name, taskName, StringComparison.OrdinalIgnoreCase));
        if (item is null)
            return new ScheduledTaskOperationResult { Success = false, Changed = false, Message = "Задача не найдена в каталоге анализа Merzo." };
        if (!item.CanManage)
            return new ScheduledTaskOperationResult { Success = false, Changed = false, Message = "Эта задача помечена KEEP и не отключается из Merzo." };
        if (!item.Enabled)
            return new ScheduledTaskOperationResult { Success = true, Changed = false, Message = "Задача уже отключена; Merzo ничего не менял." };

        var operationId = $"task.{NormalizeId(taskPath)}.{NormalizeId(taskName)}";
        var snapshot = await _snapshots.CreateForScheduledTaskAsync(
            operationId,
            $"Scheduled Task: {taskName}",
            $"Перед отключением Scheduled Task {taskPath}{taskName}",
            new ScheduledTaskStateSnapshot { TaskPath = taskPath, TaskName = taskName, WasEnabled = item.Enabled },
            cancellationToken).ConfigureAwait(false);

        try
        {
            var script = $"Disable-ScheduledTask -TaskPath {Ps(taskPath)} -TaskName {Ps(taskName)} -ErrorAction Stop | Out-Null";
            await RunPowerShellAsync(script, cancellationToken).ConfigureAwait(false);
            await _logger.WriteAsync(new AuditLogEntry
            {
                Category = "ScheduledTasks",
                Action = $"Disable task {taskPath}{taskName}",
                Status = "Success",
                TweakId = operationId,
                OldValue = "Enabled",
                NewValue = "Disabled",
                Details = $"Snapshot {snapshot.Id}"
            }, cancellationToken).ConfigureAwait(false);

            return new ScheduledTaskOperationResult
            {
                Success = true,
                Changed = true,
                SnapshotId = snapshot.Id,
                Message = $"Задача «{taskName}» отключена. Snapshot {snapshot.Id.ToString("N")[..8]} создан."
            };
        }
        catch (Exception ex)
        {
            var rollback = await _restore.RestoreAsync(snapshot.Id, CancellationToken.None).ConfigureAwait(false);
            return new ScheduledTaskOperationResult
            {
                Success = false,
                Changed = false,
                SnapshotId = snapshot.Id,
                Message = $"Не удалось отключить задачу: {ex.Message}. Rollback: {rollback.Message}"
            };
        }
    }

    public async Task<ScheduledTaskOperationResult> RestoreAsync(string taskPath, string taskName, CancellationToken cancellationToken = default)
    {
        if (_restore is null)
            return new ScheduledTaskOperationResult { Success = false, Changed = false, Message = "Restore Scheduled Task не инициализирован." };
        var operationId = $"task.{NormalizeId(taskPath)}.{NormalizeId(taskName)}";
        var result = await _restore.RestoreLatestForTweakAsync(operationId, cancellationToken).ConfigureAwait(false);
        return new ScheduledTaskOperationResult { Success = result.Success, Changed = result.Changed, SnapshotId = result.SnapshotId, Message = result.Message };
    }

    internal static async Task<string> RunPowerShellAsync(string script, CancellationToken cancellationToken)
    {
        var encoded = Convert.ToBase64String(Encoding.Unicode.GetBytes(script));
        var psi = new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = $"-NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand {encoded}",
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
            CreateNoWindow = true
        };

        using var process = Process.Start(psi) ?? throw new InvalidOperationException("Не удалось запустить PowerShell.");
        var outputTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var errorTask = process.StandardError.ReadToEndAsync(cancellationToken);
        try
        {
            await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            try { if (!process.HasExited) process.Kill(entireProcessTree: true); } catch { }
            throw;
        }
        var output = await outputTask.ConfigureAwait(false);
        var error = await errorTask.ConfigureAwait(false);
        if (process.ExitCode != 0)
            throw new InvalidOperationException($"PowerShell завершился с кодом {process.ExitCode}: {error.Trim()}");
        return output;
    }

    private static string Ps(string value) => "'" + value.Replace("'", "''", StringComparison.Ordinal) + "'";
    private static string NormalizeId(string value) => new(value.Where(char.IsLetterOrDigit).Select(char.ToLowerInvariant).ToArray());

    private static string GetString(JsonElement element, string property)
    {
        if (!element.TryGetProperty(property, out var value)) return string.Empty;
        return value.ValueKind == JsonValueKind.String ? value.GetString() ?? string.Empty : value.ToString();
    }

    private static bool GetBool(JsonElement element, string property, bool fallback)
    {
        if (!element.TryGetProperty(property, out var value)) return fallback;
        return value.ValueKind switch
        {
            JsonValueKind.True => true,
            JsonValueKind.False => false,
            JsonValueKind.String when bool.TryParse(value.GetString(), out var parsed) => parsed,
            _ => fallback
        };
    }
}
