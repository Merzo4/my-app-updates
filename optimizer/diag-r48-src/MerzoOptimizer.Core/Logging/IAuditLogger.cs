namespace MerzoOptimizer.Core.Logging;

public interface IAuditLogger
{
    string LogDirectory { get; }
    Task WriteAsync(AuditLogEntry entry, CancellationToken cancellationToken = default);
}

public sealed record AuditLogEntry
{
    public DateTimeOffset Timestamp { get; init; } = DateTimeOffset.Now;
    public required string Category { get; init; }
    public required string Action { get; init; }
    public required string Status { get; init; }
    public string? TweakId { get; init; }
    public string? OldValue { get; init; }
    public string? NewValue { get; init; }
    public string? Details { get; init; }
    public string? ErrorCode { get; init; }
}
