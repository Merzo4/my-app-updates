using Microsoft.Win32;
using MerzoOptimizer.Core.Diagnostics;
using MerzoOptimizer.Core.Logging;
using MerzoOptimizer.Core.Safety;
using MerzoOptimizer.Core.Tweaks;
using MerzoOptimizer.Windows.RegistryAccess;
using MerzoOptimizer.Windows.Restore;
using MerzoOptimizer.Windows.Snapshots;
using MerzoOptimizer.Windows.Tweaks;

namespace MerzoOptimizer.Windows.Diagnostics;

public sealed class SafeRecoveryDiagnosticService : IRecoveryDiagnosticService
{
    private const string TestKeyPath = @"SOFTWARE\MerzoWindowsOptimizer\TestSandbox";
    private const string TestValueName = "RecoveryProbe";
    private readonly IAuditLogger _logger;
    private readonly RegistryTweakAccessor _registry = new();

    public SafeRecoveryDiagnosticService(IAuditLogger logger)
    {
        _logger = logger;
    }

    public async Task<RecoveryDiagnosticResult> RunAsync(CancellationToken cancellationToken = default)
    {
        var tempRoot = Path.Combine(Path.GetTempPath(), "MerzoWindowsOptimizer", "recovery-selftest", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(tempRoot);

        var keyExistedBefore = KeyExists();
        var desiredValue = (DateTime.UtcNow.Ticks & 0x3FFFFFFF) + 1000;
        var action = new RegistryTweakAction
        {
            Hive = RegistryHiveScope.CurrentUser,
            KeyPath = TestKeyPath,
            ValueName = TestValueName,
            ValueType = RegistryTweakValueType.QWord,
            IntegerValue = desiredValue
        };

        var tweak = new TweakDefinition
        {
            Id = "diagnostic.snapshot_restore",
            Name = "Диагностика Snapshot / Restore",
            Category = "Diagnostics",
            Risk = TweakRisk.Safe,
            RequiresAdmin = false,
            RequiresRestart = false,
            Description = "Временный тест механизма восстановления в собственном HKCU-разделе Merzo.",
            ExpectedEffect = "После проверки исходное состояние должно быть восстановлено полностью.",
            RegistryActions = [action]
        };

        var before = _registry.Capture(action);

        try
        {
            var tempSnapshots = new WindowsSnapshotService(tempRoot);
            var safety = new SafetyEngine();
            var restore = new WindowsRestoreService(tempSnapshots, _logger);
            var execution = new WindowsTweakExecutionService(tempSnapshots, restore, safety, _logger);

            var apply = await execution.ApplyAsync(tweak, cancellationToken).ConfigureAwait(false);
            if (!apply.Success || apply.SnapshotId is null)
                return await FailAsync($"Apply не прошёл: {apply.Message}", cancellationToken).ConfigureAwait(false);

            var appliedState = await execution.GetStateAsync(tweak, cancellationToken).ConfigureAwait(false);
            if (appliedState.State != TweakState.Applied)
                return await FailAsync("После Apply тестовое значение не перешло в целевое состояние.", cancellationToken).ConfigureAwait(false);

            var restoreResult = await restore.RestoreAsync(apply.SnapshotId.Value, cancellationToken).ConfigureAwait(false);
            if (!restoreResult.Success)
                return await FailAsync($"Restore не прошёл: {restoreResult.Message}", cancellationToken).ConfigureAwait(false);

            var after = _registry.Capture(action);
            if (!Equivalent(before, after))
                return await FailAsync("После Restore тестовое значение отличается от исходного состояния.", cancellationToken).ConfigureAwait(false);

            await _logger.WriteAsync(new AuditLogEntry
            {
                Category = "Diagnostics",
                Action = "Snapshot / Restore safe self-test",
                Status = "Success",
                TweakId = tweak.Id,
                OldValue = RegistryTweakAccessor.Describe(before),
                NewValue = RegistryTweakAccessor.Describe(after),
                Details = "Реальный SnapshotEngine → Apply → Restore прошёл в HKCU Merzo TestSandbox."
            }, cancellationToken).ConfigureAwait(false);

            return new RecoveryDiagnosticResult
            {
                Success = true,
                Message = "PASS: Snapshot → Apply → Restore восстановили исходное состояние.",
                Details = "Тест использовал только HKCU\\Software\\MerzoWindowsOptimizer\\TestSandbox и временное хранилище snapshot."
            };
        }
        catch (Exception ex)
        {
            return await FailAsync($"Ошибка диагностики: {ex.Message}", CancellationToken.None, ex.ToString()).ConfigureAwait(false);
        }
        finally
        {
            try
            {
                var current = _registry.Capture(action);
                if (!Equivalent(before, current))
                    _registry.Restore(before);
            }
            catch
            {
                // Main failure is already reported. Best-effort safety cleanup continues below.
            }

            try
            {
                if (!keyExistedBefore)
                    PruneTestKeyIfEmpty();
            }
            catch
            {
                // Leaving an empty Merzo test key is harmless; never hide the main diagnostic result.
            }

            try
            {
                if (Directory.Exists(tempRoot))
                    Directory.Delete(tempRoot, recursive: true);
            }
            catch
            {
                // Temporary diagnostics are non-critical.
            }
        }
    }

    private async Task<RecoveryDiagnosticResult> FailAsync(string message, CancellationToken cancellationToken, string? details = null)
    {
        await _logger.WriteAsync(new AuditLogEntry
        {
            Category = "Diagnostics",
            Action = "Snapshot / Restore safe self-test",
            Status = "Error",
            TweakId = "diagnostic.snapshot_restore",
            Details = details ?? message
        }, cancellationToken).ConfigureAwait(false);

        return new RecoveryDiagnosticResult
        {
            Success = false,
            Message = $"FAIL: {message}",
            Details = details
        };
    }

    private static bool Equivalent(MerzoOptimizer.Core.Snapshots.RegistryValueSnapshot left, MerzoOptimizer.Core.Snapshots.RegistryValueSnapshot right) =>
        left.Existed == right.Existed &&
        left.ValueType == right.ValueType &&
        left.IntegerValue == right.IntegerValue &&
        string.Equals(left.StringValue, right.StringValue, StringComparison.Ordinal) &&
        string.Equals(left.BinaryBase64, right.BinaryBase64, StringComparison.Ordinal) &&
        ((left.MultiStringValue is null && right.MultiStringValue is null) ||
         (left.MultiStringValue is not null && right.MultiStringValue is not null && left.MultiStringValue.SequenceEqual(right.MultiStringValue, StringComparer.Ordinal)));

    private static bool KeyExists()
    {
        using var baseKey = RegistryKey.OpenBaseKey(RegistryHive.CurrentUser, RegistryView.Registry64);
        using var key = baseKey.OpenSubKey(TestKeyPath, writable: false);
        return key is not null;
    }

    private static void PruneTestKeyIfEmpty()
    {
        using var baseKey = RegistryKey.OpenBaseKey(RegistryHive.CurrentUser, RegistryView.Registry64);
        using var key = baseKey.OpenSubKey(TestKeyPath, writable: false);
        if (key is null || key.ValueCount != 0 || key.SubKeyCount != 0)
            return;

        baseKey.DeleteSubKey(TestKeyPath, throwOnMissingSubKey: false);
    }
}
