using MerzoOptimizer.Core.Snapshots;
using MerzoOptimizer.Core.Tweaks;

namespace MerzoOptimizer.Core.Startup;

public sealed record StartupManagedItem
{
    public required string Id { get; init; }
    public required string Name { get; init; }
    public required string Command { get; init; }
    public required string Source { get; init; }
    public required string Scope { get; init; }
    public bool IsEnabled { get; init; } = true;
    public bool CanManage { get; init; }
    public bool HasRestorePoint { get; init; }
    public string Recommendation { get; init; } = "Решение пользователя";
    public TweakDefinition? DisableDefinition { get; init; }
}

public interface IStartupOptimizerService
{
    Task<IReadOnlyList<StartupManagedItem>> ScanAsync(CancellationToken cancellationToken = default);
    Task<TweakApplyResult> DisableAsync(StartupManagedItem item, CancellationToken cancellationToken = default);
    Task<RestoreResult> RestoreAsync(StartupManagedItem item, CancellationToken cancellationToken = default);
}
