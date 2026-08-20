from pathlib import Path
import os, re

root = Path(os.environ['SOURCE_ROOT'])

def read(path):
    return path.read_text(encoding='utf-8-sig')

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')

def once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'R55 anchor {label} count={count}')
    return text.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Core contracts: immutable samples + grouped deltas. The analyzer is read-only.
# -----------------------------------------------------------------------------
models = r'''namespace MerzoOptimizer.Core.Audit;

public sealed record ProcessStabilityAuditOptions(IReadOnlyList<TimeSpan> SampleOffsets)
{
    public static ProcessStabilityAuditOptions Production { get; } = new(
        [TimeSpan.Zero, TimeSpan.FromMinutes(1), TimeSpan.FromMinutes(5), TimeSpan.FromMinutes(10), TimeSpan.FromMinutes(15)]);
}

public sealed record ProcessStabilityProgress(TimeSpan Elapsed, int SampleIndex, int SampleCount, int ProcessCount, string Phase);

public sealed record ProcessStabilityFamilySnapshot(
    string FamilyName,
    int Count,
    IReadOnlyList<int> Pids,
    IReadOnlyList<string> Paths,
    string Source,
    string Classification,
    string Recommendation,
    string Evidence);

public sealed record ProcessStabilitySample(TimeSpan Elapsed, int ProcessCount, IReadOnlyList<ProcessStabilityFamilySnapshot> Families);

public sealed record ProcessStabilityDelta(
    string FamilyName,
    int BaselineCount,
    int PeakCount,
    int FinalCount,
    int AddedPeak,
    string Source,
    string Classification,
    string Recommendation,
    string Evidence);

public sealed record ProcessStabilityReport(
    DateTimeOffset StartedAt,
    int BaselineCount,
    int FinalCount,
    int PeakCount,
    int AddedAtPeak,
    int ReviewAddedCount,
    int ProtectedAddedCount,
    IReadOnlyList<ProcessStabilitySample> Samples,
    IReadOnlyList<ProcessStabilityDelta> Deltas);
'''
write(root/'src'/'MerzoOptimizer.Core'/'Audit'/'ProcessStabilityModels.cs', models)

# -----------------------------------------------------------------------------
# Windows analyzer. It does not terminate, disable or mutate any process source.
# Source inventory = Run/RunOnce + Startup folders + scheduled task actions +
# Win32 service ImagePath. Classification is conservative and fail-safe.
# -----------------------------------------------------------------------------
analyzer = r'''using System.Diagnostics;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Win32;
using MerzoOptimizer.Core.Audit;

namespace MerzoOptimizer.Windows.Processes;

public sealed class WindowsProcessStabilityAnalyzer
{
    private static readonly HashSet<string> ProtectedFamilies = new(StringComparer.OrdinalIgnoreCase)
    {
        "System", "Registry", "smss", "csrss", "wininit", "winlogon", "services", "lsass", "svchost",
        "fontdrvhost", "dwm", "explorer", "sihost", "taskhostw", "ctfmon", "dllhost", "audiodg",
        "wudfhost", "Runtime Broker", "StartMenuExperienceHost", "ShellExperienceHost", "SearchHost",
        "SecurityHealthService", "SecurityHealthSystray", "MsMpEng", "NisSrv", "WmiPrvSE"
    };

    private static readonly HashSet<string> ReviewFamilies = new(StringComparer.OrdinalIgnoreCase)
    {
        "Edge", "WebView2", "Widgets", "Teams", "Phone Link", "OneDrive", "Outlook", "Copilot",
        "Game Bar", "Steam WebHelper", "Discord"
    };

    private static readonly string[] DriverVendorHints =
    [
        "\\NVIDIA Corporation\\", "\\AMD\\", "\\ATI Technologies\\", "\\Intel\\", "\\Realtek\\",
        "\\Logitech\\", "\\Razer\\", "\\Corsair\\", "\\Elgato\\"
    ];

    private static readonly HashSet<string> DriverProcessHints = new(StringComparer.OrdinalIgnoreCase)
    {
        "NVDisplay.Container", "nvcontainer", "RadeonSoftware", "AMDRSServ", "atiesrxx", "atieclxx",
        "igfxCUIService", "igfxEM", "RtkAudUService", "RtkAudioService"
    };

    public async Task<ProcessStabilityReport> RunAsync(
        ProcessStabilityAuditOptions? options = null,
        IProgress<ProcessStabilityProgress>? progress = null,
        CancellationToken cancellationToken = default)
    {
        options ??= ProcessStabilityAuditOptions.Production;
        var offsets = options.SampleOffsets
            .Where(static x => x >= TimeSpan.Zero)
            .Distinct()
            .OrderBy(static x => x)
            .ToArray();
        if (offsets.Length == 0 || offsets[0] != TimeSpan.Zero)
            offsets = [TimeSpan.Zero, .. offsets];

        var inventory = await Task.Run(BuildSourceInventory, cancellationToken).ConfigureAwait(false);
        var started = DateTimeOffset.Now;
        var sw = Stopwatch.StartNew();
        var samples = new List<ProcessStabilitySample>(offsets.Length);

        for (var i = 0; i < offsets.Length; i++)
        {
            var remaining = offsets[i] - sw.Elapsed;
            if (remaining > TimeSpan.Zero)
                await Task.Delay(remaining, cancellationToken).ConfigureAwait(false);

            cancellationToken.ThrowIfCancellationRequested();
            var sample = Capture(sw.Elapsed, inventory);
            samples.Add(sample);
            progress?.Report(new ProcessStabilityProgress(sample.Elapsed, i + 1, offsets.Length, sample.ProcessCount,
                i == 0 ? "Базовый снимок" : $"Контроль {FormatOffset(offsets[i])}"));
        }

        var baseline = samples[0];
        var baselineMap = baseline.Families.ToDictionary(static x => x.FamilyName, StringComparer.OrdinalIgnoreCase);
        var allNames = samples.SelectMany(static x => x.Families).Select(static x => x.FamilyName)
            .Distinct(StringComparer.OrdinalIgnoreCase).OrderBy(static x => x, StringComparer.OrdinalIgnoreCase);
        var deltas = new List<ProcessStabilityDelta>();

        foreach (var name in allNames)
        {
            baselineMap.TryGetValue(name, out var b);
            var familySamples = samples.Select(s => s.Families.FirstOrDefault(f => string.Equals(f.FamilyName, name, StringComparison.OrdinalIgnoreCase))).ToArray();
            var peak = familySamples.Max(static x => x?.Count ?? 0);
            var final = familySamples[^1]?.Count ?? 0;
            var baseCount = b?.Count ?? 0;
            var added = Math.Max(0, peak - baseCount);
            if (added == 0) continue;
            var evidence = familySamples.LastOrDefault(static x => x is not null) ?? b;
            if (evidence is null) continue;
            deltas.Add(new ProcessStabilityDelta(name, baseCount, peak, final, added,
                evidence.Source, evidence.Classification, evidence.Recommendation, evidence.Evidence));
        }

        deltas = deltas.OrderByDescending(static x => x.AddedPeak).ThenBy(static x => x.FamilyName, StringComparer.OrdinalIgnoreCase).ToList();
        var peakCount = samples.Max(static x => x.ProcessCount);
        var reviewAdded = deltas.Where(static x => x.Classification is "Проверить" or "Необязательный") .Sum(static x => x.AddedPeak);
        var protectedAdded = deltas.Where(static x => x.Classification is "Не трогать" or "Драйвер / оставить") .Sum(static x => x.AddedPeak);
        return new ProcessStabilityReport(started, baseline.ProcessCount, samples[^1].ProcessCount, peakCount,
            Math.Max(0, peakCount - baseline.ProcessCount), reviewAdded, protectedAdded, samples, deltas);
    }

    private static ProcessStabilitySample Capture(TimeSpan elapsed, SourceInventory inventory)
    {
        var items = new List<RawProcess>();
        Process[] processes;
        try { processes = Process.GetProcesses(); }
        catch { processes = []; }
        foreach (var process in processes)
        {
            try
            {
                var name = SafeName(process);
                var path = SafePath(process);
                items.Add(new RawProcess(process.Id, name, path));
            }
            finally { process.Dispose(); }
        }

        var families = items.GroupBy(static x => NormalizeFamily(x.Name), StringComparer.OrdinalIgnoreCase)
            .Select(g => BuildFamily(g.Key, g.ToArray(), inventory))
            .OrderByDescending(static x => x.Count)
            .ThenBy(static x => x.FamilyName, StringComparer.OrdinalIgnoreCase)
            .ToArray();
        return new ProcessStabilitySample(elapsed, items.Count, families);
    }

    private static ProcessStabilityFamilySnapshot BuildFamily(string family, IReadOnlyList<RawProcess> items, SourceInventory inventory)
    {
        var paths = items.Select(static x => x.Path).Where(static x => !string.IsNullOrWhiteSpace(x)).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        var originalNames = items.Select(static x => x.Name).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        var exeNames = originalNames.Select(static x => x + ".exe").ToHashSet(StringComparer.OrdinalIgnoreCase);
        foreach (var path in paths)
            exeNames.Add(Path.GetFileName(path));

        var startup = inventory.StartupExecutables.FirstOrDefault(exeNames.Contains);
        var task = inventory.TaskExecutables.FirstOrDefault(exeNames.Contains);
        var service = inventory.ServiceExecutables.FirstOrDefault(exeNames.Contains);
        var pathJoined = string.Join(" | ", paths);

        string source;
        string classification;
        string recommendation;
        string evidence;

        if (ProtectedFamilies.Contains(family) || paths.Any(IsWindowsSystemPath))
        {
            source = service is null ? "Windows / системный" : $"Служба: {service}";
            classification = "Не трогать";
            recommendation = "Системный компонент. Не отключать ради числа процессов.";
            evidence = string.IsNullOrWhiteSpace(pathJoined) ? family : pathJoined;
        }
        else if (DriverProcessHints.Contains(family) || paths.Any(IsDriverVendorPath))
        {
            source = service is null ? "Драйвер / vendor utility" : $"Служба/драйвер: {service}";
            classification = "Драйвер / оставить";
            recommendation = "Оставить по умолчанию; отключать только после проверки конкретной функции устройства.";
            evidence = pathJoined;
        }
        else if (startup is not null)
        {
            source = $"Автозагрузка: {startup}";
            classification = ReviewFamilies.Contains(family) ? "Необязательный" : "Проверить";
            recommendation = "Проверьте необходимость автозапуска. Merzo не отключает неизвестный источник автоматически.";
            evidence = pathJoined;
        }
        else if (task is not null)
        {
            source = $"Планировщик: {task}";
            classification = ReviewFamilies.Contains(family) ? "Необязательный" : "Проверить";
            recommendation = "Проверьте задачу и программу-владельца. Неизвестная задача автоматически не отключается.";
            evidence = pathJoined;
        }
        else if (service is not null)
        {
            source = $"Служба: {service}";
            classification = "Проверить";
            recommendation = "Служба обнаружена как источник. Менять её можно только через проверенный allow-list и Snapshot/Undo.";
            evidence = pathJoined;
        }
        else if (ReviewFamilies.Contains(family))
        {
            source = "Приложение / background host";
            classification = "Необязательный";
            recommendation = "Фоновый компонент приложения; отключение зависит от того, пользуетесь ли вы этой функцией.";
            evidence = pathJoined;
        }
        else if (paths.Any(IsProgramFilesPath) || paths.Any(IsUserApplicationPath))
        {
            source = "Стороннее приложение";
            classification = "Проверить";
            recommendation = "Проверьте настройки автозапуска/фоновой работы приложения; Merzo не завершает его автоматически.";
            evidence = pathJoined;
        }
        else
        {
            source = "Источник не подтверждён";
            classification = "Проверить";
            recommendation = "Нужна ручная проверка владельца процесса. Автоматическое отключение запрещено.";
            evidence = pathJoined;
        }

        return new ProcessStabilityFamilySnapshot(family, items.Count, items.Select(static x => x.Pid).OrderBy(static x => x).ToArray(),
            paths, source, classification, recommendation, evidence);
    }

    private static SourceInventory BuildSourceInventory()
    {
        var startup = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var tasks = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var services = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        ReadRunKey(Registry.CurrentUser, @"Software\Microsoft\Windows\CurrentVersion\Run", startup);
        ReadRunKey(Registry.CurrentUser, @"Software\Microsoft\Windows\CurrentVersion\RunOnce", startup);
        ReadRunKey(Registry.LocalMachine, @"Software\Microsoft\Windows\CurrentVersion\Run", startup);
        ReadRunKey(Registry.LocalMachine, @"Software\Microsoft\Windows\CurrentVersion\RunOnce", startup);
        ReadStartupFolder(Environment.GetFolderPath(Environment.SpecialFolder.Startup), startup);
        ReadStartupFolder(Environment.GetFolderPath(Environment.SpecialFolder.CommonStartup), startup);
        ReadServiceImages(services);
        ReadScheduledTaskActions(tasks);
        return new SourceInventory(startup, tasks, services);
    }

    private static void ReadRunKey(RegistryKey hive, string subKey, HashSet<string> target)
    {
        try
        {
            using var key = hive.OpenSubKey(subKey, writable: false);
            if (key is null) return;
            foreach (var name in key.GetValueNames())
                AddExecutable(target, key.GetValue(name)?.ToString());
        }
        catch { }
    }

    private static void ReadStartupFolder(string folder, HashSet<string> target)
    {
        try
        {
            if (!Directory.Exists(folder)) return;
            foreach (var file in Directory.EnumerateFiles(folder))
                target.Add(Path.GetFileName(file));
        }
        catch { }
    }

    private static void ReadServiceImages(HashSet<string> target)
    {
        try
        {
            using var root = Registry.LocalMachine.OpenSubKey(@"SYSTEM\CurrentControlSet\Services", writable: false);
            if (root is null) return;
            foreach (var name in root.GetSubKeyNames())
            {
                try
                {
                    using var key = root.OpenSubKey(name, writable: false);
                    var type = Convert.ToInt32(key?.GetValue("Type") ?? 0);
                    if ((type & 0x10) == 0 && (type & 0x20) == 0) continue;
                    AddExecutable(target, key?.GetValue("ImagePath")?.ToString());
                }
                catch { }
            }
        }
        catch { }
    }

    private static void ReadScheduledTaskActions(HashSet<string> target)
    {
        try
        {
            var encoded = Convert.ToBase64String(System.Text.Encoding.Unicode.GetBytes(
                "$ErrorActionPreference='SilentlyContinue'; Get-ScheduledTask | ForEach-Object { $_.Actions | ForEach-Object { if($_.Execute){ [pscustomobject]@{Execute=$_.Execute} } } } | ConvertTo-Json -Compress"));
            using var p = Process.Start(new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments = $"-NoProfile -NonInteractive -EncodedCommand {encoded}",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            });
            if (p is null) return;
            var output = p.StandardOutput.ReadToEnd();
            if (!p.WaitForExit(8000)) { try { p.Kill(entireProcessTree: true); } catch { } return; }
            if (p.ExitCode != 0 || string.IsNullOrWhiteSpace(output)) return;
            using var doc = JsonDocument.Parse(output);
            if (doc.RootElement.ValueKind == JsonValueKind.Array)
                foreach (var item in doc.RootElement.EnumerateArray()) if (item.TryGetProperty("Execute", out var e)) AddExecutable(target, e.GetString());
            else if (doc.RootElement.ValueKind == JsonValueKind.Object && doc.RootElement.TryGetProperty("Execute", out var e)) AddExecutable(target, e.GetString());
        }
        catch { }
    }

    private static void AddExecutable(HashSet<string> target, string? command)
    {
        if (string.IsNullOrWhiteSpace(command)) return;
        var expanded = Environment.ExpandEnvironmentVariables(command.Trim());
        var m = Regex.Match(expanded, "^\\s*\\\"(?<p>[^\\\"]+\\.exe)\\\"|^\\s*(?<p>[^\\s]+\\.exe)", RegexOptions.IgnoreCase);
        var candidate = m.Success ? m.Groups["p"].Value : expanded;
        var file = Path.GetFileName(candidate.Trim('"'));
        if (!string.IsNullOrWhiteSpace(file)) target.Add(file);
    }

    private static string SafeName(Process p) { try { return p.ProcessName; } catch { return $"pid-{p.Id}"; } }
    private static string SafePath(Process p) { try { return p.MainModule?.FileName ?? string.Empty; } catch { return string.Empty; } }

    private static string NormalizeFamily(string name) => name.ToLowerInvariant() switch
    {
        "svchost" => "svchost",
        "runtimebroker" => "Runtime Broker",
        "msedgewebview2" => "WebView2",
        "msedge" => "Edge",
        "widgetservice" or "widgets" => "Widgets",
        "msteams" or "teams" => "Teams",
        "yourphone" or "phoneexperiencehost" => "Phone Link",
        "onedrive" => "OneDrive",
        "olk" or "outlook" or "outlookforwindows" => "Outlook",
        "copilot" => "Copilot",
        "gamebar" or "gamebarftserver" or "xboxgamebarwidgets" => "Game Bar",
        "steamwebhelper" => "Steam WebHelper",
        "discord" => "Discord",
        _ => name
    };

    private static bool IsWindowsSystemPath(string path)
    {
        if (string.IsNullOrWhiteSpace(path)) return false;
        var windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        return path.StartsWith(windows, StringComparison.OrdinalIgnoreCase);
    }

    private static bool IsDriverVendorPath(string path) => DriverVendorHints.Any(h => path.Contains(h, StringComparison.OrdinalIgnoreCase));
    private static bool IsProgramFilesPath(string path) => path.StartsWith(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), StringComparison.OrdinalIgnoreCase) ||
        (!string.IsNullOrWhiteSpace(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86)) && path.StartsWith(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), StringComparison.OrdinalIgnoreCase));
    private static bool IsUserApplicationPath(string path) => path.Contains("\\AppData\\", StringComparison.OrdinalIgnoreCase);
    private static string FormatOffset(TimeSpan x) => x.TotalMinutes >= 1 ? $"{x.TotalMinutes:0} мин" : $"{x.TotalSeconds:0} сек";

    private sealed record RawProcess(int Pid, string Name, string Path);
    private sealed record SourceInventory(HashSet<string> StartupExecutables, HashSet<string> TaskExecutables, HashSet<string> ServiceExecutables);
}
'''
write(root/'src'/'MerzoOptimizer.Windows'/'Processes'/'WindowsProcessStabilityAnalyzer.cs', analyzer)

# -----------------------------------------------------------------------------
# ViewModel integration into the existing R34 Process Reduction page.
# -----------------------------------------------------------------------------
vm_path = root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
vm = read(vm_path)
if 'using MerzoOptimizer.Windows.Processes;' not in vm:
    anchor = 'using MerzoOptimizer.Core.Tweaks;\n'
    if anchor not in vm:
        # Later generators may reorder usings; namespace declaration is stable.
        anchor = 'namespace MerzoOptimizer.App.ViewModels;\n'
        vm = once(vm, anchor, 'using MerzoOptimizer.Windows.Processes;\n\n'+anchor, 'vm using namespace fallback')
    else:
        vm = once(vm, anchor, anchor+'using MerzoOptimizer.Windows.Processes;\n', 'vm using')

vm = once(vm,
'''    private readonly INetworkRepairService _networkRepairService;\n''',
'''    private readonly INetworkRepairService _networkRepairService;\n    private readonly WindowsProcessStabilityAnalyzer _processStabilityAnalyzer = new();\n''','analyzer field')
vm = once(vm,
'''    private string _processReductionStatusText = "После аудита Merzo покажет безопасные источники фоновой нагрузки.";\n''',
'''    private string _processReductionStatusText = "После аудита Merzo покажет безопасные источники фоновой нагрузки.";\n    private bool _isProcessStabilityAuditing;\n    private double _processStabilityProgress;\n    private string _processStabilityStatusText = "15-минутный аудит ещё не запускался.";\n    private string _processStabilityTimelineText = "Точки: старт → 1 мин → 5 мин → 10 мин → 15 мин";\n    private string _processStabilitySummaryText = "Запустите аудит, чтобы увидеть, кто появляется после загрузки Windows.";\n    private CancellationTokenSource? _processStabilityCts;\n''','stability state')
vm = once(vm,
'''        SelectProcessLiteCommand = new AsyncRelayCommand(() => SelectProcessReductionProfileAsync("process_lite", "LITE-LIKE"), () => !IsStage2Busy);\n''',
'''        SelectProcessLiteCommand = new AsyncRelayCommand(() => SelectProcessReductionProfileAsync("process_lite", "LITE-LIKE"), () => !IsStage2Busy);\n        RunProcessStabilityAuditCommand = new AsyncRelayCommand(RunProcessStabilityAuditAsync);\n        CancelProcessStabilityAuditCommand = new AsyncRelayCommand(CancelProcessStabilityAuditAsync);\n''','stability commands ctor')
vm = once(vm,
'''    public AsyncRelayCommand SelectProcessLiteCommand { get; }\n''',
'''    public AsyncRelayCommand SelectProcessLiteCommand { get; }\n    public AsyncRelayCommand RunProcessStabilityAuditCommand { get; }\n    public AsyncRelayCommand CancelProcessStabilityAuditCommand { get; }\n''','command properties')

props = r'''    public bool IsProcessStabilityAuditing
    {
        get => _isProcessStabilityAuditing;
        private set => SetProperty(ref _isProcessStabilityAuditing, value);
    }
    public double ProcessStabilityProgress { get => _processStabilityProgress; private set => SetProperty(ref _processStabilityProgress, value); }
    public string ProcessStabilityStatusText { get => _processStabilityStatusText; private set => SetProperty(ref _processStabilityStatusText, value); }
    public string ProcessStabilityTimelineText { get => _processStabilityTimelineText; private set => SetProperty(ref _processStabilityTimelineText, value); }
    public string ProcessStabilitySummaryText { get => _processStabilitySummaryText; private set => SetProperty(ref _processStabilitySummaryText, value); }

'''
vm = once(vm,
'''    public string ProcessReductionStatusText\n    {\n        get => _processReductionStatusText;\n        private set => SetProperty(ref _processReductionStatusText, value);\n    }\n''',
'''    public string ProcessReductionStatusText\n    {\n        get => _processReductionStatusText;\n        private set => SetProperty(ref _processReductionStatusText, value);\n    }\n\n'''+props,'stability properties')
vm = once(vm,
'''    public ObservableCollection<ProcessSnapshot> TopProcesses { get; } = [];\n''',
'''    public ObservableCollection<ProcessSnapshot> TopProcesses { get; } = [];\n    public ObservableCollection<ProcessStabilityDelta> ProcessStabilityRows { get; } = [];\n''','stability collection')

method = r'''    private async Task RunProcessStabilityAuditAsync()
    {
        if (IsProcessStabilityAuditing) return;
        _processStabilityCts?.Cancel();
        _processStabilityCts?.Dispose();
        _processStabilityCts = CancellationTokenSource.CreateLinkedTokenSource(_lifetimeCts.Token);
        IsProcessStabilityAuditing = true;
        ProcessStabilityProgress = 0;
        ProcessStabilityRows.Clear();
        ProcessStabilityStatusText = "Снимаю базовый список процессов…";
        ProcessStabilitySummaryText = "Аудит read-only: Merzo ничего не завершает и не отключает.";
        var progress = new Progress<ProcessStabilityProgress>(p =>
        {
            ProcessStabilityProgress = Math.Clamp(p.SampleIndex * 100d / Math.Max(1, p.SampleCount), 0, 100);
            ProcessStabilityStatusText = $"{p.Phase}: {p.ProcessCount} процессов";
        });
        try
        {
            var report = await _processStabilityAnalyzer.RunAsync(ProcessStabilityAuditOptions.Production, progress, _processStabilityCts.Token);
            foreach (var row in report.Deltas) ProcessStabilityRows.Add(row);
            ProcessStabilityTimelineText = string.Join("  →  ", report.Samples.Select(s => $"{FormatProcessStabilityOffset(s.Elapsed)}: {s.ProcessCount}"));
            ProcessStabilitySummaryText = $"Старт: {report.BaselineCount} → 15 мин: {report.FinalCount} · пик: {report.PeakCount} (+{report.AddedAtPeak}) · проверить/необязательных: {report.ReviewAddedCount} · системных/драйверных новых: {report.ProtectedAddedCount}.";
            ProcessReductionStatusText = report.ReviewAddedCount > 0
                ? $"R55 нашёл {report.ReviewAddedCount} поздно появляющихся процессов для проверки. Неизвестные источники автоматически не отключаются."
                : "R55 не нашёл подтверждённых необязательных источников роста; системные процессы не трогаем.";
            ProcessStabilityStatusText = "15-минутный аудит завершён.";
            ProcessStabilityProgress = 100;
        }
        catch (OperationCanceledException)
        {
            ProcessStabilityStatusText = "Аудит остановлен. Изменений в Windows не было.";
        }
        catch (Exception ex)
        {
            ProcessStabilityStatusText = "Не удалось завершить аудит: " + ex.Message;
        }
        finally
        {
            IsProcessStabilityAuditing = false;
        }
    }

    private Task CancelProcessStabilityAuditAsync()
    {
        _processStabilityCts?.Cancel();
        return Task.CompletedTask;
    }

    private static string FormatProcessStabilityOffset(TimeSpan elapsed)
    {
        if (elapsed.TotalMinutes < 0.5) return "старт";
        return $"{elapsed.TotalMinutes:0} мин";
    }

'''
method_anchor = '    private async Task SelectProcessReductionProfileAsync(string tag, string title)'
if method_anchor not in vm:
    raise SystemExit('R55 process reduction method anchor missing')
vm = vm.replace(method_anchor, method+method_anchor, 1)
vm = once(vm,
'''        _deepScanCts?.Cancel(); _cleanupScanCts?.Cancel(); _cleanupOperationCts?.Cancel(); _updateOperationCts?.Cancel();\n''',
'''        _deepScanCts?.Cancel(); _cleanupScanCts?.Cancel(); _cleanupOperationCts?.Cancel(); _updateOperationCts?.Cancel(); _processStabilityCts?.Cancel();\n''','dispose cancel')
write(vm_path, vm)

# -----------------------------------------------------------------------------
# Compact UI: keep current TOP and add an explicit delayed-growth table.
# -----------------------------------------------------------------------------
xaml_path = root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x = read(xaml_path)
pattern = re.compile(r'<TabItem Header="Процессы" Style="\{StaticResource SubTabItem\}">.*?</TabItem>', re.S)
m = pattern.search(x)
if not m:
    raise SystemExit('R55 process tab anchor missing')
process_tab = r'''<TabItem Header="Процессы" Style="{StaticResource SubTabItem}">
    <Grid Margin="0,6,0,0">
        <Grid.RowDefinitions><RowDefinition Height="108"/><RowDefinition Height="*"/></Grid.RowDefinitions>
        <Border Style="{StaticResource R43HeroCard}" Padding="11,8" Margin="0,0,0,7">
            <Grid>
                <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                <StackPanel><TextBlock Text="{Binding PerformanceProcessSummaryText, Mode=OneWay}" FontSize="11.6" FontWeight="SemiBold"/><TextBlock Text="{Binding ProcessStabilitySummaryText, Mode=OneWay}" Foreground="{StaticResource TextSecondary}" FontSize="9.7" TextWrapping="Wrap" Margin="0,2,8,0"/></StackPanel>
                <StackPanel Grid.Column="1" Orientation="Horizontal" VerticalAlignment="Top"><Button Style="{StaticResource CompactPrimaryButton}" Command="{Binding RunProcessStabilityAuditCommand}" Content="Аудит 15 минут" Margin="0,0,5,0"/><Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding CancelProcessStabilityAuditCommand}" Content="Стоп"/></StackPanel>
                <TextBlock Grid.Row="1" Grid.ColumnSpan="2" Text="{Binding ProcessStabilityTimelineText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.5" Margin="0,4,0,0" TextTrimming="CharacterEllipsis"/>
                <Grid Grid.Row="2" Grid.ColumnSpan="2" Margin="0,4,0,0"><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="140"/></Grid.ColumnDefinitions><TextBlock Text="{Binding ProcessStabilityStatusText, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.4" TextTrimming="CharacterEllipsis"/><ProgressBar Grid.Column="1" Height="4" Maximum="100" Value="{Binding ProcessStabilityProgress}" VerticalAlignment="Center"/></Grid>
            </Grid>
        </Border>
        <TabControl Grid.Row="1" Background="Transparent" BorderThickness="0">
            <TabItem Header="Рост после входа" Style="{StaticResource SubTabItem}">
                <Border Style="{StaticResource R43PageCard}" Margin="0,5,0,0"><DataGrid ItemsSource="{Binding ProcessStabilityRows}" AutoGenerateColumns="False" IsReadOnly="True" BorderThickness="0"><DataGrid.Columns>
                    <DataGridTextColumn Header="Семейство" Binding="{Binding FamilyName, Mode=OneWay}" Width="115"/><DataGridTextColumn Header="Старт" Binding="{Binding BaselineCount, Mode=OneWay}" Width="52"/><DataGridTextColumn Header="Пик" Binding="{Binding PeakCount, Mode=OneWay}" Width="46"/><DataGridTextColumn Header="15 мин" Binding="{Binding FinalCount, Mode=OneWay}" Width="52"/><DataGridTextColumn Header="+" Binding="{Binding AddedPeak, Mode=OneWay}" Width="38"/><DataGridTextColumn Header="Источник" Binding="{Binding Source, Mode=OneWay}" Width="170"/><DataGridTextColumn Header="Решение" Binding="{Binding Classification, Mode=OneWay}" Width="105"/><DataGridTextColumn Header="Почему" Binding="{Binding Recommendation, Mode=OneWay}" Width="*"/>
                </DataGrid.Columns></DataGrid></Border>
            </TabItem>
            <TabItem Header="Текущий TOP" Style="{StaticResource SubTabItem}">
                <Border Style="{StaticResource R43PageCard}" Margin="0,5,0,0"><DataGrid ItemsSource="{Binding TopProcesses}" AutoGenerateColumns="False" IsReadOnly="True" BorderThickness="0"><DataGrid.Columns><DataGridTextColumn Header="Процесс" Binding="{Binding Name, Mode=OneWay}" Width="120"/><DataGridTextColumn Header="RAM" Binding="{Binding WorkingSetHuman, Mode=OneWay}" Width="70"/><DataGridTextColumn Header="Источник" Binding="{Binding SourceHint, Mode=OneWay}" Width="180"/><DataGridTextColumn Header="Потенциал" Binding="{Binding ReductionPotential, Mode=OneWay}" Width="90"/><DataGridTextColumn Header="Рекомендация" Binding="{Binding PerformanceAdvice, Mode=OneWay}" Width="*"/></DataGrid.Columns></DataGrid></Border>
            </TabItem>
        </TabControl>
    </Grid>
</TabItem>'''
x = x[:m.start()] + process_tab + x[m.end():]
write(xaml_path, x)

(root/'R55_PROCESS_STABILITY.marker').write_text('R55 delayed process stability analyzer integrated\n', encoding='utf-8')
print('R55_PROCESS_STABILITY_PATCH_PASS')
