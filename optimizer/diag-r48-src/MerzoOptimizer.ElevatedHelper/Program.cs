using System.Diagnostics;
using System.IO.Pipes;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;
using MerzoOptimizer.Core.Cleanup;
using MerzoOptimizer.Core.Elevation;
using MerzoOptimizer.Core.Logging;
using MerzoOptimizer.Core.Network;
using MerzoOptimizer.Core.Power;
using MerzoOptimizer.Core.Safety;
using MerzoOptimizer.Core.ScheduledTasks;
using MerzoOptimizer.Core.Services;
using MerzoOptimizer.Core.Snapshots;
using MerzoOptimizer.Core.Tweaks;
using MerzoOptimizer.Windows.Cleanup;
using MerzoOptimizer.Windows.Power;
using MerzoOptimizer.Windows.Restore;
using MerzoOptimizer.Windows.ScheduledTasks;
using MerzoOptimizer.Windows.Services;
using MerzoOptimizer.Windows.Snapshots;
using MerzoOptimizer.Windows.SystemInfo;
using MerzoOptimizer.Windows.Tweaks;

namespace MerzoOptimizer.ElevatedHelper;

internal static class Program
{
    private const string Protocol = "MERZO-ELEVATION/46";
    private const int MaximumRequestChars = 128 * 1024;
    private const string StartupRunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";
    private const string StartupIdPrefix = "startup.disable.";

    private static readonly JsonSerializerOptions JsonOptions = ElevationJson.CreateOptions();

    [STAThread]
    private static async Task<int> Main(string[] args)
    {
        if (!OperatingSystem.IsWindows() || !AdminService.IsAdministrator())
            return 5;

        var pipeName = GetArgument(args, "--pipe");
        var nonce = GetArgument(args, "--nonce");
        var parentText = GetArgument(args, "--parent-pid");
        var snapshotDirectory = DecodeArgument(args, "--snapshot-b64");
        var logDirectory = DecodeArgument(args, "--log-b64");
        var backupDirectory = DecodeArgument(args, "--backup-b64");
        if (string.IsNullOrWhiteSpace(pipeName) || !IsValidNonce(nonce) ||
            !int.TryParse(parentText, out var parentPid) || parentPid <= 0 ||
            string.IsNullOrWhiteSpace(snapshotDirectory) || string.IsNullOrWhiteSpace(logDirectory) || string.IsNullOrWhiteSpace(backupDirectory))
            return 2;

        try
        {
            using var pipe = new NamedPipeClientStream(".", pipeName, PipeDirection.InOut, PipeOptions.Asynchronous);
            using var connectCts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
            await pipe.ConnectAsync(connectCts.Token).ConfigureAwait(false);
            ValidateParentProcess(pipe.SafePipeHandle, parentPid);

            using var reader = new StreamReader(pipe, new UTF8Encoding(false), detectEncodingFromByteOrderMarks: false, bufferSize: 8192, leaveOpen: true);
            using var writer = new StreamWriter(pipe, new UTF8Encoding(false), bufferSize: 8192, leaveOpen: true) { AutoFlush = true };

            await writer.WriteLineAsync($"{Protocol} HELLO {nonce}").ConfigureAwait(false);
            using (var handshakeCts = new CancellationTokenSource(TimeSpan.FromSeconds(5)))
            {
                var ack = await reader.ReadLineAsync(handshakeCts.Token).ConfigureAwait(false);
                if (!string.Equals(ack, $"{Protocol} OK {nonce}", StringComparison.Ordinal))
                    return 11;
            }

            var logger = new JsonLinesAuditLogger(Path.GetFullPath(logDirectory));
            var snapshots = new WindowsSnapshotService(Path.GetFullPath(snapshotDirectory));
            var restore = new WindowsRestoreService(snapshots, logger);
            var tweaks = new WindowsTweakExecutionService(snapshots, restore, new SafetyEngine(), logger);
            var cleanup = new WindowsCleanupService(snapshots, logger, Path.GetFullPath(backupDirectory));
            var services = new WindowsServiceAuditService(snapshots, restore, logger);
            var tasks = new WindowsScheduledTaskAuditService(snapshots, restore, logger);
            var power = new WindowsPowerProfileService(snapshots, restore, logger);
            var tweakCatalog = LoadTweakCatalog();

            while (pipe.IsConnected)
            {
                var line = await reader.ReadLineAsync().ConfigureAwait(false);
                if (line is null) break;
                if (line.Length == 0 || line.Length > MaximumRequestChars)
                {
                    await writer.WriteLineAsync(JsonSerializer.Serialize(new ElevatedOperationResponse
                    {
                        RequestId = "invalid",
                        Success = false,
                        Error = "Elevation request exceeded the safe protocol limit."
                    }, JsonOptions)).ConfigureAwait(false);
                    break;
                }

                ElevatedOperationRequest? request = null;
                ElevatedOperationResponse response;
                try
                {
                    request = JsonSerializer.Deserialize<ElevatedOperationRequest>(line, JsonOptions)
                        ?? throw new InvalidDataException("Elevation request is empty.");
                    ValidateRequestId(request.RequestId);

                    if (request.Kind == ElevatedOperationKind.Shutdown)
                    {
                        response = Success(request.RequestId, new { stopped = true });
                        await writer.WriteLineAsync(JsonSerializer.Serialize(response, JsonOptions)).ConfigureAwait(false);
                        break;
                    }

                    response = await ExecuteAsync(request, tweakCatalog, snapshots, tweaks, cleanup, services, tasks, power, restore, backupDirectory).ConfigureAwait(false);
                }
                catch (Exception ex)
                {
                    response = new ElevatedOperationResponse
                    {
                        RequestId = request?.RequestId ?? "invalid",
                        Success = false,
                        Error = ex.Message
                    };
                }

                await writer.WriteLineAsync(JsonSerializer.Serialize(response, JsonOptions)).ConfigureAwait(false);
            }

            return 0;
        }
        catch
        {
            return 10;
        }
    }

    private static async Task<ElevatedOperationResponse> ExecuteAsync(
        ElevatedOperationRequest request,
        IReadOnlyDictionary<string, TweakDefinition> tweakCatalog,
        WindowsSnapshotService snapshots,
        ITweakExecutionService tweaks,
        ICleanupService cleanup,
        IServiceOptimizationService services,
        IScheduledTaskOptimizationService tasks,
        IPowerProfileService power,
        IRestoreService restore,
        string backupDirectory)
    {
        object result = request.Kind switch
        {
            ElevatedOperationKind.ApplyTweak => await tweaks.ApplyAsync(
                ResolveAllowedTweak(request, tweakCatalog)).ConfigureAwait(false),

            ElevatedOperationKind.CleanCategory => await cleanup.CleanAsync(
                await ValidateCleanupCategoryAsync(cleanup, Require(request.CategoryId, "Cleanup category missing.")).ConfigureAwait(false),
                request.CreateBackup).ConfigureAwait(false),

            ElevatedOperationKind.DisableService => await services.DisableAsync(
                await ValidateServiceAsync(services, Require(request.ServiceName, "Service name missing.")).ConfigureAwait(false)).ConfigureAwait(false),

            ElevatedOperationKind.RestoreService => await RestoreServiceAsync(
                services, snapshots, restore, Require(request.ServiceName, "Service name missing."), tweakCatalog, cleanup, tasks, backupDirectory).ConfigureAwait(false),

            ElevatedOperationKind.DisableScheduledTask => await DisableTaskAsync(
                tasks, Require(request.TaskPath, "Task path missing."), Require(request.TaskName, "Task name missing.")).ConfigureAwait(false),

            ElevatedOperationKind.RestoreScheduledTask => await RestoreTaskAsync(
                tasks, snapshots, restore, Require(request.TaskPath, "Task path missing."), Require(request.TaskName, "Task name missing."), tweakCatalog, cleanup, services, backupDirectory).ConfigureAwait(false),

            ElevatedOperationKind.ActivatePowerScheme => await power.ActivateAsync(
                ValidatePowerTarget(Require(request.PowerTarget, "Power scheme missing.")),
                request.DisplayName ?? request.PowerTarget!).ConfigureAwait(false),

            ElevatedOperationKind.RestorePowerScheme => await RestorePowerAsync(
                snapshots, restore, tweakCatalog, cleanup, services, tasks, backupDirectory).ConfigureAwait(false),

            ElevatedOperationKind.RestoreSnapshot => await RestoreValidatedSnapshotAsync(
                snapshots, restore, request.SnapshotId ?? throw new InvalidDataException("Snapshot id missing."), tweakCatalog, cleanup, services, tasks, backupDirectory).ConfigureAwait(false),

            ElevatedOperationKind.RestoreLatestTweak => await RestoreLatestValidatedAsync(
                snapshots, restore, Require(request.TweakId, "Tweak id missing."), tweakCatalog, cleanup, services, tasks, backupDirectory).ConfigureAwait(false),

            ElevatedOperationKind.RestoreAllActive => await RestoreAllValidatedAsync(
                snapshots, restore, tweakCatalog, cleanup, services, tasks, backupDirectory).ConfigureAwait(false),

            ElevatedOperationKind.NetworkRepair => await ExecuteNetworkRepairAsync(
                Require(request.NetworkAction, "Network repair action missing.")).ConfigureAwait(false),

            _ => throw new NotSupportedException($"Unsupported elevated operation: {request.Kind}")
        };

        return Success(request.RequestId, result);
    }

    private static IReadOnlyDictionary<string, TweakDefinition> LoadTweakCatalog()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "data", "tweaks.json");
        var items = TweakCatalogLoader.Load(path);
        if (items.Count == 0)
            throw new InvalidDataException("Official tweak catalog is missing; elevated mutations are blocked.");
        return items.ToDictionary(static x => x.Id, StringComparer.OrdinalIgnoreCase);
    }

    private static TweakDefinition ResolveAllowedTweak(ElevatedOperationRequest request, IReadOnlyDictionary<string, TweakDefinition> catalog)
    {
        var id = request.TweakId ?? request.Tweak?.Id ?? string.Empty;
        if (catalog.TryGetValue(id, out var official))
        {
            if (!official.RequiresAdmin || official.ScanOnly)
                throw new InvalidDataException("Tweak is not eligible for elevated mutation.");
            return official;
        }

        if (request.Tweak is not null && ValidateStartupDynamicTweak(request.Tweak))
            return request.Tweak;

        throw new InvalidDataException("Tweak is not present in the official allow-list.");
    }

    private static bool ValidateStartupDynamicTweak(TweakDefinition tweak)
    {
        if (!tweak.RequiresAdmin || tweak.ScanOnly || tweak.Risk != TweakRisk.Safe || tweak.RegistryActions.Count != 1)
            return false;
        var action = tweak.RegistryActions[0];
        if (action.Mode != RegistryTweakActionMode.DeleteValue || action.Hive != RegistryHiveScope.LocalMachine ||
            !string.Equals(action.KeyPath, StartupRunKey, StringComparison.OrdinalIgnoreCase) ||
            string.IsNullOrWhiteSpace(action.ValueName) || action.ValueName.Length > 260)
            return false;
        return string.Equals(tweak.Id, BuildStartupId(action.Hive, action.KeyPath, action.ValueName), StringComparison.OrdinalIgnoreCase);
    }

    private static async Task<string> ValidateCleanupCategoryAsync(ICleanupService cleanup, string categoryId)
    {
        var category = (await cleanup.ScanAsync().ConfigureAwait(false)).FirstOrDefault(x => string.Equals(x.Id, categoryId, StringComparison.OrdinalIgnoreCase));
        if (category is null || !category.RequiresAdmin)
            throw new InvalidDataException("Cleanup category is not allow-listed for elevated mutation.");
        return category.Id;
    }

    private static async Task<string> ValidateServiceAsync(IServiceOptimizationService services, string serviceName)
    {
        var item = (await services.ScanAsync().ConfigureAwait(false)).FirstOrDefault(x =>
            string.Equals(x.ServiceName, serviceName, StringComparison.OrdinalIgnoreCase) && x.CanManage);
        if (item is null)
            throw new InvalidDataException("Service is not allow-listed for elevated mutation.");
        return item.ServiceName;
    }

    private static async Task<string> ValidateKnownServiceAsync(IServiceOptimizationService services, string serviceName)
    {
        var item = (await services.ScanAsync().ConfigureAwait(false)).FirstOrDefault(x =>
            string.Equals(x.ServiceName, serviceName, StringComparison.OrdinalIgnoreCase));
        if (item is null)
            throw new InvalidDataException("Service snapshot target is not present in the official catalog.");
        return item.ServiceName;
    }

    private static async Task<ScheduledTaskOperationResult> DisableTaskAsync(IScheduledTaskOptimizationService tasks, string path, string name)
    {
        await ValidateTaskAsync(tasks, path, name).ConfigureAwait(false);
        return await tasks.DisableAsync(path, name).ConfigureAwait(false);
    }

    private static async Task ValidateTaskAsync(IScheduledTaskOptimizationService tasks, string path, string name)
    {
        var item = (await tasks.ScanAsync().ConfigureAwait(false)).FirstOrDefault(x =>
            string.Equals(x.Path, path, StringComparison.OrdinalIgnoreCase) &&
            string.Equals(x.Name, name, StringComparison.OrdinalIgnoreCase) && x.CanManage);
        if (item is null)
            throw new InvalidDataException("Scheduled Task is not allow-listed for elevated mutation.");
    }

    private static async Task ValidateKnownTaskAsync(IScheduledTaskOptimizationService tasks, string path, string name)
    {
        var item = (await tasks.ScanAsync().ConfigureAwait(false)).FirstOrDefault(x =>
            string.Equals(x.Path, path, StringComparison.OrdinalIgnoreCase) &&
            string.Equals(x.Name, name, StringComparison.OrdinalIgnoreCase));
        if (item is null)
            throw new InvalidDataException("Scheduled Task snapshot target is not present in the official catalog.");
    }

    private static string ValidatePowerTarget(string target) => target.ToUpperInvariant() switch
    {
        "SCHEME_BALANCED" => "SCHEME_BALANCED",
        "SCHEME_MIN" => "SCHEME_MIN",
        _ => throw new InvalidDataException("Power target is not allow-listed.")
    };

    private static async Task<ServiceOperationResult> RestoreServiceAsync(
        IServiceOptimizationService services, WindowsSnapshotService snapshots, IRestoreService restore, string serviceName,
        IReadOnlyDictionary<string, TweakDefinition> tweaks, ICleanupService cleanup, IScheduledTaskOptimizationService tasks, string backupDirectory)
    {
        await ValidateKnownServiceAsync(services, serviceName).ConfigureAwait(false);
        var id = $"service.{serviceName}";
        var result = await RestoreLatestValidatedAsync(snapshots, restore, id, tweaks, cleanup, services, tasks, backupDirectory).ConfigureAwait(false);
        return new ServiceOperationResult { Success = result.Success, Changed = result.Changed, SnapshotId = result.SnapshotId, Message = result.Message };
    }

    private static async Task<ScheduledTaskOperationResult> RestoreTaskAsync(
        IScheduledTaskOptimizationService taskService, WindowsSnapshotService snapshots, IRestoreService restore, string path, string name,
        IReadOnlyDictionary<string, TweakDefinition> tweaks, ICleanupService cleanup, IServiceOptimizationService services, string backupDirectory)
    {
        await ValidateKnownTaskAsync(taskService, path, name).ConfigureAwait(false);
        var id = $"task.{NormalizeTaskId(path)}.{NormalizeTaskId(name)}";
        var result = await RestoreLatestValidatedAsync(snapshots, restore, id, tweaks, cleanup, services, taskService, backupDirectory).ConfigureAwait(false);
        return new ScheduledTaskOperationResult { Success = result.Success, Changed = result.Changed, SnapshotId = result.SnapshotId, Message = result.Message };
    }

    private static async Task<PowerOperationResult> RestorePowerAsync(
        WindowsSnapshotService snapshots, IRestoreService restore, IReadOnlyDictionary<string, TweakDefinition> tweaks,
        ICleanupService cleanup, IServiceOptimizationService services, IScheduledTaskOptimizationService tasks, string backupDirectory)
    {
        var result = await RestoreLatestValidatedAsync(snapshots, restore, "power.profile", tweaks, cleanup, services, tasks, backupDirectory).ConfigureAwait(false);
        return new PowerOperationResult { Success = result.Success, Changed = result.Changed, SnapshotId = result.SnapshotId, Message = result.Message };
    }

    private static async Task<RestoreResult> RestoreValidatedSnapshotAsync(
        WindowsSnapshotService snapshots, IRestoreService restore, Guid id, IReadOnlyDictionary<string, TweakDefinition> tweaks,
        ICleanupService cleanup, IServiceOptimizationService services, IScheduledTaskOptimizationService tasks, string backupDirectory)
    {
        var snapshot = await snapshots.GetAsync(id).ConfigureAwait(false) ?? throw new InvalidDataException("Snapshot not found.");
        await ValidateSnapshotAsync(snapshot, tweaks, cleanup, services, tasks, backupDirectory).ConfigureAwait(false);
        return await restore.RestoreAsync(id).ConfigureAwait(false);
    }

    private static async Task<RestoreResult> RestoreLatestValidatedAsync(
        WindowsSnapshotService snapshots, IRestoreService restore, string tweakId, IReadOnlyDictionary<string, TweakDefinition> tweaks,
        ICleanupService cleanup, IServiceOptimizationService services, IScheduledTaskOptimizationService tasks, string backupDirectory)
    {
        var snapshot = await snapshots.GetLatestActiveForTweakAsync(tweakId).ConfigureAwait(false);
        if (snapshot is null)
            return new RestoreResult { Success = true, Changed = false, Message = "Для этого действия нет активного snapshot." };
        await ValidateSnapshotAsync(snapshot, tweaks, cleanup, services, tasks, backupDirectory).ConfigureAwait(false);
        return await restore.RestoreAsync(snapshot.Id).ConfigureAwait(false);
    }

    private static async Task<RestoreResult> RestoreAllValidatedAsync(
        WindowsSnapshotService snapshots, IRestoreService restore, IReadOnlyDictionary<string, TweakDefinition> tweaks,
        ICleanupService cleanup, IServiceOptimizationService services, IScheduledTaskOptimizationService tasks, string backupDirectory)
    {
        var active = (await snapshots.ListAsync().ConfigureAwait(false)).Where(static x => !x.IsRestored).ToArray();
        foreach (var snapshot in active)
            await ValidateSnapshotAsync(snapshot, tweaks, cleanup, services, tasks, backupDirectory).ConfigureAwait(false);
        return await restore.RestoreAllActiveAsync().ConfigureAwait(false);
    }

    private static async Task ValidateSnapshotAsync(
        ChangeSnapshot snapshot, IReadOnlyDictionary<string, TweakDefinition> tweaks, ICleanupService cleanup,
        IServiceOptimizationService services, IScheduledTaskOptimizationService tasks, string backupDirectory)
    {
        var payloadKinds = (snapshot.RegistryValues.Count > 0 ? 1 : 0) +
                           (snapshot.CleanupArchive is not null ? 1 : 0) +
                           (snapshot.ServiceState is not null ? 1 : 0) +
                           (snapshot.ScheduledTaskState is not null ? 1 : 0) +
                           (snapshot.PowerSchemeState is not null ? 1 : 0);
        if (payloadKinds != 1 || string.IsNullOrWhiteSpace(snapshot.TweakId))
            throw new InvalidDataException("Snapshot structure is not trusted for elevated restore.");

        if (snapshot.RegistryValues.Count > 0)
        {
            if (tweaks.TryGetValue(snapshot.TweakId, out var tweak))
            {
                foreach (var entry in snapshot.RegistryValues)
                {
                    if (!tweak.RegistryActions.Any(a => a.Hive == entry.Hive &&
                        string.Equals(a.KeyPath, entry.KeyPath, StringComparison.OrdinalIgnoreCase) &&
                        string.Equals(a.ValueName, entry.ValueName, StringComparison.OrdinalIgnoreCase)))
                        throw new InvalidDataException("Snapshot registry target is outside the official tweak allow-list.");
                }
                return;
            }

            if (snapshot.TweakId.StartsWith(StartupIdPrefix, StringComparison.OrdinalIgnoreCase) && snapshot.RegistryValues.Count == 1)
            {
                var entry = snapshot.RegistryValues[0];
                if (!string.Equals(entry.KeyPath, StartupRunKey, StringComparison.OrdinalIgnoreCase) ||
                    string.IsNullOrWhiteSpace(entry.ValueName) || entry.ValueName.Length > 260 ||
                    !string.Equals(snapshot.TweakId, BuildStartupId(entry.Hive, entry.KeyPath, entry.ValueName), StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException("Startup snapshot failed allow-list validation.");
                return;
            }

            throw new InvalidDataException("Snapshot tweak id is not present in the official allow-list.");
        }

        if (snapshot.ServiceState is not null)
        {
            await ValidateKnownServiceAsync(services, snapshot.ServiceState.ServiceName).ConfigureAwait(false);
            if (!string.Equals(snapshot.TweakId, $"service.{snapshot.ServiceState.ServiceName}", StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Service snapshot id mismatch.");
            return;
        }

        if (snapshot.ScheduledTaskState is not null)
        {
            await ValidateKnownTaskAsync(tasks, snapshot.ScheduledTaskState.TaskPath, snapshot.ScheduledTaskState.TaskName).ConfigureAwait(false);
            var expected = $"task.{NormalizeTaskId(snapshot.ScheduledTaskState.TaskPath)}.{NormalizeTaskId(snapshot.ScheduledTaskState.TaskName)}";
            if (!string.Equals(snapshot.TweakId, expected, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Scheduled Task snapshot id mismatch.");
            return;
        }

        if (snapshot.PowerSchemeState is not null)
        {
            if (!string.Equals(snapshot.TweakId, "power.profile", StringComparison.OrdinalIgnoreCase) ||
                !Guid.TryParse(snapshot.PowerSchemeState.ActiveSchemeGuid, out _))
                throw new InvalidDataException("Power snapshot failed validation.");
            return;
        }

        if (snapshot.CleanupArchive is not null)
        {
            var categories = await cleanup.ScanAsync().ConfigureAwait(false);
            var category = categories.FirstOrDefault(x => string.Equals(x.Id, snapshot.CleanupArchive.CategoryId, StringComparison.OrdinalIgnoreCase));
            if (category is null || !string.Equals(snapshot.TweakId, $"cleanup.{category.Id}", StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Cleanup snapshot category failed validation.");

            var canonicalBackup = Path.GetFullPath(snapshot.CleanupArchive.ArchivePath);
            if (!IsPathInsideDirectory(canonicalBackup, Path.GetFullPath(backupDirectory)))
                throw new InvalidDataException("Cleanup archive is outside the Merzo backup directory.");
            foreach (var file in snapshot.CleanupArchive.Files)
            {
                if (!IsPathInsideDirectory(Path.GetFullPath(file.OriginalPath), Path.GetFullPath(category.RootPath)) ||
                    string.IsNullOrWhiteSpace(file.ArchiveEntryName) || file.ArchiveEntryName.Contains("..", StringComparison.Ordinal))
                    throw new InvalidDataException("Cleanup snapshot contains a path outside its allow-listed root.");
            }
            return;
        }

        throw new InvalidDataException("Snapshot type is unsupported for elevated restore.");
    }

    private static string BuildStartupId(RegistryHiveScope hive, string keyPath, string valueName)
    {
        var raw = $"{hive}|{keyPath}|{valueName}";
        var hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(raw))).ToLowerInvariant()[..12];
        return $"{StartupIdPrefix}{hash}";
    }

    private static string NormalizeTaskId(string value)
    {
        var chars = value.Where(char.IsLetterOrDigit).Select(char.ToLowerInvariant).ToArray();
        return chars.Length == 0 ? "item" : new string(chars);
    }

    private static bool IsPathInsideDirectory(string path, string directory)
    {
        var relative = Path.GetRelativePath(Path.GetFullPath(directory), Path.GetFullPath(path));
        return !Path.IsPathRooted(relative) && !relative.Equals("..", StringComparison.Ordinal) &&
               !relative.StartsWith(".." + Path.DirectorySeparatorChar, StringComparison.Ordinal);
    }

    private static void ValidateRequestId(string requestId)
    {
        if (requestId.Length != 32 || !Guid.TryParseExact(requestId, "N", out _))
            throw new InvalidDataException("Invalid elevation request id.");
    }

    private static bool IsValidNonce(string? value) =>
        value is { Length: 64 } && value.All(Uri.IsHexDigit);

    private static void ValidateParentProcess(SafePipeHandle pipeHandle, int expectedParentPid)
    {
        if (!GetNamedPipeServerProcessId(pipeHandle, out var serverPid) || serverPid != (uint)expectedParentPid)
            throw new InvalidDataException("Named pipe server PID did not match the launching application.");

        using var parent = Process.GetProcessById(expectedParentPid);
        var parentPath = parent.MainModule?.FileName;
        if (string.IsNullOrWhiteSpace(parentPath) || !Path.GetFileName(parentPath).Equals("MerzoWindowsOptimizer.exe", StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("UAC-helper parent executable identity is invalid.");

        var expectedBesideHelper = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "MerzoWindowsOptimizer.exe"));
        if (File.Exists(expectedBesideHelper) && !Path.GetFullPath(parentPath).Equals(expectedBesideHelper, StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("UAC-helper was not started by the Merzo executable beside it.");

        var helperPath = Environment.ProcessPath ?? throw new InvalidDataException("Helper executable path is unavailable.");
        var parentVersion = FileVersionInfo.GetVersionInfo(parentPath).FileVersion ?? string.Empty;
        var helperVersion = FileVersionInfo.GetVersionInfo(helperPath).FileVersion ?? string.Empty;
        if (string.IsNullOrWhiteSpace(parentVersion) || !string.Equals(parentVersion, helperVersion, StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Main EXE and UAC-helper versions do not match.");
    }

    private static async Task<NetworkRepairResult> ExecuteNetworkRepairAsync(string action)
    {
        var normalized = action.Trim().ToLowerInvariant();
        if (normalized is "gaming_network_safe" or "gaming_network_extreme" or "restore_gaming_network")
            return await ExecuteGamingNetworkPresetAsync(normalized).ConfigureAwait(false);

        var (fileName, arguments, rebootRequired, successMessage) = normalized switch
        {
            "flush_dns" => ("ipconfig.exe", "/flushdns", false, "DNS-кэш Windows очищен."),
            "renew_dhcp" => ("ipconfig.exe", "/renew", false, "DHCP-аренда обновлена."),
            "reset_winsock" => ("netsh.exe", "winsock reset", true, "Winsock сброшен. Для полного применения рекомендуется перезагрузка."),
            "reset_tcpip" => ("netsh.exe", "int ip reset", true, "TCP/IP стек сброшен. Для полного применения рекомендуется перезагрузка."),
            _ => throw new NotSupportedException($"Network repair action is not allow-listed: {action}")
        };

        var psi = new ProcessStartInfo
        {
            FileName = fileName,
            Arguments = arguments,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        using var process = Process.Start(psi) ?? throw new InvalidOperationException($"Не удалось запустить {fileName}.");
        var outputTask = process.StandardOutput.ReadToEndAsync();
        var errorTask = process.StandardError.ReadToEndAsync();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(normalized == "renew_dhcp" ? 35 : 20));
        try
        {
            await process.WaitForExitAsync(timeout.Token).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            try { process.Kill(entireProcessTree: true); } catch { }
            return new NetworkRepairResult(false, $"Команда {action} превысила безопасный таймаут.", rebootRequired, -1);
        }
        var output = (await outputTask.ConfigureAwait(false)).Trim();
        var error = (await errorTask.ConfigureAwait(false)).Trim();
        if (process.ExitCode != 0)
        {
            var detail = string.IsNullOrWhiteSpace(error) ? output : error;
            if (detail.Length > 280) detail = detail[..280] + "…";
            return new NetworkRepairResult(false, $"Windows вернула код {process.ExitCode}. {detail}", rebootRequired, process.ExitCode);
        }
        return new NetworkRepairResult(true, successMessage, rebootRequired, process.ExitCode);
    }

    private static async Task<NetworkRepairResult> ExecuteGamingNetworkPresetAsync(string action)
    {
        var baseline = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MerzoWindowsOptimizer", "network-gaming-baseline.json");
        Directory.CreateDirectory(Path.GetDirectoryName(baseline)!);
        var baselinePs = baseline.Replace("'", "''", StringComparison.Ordinal);

        string script;
        string successMessage;
        if (action == "gaming_network_safe")
        {
            script = """
$ErrorActionPreference='Stop'
netsh int tcp set global rss=enabled | Out-Null
netsh int tcp set global autotuninglevel=normal | Out-Null
$a=Get-NetAdapter | Where-Object {$_.Status -eq 'Up' -and $_.HardwareInterface} | Sort-Object LinkSpeed -Descending | Select-Object -First 1
if($a){ try { Set-NetAdapterRss -Name $a.Name -Enabled $true -NoRestart -ErrorAction Stop } catch {} }
Write-Output 'RSS включён; TCP Auto-Tuning установлен Normal. Адаптер не перезапускался.'
""";
            successMessage = "Gaming Network SAFE применён: RSS включён, TCP Auto-Tuning = Normal. Соединение не перезапускалось.";
        }
        else if (action == "gaming_network_extreme")
        {
            script = $$"""
$ErrorActionPreference='Stop'
$a=Get-NetAdapter | Where-Object {$_.Status -eq 'Up' -and $_.HardwareInterface} | Sort-Object LinkSpeed -Descending | Select-Object -First 1
if(-not $a){ throw 'Активный аппаратный сетевой адаптер не найден.' }
$rss=Get-NetAdapterRss -Name $a.Name -ErrorAction SilentlyContinue
$rsc=Get-NetAdapterRsc -Name $a.Name -ErrorAction SilentlyContinue
$pm=Get-NetAdapterPowerManagement -Name $a.Name -ErrorAction SilentlyContinue
$im=Get-NetAdapterAdvancedProperty -Name $a.Name -AllProperties -ErrorAction SilentlyContinue | Where-Object {$_.RegistryKeyword -match 'InterruptModeration'} | Select-Object -First 1
[pscustomobject]@{
 Name=$a.Name
 RssEnabled=if($rss){[bool]$rss.Enabled}else{$null}
 RscIPv4=if($rsc){[bool]$rsc.IPv4Enabled}else{$null}
 RscIPv6=if($rsc){[bool]$rsc.IPv6Enabled}else{$null}
 SelectiveSuspend=if($pm){[string]$pm.SelectiveSuspend}else{$null}
 DeviceSleepOnDisconnect=if($pm){[string]$pm.DeviceSleepOnDisconnect}else{$null}
 InterruptDisplayName=if($im){[string]$im.DisplayName}else{$null}
 InterruptDisplayValue=if($im){[string]$im.DisplayValue}else{$null}
} | ConvertTo-Json | Set-Content -LiteralPath '{{baselinePs}}' -Encoding UTF8
$applied=0
netsh int tcp set global rss=enabled | Out-Null; $applied++
netsh int tcp set global autotuninglevel=normal | Out-Null; $applied++
try { Set-NetAdapterRss -Name $a.Name -Enabled $true -NoRestart -ErrorAction Stop; $applied++ } catch {}
try { Disable-NetAdapterRsc -Name $a.Name -NoRestart -ErrorAction Stop; $applied++ } catch {}
try { Disable-NetAdapterPowerManagement -Name $a.Name -SelectiveSuspend -DeviceSleepOnDisconnect -NoRestart -ErrorAction Stop; $applied++ } catch {}
if($im){ try { Set-NetAdapterAdvancedProperty -Name $a.Name -RegistryKeyword $im.RegistryKeyword -RegistryValue 0 -NoRestart -ErrorAction Stop; $applied++ } catch {} }
Write-Output ("EXTREME applied="+$applied+" adapter="+$a.Name+". Baseline saved. No adapter restart was forced.")
""";
            successMessage = "Gaming Network EXTREME применён. Сохранён baseline адаптера; RSS/Auto-Tuning нормализованы, а поддерживаемые low-latency параметры применены без принудительного перезапуска адаптера.";
        }
        else
        {
            script = $$"""
$ErrorActionPreference='Stop'
if(-not (Test-Path -LiteralPath '{{baselinePs}}')){ throw 'Baseline Gaming Network не найден. Сначала примените EXTREME.' }
$b=Get-Content -LiteralPath '{{baselinePs}}' -Raw | ConvertFrom-Json
$a=Get-NetAdapter -Name $b.Name -ErrorAction Stop
if($null -ne $b.RssEnabled){ try { Set-NetAdapterRss -Name $a.Name -Enabled ([bool]$b.RssEnabled) -NoRestart -ErrorAction Stop } catch {} }
if($null -ne $b.RscIPv4 -or $null -ne $b.RscIPv6){
 try { Set-NetAdapterRsc -Name $a.Name -IPv4Enabled ([bool]$b.RscIPv4) -IPv6Enabled ([bool]$b.RscIPv6) -NoRestart -ErrorAction Stop } catch {}
}
if($b.SelectiveSuspend -or $b.DeviceSleepOnDisconnect){
 try { Set-NetAdapterPowerManagement -Name $a.Name -SelectiveSuspend $b.SelectiveSuspend -DeviceSleepOnDisconnect $b.DeviceSleepOnDisconnect -NoRestart -ErrorAction Stop } catch {}
}
if($b.InterruptDisplayName -and $b.InterruptDisplayValue){
 try { Set-NetAdapterAdvancedProperty -Name $a.Name -DisplayName $b.InterruptDisplayName -DisplayValue $b.InterruptDisplayValue -NoRestart -ErrorAction Stop } catch {}
}
netsh int tcp set global rss=enabled | Out-Null
netsh int tcp set global autotuninglevel=normal | Out-Null
Remove-Item -LiteralPath '{{baselinePs}}' -Force -ErrorAction SilentlyContinue
Write-Output ('Gaming Network baseline restored for '+$a.Name+'. TCP defaults left at RSS enabled / Auto-Tuning Normal.')
""";
            successMessage = "Gaming Network baseline восстановлен для адаптера. TCP оставлен в рекомендуемом состоянии RSS Enabled / Auto-Tuning Normal.";
        }

        var encoded = Convert.ToBase64String(Encoding.Unicode.GetBytes(script));
        var psi = new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = $"-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand {encoded}",
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        using var process = Process.Start(psi) ?? throw new InvalidOperationException("Не удалось запустить Windows PowerShell для Gaming Network.");
        var outputTask = process.StandardOutput.ReadToEndAsync();
        var errorTask = process.StandardError.ReadToEndAsync();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(40));
        try
        {
            await process.WaitForExitAsync(timeout.Token).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            try { process.Kill(entireProcessTree: true); } catch { }
            return new NetworkRepairResult(false, "Gaming Network превысил безопасный таймаут 40 секунд.", false, -1);
        }
        var output = (await outputTask.ConfigureAwait(false)).Trim();
        var error = (await errorTask.ConfigureAwait(false)).Trim();
        if (process.ExitCode != 0)
        {
            var detail = string.IsNullOrWhiteSpace(error) ? output : error;
            if (detail.Length > 500) detail = detail[..500] + "…";
            return new NetworkRepairResult(false, $"Gaming Network: Windows вернула код {process.ExitCode}. {detail}", false, process.ExitCode);
        }
        var suffix = string.IsNullOrWhiteSpace(output) ? string.Empty : $"\n{output}";
        return new NetworkRepairResult(true, successMessage + suffix, false, process.ExitCode);
    }

    private static ElevatedOperationResponse Success(string requestId, object result) => new()
    {
        RequestId = requestId,
        Success = true,
        ResultJson = JsonSerializer.Serialize(result, result.GetType(), JsonOptions)
    };

    private static string Require(string? value, string error) => !string.IsNullOrWhiteSpace(value) ? value : throw new InvalidDataException(error);

    private static string? DecodeArgument(string[] args, string name)
    {
        var encoded = GetArgument(args, name);
        if (string.IsNullOrWhiteSpace(encoded)) return null;
        try { return Encoding.UTF8.GetString(Convert.FromBase64String(encoded)); }
        catch (FormatException) { return null; }
    }

    private static string? GetArgument(string[] args, string name)
    {
        for (var i = 0; i < args.Length - 1; i++)
            if (string.Equals(args[i], name, StringComparison.OrdinalIgnoreCase))
                return args[i + 1];
        return null;
    }

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetNamedPipeServerProcessId(SafePipeHandle Pipe, out uint ServerProcessId);
}
