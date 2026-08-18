using System.IO.Compression;
using MerzoOptimizer.Core.Logging;
using MerzoOptimizer.Core.Snapshots;
using MerzoOptimizer.Windows.RegistryAccess;

namespace MerzoOptimizer.Windows.Restore;

public sealed class WindowsRestoreService : IRestoreService
{
    private readonly ISnapshotService _snapshots;
    private readonly IAuditLogger _logger;
    private readonly RegistryTweakAccessor _registry = new();

    public WindowsRestoreService(ISnapshotService snapshots, IAuditLogger logger)
    {
        _snapshots = snapshots;
        _logger = logger;
    }

    public async Task<RestoreResult> RestoreAsync(Guid snapshotId, CancellationToken cancellationToken = default)
    {
        var snapshot = await _snapshots.GetAsync(snapshotId, cancellationToken).ConfigureAwait(false);
        if (snapshot is null)
        {
            return new RestoreResult
            {
                Success = false,
                Changed = false,
                SnapshotId = snapshotId,
                Message = "Snapshot не найден."
            };
        }

        if (snapshot.IsRestored)
        {
            return new RestoreResult
            {
                Success = true,
                Changed = false,
                SnapshotId = snapshotId,
                Message = "Этот snapshot уже был восстановлен."
            };
        }

        try
        {
            foreach (var entry in snapshot.RegistryValues.Reverse())
            {
                cancellationToken.ThrowIfCancellationRequested();
                var before = CaptureCurrent(entry);
                _registry.Restore(entry);

                await _logger.WriteAsync(new AuditLogEntry
                {
                    Category = "Restore",
                    Action = $"Restore registry {entry.Hive}\\{entry.KeyPath}\\{entry.ValueName}",
                    Status = "Success",
                    TweakId = snapshot.TweakId,
                    OldValue = RegistryTweakAccessor.Describe(before),
                    NewValue = RegistryTweakAccessor.Describe(entry),
                    Details = $"Snapshot {snapshot.Id}"
                }, cancellationToken).ConfigureAwait(false);
            }

            if (snapshot.CleanupArchive is not null)
                await RestoreCleanupArchiveAsync(snapshot, cancellationToken).ConfigureAwait(false);

            if (snapshot.ServiceState is not null)
                await RestoreServiceAsync(snapshot, cancellationToken).ConfigureAwait(false);

            if (snapshot.ScheduledTaskState is not null)
                await RestoreScheduledTaskAsync(snapshot, cancellationToken).ConfigureAwait(false);

            if (snapshot.PowerSchemeState is not null)
                await RestorePowerSchemeAsync(snapshot, cancellationToken).ConfigureAwait(false);

            await _snapshots.MarkRestoredAsync(snapshot.Id, DateTimeOffset.Now, cancellationToken).ConfigureAwait(false);

            await _logger.WriteAsync(new AuditLogEntry
            {
                Category = "Restore",
                Action = snapshot.TweakName ?? snapshot.Reason,
                Status = "Success",
                TweakId = snapshot.TweakId,
                Details = $"Snapshot {snapshot.Id} полностью восстановлен."
            }, cancellationToken).ConfigureAwait(false);

            return new RestoreResult
            {
                Success = true,
                Changed = true,
                SnapshotId = snapshot.Id,
                Message = $"Восстановлено: {snapshot.TweakName ?? snapshot.Reason}."
            };
        }
        catch (Exception ex)
        {
            await _logger.WriteAsync(new AuditLogEntry
            {
                Category = "Restore",
                Action = snapshot.TweakName ?? snapshot.Reason,
                Status = "Error",
                TweakId = snapshot.TweakId,
                Details = ex.ToString(),
                ErrorCode = ex.HResult.ToString("X8")
            }, CancellationToken.None).ConfigureAwait(false);

            return new RestoreResult
            {
                Success = false,
                Changed = false,
                SnapshotId = snapshot.Id,
                Message = $"Ошибка восстановления: {ex.Message}"
            };
        }
    }

    public async Task<RestoreResult> RestoreLatestForTweakAsync(
        string tweakId,
        CancellationToken cancellationToken = default)
    {
        var snapshot = await _snapshots.GetLatestActiveForTweakAsync(tweakId, cancellationToken).ConfigureAwait(false);
        if (snapshot is null)
        {
            return new RestoreResult
            {
                Success = true,
                Changed = false,
                Message = "Для этого твика нет активного snapshot."
            };
        }

        return await RestoreAsync(snapshot.Id, cancellationToken).ConfigureAwait(false);
    }

    public async Task<RestoreResult> RestoreAllActiveAsync(CancellationToken cancellationToken = default)
    {
        var active = (await _snapshots.ListAsync(cancellationToken).ConfigureAwait(false))
            .Where(static s => !s.IsRestored)
            .OrderByDescending(static s => s.CreatedAt)
            .ToArray();

        if (active.Length == 0)
        {
            return new RestoreResult
            {
                Success = true,
                Changed = false,
                Message = "Активных snapshot для восстановления нет."
            };
        }

        var restored = 0;
        foreach (var snapshot in active)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var result = await RestoreAsync(snapshot.Id, cancellationToken).ConfigureAwait(false);
            if (!result.Success)
            {
                return new RestoreResult
                {
                    Success = false,
                    Changed = restored > 0,
                    Message = $"Восстановлено {restored} из {active.Length}. Остановка: {result.Message}"
                };
            }

            if (result.Changed)
                restored++;
        }

        return new RestoreResult
        {
            Success = true,
            Changed = restored > 0,
            Message = $"Restore All завершён. Восстановлено snapshot: {restored}."
        };
    }

    private async Task RestoreCleanupArchiveAsync(ChangeSnapshot snapshot, CancellationToken cancellationToken)
    {
        var cleanup = snapshot.CleanupArchive
            ?? throw new InvalidOperationException("Cleanup snapshot не содержит archive metadata.");

        if (!File.Exists(cleanup.ArchivePath))
            throw new FileNotFoundException("ZIP-backup очистки не найден.", cleanup.ArchivePath);

        var restored = 0;

        using var archive = ZipFile.OpenRead(cleanup.ArchivePath);
        var entries = archive.Entries.ToDictionary(static e => e.FullName, StringComparer.Ordinal);
        var conflicts = cleanup.Files.Count(file => File.Exists(file.OriginalPath));
        if (conflicts > 0)
            throw new InvalidOperationException($"Restore отменён: {conflicts} временных путей уже созданы заново. Merzo не будет перезаписывать более новые файлы; snapshot и ZIP-backup сохранены.");

        foreach (var file in cleanup.Files)
        {
            cancellationToken.ThrowIfCancellationRequested();

            if (!entries.TryGetValue(file.ArchiveEntryName, out var archiveEntry))
                throw new InvalidDataException($"В backup отсутствует entry {file.ArchiveEntryName}.");

            var parent = Path.GetDirectoryName(file.OriginalPath);
            if (!string.IsNullOrWhiteSpace(parent))
                Directory.CreateDirectory(parent);

            await using var source = archiveEntry.Open();
            await using var target = new FileStream(file.OriginalPath, FileMode.CreateNew, FileAccess.Write, FileShare.None);
            await source.CopyToAsync(target, cancellationToken).ConfigureAwait(false);
            restored++;
        }

        await _logger.WriteAsync(new AuditLogEntry
        {
            Category = "Restore",
            Action = $"Restore cleanup {cleanup.CategoryName}",
            Status = "Success",
            TweakId = snapshot.TweakId,
            OldValue = $"ZIP backup: {cleanup.ArchivePath}",
            NewValue = $"Restored files: {restored}",
            Details = $"Snapshot {snapshot.Id}"
        }, cancellationToken).ConfigureAwait(false);

        try
        {
            File.Delete(cleanup.ArchivePath);
        }
        catch (IOException)
        {
            // A restored snapshot remains correct even if backup cleanup is delayed.
        }
        catch (UnauthorizedAccessException)
        {
            // Same: leave the backup for manual cleanup and diagnostics.
        }
    }


    private async Task RestoreServiceAsync(ChangeSnapshot snapshot, CancellationToken cancellationToken)
    {
        var state = snapshot.ServiceState ?? throw new InvalidOperationException("Service snapshot metadata missing.");
        using var key = global::Microsoft.Win32.Registry.LocalMachine.OpenSubKey($@"SYSTEM\CurrentControlSet\Services\{state.ServiceName}", writable: true)
            ?? throw new InvalidOperationException($"Служба {state.ServiceName} больше не найдена.");
        key.SetValue("Start", state.StartValue, global::Microsoft.Win32.RegistryValueKind.DWord);

        await _logger.WriteAsync(new AuditLogEntry
        {
            Category = "Restore",
            Action = $"Restore service {state.ServiceName}",
            Status = "Success",
            TweakId = snapshot.TweakId,
            OldValue = "Start=4",
            NewValue = $"Start={state.StartValue}",
            Details = $"Snapshot {snapshot.Id}; previous running={state.WasRunning}. Merzo does not force-start restored services."
        }, cancellationToken).ConfigureAwait(false);
    }

    private async Task RestoreScheduledTaskAsync(ChangeSnapshot snapshot, CancellationToken cancellationToken)
    {
        var state = snapshot.ScheduledTaskState ?? throw new InvalidOperationException("Scheduled Task snapshot metadata missing.");
        var command = state.WasEnabled ? "Enable-ScheduledTask" : "Disable-ScheduledTask";
        var script = $"{command} -TaskPath {Ps(state.TaskPath)} -TaskName {Ps(state.TaskName)} -ErrorAction Stop | Out-Null";
        await RunPowerShellAsync(script, cancellationToken).ConfigureAwait(false);

        await _logger.WriteAsync(new AuditLogEntry
        {
            Category = "Restore",
            Action = $"Restore task {state.TaskPath}{state.TaskName}",
            Status = "Success",
            TweakId = snapshot.TweakId,
            OldValue = state.WasEnabled ? "Disabled" : "Enabled",
            NewValue = state.WasEnabled ? "Enabled" : "Disabled",
            Details = $"Snapshot {snapshot.Id}"
        }, cancellationToken).ConfigureAwait(false);
    }

    private async Task RestorePowerSchemeAsync(ChangeSnapshot snapshot, CancellationToken cancellationToken)
    {
        var state = snapshot.PowerSchemeState ?? throw new InvalidOperationException("Power scheme snapshot metadata missing.");
        var psi = new System.Diagnostics.ProcessStartInfo
        {
            FileName = "powercfg.exe",
            Arguments = $"/setactive {state.ActiveSchemeGuid}",
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        using var process = System.Diagnostics.Process.Start(psi) ?? throw new InvalidOperationException("Не удалось запустить powercfg.exe.");
        try
        {
            await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            try { if (!process.HasExited) process.Kill(entireProcessTree: true); } catch { }
            throw;
        }
        if (process.ExitCode != 0)
            throw new InvalidOperationException($"powercfg /setactive завершился с кодом {process.ExitCode}: {await process.StandardError.ReadToEndAsync(cancellationToken)}");

        await _logger.WriteAsync(new AuditLogEntry
        {
            Category = "Restore",
            Action = "Restore power scheme",
            Status = "Success",
            TweakId = snapshot.TweakId,
            NewValue = $"{state.ActiveSchemeName} ({state.ActiveSchemeGuid})",
            Details = $"Snapshot {snapshot.Id}"
        }, cancellationToken).ConfigureAwait(false);
    }

    private static async Task<string> RunPowerShellAsync(string script, CancellationToken cancellationToken)
    {
        var encoded = Convert.ToBase64String(System.Text.Encoding.Unicode.GetBytes(script));
        var psi = new System.Diagnostics.ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = $"-NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand {encoded}",
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = System.Text.Encoding.UTF8,
            StandardErrorEncoding = System.Text.Encoding.UTF8,
            CreateNoWindow = true
        };
        using var process = System.Diagnostics.Process.Start(psi) ?? throw new InvalidOperationException("Не удалось запустить PowerShell.");
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

    private RegistryValueSnapshot CaptureCurrent(RegistryValueSnapshot entry)
    {
        var action = new MerzoOptimizer.Core.Tweaks.RegistryTweakAction
        {
            Hive = entry.Hive,
            KeyPath = entry.KeyPath,
            ValueName = entry.ValueName,
            ValueType = entry.ValueType ?? MerzoOptimizer.Core.Tweaks.RegistryTweakValueType.DWord,
            IntegerValue = entry.IntegerValue,
            StringValue = entry.StringValue
        };

        return _registry.Capture(action);
    }
}
