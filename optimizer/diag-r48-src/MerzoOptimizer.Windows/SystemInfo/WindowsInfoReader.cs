using Microsoft.Win32;
using System.Runtime.InteropServices;
using MerzoOptimizer.Core.Models;

namespace MerzoOptimizer.Windows.SystemInfo;

internal static class WindowsInfoReader
{
    private const string CurrentVersionKey = @"SOFTWARE\Microsoft\Windows NT\CurrentVersion";

    public static WindowsInfoSnapshot Read()
    {
        using var key = global::Microsoft.Win32.Registry.LocalMachine.OpenSubKey(CurrentVersionKey);

        var productName = GetString(key, "ProductName", "Windows");
        var editionId = GetString(key, "EditionID", "Unknown");
        var displayVersion = GetString(key, "DisplayVersion",
            GetString(key, "ReleaseId", "Unknown"));

        var currentBuild = GetString(key, "CurrentBuildNumber",
            Environment.OSVersion.Version.Build.ToString());

        var ubr = key?.GetValue("UBR")?.ToString();
        var build = string.IsNullOrWhiteSpace(ubr) ? currentBuild : $"{currentBuild}.{ubr}";

        return new WindowsInfoSnapshot(
            productName,
            editionId,
            displayVersion,
            build,
            RuntimeInformation.OSArchitecture.ToString());
    }

    private static string GetString(RegistryKey? key, string valueName, string fallback)
    {
        var value = key?.GetValue(valueName)?.ToString();
        return string.IsNullOrWhiteSpace(value) ? fallback : value;
    }
}
