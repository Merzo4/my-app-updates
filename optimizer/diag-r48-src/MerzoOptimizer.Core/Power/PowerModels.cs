namespace MerzoOptimizer.Core.Power;

public sealed record PowerSchemeInfo
{
    public required string Guid { get; init; }
    public required string Name { get; init; }
    public bool IsActive { get; init; }
}

public sealed record PowerOperationResult
{
    public bool Success { get; init; }
    public bool Changed { get; init; }
    public Guid? SnapshotId { get; init; }
    public required string Message { get; init; }
}

public interface IPowerProfileService
{
    Task<IReadOnlyList<PowerSchemeInfo>> ListSchemesAsync(CancellationToken cancellationToken = default);
    Task<PowerOperationResult> ActivateAsync(string targetAliasOrGuid, string displayName, CancellationToken cancellationToken = default);
    Task<PowerOperationResult> RestoreLastAsync(CancellationToken cancellationToken = default);
}
