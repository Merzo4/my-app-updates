using MerzoOptimizer.Core.Tweaks;

namespace MerzoOptimizer.Core.Snapshots;

public sealed record RegistryValueSnapshot
{
    public RegistryHiveScope Hive { get; init; }
    public required string KeyPath { get; init; }
    public required string ValueName { get; init; }
    public bool Existed { get; init; }
    public RegistryTweakValueType? ValueType { get; init; }
    public long? IntegerValue { get; init; }
    public string? StringValue { get; init; }
    public string[]? MultiStringValue { get; init; }
    public string? BinaryBase64 { get; init; }
}

public sealed record CleanupArchiveEntrySnapshot
{
    public required string OriginalPath { get; init; }
    public required string ArchiveEntryName { get; init; }
    public long OriginalBytes { get; init; }
}

public sealed record CleanupArchiveSnapshot
{
    public required string CategoryId { get; init; }
    public required string CategoryName { get; init; }
    public required string ArchivePath { get; init; }
    public IReadOnlyList<CleanupArchiveEntrySnapshot> Files { get; init; } = [];
}

public sealed record ServiceStateSnapshot
{
    public required string ServiceName { get; init; }
    public int StartValue { get; init; }
    public bool WasRunning { get; init; }
}

public sealed record ScheduledTaskStateSnapshot
{
    public required string TaskPath { get; init; }
    public required string TaskName { get; init; }
    public bool WasEnabled { get; init; }
}

public sealed record PowerSchemeStateSnapshot
{
    public required string ActiveSchemeGuid { get; init; }
    public required string ActiveSchemeName { get; init; }
}

public sealed record ChangeSnapshot
{
    public required Guid Id { get; init; }
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.Now;
    public required string Reason { get; init; }
    public required string AppVersion { get; init; }
    public string? TweakId { get; init; }
    public string? TweakName { get; init; }
    public IReadOnlyList<RegistryValueSnapshot> RegistryValues { get; init; } = [];
    public CleanupArchiveSnapshot? CleanupArchive { get; init; }
    public ServiceStateSnapshot? ServiceState { get; init; }
    public ScheduledTaskStateSnapshot? ScheduledTaskState { get; init; }
    public PowerSchemeStateSnapshot? PowerSchemeState { get; init; }
    public DateTimeOffset? RestoredAt { get; init; }

    public bool IsRestored => RestoredAt is not null;
    public string StatusText => IsRestored ? "Восстановлен" : "Активен";
}

public sealed record RestoreResult
{
    public bool Success { get; init; }
    public bool Changed { get; init; }
    public required string Message { get; init; }
    public Guid? SnapshotId { get; init; }
}

public interface ISnapshotService
{
    string SnapshotDirectory { get; }

    Task<ChangeSnapshot> CreateForTweakAsync(
        TweakDefinition tweak,
        string reason,
        CancellationToken cancellationToken = default);

    Task<ChangeSnapshot> CreateForCleanupAsync(
        string operationId,
        string operationName,
        string reason,
        CleanupArchiveSnapshot cleanupArchive,
        CancellationToken cancellationToken = default);

    Task<ChangeSnapshot> CreateForServiceAsync(
        string operationId,
        string operationName,
        string reason,
        ServiceStateSnapshot serviceState,
        CancellationToken cancellationToken = default);

    Task<ChangeSnapshot> CreateForScheduledTaskAsync(
        string operationId,
        string operationName,
        string reason,
        ScheduledTaskStateSnapshot taskState,
        CancellationToken cancellationToken = default);

    Task<ChangeSnapshot> CreateForPowerSchemeAsync(
        string operationId,
        string operationName,
        string reason,
        PowerSchemeStateSnapshot powerState,
        CancellationToken cancellationToken = default);

    Task<IReadOnlyList<ChangeSnapshot>> ListAsync(CancellationToken cancellationToken = default);
    Task<ChangeSnapshot?> GetAsync(Guid snapshotId, CancellationToken cancellationToken = default);
    Task<ChangeSnapshot?> GetLatestActiveForTweakAsync(string tweakId, CancellationToken cancellationToken = default);
    Task MarkRestoredAsync(Guid snapshotId, DateTimeOffset restoredAt, CancellationToken cancellationToken = default);
}

public interface IRestoreService
{
    Task<RestoreResult> RestoreAsync(Guid snapshotId, CancellationToken cancellationToken = default);
    Task<RestoreResult> RestoreLatestForTweakAsync(string tweakId, CancellationToken cancellationToken = default);
    Task<RestoreResult> RestoreAllActiveAsync(CancellationToken cancellationToken = default);
}
