namespace MerzoOptimizer.Core.ScheduledTasks;

public sealed record ScheduledTaskRule
{
    public required string Pattern { get; init; }
    public required string Risk { get; init; }
    public required string Recommendation { get; init; }
}

public sealed record ScheduledTaskAuditItem
{
    public required string Name { get; init; }
    public required string Path { get; init; }
    public required string State { get; init; }
    public bool Enabled { get; init; }
    public string? Author { get; init; }
    public required string Risk { get; init; }
    public required string Recommendation { get; init; }
    public bool CanManage => !string.Equals(Risk, "KEEP", StringComparison.OrdinalIgnoreCase);
    public string FullPath => $"{Path}{Name}";
}

public sealed record ScheduledTaskOperationResult
{
    public bool Success { get; init; }
    public bool Changed { get; init; }
    public Guid? SnapshotId { get; init; }
    public required string Message { get; init; }
}

public interface IScheduledTaskAuditService
{
    Task<IReadOnlyList<ScheduledTaskAuditItem>> ScanAsync(CancellationToken cancellationToken = default);
}

public interface IScheduledTaskOptimizationService : IScheduledTaskAuditService
{
    Task<ScheduledTaskOperationResult> DisableAsync(string taskPath, string taskName, CancellationToken cancellationToken = default);
    Task<ScheduledTaskOperationResult> RestoreAsync(string taskPath, string taskName, CancellationToken cancellationToken = default);
}
