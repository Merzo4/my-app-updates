using System.Diagnostics;
using MerzoOptimizer.Core.Logging;
using MerzoOptimizer.Core.Power;
using MerzoOptimizer.Core.Snapshots;

namespace MerzoOptimizer.Windows.Power;

public sealed class WindowsPowerProfileService : IPowerProfileService
{
    private readonly ISnapshotService _snapshots;
    private readonly IRestoreService _restore;
    private readonly IAuditLogger _logger;

    public WindowsPowerProfileService(ISnapshotService snapshots, IRestoreService restore, IAuditLogger logger)
    {
        _snapshots = snapshots;
        _restore = restore;
        _logger = logger;
    }

    public Task<IReadOnlyList<PowerSchemeInfo>> ListSchemesAsync(CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return Task.FromResult(PowerPlanReader.ReadAllSchemes());
    }

    public async Task<PowerOperationResult> ActivateAsync(string targetAliasOrGuid, string displayName, CancellationToken cancellationToken = default)
    {
        var schemes = await ListSchemesAsync(cancellationToken).ConfigureAwait(false);
        var current = schemes.FirstOrDefault(static x => x.IsActive);
        if (current is null)
            return new PowerOperationResult { Success = false, Changed = false, Message = "Не удалось определить текущий план питания." };

        if (string.Equals(current.Name, displayName, StringComparison.CurrentCultureIgnoreCase))
            return new PowerOperationResult { Success = true, Changed = false, Message = $"План «{displayName}» уже активен." };

        var snapshot = await _snapshots.CreateForPowerSchemeAsync(
            "power.profile",
            "Профиль питания",
            $"Перед переключением плана питания на {displayName}",
            new PowerSchemeStateSnapshot { ActiveSchemeGuid = current.Guid, ActiveSchemeName = current.Name },
            cancellationToken).ConfigureAwait(false);

        try
        {
            await RunPowerCfgAsync($"/setactive {targetAliasOrGuid}", cancellationToken).ConfigureAwait(false);
            await _logger.WriteAsync(new AuditLogEntry
            {
                Category = "Power",
                Action = $"Activate power scheme {displayName}",
                Status = "Success",
                TweakId = "power.profile",
                OldValue = $"{current.Name} ({current.Guid})",
                NewValue = displayName,
                Details = $"Snapshot {snapshot.Id}"
            }, cancellationToken).ConfigureAwait(false);
            return new PowerOperationResult { Success = true, Changed = true, SnapshotId = snapshot.Id, Message = $"Активирован профиль «{displayName}». Snapshot {snapshot.Id.ToString("N")[..8]} создан." };
        }
        catch (Exception ex)
        {
            var rollback = await _restore.RestoreAsync(snapshot.Id, CancellationToken.None).ConfigureAwait(false);
            return new PowerOperationResult { Success = false, Changed = false, SnapshotId = snapshot.Id, Message = $"Не удалось переключить питание: {ex.Message}. Rollback: {rollback.Message}" };
        }
    }

    public async Task<PowerOperationResult> RestoreLastAsync(CancellationToken cancellationToken = default)
    {
        var result = await _restore.RestoreLatestForTweakAsync("power.profile", cancellationToken).ConfigureAwait(false);
        return new PowerOperationResult { Success = result.Success, Changed = result.Changed, SnapshotId = result.SnapshotId, Message = result.Message };
    }

    private static async Task<string> RunPowerCfgAsync(string arguments, CancellationToken cancellationToken)
    {
        var psi = new ProcessStartInfo
        {
            FileName = "powercfg.exe",
            Arguments = arguments,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        using var process = Process.Start(psi) ?? throw new InvalidOperationException("Не удалось запустить powercfg.exe.");
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
            throw new InvalidOperationException($"powercfg завершился с кодом {process.ExitCode}: {error.Trim()}");
        return output;
    }

}
