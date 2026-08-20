from pathlib import Path
import os

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8')
def replace_once(s,old,new,label):
    c=s.count(old)
    if c!=1: raise SystemExit(f'R49 {label} anchor count={c}')
    return s.replace(old,new,1)

# ---- Core elevation protocol: add only two fixed, allow-listed operation kinds. ----
core=root/'src'/'MerzoOptimizer.Core'/'Elevation'/'ElevationModels.cs'
s=read(core)
s=replace_once(s,
'''    RestoreAllActive,\n    NetworkRepair,\n    Shutdown''',
'''    RestoreAllActive,\n    NetworkRepair,\n    CreateSystemRestorePoint,\n    UninstallOneDrive,\n    Shutdown''',
'elevation enum')
write(core,s)

# ---- Recovery Package service. No arbitrary command execution is exposed to the UI. ----
recovery=root/'src'/'MerzoOptimizer.Windows'/'Recovery'/'WindowsRecoveryPackageService.cs'
write(recovery,r'''using System.Text.Json;
using MerzoOptimizer.Core.Elevation;
using MerzoOptimizer.Core.Logging;
using MerzoOptimizer.Windows.Elevation;

namespace MerzoOptimizer.Windows.Recovery;

public sealed record RecoveryPackageResult(
    bool Success,
    string PackageId,
    string PackageDirectory,
    bool SystemRestorePointReady,
    string Message);

public interface IRecoveryPackageService
{
    Task<RecoveryPackageResult> CreateAsync(string profileName, IReadOnlyCollection<string> plannedOperations, CancellationToken cancellationToken = default);
    Task CompleteAsync(string packageId, IReadOnlyCollection<Guid> snapshotIds, bool networkBaselineUsed, string? note = null, CancellationToken cancellationToken = default);
}

public sealed class WindowsRecoveryPackageService : IRecoveryPackageService
{
    private readonly ElevatedOperationBroker _broker;
    private readonly string _root;
    private readonly IAuditLogger _logger;

    public WindowsRecoveryPackageService(ElevatedOperationBroker broker, string root, IAuditLogger logger)
    {
        _broker = broker;
        _root = Path.GetFullPath(root);
        _logger = logger;
        Directory.CreateDirectory(_root);
    }

    public async Task<RecoveryPackageResult> CreateAsync(string profileName, IReadOnlyCollection<string> plannedOperations, CancellationToken cancellationToken = default)
    {
        var safeProfile = NormalizeProfile(profileName);
        var packageId = $"{DateTimeOffset.Now:yyyyMMdd-HHmmss}-{Guid.NewGuid():N}";
        var directory = Path.Combine(_root, packageId);
        Directory.CreateDirectory(directory);
        var manifestPath = Path.Combine(directory, "manifest.json");

        await WriteJsonAsync(manifestPath, new
        {
            schema = 1,
            packageId,
            createdAt = DateTimeOffset.Now,
            profile = safeProfile,
            computer = Environment.MachineName,
            os = Environment.OSVersion.VersionString,
            appVersion = typeof(WindowsRecoveryPackageService).Assembly.GetName().Version?.ToString() ?? "unknown",
            plannedOperations = plannedOperations.OrderBy(static x => x, StringComparer.OrdinalIgnoreCase).ToArray(),
            systemRestorePoint = "creating",
            status = "preparing"
        }, cancellationToken).ConfigureAwait(false);

        try
        {
            var description = $"Merzo Windows Optimizer {safeProfile}";
            var result = await _broker.ExecuteAsync<JsonElement>(new ElevatedOperationRequest
            {
                RequestId = Guid.NewGuid().ToString("N"),
                Kind = ElevatedOperationKind.CreateSystemRestorePoint,
                DisplayName = description
            }, cancellationToken).ConfigureAwait(false);

            var ready = result.TryGetProperty("ready", out var readyEl) && readyEl.ValueKind == JsonValueKind.True;
            var message = result.TryGetProperty("message", out var msgEl) ? msgEl.GetString() ?? "System Restore result received." : "System Restore result received.";
            if (!ready)
                throw new InvalidOperationException(message);

            await WriteJsonAsync(manifestPath, new
            {
                schema = 1,
                packageId,
                createdAt = DateTimeOffset.Now,
                profile = safeProfile,
                computer = Environment.MachineName,
                os = Environment.OSVersion.VersionString,
                appVersion = typeof(WindowsRecoveryPackageService).Assembly.GetName().Version?.ToString() ?? "unknown",
                plannedOperations = plannedOperations.OrderBy(static x => x, StringComparer.OrdinalIgnoreCase).ToArray(),
                systemRestorePoint = "ready",
                systemRestoreMessage = message,
                status = "ready"
            }, cancellationToken).ConfigureAwait(false);

            await _logger.WriteAsync(new AuditLogEntry
            {
                Category = "Recovery",
                Action = $"Recovery Package {safeProfile}",
                Status = "Success",
                Details = $"Package {packageId}; System Restore ready; {message}"
            }, cancellationToken).ConfigureAwait(false);

            return new RecoveryPackageResult(true, packageId, directory, true, $"Recovery Package готов: {message}");
        }
        catch (Exception ex)
        {
            try
            {
                await WriteJsonAsync(manifestPath, new
                {
                    schema = 1,
                    packageId,
                    createdAt = DateTimeOffset.Now,
                    profile = safeProfile,
                    plannedOperations = plannedOperations.ToArray(),
                    systemRestorePoint = "failed",
                    status = "failed",
                    error = ex.Message
                }, CancellationToken.None).ConfigureAwait(false);
            }
            catch { }

            await _logger.WriteAsync(new AuditLogEntry
            {
                Category = "Recovery",
                Action = $"Recovery Package {safeProfile}",
                Status = "Error",
                Details = ex.ToString()
            }, CancellationToken.None).ConfigureAwait(false);

            return new RecoveryPackageResult(false, packageId, directory, false, $"Recovery Package не создан: {ex.Message}");
        }
    }

    public async Task CompleteAsync(string packageId, IReadOnlyCollection<Guid> snapshotIds, bool networkBaselineUsed, string? note = null, CancellationToken cancellationToken = default)
    {
        ValidatePackageId(packageId);
        var directory = Path.Combine(_root, packageId);
        if (!Directory.Exists(directory))
            throw new DirectoryNotFoundException("Recovery Package directory not found.");

        await WriteJsonAsync(Path.Combine(directory, "completion.json"), new
        {
            schema = 1,
            packageId,
            completedAt = DateTimeOffset.Now,
            snapshots = snapshotIds.Select(static x => x.ToString("D")).ToArray(),
            networkBaselineUsed,
            note = note ?? string.Empty,
            status = "completed"
        }, cancellationToken).ConfigureAwait(false);
    }

    private static string NormalizeProfile(string value)
    {
        var normalized = (value ?? string.Empty).Trim().ToUpperInvariant();
        return normalized switch
        {
            "LIGHT" or "ЛАЙТ" => "LIGHT",
            "GAME" => "GAME",
            "EXTREME" => "EXTREME",
            "ONEDRIVE" => "ONEDRIVE",
            _ => throw new InvalidDataException("Recovery Package profile is not allow-listed.")
        };
    }

    private static void ValidatePackageId(string value)
    {
        if (string.IsNullOrWhiteSpace(value) || value.Length > 80 || value.Any(ch => !(char.IsLetterOrDigit(ch) || ch is '-' or '_')))
            throw new InvalidDataException("Recovery Package id is invalid.");
    }

    private static Task WriteJsonAsync(string path, object payload, CancellationToken cancellationToken) =>
        File.WriteAllTextAsync(path, JsonSerializer.Serialize(payload, new JsonSerializerOptions { WriteIndented = true }), cancellationToken);
}
''')

# ---- Known OneDrive manager. It inspects account state and never deletes user folders. ----
onedrive=root/'src'/'MerzoOptimizer.Windows'/'OneDrive'/'WindowsOneDriveOptimizationService.cs'
write(onedrive,r'''using System.Diagnostics;
using System.Text.Json;
using Microsoft.Win32;
using MerzoOptimizer.Core.Elevation;
using MerzoOptimizer.Windows.Elevation;

namespace MerzoOptimizer.Windows.OneDrive;

public sealed record OneDriveStatus(bool Installed, bool Configured, bool Running, string Summary);
public sealed record OneDriveOperationResult(bool Success, bool Changed, string Message);

public interface IOneDriveOptimizationService
{
    Task<OneDriveStatus> InspectAsync(CancellationToken cancellationToken = default);
    Task<OneDriveOperationResult> UninstallAsync(CancellationToken cancellationToken = default);
}

public sealed class WindowsOneDriveOptimizationService : IOneDriveOptimizationService
{
    private readonly ElevatedOperationBroker _broker;

    public WindowsOneDriveOptimizationService(ElevatedOperationBroker broker) => _broker = broker;

    public Task<OneDriveStatus> InspectAsync(CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var installed = KnownInstallPaths().Any(File.Exists) || Process.GetProcessesByName("OneDrive").Length > 0;
        var running = Process.GetProcessesByName("OneDrive").Any(static p =>
        {
            try { p.Dispose(); return true; } catch { return true; }
        });
        var configured = HasConfiguredAccount();
        var summary = !installed
            ? "OneDrive не установлен."
            : configured
                ? "OneDrive установлен и найден настроенный аккаунт/папка синхронизации."
                : "OneDrive установлен, но настроенный аккаунт синхронизации не обнаружен.";
        return Task.FromResult(new OneDriveStatus(installed, configured, running, summary));
    }

    public async Task<OneDriveOperationResult> UninstallAsync(CancellationToken cancellationToken = default)
    {
        var before = await InspectAsync(cancellationToken).ConfigureAwait(false);
        if (!before.Installed)
            return new OneDriveOperationResult(true, false, "OneDrive уже отсутствует.");

        var result = await _broker.ExecuteAsync<JsonElement>(new ElevatedOperationRequest
        {
            RequestId = Guid.NewGuid().ToString("N"),
            Kind = ElevatedOperationKind.UninstallOneDrive
        }, cancellationToken).ConfigureAwait(false);
        var changed = result.TryGetProperty("uninstalled", out var changedEl) && changedEl.ValueKind == JsonValueKind.True;
        var message = result.TryGetProperty("message", out var msgEl) ? msgEl.GetString() ?? "OneDrive uninstall completed." : "OneDrive uninstall completed.";
        return new OneDriveOperationResult(true, changed, message);
    }

    private static bool HasConfiguredAccount()
    {
        try
        {
            using var accounts = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\OneDrive\Accounts", writable: false);
            if (accounts is not null)
            {
                foreach (var name in accounts.GetSubKeyNames())
                {
                    using var account = accounts.OpenSubKey(name, writable: false);
                    if (account is null) continue;
                    foreach (var valueName in new[] { "UserEmail", "UserFolder", "ConfiguredTenantId", "cid" })
                    {
                        var value = account.GetValue(valueName)?.ToString();
                        if (!string.IsNullOrWhiteSpace(value)) return true;
                    }
                }
            }
        }
        catch { }

        var oneDrive = Environment.GetEnvironmentVariable("OneDrive");
        return !string.IsNullOrWhiteSpace(oneDrive) && Directory.Exists(oneDrive);
    }

    private static IEnumerable<string> KnownInstallPaths()
    {
        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        var windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
        if (!string.IsNullOrWhiteSpace(local))
        {
            yield return Path.Combine(local, "Microsoft", "OneDrive", "OneDrive.exe");
            yield return Path.Combine(local, "Microsoft", "OneDrive", "Update", "OneDriveSetup.exe");
        }
        if (!string.IsNullOrWhiteSpace(windows))
        {
            yield return Path.Combine(windows, "System32", "OneDriveSetup.exe");
            yield return Path.Combine(windows, "SysWOW64", "OneDriveSetup.exe");
        }
    }
}
''')

# ---- Elevated helper: fixed restore-point and OneDrive operations only. ----
helper=root/'src'/'MerzoOptimizer.ElevatedHelper'/'Program.cs'
s=read(helper)
s=replace_once(s,
'''            ElevatedOperationKind.NetworkRepair => await ExecuteNetworkRepairAsync(\n                Require(request.NetworkAction, "Network repair action missing.")).ConfigureAwait(false),\n\n            _ => throw new NotSupportedException($"Unsupported elevated operation: {request.Kind}")''',
'''            ElevatedOperationKind.NetworkRepair => await ExecuteNetworkRepairAsync(\n                Require(request.NetworkAction, "Network repair action missing.")).ConfigureAwait(false),\n\n            ElevatedOperationKind.CreateSystemRestorePoint => await CreateSystemRestorePointAsync(request.DisplayName).ConfigureAwait(false),\n\n            ElevatedOperationKind.UninstallOneDrive => await UninstallOneDriveAsync().ConfigureAwait(false),\n\n            _ => throw new NotSupportedException($"Unsupported elevated operation: {request.Kind}")''',
'helper operation switch')
anchor='''    private static async Task<NetworkRepairResult> ExecuteNetworkRepairAsync(string action)\n'''
methods=r'''    private static async Task<object> CreateSystemRestorePointAsync(string? rawDescription)
    {
        var description = (rawDescription ?? string.Empty).Trim();
        if (!description.StartsWith("Merzo Windows Optimizer", StringComparison.Ordinal) || description.Length > 96 ||
            description.Any(ch => !(char.IsLetterOrDigit(ch) || char.IsWhiteSpace(ch) || ch is '-' or '_' or '.' or '(' or ')')))
            throw new InvalidDataException("System Restore description failed the allow-list.");

        var drive = Path.GetPathRoot(Environment.SystemDirectory) ?? @"C:\";
        var psDescription = description.Replace("'", "''", StringComparison.Ordinal);
        var psDrive = drive.Replace("'", "''", StringComparison.Ordinal);
        var script = string.Join(Environment.NewLine, new[]
        {
            "$ErrorActionPreference='Stop'",
            "$recent=Get-ComputerRestorePoint -ErrorAction SilentlyContinue | Where-Object {$_.Description -like 'Merzo Windows Optimizer*'} | Sort-Object SequenceNumber -Descending | Select-Object -First 1",
            "if($recent){ try { $dt=[Management.ManagementDateTimeConverter]::ToDateTime([string]$recent.CreationTime); if($dt -gt (Get-Date).AddHours(-24)){ Write-Output ('REUSED|' + $recent.SequenceNumber); exit 0 } } catch {} }",
            $"Enable-ComputerRestore -Drive '{psDrive}' -ErrorAction Stop",
            $"Checkpoint-Computer -Description '{psDescription}' -RestorePointType MODIFY_SETTINGS -ErrorAction Stop",
            "Write-Output 'CREATED'"
        });
        var output = await RunFixedPowerShellAsync(script, TimeSpan.FromSeconds(120)).ConfigureAwait(false);
        var reused = output.Contains("REUSED|", StringComparison.OrdinalIgnoreCase);
        var created = output.Contains("CREATED", StringComparison.OrdinalIgnoreCase);
        if (!reused && !created)
            throw new InvalidOperationException("Windows не подтвердила создание или безопасное переиспользование точки восстановления Merzo.");
        return new { ready = true, reused, created, message = reused ? "Использована недавняя точка восстановления Merzo." : "Создана новая точка восстановления Windows." };
    }

    private static async Task<object> UninstallOneDriveAsync()
    {
        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        var windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
        var candidates = new List<string>();
        if (!string.IsNullOrWhiteSpace(local)) candidates.Add(Path.Combine(local, "Microsoft", "OneDrive", "Update", "OneDriveSetup.exe"));
        if (!string.IsNullOrWhiteSpace(windows))
        {
            candidates.Add(Path.Combine(windows, "SysWOW64", "OneDriveSetup.exe"));
            candidates.Add(Path.Combine(windows, "System32", "OneDriveSetup.exe"));
        }
        var setup = candidates.FirstOrDefault(File.Exists);
        if (setup is null)
            return new { uninstalled = false, message = "OneDriveSetup.exe не найден в разрешённых штатных путях; пользовательские файлы не затронуты." };

        var full = Path.GetFullPath(setup);
        if (!candidates.Select(Path.GetFullPath).Contains(full, StringComparer.OrdinalIgnoreCase) || !Path.GetFileName(full).Equals("OneDriveSetup.exe", StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("OneDrive uninstaller path failed the allow-list.");

        var psi = new ProcessStartInfo
        {
            FileName = full,
            Arguments = "/uninstall",
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        using var process = Process.Start(psi) ?? throw new InvalidOperationException("Не удалось запустить штатный OneDriveSetup.exe.");
        var outputTask = process.StandardOutput.ReadToEndAsync();
        var errorTask = process.StandardError.ReadToEndAsync();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(120));
        try { await process.WaitForExitAsync(timeout.Token).ConfigureAwait(false); }
        catch (OperationCanceledException)
        {
            try { process.Kill(entireProcessTree: true); } catch { }
            throw new TimeoutException("OneDrive uninstall превысил 120 секунд.");
        }
        var output = (await outputTask.ConfigureAwait(false)).Trim();
        var error = (await errorTask.ConfigureAwait(false)).Trim();
        if (process.ExitCode != 0)
            throw new InvalidOperationException($"OneDriveSetup /uninstall завершился с кодом {process.ExitCode}: {(string.IsNullOrWhiteSpace(error) ? output : error)}");
        return new { uninstalled = true, message = "Приложение OneDrive удалено штатным OneDriveSetup. Папки и файлы пользователя Merzo не удалял." };
    }

    private static async Task<string> RunFixedPowerShellAsync(string script, TimeSpan timeoutValue)
    {
        var encoded = Convert.ToBase64String(Encoding.Unicode.GetBytes(script));
        var psi = new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = $"-NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand {encoded}",
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8
        };
        using var process = Process.Start(psi) ?? throw new InvalidOperationException("Не удалось запустить фиксированную системную операцию PowerShell.");
        var outputTask = process.StandardOutput.ReadToEndAsync();
        var errorTask = process.StandardError.ReadToEndAsync();
        using var timeout = new CancellationTokenSource(timeoutValue);
        try { await process.WaitForExitAsync(timeout.Token).ConfigureAwait(false); }
        catch (OperationCanceledException)
        {
            try { process.Kill(entireProcessTree: true); } catch { }
            throw new TimeoutException("Системная операция восстановления превысила безопасный таймаут.");
        }
        var output = await outputTask.ConfigureAwait(false);
        var error = await errorTask.ConfigureAwait(false);
        if (process.ExitCode != 0)
            throw new InvalidOperationException($"Windows PowerShell вернула код {process.ExitCode}: {error.Trim()}");
        return output.Trim();
    }

'''
if s.count(anchor)!=1: raise SystemExit(f'R49 helper method anchor count={s.count(anchor)}')
s=s.replace(anchor,methods+anchor,1)
write(helper,s)

(root/'R49_RECOVERY_ONEDRIVE_INFRA.marker').write_text('R49 recovery + OneDrive fixed operations\n',encoding='utf-8')
print('R49 recovery/OneDrive infrastructure OK')
