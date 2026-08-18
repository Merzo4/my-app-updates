namespace MerzoOptimizer.Core.Cleanup;

public sealed record CleanupCategorySnapshot
{
    public required string Id { get; init; }
    public required string Name { get; init; }
    public required string Description { get; init; }
    public required string RootPath { get; init; }
    public int EligibleFileCount { get; init; }
    public long EligibleBytes { get; init; }
    public bool RequiresAdmin { get; init; }
    public bool CanClean { get; init; }
}

public sealed record CleanupRunResult
{
    public bool Success { get; init; }
    public bool Changed { get; init; }
    public Guid? SnapshotId { get; init; }
    public int ArchivedFileCount { get; init; }
    public long OriginalBytes { get; init; }
    public long BackupBytes { get; init; }
    public long NetFreedBytes { get; init; }
    public required string Message { get; init; }
}

public interface ICleanupService
{
    Task<IReadOnlyList<CleanupCategorySnapshot>> ScanAsync(CancellationToken cancellationToken = default);
    Task<CleanupRunResult> CleanAsync(string categoryId, bool createBackup = true, CancellationToken cancellationToken = default);
}
