namespace MerzoOptimizer.Core.Updates;

public sealed record UpdateSettings
{
    public bool AutoCheck { get; init; } = true;
    public bool AutoDownload { get; init; }
    public bool AutoInstall { get; init; }
    public string Provider { get; init; } = "GitHub";
    public string RepositoryOwner { get; init; } = string.Empty;
    public string RepositoryName { get; init; } = string.Empty;
    public string ReleaseTagPrefix { get; init; } = "mwo-v";
    public string AssetNameContains { get; init; } = "MerzoWindowsOptimizerSetup-win-x64.exe";
    public string InstallerSilentArgs { get; init; } = "/SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-";
}

public sealed record UpdateCheckResult
{
    public bool Success { get; init; }
    public bool Configured { get; init; }
    public bool UpdateAvailable { get; init; }
    public string CurrentVersion { get; init; } = string.Empty;
    public string LatestVersion { get; init; } = string.Empty;
    public string ReleaseName { get; init; } = string.Empty;
    public string Notes { get; init; } = string.Empty;
    public string AssetName { get; init; } = string.Empty;
    public string AssetUrl { get; init; } = string.Empty;
    public string AssetDigest { get; init; } = string.Empty;
    public string ChecksumUrl { get; init; } = string.Empty;
    public long AssetSize { get; init; }
    public string Message { get; init; } = string.Empty;
}


public sealed record UpdateProgressInfo
{
    public string Phase { get; init; } = string.Empty;
    public string Message { get; init; } = string.Empty;
    public long BytesReceived { get; init; }
    public long TotalBytes { get; init; }
    public double Percent { get; init; }
    public double BytesPerSecond { get; init; }
    public bool IsIndeterminate { get; init; }
}

public sealed record UpdateDownloadResult
{
    public bool Success { get; init; }
    public string FilePath { get; init; } = string.Empty;
    public string VerifiedSha256 { get; init; } = string.Empty;
    public long VerifiedSize { get; init; }
    public string Message { get; init; } = string.Empty;
}

public sealed record UpdateInstallResult
{
    public bool Success { get; init; }
    public bool InstalledLayout { get; init; }
    public string Message { get; init; } = string.Empty;
}

public interface IUpdateService
{
    UpdateSettings Settings { get; }
    Task<UpdateCheckResult> CheckAsync(CancellationToken cancellationToken = default);
    Task<UpdateDownloadResult> DownloadAsync(UpdateCheckResult update, CancellationToken cancellationToken = default);
    Task<UpdateDownloadResult> DownloadAsync(UpdateCheckResult update, IProgress<UpdateProgressInfo>? progress, CancellationToken cancellationToken = default);
    UpdateInstallResult LaunchInstaller(UpdateDownloadResult download);
}
