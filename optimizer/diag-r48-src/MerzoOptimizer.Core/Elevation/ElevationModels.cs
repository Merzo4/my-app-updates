using System.Text.Json;
using System.Text.Json.Serialization;
using MerzoOptimizer.Core.Tweaks;

namespace MerzoOptimizer.Core.Elevation;

public enum ElevatedOperationKind
{
    ApplyTweak,
    CleanCategory,
    DisableService,
    RestoreService,
    DisableScheduledTask,
    RestoreScheduledTask,
    ActivatePowerScheme,
    RestorePowerScheme,
    RestoreSnapshot,
    RestoreLatestTweak,
    RestoreAllActive,
    NetworkRepair,
    Shutdown
}

public sealed record ElevatedOperationRequest
{
    public required string RequestId { get; init; }
    public required ElevatedOperationKind Kind { get; init; }
    public TweakDefinition? Tweak { get; init; }
    public string? TweakId { get; init; }
    public string? CategoryId { get; init; }
    public bool CreateBackup { get; init; } = true;
    public string? ServiceName { get; init; }
    public string? TaskPath { get; init; }
    public string? TaskName { get; init; }
    public string? PowerTarget { get; init; }
    public string? DisplayName { get; init; }
    public string? NetworkAction { get; init; }
    public Guid? SnapshotId { get; init; }
}

public sealed record ElevatedOperationResponse
{
    public required string RequestId { get; init; }
    public bool Success { get; init; }
    public string? ResultJson { get; init; }
    public string? Error { get; init; }
}

public static class ElevationJson
{
    public static JsonSerializerOptions CreateOptions()
    {
        var options = new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            PropertyNameCaseInsensitive = true
        };
        options.Converters.Add(new JsonStringEnumConverter());
        return options;
    }
}
