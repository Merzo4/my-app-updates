using System.Text.Json;
using System.Text.Json.Serialization;
using MerzoOptimizer.Core.Snapshots;
using MerzoOptimizer.Core.Tweaks;
using MerzoOptimizer.Windows.RegistryAccess;

namespace MerzoOptimizer.Windows.Snapshots;

public sealed class WindowsSnapshotService : ISnapshotService
{
    private const string AppVersion = "0.1 R20";

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        Converters = { new JsonStringEnumConverter() }
    };

    private readonly RegistryTweakAccessor _registry = new();
    private readonly SemaphoreSlim _ioLock = new(1, 1);

    public WindowsSnapshotService(string? snapshotDirectory = null)
    {
        SnapshotDirectory = snapshotDirectory ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "MerzoWindowsOptimizer",
            "snapshots");

        Directory.CreateDirectory(SnapshotDirectory);
    }

    public string SnapshotDirectory { get; }

    public async Task<ChangeSnapshot> CreateForTweakAsync(
        TweakDefinition tweak,
        string reason,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();

        var values = tweak.RegistryActions
            .Select(_registry.Capture)
            .ToArray();

        var snapshot = new ChangeSnapshot
        {
            Id = Guid.NewGuid(),
            CreatedAt = DateTimeOffset.Now,
            Reason = reason,
            AppVersion = AppVersion,
            TweakId = tweak.Id,
            TweakName = tweak.Name,
            RegistryValues = values
        };

        await SaveAsync(snapshot, cancellationToken).ConfigureAwait(false);
        return snapshot;
    }

    public async Task<ChangeSnapshot> CreateForCleanupAsync(
        string operationId,
        string operationName,
        string reason,
        CleanupArchiveSnapshot cleanupArchive,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();

        var snapshot = new ChangeSnapshot
        {
            Id = Guid.NewGuid(),
            CreatedAt = DateTimeOffset.Now,
            Reason = reason,
            AppVersion = AppVersion,
            TweakId = operationId,
            TweakName = operationName,
            CleanupArchive = cleanupArchive
        };

        await SaveAsync(snapshot, cancellationToken).ConfigureAwait(false);
        return snapshot;
    }


    public async Task<ChangeSnapshot> CreateForServiceAsync(
        string operationId,
        string operationName,
        string reason,
        ServiceStateSnapshot serviceState,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var snapshot = new ChangeSnapshot
        {
            Id = Guid.NewGuid(),
            CreatedAt = DateTimeOffset.Now,
            Reason = reason,
            AppVersion = AppVersion,
            TweakId = operationId,
            TweakName = operationName,
            ServiceState = serviceState
        };
        await SaveAsync(snapshot, cancellationToken).ConfigureAwait(false);
        return snapshot;
    }

    public async Task<ChangeSnapshot> CreateForScheduledTaskAsync(
        string operationId,
        string operationName,
        string reason,
        ScheduledTaskStateSnapshot taskState,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var snapshot = new ChangeSnapshot
        {
            Id = Guid.NewGuid(),
            CreatedAt = DateTimeOffset.Now,
            Reason = reason,
            AppVersion = AppVersion,
            TweakId = operationId,
            TweakName = operationName,
            ScheduledTaskState = taskState
        };
        await SaveAsync(snapshot, cancellationToken).ConfigureAwait(false);
        return snapshot;
    }

    public async Task<ChangeSnapshot> CreateForPowerSchemeAsync(
        string operationId,
        string operationName,
        string reason,
        PowerSchemeStateSnapshot powerState,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var snapshot = new ChangeSnapshot
        {
            Id = Guid.NewGuid(),
            CreatedAt = DateTimeOffset.Now,
            Reason = reason,
            AppVersion = AppVersion,
            TweakId = operationId,
            TweakName = operationName,
            PowerSchemeState = powerState
        };
        await SaveAsync(snapshot, cancellationToken).ConfigureAwait(false);
        return snapshot;
    }

    public async Task<IReadOnlyList<ChangeSnapshot>> ListAsync(CancellationToken cancellationToken = default)
    {
        var result = new List<ChangeSnapshot>();
        foreach (var file in Directory.EnumerateFiles(SnapshotDirectory, "snapshot-*.json"))
        {
            cancellationToken.ThrowIfCancellationRequested();
            try
            {
                var json = await File.ReadAllTextAsync(file, cancellationToken).ConfigureAwait(false);
                var snapshot = JsonSerializer.Deserialize<ChangeSnapshot>(json, JsonOptions);
                if (snapshot is not null)
                    result.Add(snapshot);
            }
            catch (JsonException)
            {
                // A damaged snapshot is ignored by the list and remains on disk for manual diagnostics.
            }
            catch (IOException)
            {
                // A temporarily locked snapshot must not break the whole Restore Center.
            }
        }

        return result.OrderByDescending(static s => s.CreatedAt).ToArray();
    }

    public async Task<ChangeSnapshot?> GetAsync(Guid snapshotId, CancellationToken cancellationToken = default)
    {
        var path = FindPath(snapshotId);
        if (path is null)
            return null;

        var json = await File.ReadAllTextAsync(path, cancellationToken).ConfigureAwait(false);
        return JsonSerializer.Deserialize<ChangeSnapshot>(json, JsonOptions);
    }

    public async Task<ChangeSnapshot?> GetLatestActiveForTweakAsync(
        string tweakId,
        CancellationToken cancellationToken = default)
    {
        var snapshots = await ListAsync(cancellationToken).ConfigureAwait(false);
        return snapshots.FirstOrDefault(s =>
            !s.IsRestored && string.Equals(s.TweakId, tweakId, StringComparison.OrdinalIgnoreCase));
    }

    public async Task MarkRestoredAsync(
        Guid snapshotId,
        DateTimeOffset restoredAt,
        CancellationToken cancellationToken = default)
    {
        var snapshot = await GetAsync(snapshotId, cancellationToken).ConfigureAwait(false)
            ?? throw new FileNotFoundException($"Snapshot {snapshotId} не найден.");

        await SaveAsync(snapshot with { RestoredAt = restoredAt }, cancellationToken).ConfigureAwait(false);
    }

    private async Task SaveAsync(ChangeSnapshot snapshot, CancellationToken cancellationToken)
    {
        var path = Path.Combine(
            SnapshotDirectory,
            $"snapshot-{snapshot.CreatedAt:yyyyMMdd-HHmmssfff}-{snapshot.Id:N}.json");

        var existing = FindPath(snapshot.Id);
        if (existing is not null)
            path = existing;

        var json = JsonSerializer.Serialize(snapshot, JsonOptions);

        await _ioLock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            await File.WriteAllTextAsync(path, json, cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _ioLock.Release();
        }
    }

    private string? FindPath(Guid snapshotId) =>
        Directory.EnumerateFiles(SnapshotDirectory, $"snapshot-*-{snapshotId:N}.json").FirstOrDefault();
}
