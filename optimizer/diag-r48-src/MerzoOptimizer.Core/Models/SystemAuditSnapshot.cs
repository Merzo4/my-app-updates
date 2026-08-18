namespace MerzoOptimizer.Core.Models;

public sealed record SystemAuditSnapshot
{
    public DateTimeOffset CapturedAt { get; init; } = DateTimeOffset.Now;
    public required WindowsInfoSnapshot Windows { get; init; }
    public required CpuSnapshot Cpu { get; init; }
    public IReadOnlyList<GpuSnapshot> Gpus { get; init; } = [];
    public required MemorySnapshot Memory { get; init; }
    public int ProcessCount { get; init; }
    public int SystemProcessCount { get; init; }
    public int UserProcessCount { get; init; }
    public IReadOnlyList<ProcessSnapshot> TopProcesses { get; init; } = [];
    public bool IsAdministrator { get; init; }
    public required string ActivePowerPlan { get; init; }
    public IReadOnlyList<StartupItemSnapshot> StartupItems { get; init; } = [];
    public IReadOnlyList<StorageSnapshot> Storage { get; init; } = [];
    public required HealthScoreResult Health { get; init; }
}

public sealed record WindowsInfoSnapshot(
    string ProductName,
    string EditionId,
    string DisplayVersion,
    string Build,
    string Architecture);

public sealed record CpuSnapshot(
    string Name,
    int LogicalProcessors,
    double UsagePercent);

public sealed record GpuSnapshot(string Name);

public sealed record MemorySnapshot(
    ulong TotalBytes,
    ulong AvailableBytes)
{
    public ulong UsedBytes => TotalBytes > AvailableBytes ? TotalBytes - AvailableBytes : 0;
    public double UsedPercent => TotalBytes == 0 ? 0 : UsedBytes * 100d / TotalBytes;
}

public sealed record ProcessSnapshot(
    string Name,
    int ProcessId,
    long WorkingSetBytes,
    int SessionId,
    bool IsSystemSession)
{
    public double WorkingSetMegabytes => WorkingSetBytes / 1024d / 1024d;
    public string WorkingSetHuman => WorkingSetBytes >= 1024L * 1024L * 1024L ? $"{WorkingSetBytes / 1024d / 1024d / 1024d:F1} ГБ" : $"{WorkingSetMegabytes:F0} МБ";
    public string SessionKind => IsSystemSession ? "System" : "User";
    public bool IsLikelyBackgroundCandidate => !IsSystemSession && PerformanceAdvisor.IsBackgroundCandidate(Name);
    public string PerformanceClass => PerformanceAdvisor.Classify(Name, IsSystemSession);
    public string PerformanceAdvice => PerformanceAdvisor.Advice(Name, IsSystemSession);
    public string SourceHint => PerformanceAdvisor.SourceHint(Name, IsSystemSession);
    public string ReductionTier => PerformanceAdvisor.ReductionTier(Name, IsSystemSession);
    public string ReductionPotential => PerformanceAdvisor.ReductionPotential(Name, IsSystemSession);
}

internal static class PerformanceAdvisor
{
    private static readonly HashSet<string> Critical = new(StringComparer.OrdinalIgnoreCase)
    {
        "system", "registry", "smss", "csrss", "wininit", "services", "lsass", "winlogon", "dwm",
        "svchost", "fontdrvhost", "sihost", "taskhostw", "explorer", "searchhost", "startmenuexperiencehost",
        "shellexperiencehost", "securityhealthservice", "securityhealthsystray", "msmpeng", "memory compression"
    };
    private static readonly string[] BackgroundHints =
    {
        "onedrive", "msedge", "msedgewebview2", "widgets", "widgetservice", "phoneexperiencehost", "gamebar",
        "xbox", "teams", "ms-teams", "discord", "spotify", "steamwebhelper", "epicwebhelper", "epicgameslauncher",
        "adobe", "creative cloud", "ccxprocess", "googledrivefs", "dropbox", "chrome", "opera", "brave", "updater"
    };

    public static bool IsBackgroundCandidate(string name)
    {
        if (string.IsNullOrWhiteSpace(name) || Critical.Contains(name)) return false;
        return BackgroundHints.Any(h => name.Contains(h, StringComparison.OrdinalIgnoreCase));
    }

    public static string Classify(string name, bool system)
    {
        if (system || Critical.Contains(name)) return "Системный";
        if (IsBackgroundCandidate(name)) return "Фоновый";
        return "Пользовательский";
    }

    public static string SourceHint(string name, bool system)
    {
        if (system || Critical.Contains(name)) return "Windows / системная служба";
        if (name.Contains("onedrive", StringComparison.OrdinalIgnoreCase)) return "OneDrive · синхронизация / автозапуск";
        if (name.Contains("msedge", StringComparison.OrdinalIgnoreCase)) return "Edge · Startup Boost / Background Mode / WebView";
        if (name.Contains("widget", StringComparison.OrdinalIgnoreCase)) return "Windows Widgets / WebView";
        if (name.Contains("phone", StringComparison.OrdinalIgnoreCase)) return "Phone Link / мобильные функции";
        if (name.Contains("gamebar", StringComparison.OrdinalIgnoreCase) || name.Contains("xbox", StringComparison.OrdinalIgnoreCase)) return "Xbox / Game Bar background";
        if (name.Contains("steam", StringComparison.OrdinalIgnoreCase) || name.Contains("epic", StringComparison.OrdinalIgnoreCase)) return "Игровой launcher / web helper";
        if (name.Contains("teams", StringComparison.OrdinalIgnoreCase) || name.Contains("discord", StringComparison.OrdinalIgnoreCase) || name.Contains("spotify", StringComparison.OrdinalIgnoreCase)) return "Автозагрузка пользовательского приложения";
        if (name.Contains("adobe", StringComparison.OrdinalIgnoreCase) || name.Contains("ccx", StringComparison.OrdinalIgnoreCase) || name.Contains("updater", StringComparison.OrdinalIgnoreCase)) return "Updater / helper / background agent";
        if (name.Contains("dropbox", StringComparison.OrdinalIgnoreCase) || name.Contains("googledrive", StringComparison.OrdinalIgnoreCase)) return "Облачная синхронизация";
        if (name.Contains("chrome", StringComparison.OrdinalIgnoreCase) || name.Contains("brave", StringComparison.OrdinalIgnoreCase) || name.Contains("opera", StringComparison.OrdinalIgnoreCase)) return "Браузер · background mode / extensions";
        return "Пользовательское приложение / источник требует проверки";
    }

    public static string ReductionTier(string name, bool system)
    {
        if (system || Critical.Contains(name)) return "KEEP";
        if (name.Contains("widget", StringComparison.OrdinalIgnoreCase) || name.Contains("msedge", StringComparison.OrdinalIgnoreCase) || name.Contains("chrome", StringComparison.OrdinalIgnoreCase) || name.Contains("brave", StringComparison.OrdinalIgnoreCase) || name.Contains("opera", StringComparison.OrdinalIgnoreCase)) return "SAFE";
        if (name.Contains("onedrive", StringComparison.OrdinalIgnoreCase) || name.Contains("phone", StringComparison.OrdinalIgnoreCase) || name.Contains("xbox", StringComparison.OrdinalIgnoreCase) || name.Contains("gamebar", StringComparison.OrdinalIgnoreCase)) return "AGGRESSIVE";
        if (IsBackgroundCandidate(name)) return "РУЧНОЙ";
        return "—";
    }

    public static string ReductionPotential(string name, bool system)
    {
        if (system || Critical.Contains(name)) return "Не трогать";
        if (name.Contains("widget", StringComparison.OrdinalIgnoreCase) || name.Contains("msedge", StringComparison.OrdinalIgnoreCase) || name.Contains("onedrive", StringComparison.OrdinalIgnoreCase)) return "Высокий";
        if (IsBackgroundCandidate(name)) return "Средний";
        return "Низкий / неизвестно";
    }

    public static string Advice(string name, bool system)
    {
        if (system || Critical.Contains(name)) return "Не завершать: компонент Windows или защищённый системный процесс.";
        if (name.Contains("onedrive", StringComparison.OrdinalIgnoreCase)) return "Если синхронизация не нужна — отключите OneDrive/автозапуск, а не завершайте процесс вручную.";
        if (name.Contains("msedge", StringComparison.OrdinalIgnoreCase)) return "Проверьте Startup Boost, background mode и preload Edge в профиле Performance.";
        if (name.Contains("widget", StringComparison.OrdinalIgnoreCase)) return "Widgets можно отключить обратимым твиком — это убирает их постоянный фон.";
        if (name.Contains("steamwebhelper", StringComparison.OrdinalIgnoreCase) || name.Contains("epic", StringComparison.OrdinalIgnoreCase)) return "Лаунчер/веб-процесс. Уберите автозапуск, если он не нужен сразу после входа.";
        if (name.Contains("teams", StringComparison.OrdinalIgnoreCase) || name.Contains("discord", StringComparison.OrdinalIgnoreCase) || name.Contains("spotify", StringComparison.OrdinalIgnoreCase)) return "Пользовательское приложение: проверьте автозагрузку и фоновый запуск.";
        if (name.Contains("chrome", StringComparison.OrdinalIgnoreCase) || name.Contains("brave", StringComparison.OrdinalIgnoreCase) || name.Contains("opera", StringComparison.OrdinalIgnoreCase)) return "Браузер: отключите фоновую работу после закрытия, если она не нужна.";
        if (IsBackgroundCandidate(name)) return "Кандидат на разгрузку: сначала отключите источник автозапуска/фоновой работы через Merzo.";
        return "Нет безопасной автоматической рекомендации. Не завершайте процесс только ради уменьшения счётчика.";
    }
}

public sealed record StartupItemSnapshot(
    string Name,
    string Command,
    string Source,
    string Scope);

public sealed record StorageSnapshot(
    string Name,
    string DriveType,
    string FileSystem,
    long TotalBytes,
    long FreeBytes)
{
    public double FreePercent => TotalBytes <= 0 ? 0 : FreeBytes * 100d / TotalBytes;
    public double UsedPercent => TotalBytes <= 0 ? 0 : Math.Clamp((TotalBytes - FreeBytes) * 100d / TotalBytes, 0d, 100d);
}

public sealed record HealthScoreResult(
    int Score,
    string Rating,
    IReadOnlyList<string> Explanations);
