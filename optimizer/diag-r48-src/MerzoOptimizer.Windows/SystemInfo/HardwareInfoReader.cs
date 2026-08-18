using System.Runtime.InteropServices;
using Microsoft.Win32;
using MerzoOptimizer.Core.Models;

namespace MerzoOptimizer.Windows.SystemInfo;

internal static class HardwareInfoReader
{
    public static async Task<CpuSnapshot> ReadCpuAsync(CancellationToken cancellationToken)
    {
        var name = "Unknown CPU";
        try
        {
            using var key = global::Microsoft.Win32.Registry.LocalMachine.OpenSubKey(@"HARDWARE\DESCRIPTION\System\CentralProcessor\0");
            name = (key?.GetValue("ProcessorNameString") as string)?.Trim() ?? name;
        }
        catch
        {
            // Hardware identification is best-effort only.
        }

        var usage = await SampleCpuUsageAsync(cancellationToken).ConfigureAwait(false);
        return new CpuSnapshot(name, Environment.ProcessorCount, usage);
    }

    public static IReadOnlyList<GpuSnapshot> ReadGpus()
    {
        var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        try
        {
            using var root = global::Microsoft.Win32.Registry.LocalMachine.OpenSubKey(@"SYSTEM\CurrentControlSet\Control\Video");
            if (root is null)
                return [];

            foreach (var adapterKeyName in root.GetSubKeyNames())
            {
                using var adapterKey = root.OpenSubKey(adapterKeyName);
                if (adapterKey is null)
                    continue;

                foreach (var displayKeyName in adapterKey.GetSubKeyNames())
                {
                    if (!displayKeyName.StartsWith("000", StringComparison.OrdinalIgnoreCase))
                        continue;

                    using var displayKey = adapterKey.OpenSubKey(displayKeyName);
                    var driverDesc = (displayKey?.GetValue("DriverDesc") as string)?.Trim();
                    if (!string.IsNullOrWhiteSpace(driverDesc))
                        names.Add(driverDesc);
                }
            }
        }
        catch
        {
            // GPU discovery is best-effort only.
        }

        return names.Select(static name => new GpuSnapshot(name)).ToArray();
    }

    private static async Task<double> SampleCpuUsageAsync(CancellationToken cancellationToken)
    {
        if (!GetSystemTimes(out var idleStart, out var kernelStart, out var userStart))
            return 0;

        await Task.Delay(250, cancellationToken).ConfigureAwait(false);

        if (!GetSystemTimes(out var idleEnd, out var kernelEnd, out var userEnd))
            return 0;

        var idle = ToUInt64(idleEnd) - ToUInt64(idleStart);
        var kernel = ToUInt64(kernelEnd) - ToUInt64(kernelStart);
        var user = ToUInt64(userEnd) - ToUInt64(userStart);
        var total = kernel + user;

        if (total == 0)
            return 0;

        var busy = total > idle ? total - idle : 0;
        return Math.Clamp(busy * 100d / total, 0d, 100d);
    }

    private static ulong ToUInt64(FILETIME value) =>
        ((ulong)value.dwHighDateTime << 32) | value.dwLowDateTime;

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetSystemTimes(
        out FILETIME lpIdleTime,
        out FILETIME lpKernelTime,
        out FILETIME lpUserTime);

    [StructLayout(LayoutKind.Sequential)]
    private struct FILETIME
    {
        public uint dwLowDateTime;
        public uint dwHighDateTime;
    }
}
