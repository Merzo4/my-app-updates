using MerzoOptimizer.Core.Cleanup;
using MerzoOptimizer.Core.Elevation;
using MerzoOptimizer.Core.Power;
using MerzoOptimizer.Core.ScheduledTasks;
using MerzoOptimizer.Core.Services;
using MerzoOptimizer.Core.Snapshots;
using MerzoOptimizer.Core.Tweaks;

namespace MerzoOptimizer.Windows.Elevation;

public sealed class ElevationAwareTweakExecutionService : ITweakExecutionService
{
    private readonly ITweakExecutionService _local;
    private readonly ElevatedOperationBroker _broker;

    public ElevationAwareTweakExecutionService(ITweakExecutionService local, ElevatedOperationBroker broker)
    {
        _local = local;
        _broker = broker;
    }

    public Task<TweakStateResult> GetStateAsync(TweakDefinition tweak, CancellationToken cancellationToken = default) =>
        _local.GetStateAsync(tweak, cancellationToken);

    public async Task<TweakApplyResult> ApplyAsync(TweakDefinition tweak, CancellationToken cancellationToken = default)
    {
        if (!tweak.RequiresAdmin)
            return await _local.ApplyAsync(tweak, cancellationToken).ConfigureAwait(false);

        try
        {
            return await _broker.ExecuteAsync<TweakApplyResult>(new ElevatedOperationRequest
            {
                RequestId = Guid.NewGuid().ToString("N"),
                Kind = ElevatedOperationKind.ApplyTweak,
                TweakId = tweak.Id,
                Tweak = tweak.Id.StartsWith("startup.disable.", StringComparison.OrdinalIgnoreCase) ? tweak : null
            }, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is ElevationDeniedException or IOException or InvalidDataException)
        {
            return new TweakApplyResult { Success = false, Changed = false, Message = ex.Message };
        }
    }
}

public sealed class ElevationAwareRestoreService : IRestoreService
{
    private readonly IRestoreService _local;
    private readonly ISnapshotService _snapshots;
    private readonly ElevatedOperationBroker _broker;

    public ElevationAwareRestoreService(IRestoreService local, ISnapshotService snapshots, ElevatedOperationBroker broker)
    {
        _local = local;
        _snapshots = snapshots;
        _broker = broker;
    }

    public async Task<RestoreResult> RestoreAsync(Guid snapshotId, CancellationToken cancellationToken = default)
    {
        var snapshot = await _snapshots.GetAsync(snapshotId, cancellationToken).ConfigureAwait(false);
        if (snapshot is null)
            return new RestoreResult { Success = false, Changed = false, Message = "Snapshot не найден." };
        if (!RequiresElevation(snapshot))
            return await _local.RestoreAsync(snapshotId, cancellationToken).ConfigureAwait(false);
        return await ExecuteElevatedAsync(ElevatedOperationKind.RestoreSnapshot, snapshotId: snapshotId, cancellationToken: cancellationToken).ConfigureAwait(false);
    }

    public async Task<RestoreResult> RestoreLatestForTweakAsync(string tweakId, CancellationToken cancellationToken = default)
    {
        var snapshot = await _snapshots.GetLatestActiveForTweakAsync(tweakId, cancellationToken).ConfigureAwait(false);
        if (snapshot is null)
            return new RestoreResult { Success = true, Changed = false, Message = "Для этого действия нет активного snapshot." };
        return await RestoreAsync(snapshot.Id, cancellationToken).ConfigureAwait(false);
    }

    public async Task<RestoreResult> RestoreAllActiveAsync(CancellationToken cancellationToken = default)
    {
        var active = (await _snapshots.ListAsync(cancellationToken).ConfigureAwait(false)).Where(static s => !s.IsRestored).ToArray();
        if (active.Length == 0)
            return new RestoreResult { Success = true, Changed = false, Message = "Активных snapshot для восстановления нет." };
        if (!active.Any(RequiresElevation))
            return await _local.RestoreAllActiveAsync(cancellationToken).ConfigureAwait(false);
        return await ExecuteElevatedAsync(ElevatedOperationKind.RestoreAllActive, cancellationToken: cancellationToken).ConfigureAwait(false);
    }

    private async Task<RestoreResult> ExecuteElevatedAsync(
        ElevatedOperationKind kind,
        Guid? snapshotId = null,
        CancellationToken cancellationToken = default)
    {
        try
        {
            return await _broker.ExecuteAsync<RestoreResult>(new ElevatedOperationRequest
            {
                RequestId = Guid.NewGuid().ToString("N"),
                Kind = kind,
                SnapshotId = snapshotId
            }, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is ElevationDeniedException or IOException or InvalidDataException)
        {
            return new RestoreResult { Success = false, Changed = false, Message = ex.Message };
        }
    }

    private static bool RequiresElevation(ChangeSnapshot snapshot)
    {
        if (snapshot.RegistryValues.Any(static x => x.Hive == RegistryHiveScope.LocalMachine)) return true;
        if (snapshot.ServiceState is not null || snapshot.ScheduledTaskState is not null || snapshot.PowerSchemeState is not null) return true;
        if (snapshot.CleanupArchive is not null)
        {
            var windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (snapshot.CleanupArchive.Files.Any(x => x.OriginalPath.StartsWith(windows, StringComparison.OrdinalIgnoreCase))) return true;
        }
        return false;
    }
}

public sealed class ElevationAwareCleanupService : ICleanupService
{
    private readonly ICleanupService _local;
    private readonly ElevatedOperationBroker _broker;
    public ElevationAwareCleanupService(ICleanupService local, ElevatedOperationBroker broker) { _local = local; _broker = broker; }

    public async Task<IReadOnlyList<CleanupCategorySnapshot>> ScanAsync(CancellationToken cancellationToken = default)
    {
        var categories = await _local.ScanAsync(cancellationToken).ConfigureAwait(false);
        return categories.Select(static x => x.RequiresAdmin && x.EligibleFileCount > 0 ? x with { CanClean = true } : x).ToArray();
    }

    public async Task<CleanupRunResult> CleanAsync(string categoryId, bool createBackup = true, CancellationToken cancellationToken = default)
    {
        var category = (await _local.ScanAsync(cancellationToken).ConfigureAwait(false))
            .FirstOrDefault(x => string.Equals(x.Id, categoryId, StringComparison.OrdinalIgnoreCase));
        if (category is null)
            return new CleanupRunResult { Success = false, Changed = false, Message = "Категория очистки не найдена." };

        if (!category.RequiresAdmin)
            return await _local.CleanAsync(categoryId, createBackup, cancellationToken).ConfigureAwait(false);

        try
        {
            return await _broker.ExecuteAsync<CleanupRunResult>(new ElevatedOperationRequest
            {
                RequestId = Guid.NewGuid().ToString("N"), Kind = ElevatedOperationKind.CleanCategory, CategoryId = categoryId, CreateBackup = createBackup
            }, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is ElevationDeniedException or IOException or InvalidDataException)
        {
            return new CleanupRunResult { Success = false, Changed = false, Message = ex.Message };
        }
    }
}

public sealed class ElevationAwareServiceOptimizationService : IServiceOptimizationService
{
    private readonly IServiceOptimizationService _local;
    private readonly ElevatedOperationBroker _broker;
    public ElevationAwareServiceOptimizationService(IServiceOptimizationService local, ElevatedOperationBroker broker) { _local = local; _broker = broker; }

    public Task<IReadOnlyList<ServiceAuditItem>> ScanAsync(CancellationToken cancellationToken = default) => _local.ScanAsync(cancellationToken);

    public Task<ServiceOperationResult> DisableAsync(string serviceName, CancellationToken cancellationToken = default) =>
        ExecuteAsync(ElevatedOperationKind.DisableService, serviceName, cancellationToken);

    public Task<ServiceOperationResult> RestoreAsync(string serviceName, CancellationToken cancellationToken = default) =>
        ExecuteAsync(ElevatedOperationKind.RestoreService, serviceName, cancellationToken);

    private async Task<ServiceOperationResult> ExecuteAsync(ElevatedOperationKind kind, string serviceName, CancellationToken cancellationToken)
    {
        try
        {
            return await _broker.ExecuteAsync<ServiceOperationResult>(new ElevatedOperationRequest
            {
                RequestId = Guid.NewGuid().ToString("N"), Kind = kind, ServiceName = serviceName
            }, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is ElevationDeniedException or IOException or InvalidDataException)
        {
            return new ServiceOperationResult { Success = false, Changed = false, Message = ex.Message };
        }
    }
}

public sealed class ElevationAwareScheduledTaskOptimizationService : IScheduledTaskOptimizationService
{
    private readonly IScheduledTaskOptimizationService _local;
    private readonly ElevatedOperationBroker _broker;
    public ElevationAwareScheduledTaskOptimizationService(IScheduledTaskOptimizationService local, ElevatedOperationBroker broker) { _local = local; _broker = broker; }

    public Task<IReadOnlyList<ScheduledTaskAuditItem>> ScanAsync(CancellationToken cancellationToken = default) => _local.ScanAsync(cancellationToken);

    public Task<ScheduledTaskOperationResult> DisableAsync(string taskPath, string taskName, CancellationToken cancellationToken = default) =>
        ExecuteAsync(ElevatedOperationKind.DisableScheduledTask, taskPath, taskName, cancellationToken);

    public Task<ScheduledTaskOperationResult> RestoreAsync(string taskPath, string taskName, CancellationToken cancellationToken = default) =>
        ExecuteAsync(ElevatedOperationKind.RestoreScheduledTask, taskPath, taskName, cancellationToken);

    private async Task<ScheduledTaskOperationResult> ExecuteAsync(ElevatedOperationKind kind, string taskPath, string taskName, CancellationToken cancellationToken)
    {
        try
        {
            return await _broker.ExecuteAsync<ScheduledTaskOperationResult>(new ElevatedOperationRequest
            {
                RequestId = Guid.NewGuid().ToString("N"), Kind = kind, TaskPath = taskPath, TaskName = taskName
            }, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is ElevationDeniedException or IOException or InvalidDataException)
        {
            return new ScheduledTaskOperationResult { Success = false, Changed = false, Message = ex.Message };
        }
    }
}

public sealed class ElevationAwarePowerProfileService : IPowerProfileService
{
    private readonly IPowerProfileService _local;
    private readonly ElevatedOperationBroker _broker;
    public ElevationAwarePowerProfileService(IPowerProfileService local, ElevatedOperationBroker broker) { _local = local; _broker = broker; }

    public Task<IReadOnlyList<PowerSchemeInfo>> ListSchemesAsync(CancellationToken cancellationToken = default) => _local.ListSchemesAsync(cancellationToken);

    public async Task<PowerOperationResult> ActivateAsync(string targetAliasOrGuid, string displayName, CancellationToken cancellationToken = default)
    {
        try
        {
            return await _broker.ExecuteAsync<PowerOperationResult>(new ElevatedOperationRequest
            {
                RequestId = Guid.NewGuid().ToString("N"), Kind = ElevatedOperationKind.ActivatePowerScheme,
                PowerTarget = targetAliasOrGuid, DisplayName = displayName
            }, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is ElevationDeniedException or IOException or InvalidDataException)
        {
            return new PowerOperationResult { Success = false, Changed = false, Message = ex.Message };
        }
    }

    public async Task<PowerOperationResult> RestoreLastAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            return await _broker.ExecuteAsync<PowerOperationResult>(new ElevatedOperationRequest
            {
                RequestId = Guid.NewGuid().ToString("N"), Kind = ElevatedOperationKind.RestorePowerScheme
            }, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is ElevationDeniedException or IOException or InvalidDataException)
        {
            return new PowerOperationResult { Success = false, Changed = false, Message = ex.Message };
        }
    }
}
