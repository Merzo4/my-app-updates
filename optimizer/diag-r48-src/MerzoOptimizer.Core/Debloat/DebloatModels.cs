namespace MerzoOptimizer.Core.Debloat;

public sealed record DebloatAppSnapshot
{
    public required string Id { get; init; }
    public required string DisplayName { get; init; }
    public required string PackageName { get; init; }
    public required string Status { get; init; }
    public required string Recommendation { get; init; }
    public bool Installed { get; init; }
    public bool RemovalEnabled { get; init; }
}

public interface IDebloatScanner
{
    Task<IReadOnlyList<DebloatAppSnapshot>> ScanAsync(CancellationToken cancellationToken = default);
}
