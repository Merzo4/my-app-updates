from pathlib import Path
import os,re

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# R54.2: OneDrive is an optional destructive optimization. A stale
# OneDriveSetup.exe must not be treated as an installed client, and a failed
# uninstall must never roll back the whole LIGHT/GAME package.

one=root/'src'/'MerzoOptimizer.Windows'/'OneDrive'/'WindowsOneDriveOptimizationService.cs'
old=read(one)
if 'KnownInstallPaths().Any(File.Exists)' not in old:
    raise SystemExit('R54.2 expected legacy OneDrive install detection missing')

service=r'''using System.Diagnostics;
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
        var running = IsRunning();
        var installed = running || KnownClientPaths().Any(File.Exists);
        var configured = HasConfiguredAccount();
        var summary = !installed
            ? "OneDrive клиент не установлен. Остаточный OneDriveSetup.exe сам по себе установкой не считается."
            : configured
                ? "OneDrive установлен и найден настроенный аккаунт/папка синхронизации."
                : "OneDrive установлен, но настроенный аккаунт синхронизации не обнаружен.";
        return Task.FromResult(new OneDriveStatus(installed, configured, running, summary));
    }

    public async Task<OneDriveOperationResult> UninstallAsync(CancellationToken cancellationToken = default)
    {
        var before = await InspectAsync(cancellationToken).ConfigureAwait(false);
        if (!before.Installed)
            return new OneDriveOperationResult(true, false, "OneDrive уже отсутствует; uninstall пропущен.");

        try
        {
            var result = await _broker.ExecuteAsync<JsonElement>(new ElevatedOperationRequest
            {
                RequestId = Guid.NewGuid().ToString("N"),
                Kind = ElevatedOperationKind.UninstallOneDrive
            }, cancellationToken).ConfigureAwait(false);

            var changed = result.TryGetProperty("uninstalled", out var changedEl) && changedEl.ValueKind == JsonValueKind.True;
            var attempted = result.TryGetProperty("attempted", out var attemptedEl) && attemptedEl.ValueKind == JsonValueKind.True;
            var message = result.TryGetProperty("message", out var msgEl)
                ? msgEl.GetString() ?? "OneDrive uninstall completed."
                : "OneDrive uninstall completed.";

            var after = await InspectAsync(cancellationToken).ConfigureAwait(false);
            if (!after.Installed)
                return new OneDriveOperationResult(true, changed || attempted, message);

            // OneDrive removal is optional. Preserve the rest of the package and
            // report a warning instead of causing global rollback.
            return new OneDriveOperationResult(true, false,
                "OneDrive не был удалён и оставлен без дальнейших действий. Остальная сборка может продолжаться. " + message);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            return new OneDriveOperationResult(true, false,
                "OneDrive uninstall пропущен из-за ошибки: " + ex.Message + ". Остальная сборка продолжена; пользовательские файлы не затрагивались.");
        }
    }

    private static bool IsRunning()
    {
        Process[] processes = Array.Empty<Process>();
        try
        {
            processes = Process.GetProcessesByName("OneDrive");
            return processes.Length > 0;
        }
        catch { return false; }
        finally
        {
            foreach (var p in processes) try { p.Dispose(); } catch { }
        }
    }

    private static IEnumerable<string> KnownClientPaths()
    {
        var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        if (!string.IsNullOrWhiteSpace(local))
            yield return Path.Combine(local, "Microsoft", "OneDrive", "OneDrive.exe");

        var pf = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
        if (!string.IsNullOrWhiteSpace(pf))
            yield return Path.Combine(pf, "Microsoft OneDrive", "OneDrive.exe");

        var pfx86 = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);
        if (!string.IsNullOrWhiteSpace(pfx86))
            yield return Path.Combine(pfx86, "Microsoft OneDrive", "OneDrive.exe");
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
                    var folder = account?.GetValue("UserFolder") as string;
                    if (!string.IsNullOrWhiteSpace(folder) && Directory.Exists(folder)) return true;
                }
            }
        }
        catch { }

        var oneDrive = Environment.GetEnvironmentVariable("OneDrive");
        return !string.IsNullOrWhiteSpace(oneDrive) && Directory.Exists(oneDrive);
    }
}
'''
write(one,service)

# Elevated helper: pick only allow-listed OneDriveSetup locations, prefer the
# installed Program Files client, kill only OneDrive.exe, then verify the actual
# client state. Non-zero setup exit alone is not a package-fatal condition.
helper=root/'src'/'MerzoOptimizer.ElevatedHelper'/'Program.cs'
h=read(helper)
start=h.find('    private static async Task<object> UninstallOneDriveAsync()')
if start<0: raise SystemExit('R54.2 helper OneDrive method start missing')
end=h.find('    private static async Task<object> GamingDebloatAsync',start)
if end<0: end=h.find('    private static async Task<string> RunFixedPowerShellAsync',start)
if end<0: raise SystemExit('R54.2 helper OneDrive method end missing')
new_helper=r'''    private static async Task<object> UninstallOneDriveAsync()
    {
        static IEnumerable<string> ClientPaths()
        {
            var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (!string.IsNullOrWhiteSpace(local)) yield return Path.Combine(local, "Microsoft", "OneDrive", "OneDrive.exe");
            var pf = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
            if (!string.IsNullOrWhiteSpace(pf)) yield return Path.Combine(pf, "Microsoft OneDrive", "OneDrive.exe");
            var pfx86 = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);
            if (!string.IsNullOrWhiteSpace(pfx86)) yield return Path.Combine(pfx86, "Microsoft OneDrive", "OneDrive.exe");
        }

        static bool Running()
        {
            Process[] ps = Array.Empty<Process>();
            try { ps = Process.GetProcessesByName("OneDrive"); return ps.Length > 0; }
            catch { return false; }
            finally { foreach (var p in ps) try { p.Dispose(); } catch { } }
        }

        static bool Installed() => Running() || ClientPaths().Any(File.Exists);

        static IEnumerable<string> SetupCandidates()
        {
            foreach (var baseDir in new[]
            {
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86)
            })
            {
                if (string.IsNullOrWhiteSpace(baseDir)) continue;
                var root = Path.Combine(baseDir, "Microsoft OneDrive");
                yield return Path.Combine(root, "OneDriveSetup.exe");
                if (Directory.Exists(root))
                {
                    IEnumerable<string> dirs;
                    try { dirs = Directory.EnumerateDirectories(root).OrderByDescending(x => Path.GetFileName(x), StringComparer.OrdinalIgnoreCase).ToArray(); }
                    catch { dirs = Array.Empty<string>(); }
                    foreach (var dir in dirs) yield return Path.Combine(dir, "OneDriveSetup.exe");
                }
            }

            var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (!string.IsNullOrWhiteSpace(local))
                yield return Path.Combine(local, "Microsoft", "OneDrive", "Update", "OneDriveSetup.exe");

            var windows = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
            if (!string.IsNullOrWhiteSpace(windows))
            {
                if (Environment.Is64BitOperatingSystem) yield return Path.Combine(windows, "SysWOW64", "OneDriveSetup.exe");
                yield return Path.Combine(windows, "System32", "OneDriveSetup.exe");
            }
        }

        if (!Installed())
            return new { uninstalled = false, attempted = false, exitCode = 0, message = "OneDrive клиент уже отсутствует; setup leftovers ignored." };

        Process[] running = Array.Empty<Process>();
        try
        {
            running = Process.GetProcessesByName("OneDrive");
            foreach (var p in running)
            {
                try { p.Kill(entireProcessTree: true); p.WaitForExit(5000); } catch { }
            }
        }
        finally { foreach (var p in running) try { p.Dispose(); } catch { } }

        var setup = SetupCandidates().FirstOrDefault(File.Exists);
        if (string.IsNullOrWhiteSpace(setup))
            return new { uninstalled = false, attempted = false, exitCode = -1, message = "OneDrive установлен, но allow-listed OneDriveSetup.exe не найден. Шаг пропущен." };

        var psi = new ProcessStartInfo
        {
            FileName = setup,
            Arguments = "/uninstall",
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        using var process = Process.Start(psi) ?? throw new InvalidOperationException("Не удалось запустить OneDriveSetup.exe.");
        var stdoutTask = process.StandardOutput.ReadToEndAsync();
        var stderrTask = process.StandardError.ReadToEndAsync();
        using var timeout = new CancellationTokenSource(TimeSpan.FromMinutes(2));
        try { await process.WaitForExitAsync(timeout.Token).ConfigureAwait(false); }
        catch (OperationCanceledException)
        {
            try { process.Kill(entireProcessTree: true); } catch { }
            return new { uninstalled = false, attempted = true, exitCode = -2, message = "OneDriveSetup /uninstall превысил таймаут; OneDrive оставлен, пакет продолжен." };
        }

        var stdout = (await stdoutTask.ConfigureAwait(false)).Trim();
        var stderr = (await stderrTask.ConfigureAwait(false)).Trim();
        await Task.Delay(1500).ConfigureAwait(false);
        var remains = Installed();
        if (!remains)
            return new { uninstalled = true, attempted = true, exitCode = process.ExitCode, message = $"OneDrive удалён; exit={process.ExitCode}. Пользовательские папки не удалялись." };

        var details = string.Join(" ", new[] { stderr, stdout }.Where(x => !string.IsNullOrWhiteSpace(x))).Trim();
        return new
        {
            uninstalled = false,
            attempted = true,
            exitCode = process.ExitCode,
            message = $"OneDriveSetup /uninstall не удалил клиент (exit={process.ExitCode}). OneDrive оставлен; пакет продолжен." + (details.Length == 0 ? string.Empty : " " + details)
        };
    }

'''
h=h[:start]+new_helper+h[end:]
write(helper,h)

# Profile safety: unconfigured OneDrive is no longer silently removed. Ask the
# user explicitly. Cancellation cancels the package; No keeps policy/startup
# tweaks only.
vm=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
v=read(vm)
legacy='''                else if (oneDriveStatus.Installed && !oneDriveStatus.Configured)
                {
                    oneDriveUninstallRequested = true;
                }'''
replacement='''                else if (oneDriveStatus.Installed && !oneDriveStatus.Configured)
                {
                    var removeUnusedOneDrive = global::MerzoOptimizer.App.MerzoDialog.Show(
                        "OneDrive установлен, но настроенный аккаунт не обнаружен.\\n\\nДа — удалить только приложение OneDrive после Recovery Package.\\nНет — оставить приложение и применить только обратимые настройки.\\nОтмена — не запускать сборку.\\n\\nПользовательские папки и файлы Merzo не удаляет.",
                        "Merzo — OneDrive не настроен",
                        MessageBoxButton.YesNoCancel,
                        MessageBoxImage.Warning);
                    if (removeUnusedOneDrive == MessageBoxResult.Cancel) return;
                    oneDriveUninstallRequested = removeUnusedOneDrive == MessageBoxResult.Yes;
                }'''
if v.count(legacy)!=1:
    raise SystemExit(f'R54.2 unconfigured OneDrive auto-remove anchor count={v.count(legacy)}')
v=v.replace(legacy,replacement,1)

# Optional OneDrive removal can never abort and roll back the whole package.
old_block='''                var result = await _dispatcher.RunAsync("OneDrive uninstall", token => _oneDriveService.UninstallAsync(token), _lifetimeCts.Token);
                if (!result.Success) throw new InvalidOperationException(result.Message);
                done++;
                DeepScanSteps[DeepScanSteps.Count - 1] = result.Changed
                    ? $"✓ {done}/{total} · OneDrive удалён штатным installer · файлы пользователя не удалялись"
                    : $"✓ {done}/{total} · OneDrive уже отсутствует / uninstall не потребовался";'''
new_block='''                try
                {
                    var result = await _dispatcher.RunAsync("OneDrive uninstall", token => _oneDriveService.UninstallAsync(token), _lifetimeCts.Token);
                    done++;
                    DeepScanSteps[DeepScanSteps.Count - 1] = result.Changed
                        ? $"✓ {done}/{total} · OneDrive удалён штатным installer · файлы пользователя не удалялись"
                        : $"⚠ {done}/{total} · OneDrive оставлен / uninstall не потребовался · {result.Message}";
                }
                catch (Exception ex) when (ex is not OperationCanceledException)
                {
                    done++;
                    DeepScanSteps[DeepScanSteps.Count - 1] = $"⚠ {done}/{total} · OneDrive пропущен: {ex.Message}";
                    Stage2StatusText = "OneDrive не удалён; необязательный шаг пропущен, пакет продолжен.";
                }'''
if v.count(old_block)!=1:
    raise SystemExit(f'R54.2 OneDrive package-fatal block anchor count={v.count(old_block)}')
v=v.replace(old_block,new_block,1)
write(vm,v)

# Final source contract: stale setup is not install evidence, non-zero setup
# code is not thrown, and profile execution catches optional OneDrive failures.
svc=read(one); hp=read(helper); mv=read(vm)
for bad in [
    'KnownInstallPaths().Any(File.Exists)',
    'if (process.ExitCode != 0)\n            throw',
    'oneDriveUninstallRequested = true;\n                }'
]:
    if bad in (svc+'\n'+hp):
        raise SystemExit('R54.2 legacy OneDrive fatal contract remains: '+bad)
if 'KnownClientPaths().Any(File.Exists)' not in svc:
    raise SystemExit('R54.2 client-only install detection missing')
if 'setup leftovers ignored' not in hp or 'OneDrive оставлен; пакет продолжен' not in hp:
    raise SystemExit('R54.2 helper post-condition/nonfatal contract missing')
if 'OneDrive не удалён; необязательный шаг пропущен, пакет продолжен.' not in mv:
    raise SystemExit('R54.2 VM nonfatal OneDrive contract missing')
if 'MessageBoxButton.YesNoCancel' not in mv or 'OneDrive не настроен' not in mv:
    raise SystemExit('R54.2 explicit unconfigured OneDrive choice missing')

(root/'R54_2_ONEDRIVE_RESILIENCE.marker').write_text(
    '0.1.54.2: client-only OneDrive detection; explicit unconfigured removal choice; uninstall best-effort/nonfatal; no user files touched\n',
    encoding='utf-8')
print('R54.2 OneDrive resilience: OK')
