namespace MerzoOptimizer.Core.Services;

public sealed record ServiceRule
{
    public required string ServiceName { get; init; }
    public required string DisplayName { get; init; }
    public required string Risk { get; init; }
    public required string Recommendation { get; init; }
    public string? DependencyNote { get; init; }
}

public sealed record ServiceAuditItem
{
    public required string ServiceName { get; init; }
    public required string DisplayName { get; init; }
    public required string Status { get; init; }
    public required string StartType { get; init; }
    public int StartValue { get; init; }
    public required string Risk { get; init; }
    public required string Recommendation { get; init; }
    public string? DependencyNote { get; init; }
    public string? ImagePath { get; init; }
    public bool IsRunning => string.Equals(Status, "Работает", StringComparison.OrdinalIgnoreCase);
    public bool IsDisabled => StartValue == 4;
    public bool CanManage => !string.Equals(Risk, "KEEP", StringComparison.OrdinalIgnoreCase);
}

public sealed record ServiceOperationResult
{
    public bool Success { get; init; }
    public bool Changed { get; init; }
    public Guid? SnapshotId { get; init; }
    public required string Message { get; init; }
}

public interface IServiceAuditService
{
    Task<IReadOnlyList<ServiceAuditItem>> ScanAsync(CancellationToken cancellationToken = default);
}

public interface IServiceOptimizationService : IServiceAuditService
{
    Task<ServiceOperationResult> DisableAsync(string serviceName, CancellationToken cancellationToken = default);
    Task<ServiceOperationResult> RestoreAsync(string serviceName, CancellationToken cancellationToken = default);
}
