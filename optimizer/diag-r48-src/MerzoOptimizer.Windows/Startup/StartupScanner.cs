using Microsoft.Win32;
using MerzoOptimizer.Core.Models;

namespace MerzoOptimizer.Windows.Startup;

internal static class StartupScanner
{
    private const string RunKey = @"Software\Microsoft\Windows\CurrentVersion\Run";

    public static IReadOnlyList<StartupItemSnapshot> Scan()
    {
        var items = new List<StartupItemSnapshot>();

        ReadRegistry(items, global::Microsoft.Win32.Registry.CurrentUser, RunKey, "HKCU Run", "User");
        ReadRegistry(items, global::Microsoft.Win32.Registry.LocalMachine, RunKey, "HKLM Run", "Machine");

        ReadFolder(items, Environment.GetFolderPath(Environment.SpecialFolder.Startup), "Startup Folder", "User");
        ReadFolder(items, Environment.GetFolderPath(Environment.SpecialFolder.CommonStartup), "Common Startup Folder", "Machine");

        return items
            .OrderBy(item => item.Name, StringComparer.OrdinalIgnoreCase)
            .ThenBy(item => item.Source, StringComparer.OrdinalIgnoreCase)
            .ToArray();
    }

    private static void ReadRegistry(
        ICollection<StartupItemSnapshot> items,
        RegistryKey root,
        string path,
        string source,
        string scope)
    {
        try
        {
            using var key = root.OpenSubKey(path);
            if (key is null) return;

            foreach (var valueName in key.GetValueNames())
            {
                var command = key.GetValue(valueName)?.ToString() ?? string.Empty;
                items.Add(new StartupItemSnapshot(
                    string.IsNullOrWhiteSpace(valueName) ? "(Default)" : valueName,
                    command,
                    source,
                    scope));
            }
        }
        catch
        {
            // Audit is best-effort. A denied or damaged key must not abort the whole scan.
        }
    }

    private static void ReadFolder(
        ICollection<StartupItemSnapshot> items,
        string folder,
        string source,
        string scope)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(folder) || !Directory.Exists(folder))
                return;

            foreach (var file in Directory.EnumerateFiles(folder))
            {
                if (string.Equals(Path.GetFileName(file), "desktop.ini", StringComparison.OrdinalIgnoreCase))
                    continue;

                items.Add(new StartupItemSnapshot(
                    Path.GetFileNameWithoutExtension(file),
                    file,
                    source,
                    scope));
            }
        }
        catch
        {
            // Best-effort audit.
        }
    }
}
