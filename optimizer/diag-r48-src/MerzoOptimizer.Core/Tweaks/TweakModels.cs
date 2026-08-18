namespace MerzoOptimizer.Core.Tweaks;

public enum TweakRisk
{
    Safe,
    Balanced,
    Advanced,
    Expert
}

public enum RegistryHiveScope
{
    LocalMachine,
    CurrentUser
}


public enum RegistryTweakActionMode
{
    SetValue,
    DeleteValue
}

public enum RegistryTweakValueType
{
    DWord,
    QWord,
    String,
    ExpandString,
    MultiString,
    Binary
}

public sealed record RegistryTweakAction
{
    public RegistryTweakActionMode Mode { get; init; } = RegistryTweakActionMode.SetValue;
    public RegistryHiveScope Hive { get; init; }
    public required string KeyPath { get; init; }
    public required string ValueName { get; init; }
    public RegistryTweakValueType ValueType { get; init; } = RegistryTweakValueType.DWord;
    public long? IntegerValue { get; init; }
    public string? StringValue { get; init; }
}

public sealed record TweakDefinition
{
    public required string Id { get; init; }
    public required string Name { get; init; }
    public required string Category { get; init; }
    public TweakRisk Risk { get; init; }
    public bool RequiresAdmin { get; init; }
    public bool RequiresRestart { get; init; }
    public bool ScanOnly { get; init; }
    public int? MinWindowsBuild { get; init; }
    public required string Description { get; init; }
    public string? ExpectedEffect { get; init; }
    public string? SourceNote { get; init; }
    public IReadOnlyList<string> ProfileTags { get; init; } = [];
    public IReadOnlyList<RegistryTweakAction> RegistryActions { get; init; } = [];
}

public enum TweakState
{
    Unknown,
    NotApplied,
    Applied,
    Mixed
}

public sealed record TweakStateResult
{
    public required TweakState State { get; init; }
    public required string DisplayText { get; init; }
    public string? Details { get; init; }
    public bool IsSupported { get; init; } = true;
}

public sealed record TweakApplyResult
{
    public bool Success { get; init; }
    public bool Changed { get; init; }
    public Guid? SnapshotId { get; init; }
    public required string Message { get; init; }
}

public interface ITweakExecutionService
{
    Task<TweakStateResult> GetStateAsync(TweakDefinition tweak, CancellationToken cancellationToken = default);
    Task<TweakApplyResult> ApplyAsync(TweakDefinition tweak, CancellationToken cancellationToken = default);
}
