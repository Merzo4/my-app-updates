namespace MerzoOptimizer.Core.Diagnostics;

public sealed record RecoveryDiagnosticResult
{
    public bool Success { get; init; }
    public required string Message { get; init; }
    public string? Details { get; init; }
}

public interface IRecoveryDiagnosticService
{
    Task<RecoveryDiagnosticResult> RunAsync(CancellationToken cancellationToken = default);
}
